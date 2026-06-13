import asyncio
import json
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import db
from app import graph as agent_graph
from app import models as M
from app import monitors
from app import tools as T
from app.auth import current_context
from app.memory import memory, conversation_id_for
from app.tenancy import customer_scope

app = FastAPI(title="CMO Cofounder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


@app.on_event("startup")
async def _startup():
    # Addendum 1: the graph runs monitors, the scheduler fires them, monitors.py bridges the two.
    monitors.set_runner(agent_graph.run_monitor)
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
async def analyze_stream(url: str, mode: str = "live", ctx: dict = Depends(current_context)):
    org_id, user_id = ctx.get("org_id"), ctx.get("user_id")

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
async def chat(body: ChatBody, actx: dict = Depends(current_context)):
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
async def research(body: ResearchBody):
    findings = await T.exa_search(body.query, num=5)
    block = "\n".join(f"- {f.title} ({f.url}): {f.snippet[:160]}" for f in findings)
    system = ("You are a CMO cofounder. Turn raw research into 3 sharp, non-obvious, actionable takeaways "
              "for the founder — no filler.")
    human = f"Research question: {body.query}\nFindings:\n{block or '(none)'}\n\nReturn 3 concise takeaways."
    takeaways, name = await M.run_text("synthesize", system, human, max_tokens=600)
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
async def ui_render(body: UIBody):
    html, via = await _generate_ui(_ui_prompt(body))
    return {"html": html, "via": via}


# Serve the built frontend if present (single-container deploy)
_static = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static):
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
