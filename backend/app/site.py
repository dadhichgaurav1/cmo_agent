"""Fetch and clean the founder's own website text."""
import re

import httpx


async def fetch_site_text(url: str, max_chars: int = 6000) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    try:
        async with httpx.AsyncClient(
            timeout=25,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CMO-Agent/1.0)"},
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
