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
# Composio entity id. Per-org connected accounts use a per-org entity; the shared default covers
# no-auth tools (e.g. HN search) and local/demo mode.
DEFAULT_ENTITY = "cmo-cofounder"


def entity_for(org_id) -> str:
    return f"org-{org_id}" if org_id else DEFAULT_ENTITY

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


async def composio_search(toolkit: str, query: str, num: int = 4, entity_id: str = DEFAULT_ENTITY) -> List[Finding]:
    client = _get_client()
    slug = SLUGS.get(toolkit)
    if not client or not slug:
        return []
    entity_id = entity_id or DEFAULT_ENTITY
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
                    user_id=entity_id,
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


# --- Addendum 4: runtime tool discovery + binding over the full Composio catalogue ---

def discover(need: str, limit: int = 5) -> List[dict]:
    """Search the Composio tool catalogue for tools matching a capability the agent lacks.
    Returns lightweight candidate descriptors the model can choose from."""
    client = _get_client()
    if not client:
        return []
    try:
        items = client.tools.get_raw_composio_tools(search=need, limit=limit)
    except Exception:
        return []
    out: List[dict] = []
    for it in items or []:
        d = it if isinstance(it, dict) else (it.model_dump() if hasattr(it, "model_dump") else None)
        if not d:
            continue
        props = ((d.get("input_parameters") or {}).get("properties")) or {}
        out.append({
            "slug": d.get("slug") or d.get("name", ""),
            "description": str(d.get("description") or d.get("human_description") or "")[:300],
            "toolkit": (d.get("toolkit") or {}).get("slug") if isinstance(d.get("toolkit"), dict) else d.get("toolkit"),
            "no_auth": bool(d.get("no_auth")),
            "params": list(props.keys())[:12],
        })
    return out


async def execute_tool(slug: str, arguments: dict, num: int = 4, entity_id: str = DEFAULT_ENTITY) -> List[Finding]:
    """Execute an arbitrary discovered Composio tool and coerce its output into Findings."""
    client = _get_client()
    if not client or not slug:
        return []
    entity_id = entity_id or DEFAULT_ENTITY
    try:
        def _call():
            return client.tools.execute(
                slug=slug, arguments=arguments or {}, user_id=entity_id,
                dangerously_skip_version_check=True,
            )
        resp = await asyncio.to_thread(_call)
    except Exception:
        return []
    return _parse_generic(resp, slug)[:num]


def _as_dict(resp):
    if isinstance(resp, dict):
        return resp
    if hasattr(resp, "model_dump"):
        try:
            return resp.model_dump()
        except Exception:
            pass
    return {"data": getattr(resp, "data", {})}


def _collect_records(obj, depth=0):
    """Walk an arbitrary tool response and yield the first meaningful list of dict records."""
    if depth > 4:
        return []
    if isinstance(obj, list):
        dicts = [x for x in obj if isinstance(x, dict)]
        if dicts:
            return dicts
        for x in obj:
            found = _collect_records(x, depth + 1)
            if found:
                return found
        return []
    if isinstance(obj, dict):
        # prefer common collection keys
        for key in ("hits", "results", "items", "data", "posts", "issues", "edges", "children", "records"):
            if key in obj:
                found = _collect_records(obj[key], depth + 1)
                if found:
                    return found
        for v in obj.values():
            found = _collect_records(v, depth + 1)
            if found:
                return found
    return []


def _pick(d: dict, keys, default=""):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, dict):  # reddit-style {"title": ...} nesting handled by caller
            continue
    return default


def _parse_generic(resp, slug: str) -> List[Finding]:
    data = _as_dict(resp)
    records = _collect_records(data)
    out: List[Finding] = []
    for r in records:
        if not isinstance(r, dict):
            continue
        # unwrap reddit-style {"data": {...}} children
        inner = r.get("data") if isinstance(r.get("data"), dict) else r
        title = _pick(inner, ("title", "name", "story_title", "headline", "subject", "full_name"))
        url = _pick(inner, ("url", "html_url", "permalink", "link", "web_url"))
        if url.startswith("/r/") or url.startswith("/u/"):
            url = "https://www.reddit.com" + url
        snippet = _pick(inner, ("text", "selftext", "body", "description", "comment_text", "story_text", "abstract"))
        if not (title or snippet):
            continue
        out.append(Finding(
            title=re.sub(r"<[^>]+>", " ", str(title or url or "result"))[:160],
            url=str(url)[:400],
            snippet=re.sub(r"<[^>]+>", " ", str(snippet))[:500],
            source=f"composio:{slug.lower()}",
        ))
    return out
