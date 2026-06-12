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
    from app.memory import memory

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

    await memory.ingest("itest", "note", "integration test marker", run_id="t")
    rc = await memory.recall("itest", ["integration"])
    check("memory: ingest + recall", rc != "", f"synap_active={bool(memory.sdk)}")

    routes = set(r.path for r in appmain.app.routes if hasattr(r, "path"))
    need = {"/api/health", "/api/analyze/stream", "/api/chat", "/api/research", "/api/ui/render"}
    check("api: all routes registered", need <= routes, f"{len(routes & need)}/{len(need)}")

    print(f"   composio client constructs: {composio_tools.available()}")

    if RUN_LIVE:
        ex = await tools.exa_search("resend email api", 2)
        check("LIVE: exa search", len(ex) > 0, f"{len(ex)} results")
        txt, name = await models.run_text("chat", "You are terse.", "Reply with just: OK", max_tokens=10)
        check("LIVE: model call", len(txt) > 0, name)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed" + (" -> " + ", ".join(FAIL) if FAIL else ""))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    asyncio.run(main())
