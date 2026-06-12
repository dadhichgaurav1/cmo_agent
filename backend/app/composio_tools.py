"""Composio integration — routes community searches (Hacker News / Reddit) through
Composio's toolkits, making web-use a genuine Composio action.

Activates automatically when COMPOSIO_API_KEY is valid; otherwise callers fall back
to the direct transports in tools.py. SDK: composio 1.x — `tools.execute(slug, arguments, user_id=)`.
"""
import asyncio
from typing import List

from app import config
from app.schemas import Finding

# Composio tool slugs (toolkit_action). Confirm against the live account once the key is valid:
#   python -c "from composio import Composio; \
#     print([t.slug for t in Composio().tools.get_raw_composio_tools(toolkits=['HACKERNEWS'])])"
SLUGS = {
    "hackernews": "HACKERNEWS_SEARCH_POSTS",
    "reddit": "REDDIT_SEARCH_ACROSS_SUBREDDITS",
}
USER_ID = "cmo-cofounder"

_client = None
_ok: bool | None = None


def _get_client():
    global _client, _ok
    if _ok is False:
        return None
    if _client is None:
        if not config.has(config.COMPOSIO_API_KEY):
            _ok = False
            return None
        try:
            from composio import Composio
            _client = Composio()
            _ok = True
        except Exception:
            _ok = False
            return None
    return _client


def available() -> bool:
    return _get_client() is not None


async def composio_search(toolkit: str, query: str, num: int = 4) -> List[Finding]:
    client = _get_client()
    slug = SLUGS.get(toolkit)
    if not client or not slug:
        return []
    try:
        def _call():
            return client.tools.execute(slug=slug, arguments={"query": query}, user_id=USER_ID)
        resp = await asyncio.to_thread(_call)
        return _parse(resp, toolkit)[:num]
    except Exception:
        return []


def _parse(resp, toolkit: str) -> List[Finding]:
    data = getattr(resp, "data", None)
    if data is None and isinstance(resp, dict):
        data = resp.get("data", resp)
    data = data or {}
    items = (data.get("results") or data.get("hits") or data.get("posts")
             or data.get("children") or data.get("data") or [])
    out: List[Finding] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(Finding(
            title=str(it.get("title") or it.get("story_title") or it.get("name") or "")[:160],
            url=it.get("url") or it.get("link") or it.get("permalink") or "",
            snippet=str(it.get("text") or it.get("selftext") or it.get("body") or it.get("story_text") or "")[:500],
            source=f"composio:{toolkit}",
        ))
    return out
