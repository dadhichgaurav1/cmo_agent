"""Action Board helpers: classify a draft to a platform swimlane, and seed cards
from a completed run's summary so the board has content the moment a run finishes.

A card is a specific place to post. Only *engagement* opportunities (the ones with a
thread_url) become cards — strategic "moves" stay on the Brief as moves, not posts.
"""
from typing import List, Optional

PLATFORMS = ["reddit", "hackernews", "x", "linkedin", "indiehackers", "other"]


def classify_platform(*hints: Optional[str]) -> str:
    """Map a channel / source_name / template_id / url to one of the board swimlanes."""
    blob = " ".join(h for h in hints if h).lower()
    if "reddit" in blob:
        return "reddit"
    if "indie" in blob:  # before 'hacker' — "indie hackers" must not match the HN branch
        return "indiehackers"
    if "hacker" in blob or "ycombinator" in blob or "news.yc" in blob or blob.strip() == "hn":
        return "hackernews"
    if "linkedin" in blob:
        return "linkedin"
    if "twitter" in blob or "x.com" in blob or blob.strip() == "x":
        return "x"
    return "other"


def cards_from_summary(slug: str, run_id: Optional[str], summary: dict) -> List[dict]:
    """Build card rows from a run summary's engagement opportunities + their drafts."""
    opps = (summary or {}).get("opportunities", []) or []
    artifacts = (summary or {}).get("artifacts", []) or []
    drafts_by_opp = {a.get("opportunity_id"): a for a in artifacts if a.get("opportunity_id")}

    cards: List[dict] = []
    for o in opps:
        if o.get("type") != "engagement":
            continue  # strategic moves aren't postable cards
        thread = o.get("thread_url") or ""
        art = drafts_by_opp.get(o.get("id"))
        platform = classify_platform(o.get("source_name"), o.get("template_id"),
                                     art.get("channel") if art else None, thread)
        body = (art.get("body") if art else "") or ""
        cards.append({
            "run_id": run_id or None,
            "company_slug": slug,
            "source": "agent",
            "platform": platform,
            "kind": "reply" if thread else "post",
            "target_url": thread or None,
            "target_title": o.get("title", ""),
            "title": o.get("title", ""),
            "body": body,
            "state": "drafted" if body else "suggested",
            "metadata": {"why": o.get("why", ""), "opportunity_id": o.get("id", "")},
        })
    return cards
