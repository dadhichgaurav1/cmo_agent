"""Maximem Synap memory with a local JSON fallback so the agent always runs.

Two ingestion paths (per Synap's model):
  - bootstrap (setup-time)  -> memories.batch_create  (the company's durable market brain)
  - conversational (runtime) -> conversation.record_message + conversation.context.fetch (founder chat)

customer_id = the analyzed company.  user_id = the founder.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app import config

_LOCAL = os.getenv("LOCAL_MEMORY_PATH", "/tmp/cmo_memory.json")
USER_ID = "founder"


def _load() -> dict:
    try:
        with open(_LOCAL) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    try:
        with open(_LOCAL, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


_PENDING = os.getenv("PENDING_PATH", "/tmp/cmo_pending.json")


def _record_pending(customer_id: str, count: int) -> None:
    """Note that a write was just queued to Synap, so the UI can show 'indexing' vs 'empty'."""
    try:
        try:
            with open(_PENDING) as f:
                d = json.load(f)
        except Exception:
            d = {}
        d[customer_id] = {"count": int(count), "at": datetime.now(timezone.utc).isoformat()}
        with open(_PENDING, "w") as f:
            json.dump(d, f)
    except Exception:
        pass


def _read_pending(customer_id: str):
    try:
        with open(_PENDING) as f:
            return json.load(f).get(customer_id)
    except Exception:
        return None


def conversation_id_for(key: str) -> str:
    """Stable UUID per company so chat turns share one conversation."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "cmo-cofounder/" + key))


class Memory:
    def __init__(self):
        self.sdk = None
        self.enabled = config.has(config.SYNAP_API_KEY)
        self._tried = False

    async def _ensure(self):
        if self.sdk is not None or not self.enabled or self._tried:
            return
        self._tried = True
        try:
            from maximem_synap import MaximemSynapSDK
            self.sdk = MaximemSynapSDK(api_key=config.SYNAP_API_KEY)
            await self.sdk.initialize()
        except Exception:
            self.sdk = None
            self.enabled = False

    # --- customer-scoped retrieval (run start) ---
    async def recall(self, customer_id: str, queries: List[str]) -> str:
        await self._ensure()
        if self.sdk:
            try:
                ctx = await self.sdk.customer.context.fetch(
                    customer_id=customer_id, search_query=queries, mode="accurate"
                )
                return getattr(ctx, "formatted_context", "") or ""
            except Exception:
                pass
        data = _load().get(customer_id)
        return json.dumps(data)[:2000] if data else ""

    # --- structured recall for the Synap tab (facts / episodes / temporal events) ---
    async def recall_full(self, customer_id: str, queries: List[str]) -> dict:
        await self._ensure()
        if self.sdk:
            try:
                ctx = await self.sdk.customer.context.fetch(
                    customer_id=customer_id, search_query=queries, mode="accurate"
                )

                def _listify(attr):
                    v = getattr(ctx, attr, None) or []
                    out = []
                    for it in v:
                        if isinstance(it, dict):
                            out.append(it)
                        elif hasattr(it, "model_dump"):
                            out.append(it.model_dump())
                        else:
                            out.append({"text": str(it)})
                    return out

                facts = _listify("facts")
                episodes = _listify("episodes")
                temporal = _listify("temporal_events")
                fc = getattr(ctx, "formatted_context", "") or ""
                processing = 0
                if not (facts or episodes or fc):
                    pend = _read_pending(customer_id)
                    processing = int(pend.get("count", 0)) if pend else 0
                return {
                    "active": True,
                    "formatted_context": fc,
                    "facts": facts,
                    "episodes": episodes,
                    "temporal_events": temporal,
                    "processing": processing,
                }
            except Exception:
                pass
        # local fallback: surface the JSON brain grouped by kind
        data = _load().get(customer_id, {})
        items = []
        for kind, texts in (data.items() if isinstance(data, dict) else []):
            for t in texts:
                items.append({"kind": kind, "text": t})
        return {"active": False, "formatted_context": "", "facts": items,
                "episodes": [], "temporal_events": [], "processing": 0}

    # --- bootstrap ingest (setup-time knowledge): one batch_create ---
    async def bootstrap(self, customer_id: str, items: List[Dict[str, Any]]):
        items = [it for it in items if it.get("text")]
        if not items:
            return
        await self._ensure()
        if self.sdk:
            try:
                from maximem_synap import CreateMemoryRequest
                now = datetime.now(timezone.utc)
                docs = [
                    CreateMemoryRequest(
                        document=it["text"],
                        document_type="document",
                        customer_id=customer_id,
                        user_id=USER_ID,
                        document_created_at=now,
                        metadata={"kind": it.get("kind", ""), "source_url": it.get("url", ""), "run_id": it.get("run_id", "")},
                    )
                    for it in items
                ]
                await self.sdk.memories.batch_create(documents=docs, fail_fast=False)
                _record_pending(customer_id, len(docs))
                return
            except Exception:
                pass
        data = _load()
        for it in items:
            data.setdefault(customer_id, {}).setdefault(it.get("kind", "note"), []).append(it["text"][:1000])
        _save(data)

    # --- conversational ingest + retrieval (founder chat) ---
    async def record_turn(self, conversation_id: str, role: str, content: str, customer_id: str):
        await self._ensure()
        if self.sdk:
            try:
                await self.sdk.conversation.record_message(
                    conversation_id=conversation_id, role=role, content=content,
                    user_id=USER_ID, customer_id=customer_id,
                )
            except Exception:
                pass

    async def recall_conversation(self, conversation_id: str, customer_id: str, query: str) -> str:
        await self._ensure()
        if self.sdk:
            try:
                ctx = await self.sdk.conversation.context.fetch(
                    conversation_id=conversation_id, user_id=USER_ID, customer_id=customer_id,
                    search_query=[query], mode="fast",
                )
                return getattr(ctx, "formatted_context", "") or ""
            except Exception:
                pass
        return ""

    # --- founder preferences (USER scope, scoped to THIS customer; never cross-customer) ---
    async def recall_user(self, customer_id: str, queries: List[str]) -> str:
        await self._ensure()
        if self.sdk:
            try:
                ctx = await self.sdk.user.context.fetch(
                    user_id=USER_ID, customer_id=customer_id, search_query=queries, mode="accurate"
                )
                return getattr(ctx, "formatted_context", "") or ""
            except Exception:
                pass
        return ""


memory = Memory()
