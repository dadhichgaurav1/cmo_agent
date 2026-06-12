"""The CMO-cofounder agent as a LangGraph StateGraph.

recall -> objective -> source_strategy -> plan -> act <-> reflect -> synthesize -> draft -> remember

Nodes emit fine-grained trace events via an `emit` callback passed in config.
"""
import re
import uuid
from typing import TypedDict

from langgraph.graph import START, END, StateGraph

from app import capabilities, models, prompts, skills, tools
from app.memory import memory
from app.schemas import (
    Artifact, ProfileObjective, PlanOut, ReflectOut, SourceStrategy, SynthesisOut,
)

CAP = 5  # max research iterations


class S(TypedDict, total=False):
    url: str
    mode: str
    slug: str
    run_id: str
    prior_context: str
    profile: dict
    objective: dict
    sources: list
    plan: list
    findings: list
    iterations: int
    opportunities: list
    artifacts: list
    _sufficient: bool


def _emit(config):
    return config["configurable"]["emit"]


def slugify(url: str) -> str:
    host = (url or "").lower().replace("https://", "").replace("http://", "").split("/")[0]
    return re.sub(r"[^a-z0-9]+", "-", host).strip("-") or "company"


async def recall(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Recalling prior context (Synap)", "model": "synap"})
    ctx = await memory.recall(state["slug"], [state["url"], "adjacencies", "positioning", "channels"])
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
    await emit({"type": "sources", "label": f"{data.get('company_type', '')} — {len(data.get('sources', []))} sources",
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
    return {"plan": items}


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
    found = await capabilities.research(access, item.get("query", ""), 4, emit)
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
    return {"opportunities": opps}


async def draft(state: S, config) -> S:
    emit = _emit(config)
    opps = state.get("opportunities", [])
    targets = [o for o in opps if o.get("type") == "engagement"][:3] or opps[:1]
    humanizer = await skills.resolve_skill("humanizer", emit)  # always-on baseline voice skill
    artifacts = []
    for o in targets:
        await emit({"type": "step", "label": f"Drafting: {o.get('title', '')[:50]}", "model": "claude-haiku-4-5"})
        # bind the platform-specific writing skill for this channel (generated at runtime if unknown)
        channel_skill = await skills.resolve_skill(o.get("template_id") or o.get("source_name") or "outreach", emit)
        sys_aug = prompts.DRAFT_SYS + skills.render([humanizer, channel_skill])
        body, name = await models.run_text("draft", sys_aug,
                                           prompts.draft_human(state["profile"], state["objective"], o), max_tokens=900)
        a = Artifact(
            id=str(uuid.uuid4())[:8], opportunity_id=o.get("id", ""), title=o.get("title", ""),
            channel=o.get("source_name") or o.get("category", ""), body=body, model_used=name,
        )
        artifacts.append(a.model_dump())
        await emit({"type": "artifact", "label": a.title, "data": a.model_dump(), "model": name})
    return {"artifacts": artifacts}


async def remember(state: S, config) -> S:
    emit = _emit(config)
    await emit({"type": "step", "label": "Bootstrapping company memory (Synap)", "model": "synap"})
    cid = state["slug"]
    rid = state.get("run_id", "")
    obj = state.get("objective", {})
    prof = state.get("profile", {})
    items = [{"text": f"Objective: {obj.get('objective')} — {obj.get('reasoning')}", "kind": "objective", "run_id": rid}]
    if prof:
        items.append({
            "text": (f"Profile: {prof.get('name')} ({prof.get('category')}), stage {prof.get('stage')}, "
                     f"ICP {prof.get('icp')}, competitors: {', '.join(prof.get('competitors', []))}"),
            "kind": "profile", "run_id": rid,
        })
    for o in state.get("opportunities", [])[:8]:
        items.append({"text": f"{o.get('type')} opportunity — {o.get('title')}: {o.get('why')}",
                      "kind": "opportunity", "url": o.get("thread_url", ""), "run_id": rid})
    for a in state.get("artifacts", []):
        items.append({"text": f"Draft ({a.get('channel')}) — {a.get('title')}\n{(a.get('body') or '')[:600]}",
                      "kind": "draft", "run_id": rid})
    await memory.bootstrap(cid, items)  # one batch_create = the company's durable market brain
    await emit({"type": "capabilities", "label": "Capabilities used this run",
                "data": capabilities.registry_snapshot()})
    await emit({"type": "done", "label": "Done",
                "data": {"opportunities": state.get("opportunities", []), "artifacts": state.get("artifacts", [])}})
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
    g.add_node("remember", remember)
    g.add_edge(START, "recall")
    g.add_edge("recall", "objective")
    g.add_edge("objective", "source_strategy")
    g.add_edge("source_strategy", "plan")
    g.add_edge("plan", "act")
    g.add_edge("act", "reflect")
    g.add_conditional_edges("reflect", route_after_reflect, {"act": "act", "synthesize": "synthesize"})
    g.add_edge("synthesize", "draft")
    g.add_edge("draft", "remember")
    g.add_edge("remember", END)
    return g.compile()


GRAPH = build_graph()


async def run(url: str, mode: str, emit):
    rid = str(uuid.uuid4())[:8]
    state = {"url": url, "mode": mode, "slug": slugify(url), "run_id": rid}
    await GRAPH.ainvoke(state, config={"configurable": {"emit": emit, "run_id": rid}, "recursion_limit": 60})
