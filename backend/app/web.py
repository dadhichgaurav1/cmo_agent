"""EXA web search (via REST so it's natively async)."""
from typing import List

import httpx

from app import config
from app.schemas import ResearchFinding

EXA_SEARCH = "https://api.exa.ai/search"


async def exa_search(query: str, num: int = 5) -> List[ResearchFinding]:
    if not config.has(config.EXA_API_KEY):
        return []
    payload = {
        "query": query,
        "numResults": num,
        "contents": {"text": {"maxCharacters": 800}},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                EXA_SEARCH,
                headers={
                    "x-api-key": config.EXA_API_KEY,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []
    out: List[ResearchFinding] = []
    for item in data.get("results", [])[:num]:
        out.append(
            ResearchFinding(
                title=item.get("title") or item.get("url", ""),
                url=item.get("url", ""),
                snippet=(item.get("text") or "")[:600],
                source="exa",
            )
        )
    return out
