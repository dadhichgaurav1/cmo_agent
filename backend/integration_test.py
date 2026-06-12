"""Local integration test — verifies every piece is wired and runnable.

  backend/.venv/bin/python integration_test.py        # structural + free checks
  RUN_LIVE=1 backend/.venv/bin/python integration_test.py   # + live model/search calls
"""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))

RUN_LIVE = os.getenv("RUN_LIVE") == "1"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("✓" if cond else "✗"), name, ("- " + detail) if detail else "")


async def main():
    from app import config, graph, models, tools, composio_tools
    from app import main as appmain
    from app.memory import memory, conversation_id_for

    check("imports: all modules load", True)

    print("   --- key status ---")
    for k in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "EXA_API_KEY", "COMPOSIO_API_KEY", "SYNAP_API_KEY"]:
        print(f"     {k}: {'set' if config.has(getattr(config, k)) else 'MISSING'}")

    check("graph: LangGraph compiles", graph.GRAPH is not None)

    cache_path = os.path.join(BASE, "cache", "resend-com.json")
    try:
        events = json.load(open(cache_path))
        types = set(e["type"] for e in events)
        ok = {"objective", "sources", "opportunities", "radar", "artifact", "done"} <= types
        check("cache: resend-com.json complete", ok, f"{len(events)} events")
    except Exception as e:
        check("cache: resend-com.json complete", False, str(e)[:80])

    hn = await tools.hn_search("email api developers", 3)
    check("tool: hacker news search (free)", len(hn) > 0, f"{len(hn)} hits")

    try:
        await memory.bootstrap("itest", [{"text": "integration marker", "kind": "note", "run_id": "t"}])
        conv = conversation_id_for("itest")
        await memory.record_turn(conv, "user", "ping", "itest")
        rc = await memory.recall("itest", ["integration"])
        check("memory: bootstrap + record_turn + recall (no errors)", True,
              f"synap_active={bool(memory.sdk)} recall_len={len(rc)}")
    except Exception as e:
        check("memory: bootstrap + record_turn + recall (no errors)", False, str(e)[:90])

    routes = set(r.path for r in appmain.app.routes if hasattr(r, "path"))
    need = {"/api/health", "/api/analyze/stream", "/api/chat", "/api/research", "/api/ui/render"}
    check("api: all routes registered", need <= routes, f"{len(routes & need)}/{len(need)}")

    print(f"   composio client constructs: {composio_tools.available()}")

    # --- Addendum 4: runtime tool discovery + binding ---
    from app import capabilities
    snap = capabilities.registry_snapshot()
    builtins = {c["name"] for c in snap if c["source"] == "builtin"}
    check("capabilities: registry exposes builtin tools", {"exa", "hackernews", "reddit"} <= builtins,
          f"{len(snap)} capabilities")
    # research() must never return empty for a non-builtin access (discovers/binds or falls back to EXA)
    bound_events = []
    async def cap_emit(e):
        bound_events.append(e)
    found = await capabilities.research("github", "email api developer pain", 3, cap_emit)
    check("capabilities: non-builtin access binds-or-falls-back (never empty)", len(found) > 0,
          f"{len(found)} findings, {len(bound_events)} tool_bound events")

    # --- Addendum 2: em-dash ban + per-channel skills ---
    from app import humanize, skills
    from app.schemas import Opportunity
    dashed = humanize.humanize("We built this — fast, scaling 10—20 — and shipped it--today.")
    check("humanize: strips every em/en dash", "—" not in dashed and "–" not in dashed and "--" not in dashed, dashed)
    o = Opportunity(title="A — B", why="x — y", steps=["one — two"])
    humanize.scrub(o)
    check("humanize: scrub cleans nested structured fields",
          "—" not in (o.title + o.why + "".join(o.steps)))
    h = await skills.resolve_skill("humanizer")
    r = await skills.resolve_skill("reddit_reply")
    check("skills: humanizer + per-channel skill resolve from local catalogue",
          bool(h and h.rules) and bool(r and r.applies_to == "reddit"),
          f"humanizer={bool(h)} reddit={bool(r)}")
    if RUN_LIVE:
        gen = await skills.resolve_skill("substack_note")  # not local -> must generate-and-cache
        check("LIVE: skills generate-and-cache for an unknown channel", bool(gen and gen.rules),
              gen.name if gen else "none")
        if gen:
            os.remove(os.path.join(BASE, "app", "skills", gen.name + ".json"))

    if RUN_LIVE:
        ex = await tools.exa_search("resend email api", 2)
        check("LIVE: exa search", len(ex) > 0, f"{len(ex)} results")
        txt, name = await models.run_text("chat", "You are terse.", "Reply with just: OK", max_tokens=10)
        check("LIVE: model call", len(txt) > 0, name)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed" + (" -> " + ", ".join(FAIL) if FAIL else ""))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    asyncio.run(main())
