"""Maximem Synap memory wrapper with a local JSON fallback so the agent always runs.

customer_id = the analyzed company (the compounding "market brain").
user_id = the founder.
"""
import json
import os
from typing import List

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

    async def ingest(self, customer_id: str, kind: str, text: str, url: str = "", run_id: str = ""):
        await self._ensure()
        if self.sdk:
            try:
                await self.sdk.memories.create(
                    document=text,
                    document_type="document",
                    customer_id=customer_id,
                    user_id=USER_ID,
                    mode="fast",
                    metadata={"kind": kind, "source_url": url, "run_id": run_id},
                )
                return
            except Exception:
                pass
        data = _load()
        data.setdefault(customer_id, {}).setdefault(kind, []).append(text[:1000])
        _save(data)


memory = Memory()
