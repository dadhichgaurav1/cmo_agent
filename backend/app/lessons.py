"""The Daily Edge — one tailored marketing-psychology lesson a day.

The whole defensibility is the tie-back: a generic "today's bias: social proof" is a
newsletter you mute in a week; "remember the cold email you drafted Tuesday — its second
line triggers the curse of knowledge" needs the founder's own work and can't be cloned
(StratCMO_GTM_Problem_Map.md §1, §9). So selection requires a real tie-back card; if none
clears the bar we fall back to a positioning-tied lesson, and if even that's thin we SKIP
the day rather than ship filler.

Lazy-on-read (v1): generated on demand by GET /api/edge, so correctness never depends on
the single-instance scheduler.
"""
from __future__ import annotations

import glob
import json
import os
from datetime import date
from typing import Optional

from app import db
from app import models
from app.schemas import LessonOut

LESSONS_DIR = os.path.join(os.path.dirname(__file__), "lessons")
NO_REPEAT_DAYS = 21
_principles_cache: Optional[list] = None


def load_principles() -> list:
    """Read the principle library once (mirrors skills.py's local loader)."""
    global _principles_cache
    if _principles_cache is not None:
        return _principles_cache
    out = []
    for path in sorted(glob.glob(os.path.join(LESSONS_DIR, "*.json"))):
        try:
            with open(path) as f:
                out.append(json.load(f))
        except Exception:
            continue
    _principles_cache = out
    return out


def _actionable(card: dict) -> bool:
    return card.get("state") in ("suggested", "drafted", "approved")


def _score_principle(principle: dict, body: str) -> int:
    blob = (body or "").lower()
    return sum(1 for hint in principle.get("applies_when", []) if hint in blob)


def _select(cards: list, recently_taught: set, profile: dict) -> tuple[Optional[dict], Optional[dict]]:
    """Pick (principle, tie_back_card). Card is None for a positioning-tied fallback.
    Returns (None, None) when nothing clears the bar -> skip the day."""
    principles = [p for p in load_principles() if p.get("key") not in recently_taught]
    if not principles:
        return None, None

    # Best (principle, card) pair by how strongly the principle matches a real draft body.
    best = (0, None, None)  # (score, principle, card)
    for card in cards:
        body = card.get("body") or ""
        if not body:
            continue
        for p in principles:
            s = _score_principle(p, body)
            if s > best[0]:
                best = (s, p, card)
    if best[0] > 0:
        return best[1], best[2]

    # Fallback: a positioning/GTM principle tied to the company, no specific card.
    if profile.get("name"):
        gtm = [p for p in principles if p.get("bucket") == "gtm"]
        if gtm:
            return gtm[0], None
    return None, None


_SYS = (
    "You are a sharp, encouraging marketing coach for a solo technical founder who finds "
    "marketing hard. Teach exactly ONE principle in ~110 words of plain, warm language — no "
    "jargon, no listicles, no fluff. Make it concrete to THEIR work using the example given. "
    "End the body with a single actionable fix sentence. The title must be specific and a "
    "little provocative, not generic."
)


def _human(principle: dict, card: Optional[dict], profile: dict) -> str:
    parts = [
        f"Principle to teach: {principle.get('one_liner')}",
        f"The fix pattern: {principle.get('fix_pattern')}",
        f"Company: {profile.get('name') or 'their startup'} — {profile.get('one_liner') or ''}",
    ]
    if card:
        excerpt = (card.get("body") or "")[:400]
        parts.append(
            f"Tie it to THIS draft the founder wrote for {card.get('platform')}: \"{excerpt}\". "
            "Quote a short phrase from it so they know exactly what you mean."
        )
    else:
        parts.append("No specific draft to tie to — tie it to their positioning instead.")
    parts.append("Write title, body (~110 words, ending in the fix), and a cta_label that nudges "
                 "them to apply it to a draft on their board (send-language, e.g. 'Sharpen that "
                 "draft and ship it').")
    return "\n".join(parts)


async def _generate(principle: dict, card: Optional[dict], profile: dict) -> Optional[LessonOut]:
    try:
        out, _ = await models.run_structured("draft", _SYS, _human(principle, card, profile), LessonOut)
        return out
    except Exception:
        return None


async def get_or_create_lesson(org_id: Optional[str], slug: str, today: date,
                               profile: Optional[dict] = None) -> Optional[dict]:
    """Today's lesson for a company. Returns the row, or None when the day is skipped
    (no real teachable moment — better than filler)."""
    if not db.enabled() or not org_id:
        return None
    existing = db.get_lesson_for_day(org_id, slug, today.isoformat())
    if existing:
        return existing

    if profile is None:
        try:
            from app import graph
            profile, _obj, _run = await graph._resolve_profile(org_id, slug)
        except Exception:
            profile = {}
    profile = profile or {}

    cards = db.list_cards(org_id, slug)
    recently_taught = {l.get("principle_key") for l in db.latest_lessons(org_id, slug, limit=NO_REPEAT_DAYS)}
    principle, tie_card = _select(cards, recently_taught, profile)
    if not principle:
        return None  # skip the day — no filler

    lesson = await _generate(principle, tie_card, profile)
    if not lesson or not lesson.body:
        return None

    # CTA: the tie-back card if still actionable, else the first actionable draft on the board.
    cta_card = tie_card if (tie_card and _actionable(tie_card)) else next((c for c in cards if _actionable(c)), None)
    row = {
        "company_slug": slug,
        "day_key": today.isoformat(),
        "principle_key": principle["key"],
        "title": lesson.title or principle["one_liner"],
        "body": lesson.body,
        "tie_back": {"card_id": tie_card.get("id"), "platform": tie_card.get("platform")} if tie_card else {},
        "cta_card_id": cta_card.get("id") if cta_card else None,
        "cta_label": lesson.cta_label or "Apply it to a draft on your board and ship it",
        "state": "unread",
    }
    return db.create_lesson(org_id, row) or row


def award_applied_for_card(org_id: Optional[str], user_id: Optional[str], card: dict, tz: Optional[str]):
    """When a card that was a lesson's CTA gets shipped, mark the lesson applied and award the
    lesson_applied bonus. Returns the award payload (or None)."""
    if not db.enabled() or not org_id or not card.get("id"):
        return None
    from app import momentum
    rows = db.lessons_for_cta(org_id, card["id"])
    if not rows:
        return None
    award = None
    for r in rows:
        db.mark_lesson(org_id, r["id"], "applied")
        award = momentum.award(org_id, user_id, card, "lesson_applied", tz)
    return award
