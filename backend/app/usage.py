"""Plan quotas + cost caps.

We proxy paid APIs per user, so every billable action is metered into `usage_events` and gated
against the org's plan limits for the current calendar month. In demo mode (no org_id) nothing is
limited. An org can also be hard-disabled via org_settings.settings.disabled (abuse kill-switch).

Limits are per calendar month; `None` means unlimited. Tune freely — they're plain data.
"""
from datetime import datetime, timezone

from app import db

# kind -> monthly cap. None = unlimited.
PLAN_LIMITS = {
    "free": {"run": 10, "chat": 200, "research": 50, "monitor": 50},
    "pro":  {"run": None, "chat": None, "research": None, "monitor": None},
}


def _month_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


def org_disabled(org_id) -> bool:
    return bool(db.get_org_settings(org_id).get("disabled"))


def plan_for(org_id) -> str:
    return db.get_org(org_id).get("plan") or "free"


def quota(org_id, kind: str) -> dict:
    """{allowed, used, limit, plan} for `kind` this month. allowed=True when under/unlimited/demo."""
    if not org_id:  # demo / single-tenant mode — no limits
        return {"allowed": True, "used": 0, "limit": None, "plan": "demo"}
    plan = plan_for(org_id)
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]).get(kind)
    used = db.usage_count(org_id, kind, _month_start_iso())
    allowed = limit is None or used < limit
    return {"allowed": allowed, "used": used, "limit": limit, "plan": plan}


def all_quotas(org_id) -> dict:
    return {kind: quota(org_id, kind) for kind in ("run", "chat", "research", "monitor")}
