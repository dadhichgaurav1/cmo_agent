"""The CMO-cofounder agent as a LangGraph StateGraph.

recall -> objective -> source_strategy -> plan -> act <-> reflect -> synthesize -> draft -> remember

Nodes emit fine-grained trace events via an `emit` callback passed in config.
"""
import re
import uuid
from typing import TypedDict

from langgraph.graph import START, END, StateGraph

from app import capabilities, composio_tools, db, email, models, monitors, prompts, safety, skills, tools
from app.memory import memory
from app.tenancy import customer_scope
from app.schemas import (
    Artifact, CardQueries, DiffOut, MonitorPlan, ProfileObjective, PlanOut, ReflectOut,
    SourceStrategy, SynthesisOut,
)

# Action Board feeder: which builtin/search access to use per platform, and which writing
# skill voices the draft. reddit/hackernews are builtin; x/indiehackers fall back through
# capabilities.research (discover -> EXA), keeping the engine dependency-light.
PLATFORM_ACCESS = {"reddit": "reddit", "hackernews": "hackernews", "x": "twitter",
                   "linkedin": "linkedin", "indiehackers": "exa"}
PLATFORM_SKILL = {"reddit": "reddit_reply", "hackernews": "hn_comment", "x": "twitter_reply",
                  "linkedin": "linkedin_post", "indiehackers": "indiehackers_comment"}
DEFAULT_GEN_PLATFORMS = ["reddit", "hackernews", "x"]

CAP = 5  # max research iterations


class S(TypedDict, total=False):
    url: str
    mode: str
    slug: str
    run_id: str
    org_id: str       # tenant; None in local/demo mode
    user_id: str      # founder identity for USER-scope memory
    scope: str        # Synap customer_id = org_id:slug (or bare slug when no org)
    prior_context: str
    profile: dict
    objective: dict
    sources: list
    plan: list
    findings: list
    iterations: int
    opportunities: list
    artifacts: list
    ledger: list
    monitors: list
    _sufficient: bool


def _emit(config):
    return config["configurable"]["emit"]


async def _log_discarded(state: S, emit, stage: str, items) -> list:
    """Accumulate ideas considered-and-discarded (Addendum 3) and surface them."""
    ledger = list(state.get("ledger", []))
    entries = []
    for it in items or []:
        d = it.model_dump() if hasattr(it, "model_dump") else dict(it)
        d["stage"] = stage
        if d.get("idea"):
            entries.append(d)
    if entries:
        ledger.extend(entries)
        await emit({"type": "discarded", "label": f"{len(entries)} ideas ruled out at {stage}",
                    "data": entries, "model": "claude-sonnet-4-6"})
    return ledger


def slugify(url: str) -> str:
    host = (url or "").lower().replace("https://", "").replace("http://", "").split("/")[0]
    return re.sub(r"[^a-z0-9]+", "-", host).strip("-") or "company"


async def recall(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Recalling prior context (Synap)", "model": "synap"})
    ctx = await memory.recall(state["scope"], [state["url"], "adjacencies", "positioning", "channels"])
    if ctx:
        await emit({"type": "memory", "label": "Recalled prior context", "detail": ctx[:600]})
    return {"prior_context": ctx or "", "iterations": 0, "findings": [], "plan": []}


async def objective(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Reading your site → inferring stage & objective", "model": "claude-sonnet-4-6"})
    site = await tools.fetch_site(state["url"])
    out, name = await models.run_structured(
        "objective", prompts.OBJECTIVE_SYS,
        prompts.objective_human(state["url"], site, state.get("prior_context", "")),
        ProfileObjective,
    )
    prof = out.profile.model_dump()
    prof["url"] = state["url"]
    obj = out.objective.model_dump()
    await emit({"type": "profile", "label": prof.get("name") or state["url"], "data": prof, "model": name})
    await emit({"type": "objective", "label": obj.get("objective", ""), "data": obj, "model": name})
    return {"profile": prof, "objective": obj}


async def source_strategy(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Mapping where your customers actually are", "model": "claude-sonnet-4-6"})
    out, name = await models.run_structured(
        "source_strategy", prompts.SOURCES_SYS,
        prompts.sources_human(state["profile"], state["objective"]), SourceStrategy,
    )
    data = out.model_dump()
    await emit({"type": "sources", "label": f"{data.get('company_type', '')} · {len(data.get('sources', []))} sources",
                "data": data, "model": name})
    return {"sources": data.get("sources", [])}


async def plan(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Planning research over the chosen sources", "model": "claude-sonnet-4-6"})
    out, name = await models.run_structured(
        "plan", prompts.PLAN_SYS,
        prompts.plan_human(state["profile"], state["objective"], state["sources"]), PlanOut,
    )
    items = [i.model_dump() for i in out.items][:CAP]
    await emit({"type": "plan", "label": f"{len(items)} research moves", "data": items, "model": name})
    ledger = await _log_discarded(state, emit, "plan", out.discarded)
    return {"plan": items, "ledger": ledger}


async def act(state: S, config) -> S:
    emit = _emit(config)
    i = state.get("iterations", 0)
    plan_items = state.get("plan", [])
    if i >= len(plan_items):
        return {"iterations": i}
    item = plan_items[i]
    access = item.get("access", "exa")
    await emit({"type": "step", "label": f"Researching: {item.get('query', '')}", "model": access})
    # capabilities.research handles builtin sources directly and discovers+binds any
    # non-builtin source the planner asked for (Addendum 4).
    found = await capabilities.research(access, item.get("query", ""), 4, emit,
                                        entity_id=composio_tools.entity_for(state.get("org_id")))
    findings = list(state.get("findings", []))
    for f in found:
        findings.append(f.model_dump())
        await emit({"type": "finding", "label": f.title, "data": f.model_dump(), "model": f.source})
    return {"findings": findings, "iterations": i + 1}


async def reflect(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Critiquing: specific & non-obvious?", "model": "claude-sonnet-4-6"})
    out, name = await models.run_structured(
        "reflect", prompts.REFLECT_SYS,
        prompts.reflect_human(state["objective"], state.get("findings", [])), ReflectOut,
    )
    await emit({"type": "reflect", "label": ("Sufficient" if out.sufficient else "Needs more"),
                "data": out.model_dump(), "model": name})
    upd = {"_sufficient": bool(out.sufficient)}
    if (not out.sufficient) and out.extra_query and state.get("iterations", 0) < CAP:
        plan_items = list(state.get("plan", []))
        plan_items.append({"goal": "gap-fill", "query": out.extra_query, "access": out.extra_access or "exa"})
        upd["plan"] = plan_items
    upd["ledger"] = await _log_discarded(state, emit, "reflect", out.discarded)
    return upd


def route_after_reflect(state: S) -> str:
    if state.get("_sufficient"):
        return "synthesize"
    if state.get("iterations", 0) >= CAP:
        return "synthesize"
    if state.get("iterations", 0) >= len(state.get("plan", [])):
        return "synthesize"
    return "act"


async def synthesize(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Synthesizing prioritized moves + engagement radar", "model": "claude-sonnet-4-6"})
    human = prompts.synth_human(state["profile"], state["objective"], state["sources"], state.get("findings", []))
    out, name = await models.run_structured("synthesize", prompts.SYNTH_SYS, human, SynthesisOut,
                                            temperature=0.4, max_tokens=8000)
    if not out.opportunities:  # never return an empty board
        forced = human + ("\n\nIMPORTANT: Return at least 5 opportunities. If the findings are thin, still propose "
                          "stage-appropriate strategic moves grounded in the company's category, competitors, and objective.")
        out, name = await models.run_structured("synthesize", prompts.SYNTH_SYS, forced, SynthesisOut,
                                                temperature=0.6, max_tokens=8000)
    opps = []
    for idx, o in enumerate(out.opportunities):
        d = o.model_dump()
        d["id"] = str(idx + 1)
        opps.append(d)
    strategic = [o for o in opps if o.get("type") != "engagement"]
    engagement = [o for o in opps if o.get("type") == "engagement"]
    await emit({"type": "opportunities", "label": f"{len(strategic)} strategic moves", "data": strategic, "model": name})
    if engagement:
        await emit({"type": "radar", "label": f"{len(engagement)} engagement opportunities", "data": engagement, "model": name})
    ledger = await _log_discarded(state, emit, "synthesize", out.discarded)
    return {"opportunities": opps, "ledger": ledger}


async def draft(state: S, config) -> S:
    emit = _emit(config)
    opps = state.get("opportunities", [])
    targets = [o for o in opps if o.get("type") == "engagement"][:3] or opps[:1]
    humanizer = await skills.resolve_skill("humanizer", emit)  # always-on baseline voice skill
    # founder voice/preferences from Synap (USER scope, this company only) — drafts sound more like them over time
    prefs = await memory.recall_user(state["scope"], ["founder voice", "tone", "writing style", "phrasing", "dos and don'ts"],
                                     user_id=state.get("user_id"))
    if prefs:
        await emit({"type": "memory", "label": "Applying your voice from Synap memory", "detail": prefs[:400], "model": "synap"})
    artifacts = []
    for o in targets:
        await emit({"type": "step", "label": f"Drafting: {o.get('title', '')[:50]}", "model": "claude-haiku-4-5"})
        # bind the platform-specific writing skill for this channel (generated at runtime if unknown)
        channel_skill = await skills.resolve_skill(o.get("template_id") or o.get("source_name") or "outreach", emit)
        sys_aug = prompts.DRAFT_SYS + skills.render([humanizer, channel_skill])
        body, name = await models.run_text("draft", sys_aug,
                                           prompts.draft_human(state["profile"], state["objective"], o, prefs), max_tokens=900)
        a = Artifact(
            id=str(uuid.uuid4())[:8], opportunity_id=o.get("id", ""), title=o.get("title", ""),
            channel=o.get("source_name") or o.get("category", ""), body=body, model_used=name,
        )
        artifacts.append(a.model_dump())
        await emit({"type": "artifact", "label": a.title, "data": a.model_dump(), "model": name})
    return {"artifacts": artifacts}


async def monitor_plan(state: S, config) -> S:
    """Addendum 1: after the first analysis the agent self-identifies which signals to watch
    recurringly, registers them with the scheduler, and surfaces them."""
    emit = _emit(config)
    await emit({"type": "step", "label": "Deciding what to watch recurringly", "model": "claude-sonnet-4-6"})
    try:
        out, name = await models.run_structured(
            "synthesize", prompts.MONITOR_SYS,
            prompts.monitor_human(state["profile"], state["objective"], state.get("sources", []),
                                  state.get("opportunities", [])),
            MonitorPlan, temperature=0.3, max_tokens=1500,
        )
        jobs = [j.model_dump() for j in out.jobs]
    except Exception:
        jobs = []
    if jobs:
        monitors.save_plan(state.get("org_id"), state["slug"], jobs)  # persist + register with the scheduler
        await emit({"type": "monitors", "label": f"{len(jobs)} recurring monitors set",
                    "data": jobs, "model": name if jobs else "synap"})
    return {"monitors": jobs}


async def remember(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Bootstrapping company memory (Synap)", "model": "synap"})
    cid = state["scope"]
    rid = state.get("run_id", "")
    obj = state.get("objective", {})
    prof = state.get("profile", {})
    items = [{"text": f"Objective: {obj.get('objective')}. {obj.get('reasoning')}", "kind": "objective", "run_id": rid}]
    if prof:
        items.append({
            "text": (f"Profile: {prof.get('name')} ({prof.get('category')}), stage {prof.get('stage')}, "
                     f"ICP {prof.get('icp')}, competitors: {', '.join(prof.get('competitors', []))}"),
            "kind": "profile", "run_id": rid,
        })
    for o in state.get("opportunities", [])[:8]:
        items.append({"text": f"{o.get('type')} opportunity, {o.get('title')}: {o.get('why')}",
                      "kind": "opportunity", "url": o.get("thread_url", ""), "run_id": rid})
    for a in state.get("artifacts", []):
        items.append({"text": f"Draft ({a.get('channel')}) - {a.get('title')}\n{(a.get('body') or '')[:600]}",
                      "kind": "draft", "run_id": rid})
    for d in state.get("ledger", []):  # roads not taken, so memory knows what was already ruled out
        items.append({"text": f"Ruled out at {d.get('stage')}: {d.get('idea')} ({d.get('reason')})",
                      "kind": "reasoning", "run_id": rid})
    for m in state.get("monitors", []):
        items.append({"text": f"Monitor ({m.get('cadence')}): {m.get('name')} - {m.get('rationale')}",
                      "kind": "monitor", "run_id": rid})
    await memory.bootstrap(cid, items)  # one batch_create = the company's durable market brain
    await emit({"type": "capabilities", "label": "Capabilities used this run",
                "data": capabilities.registry_snapshot()})
    await emit({"type": "done", "label": "Done",
                "data": {"opportunities": state.get("opportunities", []), "artifacts": state.get("artifacts", []),
                         "ledger": state.get("ledger", []),
                         # profile + objective ride along so the Action Board feeder can generate
                         # fresh cards later without re-running the full analysis.
                         "profile": state.get("profile", {}), "objective": state.get("objective", {})}})
    return {}


def build_graph():
    g = StateGraph(S)
    g.add_node("recall", recall)
    g.add_node("objective", objective)
    g.add_node("source_strategy", source_strategy)
    g.add_node("plan", plan)
    g.add_node("act", act)
    g.add_node("reflect", reflect)
    g.add_node("synthesize", synthesize)
    g.add_node("draft", draft)
    g.add_node("monitor_plan", monitor_plan)
    g.add_node("remember", remember)
    g.add_edge(START, "recall")
    g.add_edge("recall", "objective")
    g.add_edge("objective", "source_strategy")
    g.add_edge("source_strategy", "plan")
    g.add_edge("plan", "act")
    g.add_edge("act", "reflect")
    g.add_conditional_edges("reflect", route_after_reflect, {"act": "act", "synthesize": "synthesize"})
    g.add_edge("synthesize", "draft")
    g.add_edge("draft", "monitor_plan")
    g.add_edge("monitor_plan", "remember")
    g.add_edge("remember", END)
    return g.compile()


GRAPH = build_graph()


async def run(url: str, mode: str, emit, org_id=None, user_id=None, run_id=None):
    rid = run_id or str(uuid.uuid4())[:8]
    slug = slugify(url)
    state = {"url": url, "mode": mode, "slug": slug, "run_id": rid,
             "org_id": org_id, "user_id": user_id, "scope": customer_scope(org_id, slug)}
    await GRAPH.ainvoke(state, config={"configurable": {"emit": emit, "run_id": rid}, "recursion_limit": 60})


async def run_monitor(org_id, slug: str, job: dict, emit=None) -> dict:
    """Addendum 1: a lightweight recurring run. Recall prior intel, pull fresh signal for one
    monitor, diff it against what Synap already knows, and record only the delta."""
    async def _noop(_ev):
        return None
    emit = emit or _noop
    scope = customer_scope(org_id, slug)
    rid = str(uuid.uuid4())[:8]
    name = job.get("name", "monitor")
    await emit({"type": "step", "label": f"Monitor: {name}", "model": "synap"})

    prior = await memory.recall(scope, [job.get("query", ""), name, "adjacencies", "channels"])
    found = await capabilities.research(job.get("access", "exa"), job.get("query", ""), 4, emit,
                                        entity_id=composio_tools.entity_for(org_id))
    findings = [f.model_dump() for f in found]

    try:
        diff, _ = await models.run_structured(
            "reflect", prompts.DIFF_SYS, prompts.diff_human(name, prior or "", findings),
            DiffOut, temperature=0.2, max_tokens=900,
        )
    except Exception:
        diff = DiffOut(summary="(diff unavailable)")

    entry = {
        "monitor": name, "summary": diff.summary, "new": diff.new, "changed": diff.changed,
        "at": monitors.now_iso(), "run_id": rid,
    }
    monitors.append_changelog(org_id, slug, entry)

    # ingest only the delta, so memory compounds instead of duplicating
    delta_items = [{"text": f"[{name}] new: {s}", "kind": "update", "run_id": rid} for s in diff.new]
    delta_items += [{"text": f"[{name}] changed: {s}", "kind": "update", "run_id": rid} for s in diff.changed]
    if delta_items:
        await memory.bootstrap(scope, delta_items)

    # Best-effort email alert to the workspace owner when a monitor surfaces movement.
    if (diff.new or diff.changed) and org_id and email.enabled():
        to = db.org_owner_email(org_id)
        if to:
            rows = "".join(f"<li>{s}</li>" for s in (diff.new + diff.changed)[:8])
            await email.send(to, f"[StratCMO] {name}: {len(diff.new)} new, {len(diff.changed)} changed",
                             f"<p>{diff.summary}</p><ul>{rows}</ul>")

    await emit({"type": "update", "label": f"{name}: {len(diff.new)} new, {len(diff.changed)} changed",
                "data": entry, "model": "claude-sonnet-4-6"})
    return entry


async def _resolve_profile(org_id, slug: str):
    """Profile + objective for the Action Board feeder. Prefer the latest run's summary
    (runs now carry them); fall back to inferring from the site so old runs still work."""
    run = db.latest_run(org_id, slug)
    summary = run.get("summary") or {}
    profile, objective = summary.get("profile") or {}, summary.get("objective") or {}
    if profile.get("name"):
        return profile, objective, run
    url = run.get("company_url") or ""
    if not url:
        return {}, {}, run
    try:
        site = await tools.fetch_site(url)
        out, _ = await models.run_structured(
            "objective", prompts.OBJECTIVE_SYS, prompts.objective_human(url, site, ""), ProfileObjective)
        prof = out.profile.model_dump(); prof["url"] = url
        return prof, out.objective.model_dump(), run
    except Exception:
        return {}, {}, run


async def generate_cards(org_id, slug: str, platforms=None, per_platform: int = 2, emit=None) -> list:
    """The suggestion engine + daily-grind feeder: for each platform, find live threads the
    company could naturally engage, draft a platform-voiced reply, and queue them as cards.
    Dedupes against threads already on the board so the feeder never re-suggests the same one."""
    async def _noop(_ev):
        return None
    emit = emit or _noop
    platforms = [p for p in (platforms or DEFAULT_GEN_PLATFORMS) if p in PLATFORM_ACCESS]
    profile, objective, run = await _resolve_profile(org_id, slug)
    if not profile.get("name"):
        await emit({"type": "step", "label": "No analysis yet — run one first to seed the feeder", "model": "synap"})
        return []

    scope = customer_scope(org_id, slug)
    prefs = await memory.recall_user(scope, ["founder voice", "tone", "writing style"], user_id=None)
    # Loop-back (P4): what the founder has actually posted/engaged with biases the next batch.
    engaged = await memory.recall(scope, ["engagement", "posted thread", "what worked"])
    humanizer = await skills.resolve_skill("humanizer", emit)
    seen = {c.get("target_url") for c in db.list_cards(org_id, slug) if c.get("target_url")}
    new_cards: list = []

    for platform in platforms:
        access = PLATFORM_ACCESS.get(platform, "exa")
        voice = await skills.resolve_skill(PLATFORM_SKILL.get(platform, "outreach"), emit)
        try:
            q, _ = await models.run_structured(
                "plan", prompts.GENQ_SYS,
                prompts.genq_human(profile, objective, platform, per_platform + 1, engaged=(engaged or "")[:600]),
                CardQueries, temperature=0.5, max_tokens=800)
            queries = [x.query for x in q.queries if x.query][: per_platform + 1]
        except Exception:
            queries = []
        made = 0
        for query in queries:
            if made >= per_platform:
                break
            await emit({"type": "step", "label": f"{platform}: searching '{query[:48]}'", "model": access})
            found = await capabilities.research(access, query, 4, emit,
                                                entity_id=composio_tools.entity_for(org_id))
            for f in found:
                if made >= per_platform:
                    break
                url = (f.url or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                opp = {"title": f.title, "source_name": platform, "template_id": PLATFORM_SKILL.get(platform, ""),
                       "why": (f.snippet or "")[:240], "thread_url": url}
                sys_aug = prompts.DRAFT_SYS + skills.render([humanizer, voice])
                body, _name = await models.run_text("draft", sys_aug,
                                                    prompts.draft_human(profile, objective, opp, prefs), max_tokens=700)
                new_cards.append({
                    "run_id": run.get("id"), "company_slug": slug, "source": "agent", "platform": platform,
                    "kind": "reply", "target_url": url, "target_title": f.title, "title": f.title,
                    "body": body, "voice": voice.name if voice else "", "state": "drafted",
                    "metadata": {"why": (f.snippet or "")[:240], "query": query,
                                 "review": safety.review_draft(body, platform)},
                })
                made += 1
        await emit({"type": "step", "label": f"{platform}: {made} cards drafted", "model": "claude-haiku-4-5"})

    created = db.bulk_create_cards(org_id, new_cards) if new_cards else []
    return created or new_cards


async def feed_all_cards() -> int:
    """Daily feeder entry point: generate fresh cards for every company that opted in via the
    Action Board toggle (db.all_feeders). The scheduler calls this once a day. Per-company, not
    a global switch. Returns the number of cards created."""
    from app import usage
    total = 0
    for f in db.all_feeders():
        org_id, slug = f.get("org_id"), f.get("slug")
        if not slug:
            continue
        if not usage.can(org_id, "monitors_active"):
            continue  # free orgs can arm the feeder, but the daily sweep only fires for Pro
        try:
            total += len(await generate_cards(org_id, slug))
        except Exception:
            pass
    return total
