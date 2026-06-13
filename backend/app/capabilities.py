"""Runtime capability layer (Addendum 4 + foundation for Addendum 2).

The agent is not limited to the tools it had at plan-time. When a research move names a
source/capability the registry doesn't know, the registry searches the Composio catalogue,
lets a model pick + bind a tool it never had before, executes it, and caches the binding.

This is the deliberate, *bounded* reversal of the build plan's "no autonomous tool-binding":
binding is a discrete, surfaced, traceable step (it emits `tool_bound`) and always falls back
to EXA so a research move never returns empty.

Skills (per-channel writing skills + humanizer) live in the same registry; see skills.py.
"""
import json
from typing import Callable, List, Optional

from app import composio_tools, models, prompts, tools
from app.schemas import Capability, Finding, ToolBinding

# Sources the agent already knows how to research without discovery.
BUILTIN_TOOLS = {"exa", "hackernews", "reddit", "browser"}

# name -> Capability, populated as the agent binds things at runtime (per process).
_REGISTRY: dict[str, Capability] = {}


def registry_snapshot() -> List[dict]:
    """All capabilities bound so far, for the Capabilities tab / trace."""
    builtins = [
        Capability(name=n, kind="tool", source="builtin", bound_at="plan").model_dump()
        for n in sorted(BUILTIN_TOOLS)
    ]
    return builtins + [c.model_dump() for c in _REGISTRY.values()]


def remember_capability(cap: Capability) -> None:
    _REGISTRY[cap.name] = cap


def lookup(name: str) -> Optional[Capability]:
    return _REGISTRY.get(name)


async def _discover_and_bind(need: str, query: str) -> Optional[Capability]:
    """Search the catalogue and let the model bind the best-fitting tool for this need."""
    candidates = composio_tools.discover(need, limit=5)
    if not candidates:
        return None
    try:
        binding, _ = await models.run_structured(
            "extract", prompts.BIND_SYS, prompts.bind_human(need, query, candidates), ToolBinding,
            temperature=0.0, max_tokens=600,
        )
    except Exception:
        return None
    if not binding.slug or binding.confidence < 0.4:
        return None
    try:
        args = json.loads(binding.args_json) if binding.args_json else {}
        if not isinstance(args, dict):
            args = {}
    except Exception:
        args = {}
    # default a query arg if the model returned nothing usable
    if not args:
        args = {"query": query}
    cap = Capability(
        name=need, kind="tool", source="composio", bound_at="runtime",
        slug=binding.slug, why=binding.why,
        spec={"args": args, "candidates": [c["slug"] for c in candidates]},
    )
    remember_capability(cap)
    return cap


async def research(access: str, query: str, num: int, emit: Callable, entity_id: str = "") -> List[Finding]:
    """Single entry point for a research move. Builtin access runs directly; an unknown
    access triggers runtime discovery + binding, then executes the bound tool.
    entity_id scopes Composio execution to the org's connected accounts (when set)."""
    if access in BUILTIN_TOOLS:
        return await tools.run_tool(access, query, num, entity_id=entity_id)

    cap = lookup(access)
    newly_bound = False
    if cap is None or not cap.slug:
        cap = await _discover_and_bind(access, query)
        newly_bound = cap is not None

    if cap and cap.slug:
        if newly_bound:
            await emit({
                "type": "tool_bound", "label": f"Bound new tool: {cap.slug}", "model": "composio",
                "data": {"need": access, "slug": cap.slug, "why": cap.why,
                         "considered": cap.spec.get("candidates", [])},
            })
        args = dict(cap.spec.get("args") or {})
        # refresh the primary query field for this specific move
        for k in ("query", "q", "search", "search_query", "keyword", "keywords", "text"):
            if k in args:
                args[k] = query
                break
        found = await composio_tools.execute_tool(cap.slug, args, num, entity_id=entity_id)
        if found:
            return found

    # discovery failed or returned nothing — never leave a move empty
    await emit({
        "type": "tool_bound", "label": f"No tool found for '{access}' — using web search",
        "model": "exa", "data": {"need": access, "slug": "", "fallback": "exa"},
    })
    return await tools.exa_search(query, num)
