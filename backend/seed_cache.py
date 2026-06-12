"""Run one live analysis and capture its event stream to cache/<slug>.json.

Doubles as the Phase 1 end-to-end live test. Usage:
    backend/.venv/bin/python backend/seed_cache.py [url]
"""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))

from app import graph  # noqa: E402  (import after env is loaded)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "resend.com"
    events = []

    async def emit(ev):
        events.append(ev)
        label = str(ev.get("label", ""))[:70]
        print(f"  [{ev.get('type'):>13}] {label}")

    print(f"=== live run: {url} ===")
    await graph.run(url, "live", emit)

    cache_dir = os.path.join(BASE, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    for e in events:
        e.setdefault("_delay", 0.45)
    out_path = os.path.join(cache_dir, graph.slugify(url) + ".json")
    with open(out_path, "w") as f:
        json.dump(events, f, indent=2, default=str)
    print(f"=== wrote {len(events)} events -> {out_path} ===")


if __name__ == "__main__":
    asyncio.run(main())
