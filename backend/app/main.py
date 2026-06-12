import asyncio
import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import graph as agent_graph

app = FastAPI(title="CMO Cofounder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "cmo-cofounder", "phase": 1}


def _sse(ev: dict) -> str:
    return f"event: {ev.get('type', 'message')}\ndata: {json.dumps(ev)}\n\n"


async def _drive_graph(url: str, mode: str, queue: "asyncio.Queue"):
    async def emit(ev):
        await queue.put(ev)
    try:
        await agent_graph.run(url, mode, emit)
    except Exception as e:
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
async def analyze_stream(url: str, mode: str = "live"):
    async def gen():
        if mode == "cached":
            for ev in _cached_events(url):
                yield _sse(ev)
                await asyncio.sleep(float(ev.get("_delay", 0.45)))
            return
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(_drive_graph(url, mode, queue))
        try:
            while True:
                ev = await queue.get()
                if ev is None:
                    break
                yield _sse(ev)
        finally:
            await task

    return StreamingResponse(gen(), media_type="text/event-stream")


# Serve the built frontend if present (single-container deploy)
_static = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static):
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
