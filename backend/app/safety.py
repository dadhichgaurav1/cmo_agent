"""Lightweight, zero-cost guardrail for agent-drafted posts.

The agent drafts replies the founder will post *under their own identity* on communities — Reddit,
Hacker News and Indie Hackers especially — that ban self-promotion aggressively. A founder getting
shadowbanned on day one is the worst possible first impression for a marketing tool, so every draft
carries a `review` note: a standing "post as yourself, follow the room's rules" reminder plus a few
heuristic flags for the smells that get posts removed. No LLM call — pure string checks.

This is a nudge, not a filter: we never block a draft, we surface what to double-check before posting.
"""
import re

# Communities where overt self-promotion / link-dropping is policed hardest.
_STRICT = {"reddit", "hackernews", "indiehackers"}

_NORMS = {
    "reddit": "Reddit removes drive-by promotion. Add real value to the thread, disclose if it's your product, and don't lead with a link.",
    "hackernews": "HN flags marketing fast. Be substantive and neutral, skip superlatives, and only link if it genuinely helps.",
    "indiehackers": "IH is founder-friendly but anti-spam. Share the lesson, not the pitch; disclose your affiliation.",
    "x": "Keep it human and specific; threads that read like ads get ignored.",
    "linkedin": "Lead with the insight, not the CTA; disclose affiliation where relevant.",
}
_DEFAULT_NORM = "Post this as yourself and follow the community's rules — it's a draft, not an auto-post."

_PROMO = re.compile(r"\b(check (it|us|this) out|sign ?up|our (product|tool|app|platform)|we built|"
                    r"try (it|us|our)|join (our|the) waitlist|use code|dm me|link in)\b", re.I)
_HYPE = re.compile(r"\b(revolutionary|game[- ]changer|best[- ]in[- ]class|cutting[- ]edge|"
                   r"world[- ]class|10x|skyrocket|unleash)\b", re.I)
_URL = re.compile(r"https?://", re.I)


def review_draft(body: str, platform: str) -> dict:
    """Return {level, flags, note} for a drafted post. level ∈ {ok, caution}."""
    text = body or ""
    plat = (platform or "").lower()
    flags = []
    if _PROMO.search(text):
        flags.append("Reads promotional — lead with genuine value, not a pitch.")
    if _HYPE.search(text):
        flags.append("Hype words may trip spam filters — make it plainer.")
    links = len(_URL.findall(text))
    if links and plat in _STRICT:
        flags.append("Contains a link — on this platform, only link if it truly helps and you've disclosed your affiliation.")
    if links > 1:
        flags.append("Multiple links read as spam — keep to at most one.")
    note = _NORMS.get(plat, _DEFAULT_NORM)
    return {"level": "caution" if flags else "ok", "flags": flags, "note": note}
