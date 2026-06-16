"""Plan entitlements — metered quotas (with a period) + capability flags + cost caps.

We proxy paid APIs per user, so every billable action is metered into `usage_events` and gated
against the org's plan for the current window. The plan has two axes:

  * quotas    — countable actions, each capped over a rolling window (day | week | month).
                `None` = unlimited (subject only to the silent FAIR_USE backstop below).
  * features  — boolean capabilities (monitors firing, agentic chat) + numeric caps (companies).

Free is the cold-start + manual loop; Pro is the engine that keeps the board full. The habit
(shipping cards, momentum, streaks, Daily Edge) is never metered — only the expensive generative
engine (runs/research) and the recurring freshness engine (monitors firing) are.

In demo mode (no org_id) nothing is limited and every capability is on. An org can also be
hard-disabled via org_settings.settings.disabled (abuse kill-switch). Limits are plain data —
tune freely.
"""
from datetime import datetime, timedelta, timezone

from app import db

_EPOCH = "1970-01-01T00:00:00+00:00"

# plan -> {"quotas": {kind: (limit, period)}, "features": {...}}
# period ∈ {"day","week","month"}. limit None = unlimited (see FAIR_USE).
PLANS = {
    "free": {
        "quotas": {
            "run":      (1,  "week"),   # one strategic run a week (+ ONBOARDING_RUNS to start)
            "chat":     (10, "day"),    # advise freely, but bounded
            "research": (5,  "day"),
            "monitor":  (0,  "month"),  # monitors are creatable but never fire (capability gate)
        },
        "features": {
            "monitors_active": False,   # the daily feeder / scheduled monitor fire
            "agent_actions":   False,   # chat that *acts* (kicks off autonomous multi-step work)
            "companies_max":   1,
        },
    },
    "pro": {
        "quotas": {
            "run":      (None, "month"),
            "chat":     (None, "day"),
            "research": (None, "day"),
            "monitor":  (None, "month"),
        },
        "features": {
            "monitors_active": True,
            "agent_actions":   True,
            "companies_max":   None,
        },
    },
}

# Silent abuse backstop applied to "unlimited" (None) paid meters — this is "fair usage limits
# apply", NOT a marketed number. Protects the LLM/Exa/Browserbase bill from the pathological tail.
FAIR_USE = {"run": 200, "research": 6000, "monitor": 3000}  # per calendar month

# First runs are free regardless of the weekly cadence — day-one fix-the-URL-and-rerun shouldn't
# burn the single weekly run before the founder has even seen a full board.
ONBOARDING_RUNS = 3

_KINDS = ("run", "chat", "research", "monitor")


def _window_start_iso(period: str) -> str:
    now = datetime.now(timezone.utc)
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":  # Monday 00:00 UTC
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # month
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat()


def _plan(plan: str) -> dict:
    return PLANS.get(plan, PLANS["free"])


def _resolve(plan: str, kind: str):
    """(limit, period) for a kind, applying the FAIR_USE backstop to unlimited paid meters."""
    limit, period = _plan(plan)["quotas"].get(kind, (None, "month"))
    if limit is None and kind in FAIR_USE:
        return FAIR_USE[kind], "month"
    return limit, period


def org_disabled(org_id) -> bool:
    return bool(db.get_org_settings(org_id).get("disabled"))


def plan_for(org_id) -> str:
    return db.get_org(org_id).get("plan") or "free"


def features(plan: str) -> dict:
    return _plan(plan)["features"]


def can(org_id, feature: str) -> bool:
    """Capability check. Demo/single-tenant (no org_id) gets every capability."""
    if not org_id:
        return True
    return bool(features(plan_for(org_id)).get(feature))


def company_limit(org_id):
    """Max distinct companies (int), or None for unlimited / demo."""
    if not org_id:
        return None
    return features(plan_for(org_id)).get("companies_max")


def quota(org_id, kind: str) -> dict:
    """{allowed, used, limit, plan, period} for `kind` in its window. Demo => always allowed."""
    if not org_id:  # demo / single-tenant mode — no limits
        return {"allowed": True, "used": 0, "limit": None, "plan": "demo", "period": "month"}
    plan = plan_for(org_id)
    limit, period = _resolve(plan, kind)
    # Onboarding burst: free runs are free until ONBOARDING_RUNS lifetime runs are used.
    if plan == "free" and kind == "run" and limit is not None:
        lifetime = db.usage_count(org_id, "run", _EPOCH)
        if lifetime < ONBOARDING_RUNS:
            return {"allowed": True, "used": lifetime, "limit": None, "plan": plan,
                    "period": "onboarding", "onboarding_left": ONBOARDING_RUNS - lifetime}
    used = db.usage_count(org_id, kind, _window_start_iso(period))
    allowed = limit is None or used < limit
    return {"allowed": allowed, "used": used, "limit": limit, "plan": plan, "period": period}


def all_quotas(org_id) -> dict:
    return {kind: quota(org_id, kind) for kind in _KINDS}


def entitlements(org_id) -> dict:
    """Full plan view for the frontend: plan + quotas + capability flags."""
    plan = plan_for(org_id) if org_id else "demo"
    return {"plan": plan, "org_id": org_id, "quotas": all_quotas(org_id),
            "features": features(plan) if org_id else PLANS["pro"]["features"]}
