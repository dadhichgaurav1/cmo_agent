"""Momentum — the founder activation score.

Counts the *brave* act (hitting send), weights it by courage, keeps a ship-streak, and
evolves an operator persona. The whole point is activation: the points math is lopsided
toward `card_posted` on purpose so the founder gets dragged toward the one act the GTM
research says is the unlock and the fear — being seen (StratCMO_GTM_Problem_Map.md §7).

Design: pure-ish module, no FastAPI imports. Streak/multiplier math takes `today`/`tz` as
inputs (never reads the clock deep inside) so it stays unit-testable. `award()` is wrapped
to never raise — a scoring failure must never break the underlying card PATCH.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app import config
from app import db

# --- tunables -------------------------------------------------------------
FREEZE_MAX = 2
GRACE_HOURS = 4          # a ship before 4am local counts for the previous day
COLD_START_SHIPS = 3     # first N ships ever get the cold-start multiplier
UNURLED_SHIP_CAP = 10    # max self-reported (no posted_url) ships that score per day

# Base points per scoreable transition (the lopsided-toward-send table).
BASE_PTS = {
    "lesson_read": 1,
    "card_reviewed": 3,    # suggested -> drafted, WITH a real edit
    "card_approved": 5,
    "card_posted": 20,     # THE SEND — the activation target
    "card_engaged": 10,    # bonus, outcome-ish, never gates streak/persona
    "lesson_applied": 10,  # a lesson's CTA card got shipped
}

# Persona ladder: (key, title, min_ships, min_platforms, min_streak, blurb).
# The only way up is to keep shipping AND conquer new platforms — a map of the §7 mindset journey.
PERSONA_LADDER = [
    ("lurker",                "Lurker",                 0,   0, 0,  "You've been reading. Time to be read."),
    ("first_blood",           "First Blood",            1,   0, 0,  "You hit send. That's more than most ever do."),
    ("poster",                "Poster",                 5,   0, 0,  "You're showing up. The grind has begun."),
    ("regular",               "Regular",                15,  2, 0,  "People are starting to see your name around."),
    ("operator",              "Operator",               40,  3, 10, "You market now. This is a muscle, and it's growing."),
    ("distribution_machine",  "Distribution Machine",   100, 4, 20, "Distribution is your moat — and you built it."),
]


# --- time helpers ---------------------------------------------------------
def _tzinfo(tz: Optional[str]):
    if not tz:
        return timezone.utc
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz)
    except Exception:
        return timezone.utc


def day_key(tz: Optional[str], now: Optional[datetime] = None) -> date:
    """The founder-local day a moment belongs to, with the early-morning grace window."""
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(_tzinfo(tz)) - timedelta(hours=GRACE_HOURS)
    return local.date()


def _as_date(v) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


# --- transition classification (what kind of event a card change is) ------
def classify_transition(prev_card: dict, patch: dict) -> Optional[str]:
    """Map a card state change to a scoreable event kind. None if not scoreable.

    Idempotent: a PATCH that doesn't move state forward (e.g. re-saving a posted card)
    scores nothing — guards against double-award.
    """
    new_state = patch.get("state")
    if not new_state:
        return None
    prev_state = (prev_card or {}).get("state")
    if new_state == prev_state:
        return None  # no forward motion -> no award

    if new_state == "drafted" and prev_state in (None, "suggested"):
        # card_reviewed only counts with a real edit (anti-gaming §5.5)
        new_body = patch.get("body")
        if new_body is None or new_body == (prev_card or {}).get("body", ""):
            return None
        return "card_reviewed"
    if new_state == "approved":
        return "card_approved"
    if new_state == "posted":
        return "card_posted"
    if new_state == "engaged" and prev_state == "posted":
        return "card_engaged"
    return None


# --- streak math (pure) ---------------------------------------------------
def apply_ship_to_streak(last_active: Optional[date], streak: int, freezes: int,
                         today: date) -> dict:
    """Update the ship-streak for a ship landing on `today`. Returns the new streak fields
    plus whether this counts as a comeback (first ship after a gap/freeze)."""
    comeback = False
    if last_active is None:
        streak = 1
    elif last_active == today:
        pass  # already shipped today; streak unchanged
    elif last_active == today - timedelta(days=1):
        streak += 1
    else:
        missed = (today - last_active).days - 1  # full days skipped
        if 0 < missed <= freezes:
            freezes -= missed     # spend freezes to bridge the gap
            streak += 1
            comeback = True
        else:
            streak = 1            # real break -> reset (gently, in copy)
            comeback = True

    # refill: +1 freeze each time the streak crosses a multiple of 7
    if streak > 0 and streak % 7 == 0 and freezes < FREEZE_MAX:
        freezes += 1
    return {"current_streak": streak, "freezes_left": min(freezes, FREEZE_MAX),
            "comeback": comeback, "last_active_day": today.isoformat()}


def streak_multiplier(streak: int) -> float:
    """+5% per current-streak day, capped at x2.0 (reached at a 20-day streak)."""
    return min(2.0, 1.0 + 0.05 * max(0, streak))


# --- persona --------------------------------------------------------------
def resolve_persona(ships: int, platforms: int, streak: int) -> tuple[str, str, str]:
    """Highest ladder tier satisfied by (ships, platform breadth, streak)."""
    chosen = PERSONA_LADDER[0]
    for tier in PERSONA_LADDER:
        _, _, min_ships, min_pf, min_streak, _ = tier
        if ships >= min_ships and platforms >= min_pf and streak >= min_streak:
            chosen = tier
    return chosen[0], chosen[1], chosen[5]


# --- the award entrypoint -------------------------------------------------
def award(org_id: Optional[str], user_id: Optional[str], card: dict,
          kind: Optional[str], tz: Optional[str], now: Optional[datetime] = None) -> Optional[dict]:
    """Resolve points for a transition, write the event, recompute state. Never raises.

    Returns the award payload for the PATCH response (so the UI can toast), or None when
    nothing was awarded (flag off, db disabled, no-op transition, gamed action)."""
    if not config.MOMENTUM_ENABLED or not kind or not db.enabled() or not org_id:
        return None
    try:
        return _award(org_id, user_id, card, kind, tz, now)
    except Exception:
        return None  # scoring must never break the card PATCH


def _award(org_id, user_id, card, kind, tz, now) -> Optional[dict]:
    slug = card.get("company_slug") or ""
    platform = card.get("platform") or ""
    today = day_key(tz, now)
    state = db.get_momentum(org_id, slug) or {}
    ships_total = int(state.get("ships_total") or 0)
    platforms_shipped = list(state.get("platforms_shipped") or [])

    base = BASE_PTS.get(kind, 0)
    if base <= 0:
        return None

    # Reading the Edge scores once per day (anti-gaming §5.5).
    if kind == "lesson_read":
        todays = db.list_events(org_id, slug, since=today.isoformat())
        if any(e.get("kind") == "lesson_read" for e in todays):
            return None

    breakdown = [f"{base} base"]
    bonus = 0
    new_streak_fields: dict = {}
    is_ship = kind == "card_posted"

    if is_ship:
        # anti-gaming: cap self-reported (no posted_url) ships per day
        if not card.get("posted_url"):
            todays = db.list_events(org_id, slug, since=today.isoformat())
            unurled = sum(1 for e in todays
                          if e.get("kind") == "card_posted"
                          and not (e.get("metadata") or {}).get("posted_url"))
            if unurled >= UNURLED_SHIP_CAP:
                return None

        # courage bonuses
        if card.get("kind") == "post":
            bonus += 15; breakdown.append("+15 original (your name on it)")
        first_on_platform = platform and platform not in platforms_shipped
        if first_on_platform:
            bonus += 25; breakdown.append(f"+25 first time on {platform}")

        # streak update (drives the multiplier)
        new_streak_fields = apply_ship_to_streak(
            _as_date(state.get("last_active_day")),
            int(state.get("current_streak") or 0),
            int(state.get("freezes_left") if state.get("freezes_left") is not None else FREEZE_MAX),
            today,
        )
        streak = new_streak_fields["current_streak"]

        mult = 1.0
        if streak > 1:  # only apply (and show) a streak bonus once there's a real streak
            mult *= streak_multiplier(streak)
            breakdown.append(f"x{streak_multiplier(streak):.2f} streak ({streak} days)")
        # variety: shipping on a platform not yet shipped *today*
        todays = db.list_events(org_id, slug, since=today.isoformat())
        platforms_today = {e.get("platform") for e in todays if e.get("kind") == "card_posted"}
        if platform and platform not in platforms_today:
            mult *= 1.5; breakdown.append("x1.5 new platform today")
        # cold-start: front-load the first 3 ships ever
        if ships_total < COLD_START_SHIPS:
            mult *= 2.0; breakdown.append("x2 first ships")
        # comeback
        if new_streak_fields.get("comeback"):
            mult *= 1.5; breakdown.append("x1.5 welcome back")
    else:
        mult = 1.0
        first_on_platform = False

    points = max(0, round((base + bonus) * mult))
    if points <= 0:
        return None

    # write the event
    db.record_event(org_id, {
        "user_id": user_id, "company_slug": slug, "kind": kind,
        "card_id": card.get("id"), "platform": platform or None,
        "points": points, "multiplier": round(mult, 3), "day_key": today.isoformat(),
        "metadata": {"original": card.get("kind") == "post", "first_on_platform": bool(first_on_platform),
                     "posted_url": card.get("posted_url") or "", "breakdown": breakdown},
    })

    # recompute the cached rollup
    prev_persona = state.get("persona_key", "lurker")
    new_state = _next_state(state, kind, platform, points, today, new_streak_fields, is_ship)
    db.upsert_momentum_state(org_id, slug, new_state)

    award_payload = {
        "awarded": points,
        "kind": kind,
        "breakdown": breakdown,
        "total_points": new_state["total_points"],
        "current_streak": new_state["current_streak"],
        "streak_safe": is_ship,  # shipping today keeps the flame lit
        "persona_key": new_state["persona_key"],
    }
    if new_state["persona_key"] != prev_persona and is_ship:
        _, title, blurb = resolve_persona(new_state["ships_total"],
                                          len(new_state["platforms_shipped"]),
                                          new_state["current_streak"])
        award_payload["leveled_up"] = {"from": prev_persona, "to": new_state["persona_key"],
                                       "title": title, "blurb": blurb}
    return award_payload


def _next_state(state: dict, kind: str, platform: str, points: int, today: date,
                streak_fields: dict, is_ship: bool) -> dict:
    """Build the upserted momentum_state row from the prior row + this event."""
    ships_total = int(state.get("ships_total") or 0)
    platforms_shipped = list(state.get("platforms_shipped") or [])
    current_streak = int(state.get("current_streak") or 0)
    longest = int(state.get("longest_streak") or 0)
    freezes = int(state.get("freezes_left") if state.get("freezes_left") is not None else FREEZE_MAX)
    last_active = state.get("last_active_day")

    if is_ship:
        ships_total += 1
        if platform and platform not in platforms_shipped:
            platforms_shipped.append(platform)
        current_streak = streak_fields["current_streak"]
        freezes = streak_fields["freezes_left"]
        last_active = streak_fields["last_active_day"]
        longest = max(longest, current_streak)

    persona_key, _, _ = resolve_persona(ships_total, len(platforms_shipped), current_streak)
    # ships toward the next persona tier (for the progress bar)
    next_threshold = next((t[2] for t in PERSONA_LADDER if t[2] > ships_total), ships_total)

    return {
        "total_points": int(state.get("total_points") or 0) + points,
        "current_streak": current_streak,
        "longest_streak": longest,
        "freezes_left": freezes,
        "last_active_day": last_active,
        "persona_key": persona_key,
        "persona_progress": ships_total,
        "ships_total": ships_total,
        "ships_this_week": _ships_this_week(state, today, is_ship),
        "platforms_shipped": platforms_shipped,
    }


def _ships_this_week(state: dict, today: date, is_ship: bool) -> int:
    """Cheap rolling counter: reset on a new ISO week, otherwise increment on ships."""
    prev = int(state.get("ships_this_week") or 0)
    last = _as_date(state.get("last_active_day"))
    same_week = last is not None and last.isocalendar()[:2] == today.isocalendar()[:2]
    base = prev if same_week else 0
    return base + (1 if is_ship else 0)


def snapshot(org_id: Optional[str], slug: Optional[str], tz: Optional[str] = None) -> Optional[dict]:
    """Header-chip + page payload. None when the feature is off (frontend then hides it)."""
    if not config.MOMENTUM_ENABLED:
        return None
    state = db.get_momentum(org_id, slug or "") or {}
    ships = int(state.get("ships_total") or 0)
    persona_key, persona_title, persona_blurb = resolve_persona(
        ships, len(state.get("platforms_shipped") or []), int(state.get("current_streak") or 0),
    )
    next_tier = next((t for t in PERSONA_LADDER if t[2] > ships), None)
    return {
        "total_points": int(state.get("total_points") or 0),
        "current_streak": int(state.get("current_streak") or 0),
        "longest_streak": int(state.get("longest_streak") or 0),
        "freezes_left": int(state.get("freezes_left") if state.get("freezes_left") is not None else FREEZE_MAX),
        "ships_total": ships,
        "ships_this_week": int(state.get("ships_this_week") or 0),
        "platforms_shipped": list(state.get("platforms_shipped") or []),
        "persona_key": persona_key,
        "persona_title": persona_title,
        "persona_blurb": persona_blurb,
        "next_persona_at": next_tier[2] if next_tier else None,
        "next_persona_title": next_tier[1] if next_tier else None,
        "shipped_today": _as_date(state.get("last_active_day")) == day_key(tz),
    }
