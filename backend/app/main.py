import asyncio
import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CMO Cofounder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "cmo-cofounder", "phase": 0}


@app.get("/api/analyze/stream")
async def analyze_stub(url: str = ""):
    """Phase 0 SSE stub — validates the streaming wiring end-to-end.
    The real LangGraph agent replaces this in Phase 1."""

    async def gen():
        steps = [
            "Booting CMO Cofounder",
            f"Received: {url or '(no url)'}",
            "Phase 0 skeleton — the agent lands in Phase 1",
        ]
        for i, s in enumerate(steps):
            yield f"event: step\ndata: {json.dumps({'type': 'step', 'label': s, 'i': i})}\n\n"
            await asyncio.sleep(0.4)
        yield f"event: done\ndata: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# Serve the built frontend if present (single-container deploy)
_static = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static):
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
