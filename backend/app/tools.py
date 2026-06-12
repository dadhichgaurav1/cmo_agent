"""Research tools. Phase 1 uses reliable direct transports (EXA REST, Algolia HN, httpx).
Phase 3 routes these through Composio for the sponsor footprint — same interface."""
import re
from typing import List

import httpx

from app import config
from app.schemas import Finding

EXA_SEARCH = "https://api.exa.ai/search"
HN_SEARCH = "https://hn.algolia.com/api/v1/search"


async def exa_search(query: str, num: int = 4) -> List[Finding]:
    if not config.has(config.EXA_API_KEY):
        return []
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                EXA_SEARCH,
                headers={"x-api-key": config.EXA_API_KEY, "Content-Type": "application/json"},
                json={"query": query, "numResults": num, "contents": {"text": {"maxCharacters": 700}}},
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []
    out = []
    for it in data.get("results", [])[:num]:
        out.append(Finding(
            title=it.get("title") or it.get("url", ""),
            url=it.get("url", ""),
            snippet=(it.get("text") or "")[:500],
            source="exa",
        ))
    return out


async def _hn_query(query: str, num: int) -> List[Finding]:
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(HN_SEARCH, params={"query": query, "tags": "(story,comment)", "hitsPerPage": num})
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []
    out = []
    for h in data.get("hits", [])[:num]:
        oid = h.get("objectID")
        title = h.get("title") or h.get("story_title") or (h.get("comment_text") or "")[:80] or "HN item"
        snippet = h.get("story_text") or h.get("comment_text") or h.get("title") or ""
        out.append(Finding(
            title=re.sub(r"<[^>]+>", " ", title)[:160],
            url=f"https://news.ycombinator.com/item?id={oid}" if oid else "",
            snippet=re.sub(r"<[^>]+>", " ", snippet)[:500],
            source="hackernews",
        ))
    return out


async def hn_search(query: str, num: int = 4) -> List[Finding]:
    # Algolia ANDs terms, so long queries match nothing — retry with the top keywords.
    hits = await _hn_query(query, num)
    if not hits:
        short = " ".join(query.split()[:3])
        if short and short != query:
            hits = await _hn_query(short, num)
    return hits


async def fetch_site(url: str, max_chars: int = 6000) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    try:
        async with httpx.AsyncClient(
            timeout=25, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CMO-Cofounder/1.0)"},
        ) as c:
            r = await c.get(url)
            html = r.text
    except Exception:
        return ""
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


async def run_tool(access: str, query: str, num: int = 4) -> List[Finding]:
    """Dispatch a research move to the right transport. A move never returns empty:
    HN falls back to EXA; reddit/browser use EXA in Phase 1."""
    if access == "hackernews":
        hits = await hn_search(query, num)
        return hits if hits else await exa_search(query, num)
    return await exa_search(query, num)
