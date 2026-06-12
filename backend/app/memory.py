"""Maximem Synap-backed context memory.

Falls back to a local JSON store so the agent runs even before Synap is wired.
Swap the `_synap_*` bodies with the real Synap SDK once the snippet is provided.
"""
import json
import os
from typing import Any, Dict

from app import config

_LOCAL_PATH = os.getenv("LOCAL_MEMORY_PATH", "/tmp/cmo_memory.json")


def _load_local() -> Dict[str, Any]:
    try:
        with open(_LOCAL_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_local(data: Dict[str, Any]) -> None:
    try:
        with open(_LOCAL_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


class Memory:
    def __init__(self):
        self.use_synap = config.has(config.SYNAP_API_KEY) and config.has(config.SYNAP_BASE_URL)

    async def store(self, namespace: str, kind: str, value: Any) -> None:
        if self.use_synap:
            try:
                return await self._synap_store(namespace, kind, value)
            except Exception:
                pass  # never let memory break the run
        data = _load_local()
        data.setdefault(namespace, {})[kind] = value
        _save_local(data)

    async def retrieve(self, namespace: str) -> Dict[str, Any]:
        if self.use_synap:
            try:
                return await self._synap_retrieve(namespace)
            except Exception:
                pass
        return _load_local().get(namespace, {})

    # --- TODO: replace with the real Maximem Synap SDK calls ---
    async def _synap_store(self, namespace: str, kind: str, value: Any) -> None:
        import httpx
        async with httpx.AsyncClient(timeout=20) as c:
            await c.post(
                f"{config.SYNAP_BASE_URL}/store",
                headers={"Authorization": f"Bearer {config.SYNAP_API_KEY}"},
                json={"namespace": namespace, "kind": kind, "value": value},
            )

    async def _synap_retrieve(self, namespace: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(
                f"{config.SYNAP_BASE_URL}/retrieve",
                headers={"Authorization": f"Bearer {config.SYNAP_API_KEY}"},
                params={"namespace": namespace},
            )
            return r.json() if r.status_code == 200 else {}


memory = Memory()
