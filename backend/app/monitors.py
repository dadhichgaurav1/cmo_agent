"""Addendum 1 — store + scheduler for the agent's self-identified recurring monitors.

The agent decides (in graph.monitor_plan) which signals to watch recurringly. Those jobs are
persisted — to Supabase when configured, else a local JSON file — and registered with an
in-process APScheduler so they auto-execute, plus a manual "run now" path so the compounding
story is demoable on demand. Each run writes a changelog entry (the delta against Synap), which
the Monitors tab reads.

Everything is scoped by (org_id, company_slug) so monitors never bleed across tenants. A
`_runner` coroutine is injected by main.py at startup to avoid a graph<->monitors import cycle.

NOTE: the in-process scheduler is still single-instance — it does not survive horizontal
scaling or restarts cleanly. Moving it to a dedicated worker / external scheduler is the next
step once the DB-backed store below is in place (the store makes that migration straightforward).
"""
import json
import os
from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Optional

from app import config, db
from app.tenancy import customer_scope

_STORE = os.getenv("MONITORS_PATH", "/tmp/cmo_monitors.json")
_CHANGELOG = os.getenv("CHANGELOG_PATH", "/tmp/cmo_changelog.json")

# daily | weekly | monthly -> interval seconds for APScheduler
CADENCE_SECONDS = {"daily": 86400, "weekly": 604800, "monthly": 2592000}

_runner: Optional[Callable[[Optional[str], str, dict], Awaitable[dict]]] = None
_scheduler = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(org_id: Optional[str], slug: str) -> str:
    return customer_scope(org_id, slug)


def _read(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _write(path: str, data: dict) -> None:
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


# --- monitor plans ---
def save_plan(org_id: Optional[str], slug: str, jobs: List[dict]) -> None:
    if db.enabled() and org_id:
        db.save_monitor(org_id, slug, jobs)
    else:
        data = _read(_STORE)
        data[_key(org_id, slug)] = {"org_id": org_id, "slug": slug, "jobs": jobs, "updated_at": now_iso()}
        _write(_STORE, data)
    if _scheduler is not None:
        _schedule_slug(org_id, slug, jobs)


def get_plan(org_id: Optional[str], slug: str) -> dict:
    if db.enabled() and org_id:
        row = db.get_monitor(org_id, slug)
        return {"jobs": row.get("jobs", []), "updated_at": row.get("updated_at", "")} if row else {"jobs": [], "updated_at": ""}
    return _read(_STORE).get(_key(org_id, slug), {"jobs": [], "updated_at": ""})


def all_monitors() -> List[dict]:
    """Every stored monitor as {org_id, slug, jobs} — used to register the scheduler at startup."""
    if db.enabled():
        return [{"org_id": r.get("org_id"), "slug": r.get("company_slug"), "jobs": r.get("jobs", [])}
                for r in db.all_monitors()]
    out = []
    for rec in _read(_STORE).values():
        out.append({"org_id": rec.get("org_id"), "slug": rec.get("slug"), "jobs": rec.get("jobs", [])})
    return out


# --- changelog ---
def append_changelog(org_id: Optional[str], slug: str, entry: dict) -> None:
    if db.enabled() and org_id:
        db.append_monitor_event(org_id, slug, entry)
        return
    data = _read(_CHANGELOG)
    k = _key(org_id, slug)
    data.setdefault(k, []).insert(0, entry)  # newest first
    data[k] = data[k][:50]
    _write(_CHANGELOG, data)


def get_changelog(org_id: Optional[str], slug: str) -> List[dict]:
    if db.enabled() and org_id:
        return db.get_monitor_events(org_id, slug)
    return _read(_CHANGELOG).get(_key(org_id, slug), [])


# --- scheduler wiring ---
def set_runner(fn: Callable[[Optional[str], str, dict], Awaitable[dict]]) -> None:
    global _runner
    _runner = fn


def redis_enabled() -> bool:
    return bool(config.REDIS_URL)


def start_scheduler() -> bool:
    """Start the in-process scheduler and register every stored monitor. Best-effort.

    No-op when Redis is configured — the dedicated Arq worker (app/worker.py) owns scheduled
    execution then, so running APScheduler here too would double-fire.
    """
    global _scheduler
    if redis_enabled():
        return False
    if _scheduler is not None:
        return True
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
    except Exception:
        _scheduler = None
        return False
    for m in all_monitors():
        _schedule_slug(m.get("org_id"), m.get("slug"), m.get("jobs", []))
    return True


def _job_id(org_id: Optional[str], slug: str, job: dict) -> str:
    return f"{_key(org_id, slug)}::{job.get('name', '')}"


def _schedule_slug(org_id: Optional[str], slug: str, jobs: List[dict]) -> None:
    if _scheduler is None:
        return
    from apscheduler.triggers.interval import IntervalTrigger
    for job in jobs:
        secs = CADENCE_SECONDS.get(job.get("cadence", "weekly"), 604800)
        jid = _job_id(org_id, slug, job)
        try:
            _scheduler.add_job(
                _fire, IntervalTrigger(seconds=secs), id=jid, replace_existing=True,
                args=[org_id, slug, job], misfire_grace_time=3600, coalesce=True,
            )
        except Exception:
            pass


async def _fire(org_id: Optional[str], slug: str, job: dict) -> None:
    if _runner is not None:
        try:
            await _runner(org_id, slug, job)
        except Exception:
            pass


async def run_now(org_id: Optional[str], slug: str) -> List[dict]:
    """Manually execute every monitor for a company and return the changelog entries produced."""
    if _runner is None:
        return []
    results = []
    for job in get_plan(org_id, slug).get("jobs", []):
        try:
            entry = await _runner(org_id, slug, job)
            if entry:
                results.append(entry)
        except Exception:
            pass
    return results
