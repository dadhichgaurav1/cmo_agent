"""Composio integration — routes Hacker News search through Composio's toolkit, making
web-use a genuine Composio action. Verified live: HACKERNEWS_SEARCH_POSTS returns Algolia hits.

Activates when COMPOSIO_API_KEY is valid; callers fall back to direct transports otherwise.
Reddit has no clean post-search action (only REDDIT_GET_SUBREDDITS_SEARCH), so reddit falls back to EXA.
"""
import asyncio
import re
from typing import List

from app import config
from app.schemas import Finding

SLUGS = {"hackernews": "HACKERNEWS_SEARCH_POSTS"}
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
    # Algolia (behind the HN toolkit) ANDs terms — retry with top keywords if a long query is empty.
    queries = [query]
    short = " ".join(query.split()[:3])
    if short and short != query:
        queries.append(short)
    for q in queries:
        try:
            def _call(qq=q):
                return client.tools.execute(
                    slug=slug,
                    arguments={"query": qq},
                    user_id=USER_ID,
                    dangerously_skip_version_check=True,
                )
            resp = await asyncio.to_thread(_call)
            hits = _parse_hn(resp)
            if hits:
                return hits[:num]
        except Exception:
            return []
    return []


def _parse_hn(resp) -> List[Finding]:
    data = resp.get("data") if isinstance(resp, dict) else getattr(resp, "data", {})
    hits = (data or {}).get("hits") or (data or {}).get("results") or []
    out: List[Finding] = []
    for h in hits:
        if not isinstance(h, dict):
            continue
        oid = h.get("objectID")
        title = h.get("title") or h.get("story_title") or (h.get("comment_text") or "")[:80] or "HN item"
        url = h.get("url") or (f"https://news.ycombinator.com/item?id={oid}" if oid else "")
        snippet = h.get("story_text") or h.get("comment_text") or h.get("title") or ""
        out.append(Finding(
            title=re.sub(r"<[^>]+>", " ", str(title))[:160],
            url=url,
            snippet=re.sub(r"<[^>]+>", " ", str(snippet))[:500],
            source="composio:hackernews",
        ))
    return out
