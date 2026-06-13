import asyncio
import json
import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class SPAStaticFiles(StaticFiles):
    """Serve the built SPA, falling back to index.html for unknown paths so
    client-side routes (e.g. /app) survive deep links and refreshes instead of
    404ing. /api/* paths are left to FastAPI's own 404."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and not path.startswith("api"):
            return await super().get_response("index.html", scope)
        return response

from app import billing
from app import cards as cards_mod
from app import config
from app import db
from app import graph as agent_graph
from app import models as M
from app import monitors
from app import ratelimit
from app import tools as T
from app import usage
from app.auth import current_context
from app.memory import memory, conversation_id_for
from app.schemas import ActionCardCreate, ActionCardPatch
from app.tenancy import customer_scope

# Per-key short-window burst caps (key = org_id, or client IP in demo mode).
RATE_LIMITS = {"run": (5, 60), "chat": (30, 60), "research": (20, 60), "ui": (20, 60)}


def _enforce(ctx: dict, request: Request, kind: str) -> None:
    """Kill-switch -> rate limit -> monthly plan quota. Raises HTTPException when blocked.
    A no-op for demo mode on quotas (org_id is None); rate limit still applies, keyed by IP."""
    org_id = ctx.get("org_id")
    if org_id and usage.org_disabled(org_id):
        raise HTTPException(status_code=403, detail="This workspace is disabled. Contact support.")
    key = f"{kind}:{org_id or (request.client.host if request.client else 'anon')}"
    limit, window = RATE_LIMITS.get(kind, (30, 60))
    if not ratelimit.allow(key, limit, window):
        raise HTTPException(status_code=429, detail="Too many requests — slow down a moment.")
    q = usage.quota(org_id, kind)
    if not q["allowed"]:
        raise HTTPException(status_code=429, detail={
            "error": "quota_exceeded", "kind": kind, "used": q["used"],
            "limit": q["limit"], "plan": q["plan"],
            "message": f"Monthly {kind} limit reached ({q['used']}/{q['limit']} on {q['plan']}). Upgrade to continue.",
        })

# Error tracking — enabled only when SENTRY_DSN is set.
if config.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=config.SENTRY_DSN, traces_sample_rate=0.1, send_default_pii=False)
    except Exception:
        pass

app = FastAPI(title="CMO Cofounder")

# CORS: lock to ALLOWED_ORIGINS in prod; permissive "*" only when unset (local/demo).
_origins = [o.strip() for o in config.ALLOWED_ORIGINS.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-XSS-Protection", "0")
    return resp

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


@app.on_event("startup")
async def _startup():
    # Addendum 1: the graph runs monitors, the scheduler fires them, monitors.py bridges the two.
    monitors.set_runner(agent_graph.run_monitor)
    monitors.set_feeder(agent_graph.feed_all_cards)  # Action Board daily card feeder (gated by config)
    monitors.start_scheduler()


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "cmo-cofounder", "phase": 1}


@app.get("/api/memory/{slug}")
async def memory_view(slug: str, ctx: dict = Depends(current_context)):
    """Addendum 5: the company's durable Synap brain, for the Memory tab."""
    scope = customer_scope(ctx.get("org_id"), slug)
    full = await memory.recall_full(scope, [slug, "objective", "adjacencies", "channels", "monitors"])
    full["conversation_id"] = conversation_id_for(scope)
    return full


@app.get("/api/monitors/{slug}")
async def monitors_view(slug: str, ctx: dict = Depends(current_context)):
    org_id = ctx.get("org_id")
    plan = monitors.get_plan(org_id, slug)
    return {"jobs": plan.get("jobs", []), "updated_at": plan.get("updated_at", ""),
            "changelog": monitors.get_changelog(org_id, slug)}


@app.post("/api/monitors/{slug}/run")
async def monitors_run(slug: str, ctx: dict = Depends(current_context)):
    """Manually fire every monitor now (demo-safe path); returns the deltas produced."""
    org_id = ctx.get("org_id")
    entries = await monitors.run_now(org_id, slug)
    db.record_usage(org_id, "monitor", len(entries), {"slug": slug})
    return {"ran": len(entries), "entries": entries, "changelog": monitors.get_changelog(org_id, slug)}


@app.get("/api/changelog/{slug}")
async def changelog_view(slug: str, ctx: dict = Depends(current_context)):
    return {"changelog": monitors.get_changelog(ctx.get("org_id"), slug)}


@app.get("/api/runs")
async def runs_view(ctx: dict = Depends(current_context)):
    """Historical analyses for the caller's workspace (empty in local/demo mode)."""
    return {"runs": db.list_runs(ctx.get("org_id"))}


@app.get("/api/usage")
async def usage_view(ctx: dict = Depends(current_context)):
    """Current-month usage vs plan limits, for the caller's workspace."""
    org_id = ctx.get("org_id")
    return {"plan": usage.plan_for(org_id) if org_id else "demo", "quotas": usage.all_quotas(org_id)}


# --- integrations (per-org connected accounts) ----------------------------
@app.get("/api/integrations")
async def integrations_list(ctx: dict = Depends(current_context)):
    return {"integrations": db.list_integrations(ctx.get("org_id"))}


class IntegrationBody(BaseModel):
    provider: str
    connection_id: str | None = None
    status: str = "connected"
    metadata: dict = {}


@app.post("/api/integrations")
async def integrations_upsert(body: IntegrationBody, ctx: dict = Depends(current_context)):
    org_id = ctx.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="no workspace")
    db.upsert_integration(org_id, body.provider, body.connection_id, body.status, body.metadata)
    return {"ok": True}


@app.delete("/api/integrations/{provider}")
async def integrations_delete(provider: str, ctx: dict = Depends(current_context)):
    db.delete_integration(ctx.get("org_id"), provider)
    return {"ok": True}


# --- action board (cards = specific places to post) -----------------------
@app.get("/api/cards")
async def cards_list(slug: str | None = None, ctx: dict = Depends(current_context)):
    """The board for a company. Lazily seeds from the latest completed run the first
    time it's viewed, so an existing analysis fills the board without a re-run."""
    org_id = ctx.get("org_id")
    if org_id and slug and db.count_cards(org_id, slug) == 0:
        run = db.latest_run(org_id, slug)
        seeded = cards_mod.cards_from_summary(slug, run.get("id"), run.get("summary") or {})
        if seeded:
            db.bulk_create_cards(org_id, seeded)
    return {"cards": db.list_cards(org_id, slug), "platforms": cards_mod.PLATFORMS}


@app.post("/api/cards")
async def cards_create(body: ActionCardCreate, ctx: dict = Depends(current_context)):
    """Create a card — manual add, or pushed by the CLI build-in-public skill (source=cli)."""
    org_id = ctx.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="no workspace")
    card = body.model_dump()
    if not card.get("platform") or card["platform"] == "other":
        card["platform"] = cards_mod.classify_platform(card.get("target_url"), card.get("title"))
    created = db.create_card(org_id, card)
    return {"card": created}


class GenerateBody(BaseModel):
    slug: str
    platforms: list[str] | None = None
    per_platform: int = 2


@app.post("/api/cards/generate")
async def cards_generate(body: GenerateBody, request: Request, ctx: dict = Depends(current_context)):
    """The feeder, on demand: find fresh threads to engage and draft platform-voiced replies,
    queued as cards. Counts as a run-class action for rate-limit/quota."""
    _enforce(ctx, request, "run")
    org_id = ctx.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="no workspace")
    created = await agent_graph.generate_cards(org_id, body.slug, body.platforms, body.per_platform)
    db.record_usage(org_id, "run", 1, {"generate_cards": body.slug})
    return {"created": len(created), "cards": created}


@app.patch("/api/cards/{card_id}")
async def cards_patch(card_id: str, body: ActionCardPatch, ctx: dict = Depends(current_context)):
    org_id = ctx.get("org_id")
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if patch.get("state") == "posted" and "posted_at" not in patch:
        patch["posted_at"] = db._now()  # stamp when a card is marked shipped
    updated = db.update_card(org_id, card_id, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="card not found")
    return {"card": updated}


@app.delete("/api/cards/{card_id}")
async def cards_delete(card_id: str, ctx: dict = Depends(current_context)):
    db.delete_card(ctx.get("org_id"), card_id)
    return {"ok": True}


# --- account / workspace deletion (data-deletion path) --------------------
@app.delete("/api/workspace")
async def delete_workspace(ctx: dict = Depends(current_context)):
    org_id, uid = ctx.get("org_id"), ctx.get("user_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="no workspace")
    if org_id not in db.owned_org_ids(uid):
        raise HTTPException(status_code=403, detail="only an owner can delete the workspace")
    db.delete_org(org_id)
    return {"deleted": org_id}


@app.delete("/api/account")
async def delete_account(ctx: dict = Depends(current_context)):
    uid = ctx.get("user_id")
    if not uid:
        raise HTTPException(status_code=400, detail="not authenticated")
    for oid in db.owned_org_ids(uid):  # cascade-delete workspaces this user owns
        db.delete_org(oid)
    return {"deleted": db.delete_user(uid)}


# --- Stripe billing -------------------------------------------------------
@app.post("/api/billing/checkout")
async def billing_checkout(ctx: dict = Depends(current_context)):
    if not billing.enabled():
        raise HTTPException(status_code=503, detail="billing not configured")
    org_id = ctx.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="no workspace")
    url = billing.create_checkout(
        org_id, ctx.get("email"),
        f"{config.APP_BASE_URL}/?billing=success", f"{config.APP_BASE_URL}/?billing=cancel",
    )
    if not url:
        raise HTTPException(status_code=500, detail="could not start checkout (price configured?)")
    return {"url": url}


@app.post("/api/billing/portal")
async def billing_portal(ctx: dict = Depends(current_context)):
    if not billing.enabled():
        raise HTTPException(status_code=503, detail="billing not configured")
    org_id = ctx.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="no workspace")
    url = billing.create_portal(org_id, f"{config.APP_BASE_URL}/?billing=portal")
    if not url:
        raise HTTPException(status_code=400, detail="no billing account yet — subscribe first")
    return {"url": url}


@app.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    """Stripe webhook — signature-verified, source of truth for entitlement. No auth dependency."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        return billing.handle_event(payload, sig)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"webhook error: {e}")


def _sse(ev: dict) -> str:
    return f"event: {ev.get('type', 'message')}\ndata: {json.dumps(ev)}\n\n"


async def _drive_graph(url: str, mode: str, queue: "asyncio.Queue", org_id=None, user_id=None, run_id=None):
    summary: dict = {}

    async def emit(ev):
        if ev.get("type") == "done":
            summary.update(ev.get("data", {}))
        await queue.put(ev)
    try:
        await agent_graph.run(url, mode, emit, org_id=org_id, user_id=user_id, run_id=run_id)
        db.finish_run(run_id, "done", summary=summary)
    except Exception as e:
        db.finish_run(run_id, "error", error=str(e))
        await queue.put({"type": "error", "label": str(e)})
    finally:
        await queue.put(None)  # sentinel


def _cached_events(url: str):
    path = os.path.join(CACHE_DIR, agent_graph.slugify(url) + ".json")
    if not os.path.exists(path):
        path = os.path.join(CACHE_DIR, "resend.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return [{"type": "error", "label": "No cached run available for this URL"}]


@app.get("/api/analyze/stream")
async def analyze_stream(request: Request, url: str, mode: str = "live", ctx: dict = Depends(current_context)):
    org_id, user_id = ctx.get("org_id"), ctx.get("user_id")
    if mode != "cached":
        _enforce(ctx, request, "run")  # cached demo runs are free

    async def gen():
        if mode == "cached":
            for ev in _cached_events(url):
                yield _sse(ev)
                await asyncio.sleep(float(ev.get("_delay", 0.45)))
            return
        slug = agent_graph.slugify(url)
        run_id = db.create_run(org_id, user_id, url, slug, customer_scope(org_id, slug), mode)
        db.record_usage(org_id, "run", 1, {"slug": slug})
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(_drive_graph(url, mode, queue, org_id=org_id, user_id=user_id, run_id=run_id))
        try:
            while True:
                ev = await queue.get()
                if ev is None:
                    break
                yield _sse(ev)
        finally:
            await task

    return StreamingResponse(gen(), media_type="text/event-stream")


class ChatBody(BaseModel):
    url: str
    message: str
    history: list = []


@app.post("/api/chat")
async def chat(body: ChatBody, request: Request, actx: dict = Depends(current_context)):
    _enforce(actx, request, "chat")
    org_id, user_id = actx.get("org_id"), actx.get("user_id")
    slug = agent_graph.slugify(body.url)
    scope = customer_scope(org_id, slug)
    conv = conversation_id_for(scope)
    await memory.record_turn(conv, "user", body.message, scope, user_id=user_id)   # conversational ingest
    ctx = await memory.recall_conversation(conv, scope, body.message, user_id=user_id) or await memory.recall(scope, [body.message])
    system = ("You are the founder's CMO cofounder copilot. Be concrete, brief, and specific to THIS company. "
              "Think adjacencies, wedges, channels and stage — never generic advice.")
    human = (f"Company context from memory:\n{ctx[:1500]}\n\n" if ctx else "") + f"Founder asks: {body.message}"
    reply, name = await M.run_text("chat", system, human, max_tokens=700)
    await memory.record_turn(conv, "assistant", reply, scope, user_id=user_id)      # record the reply turn
    db.record_usage(org_id, "chat", 1, {"slug": slug})
    return {"reply": reply, "model": name}


class ResearchBody(BaseModel):
    url: str
    query: str


@app.post("/api/research")
async def research(body: ResearchBody, request: Request, ctx: dict = Depends(current_context)):
    _enforce(ctx, request, "research")
    findings = await T.exa_search(body.query, num=5)
    block = "\n".join(f"- {f.title} ({f.url}): {f.snippet[:160]}" for f in findings)
    system = ("You are a CMO cofounder. Turn raw research into 3 sharp, non-obvious, actionable takeaways "
              "for the founder — no filler.")
    human = f"Research question: {body.query}\nFindings:\n{block or '(none)'}\n\nReturn 3 concise takeaways."
    takeaways, name = await M.run_text("synthesize", system, human, max_tokens=600)
    db.record_usage(ctx.get("org_id"), "research", 1, {"query": body.query[:120]})
    return {"findings": [f.model_dump() for f in findings], "takeaways": takeaways, "model": name}


OPENUI_SYS = (
    "You are OpenUI, a UI generator. Given a CMO dashboard's data, output ONE self-contained HTML "
    "fragment (inline styles only, dark theme, modern rounded cards, accent purple/cyan) that renders it "
    "beautifully. Output ONLY raw HTML — no markdown fences, no <html>/<head>, no explanation."
)


def _ui_prompt(b) -> str:
    return (
        f"Company: {json.dumps(b.profile)[:800]}\n"
        f"Objective: {json.dumps(b.objective)[:600]}\n"
        f"Strategic moves: {json.dumps(b.opportunities)[:2500]}\n"
        f"Engagement radar: {json.dumps(b.radar)[:1500]}\n\n"
        "Render a bespoke dashboard: a bold objective header, the prioritized strategic moves "
        "(priority + title + why), and an 'engagement radar' section. Self-contained HTML fragment only."
    )


def _extract_html(text: str) -> str:
    t = (text or "").strip()
    if "```" in t:
        parts = t.split("```")
        if len(parts) >= 3:
            body = parts[1]
            if body.lower().startswith("html"):
                body = body[4:]
            return body.strip()
    return t


async def _generate_ui(prompt: str):
    openui_url = os.getenv("OPENUI_URL", "").strip()
    if openui_url:  # genuine OpenUI (OpenAI-compatible /v1/chat/completions)
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(base_url=openui_url.rstrip("/") + "/v1", api_key="openui")
            resp = await client.chat.completions.create(
                model=os.getenv("OPENUI_MODEL", "gpt-4o"),
                messages=[{"role": "system", "content": OPENUI_SYS}, {"role": "user", "content": prompt}],
                max_tokens=2200,
            )
            return _extract_html(resp.choices[0].message.content), "openui"
        except Exception:
            pass
    html, _ = await M.run_text("synthesize", OPENUI_SYS, prompt, max_tokens=2200)
    return _extract_html(html), "model-fallback"


class UIBody(BaseModel):
    profile: dict = {}
    objective: dict = {}
    opportunities: list = []
    radar: list = []


@app.post("/api/ui/render")
async def ui_render(body: UIBody, request: Request, ctx: dict = Depends(current_context)):
    _enforce(ctx, request, "ui")
    html, via = await _generate_ui(_ui_prompt(body))
    return {"html": html, "via": via}


# Serve the built frontend if present (single-container deploy)
_static = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static):
    app.mount("/", SPAStaticFiles(directory=_static, html=True), name="static")
