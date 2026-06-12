"""Addendum 1 — store + scheduler for the agent's self-identified recurring monitors.

The agent decides (in graph.monitor_plan) which signals to watch recurringly. Those jobs are
persisted here and registered with an in-process APScheduler so they auto-execute, plus a
manual "run now" path so the compounding story is demoable on demand. Each run writes a
changelog entry (the delta against Synap), which the Monitors tab reads.

A `_runner` coroutine is injected by main.py at startup to avoid a graph<->monitors import cycle.
"""
import json
import os
from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Optional

_STORE = os.getenv("MONITORS_PATH", "/tmp/cmo_monitors.json")
_CHANGELOG = os.getenv("CHANGELOG_PATH", "/tmp/cmo_changelog.json")

# daily | weekly | monthly -> interval seconds for APScheduler
CADENCE_SECONDS = {"daily": 86400, "weekly": 604800, "monthly": 2592000}

_runner: Optional[Callable[[str, dict], Awaitable[dict]]] = None
_scheduler = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
def save_plan(slug: str, jobs: List[dict]) -> None:
    data = _read(_STORE)
    data[slug] = {"jobs": jobs, "updated_at": now_iso()}
    _write(_STORE, data)
    if _scheduler is not None:
        _schedule_slug(slug, jobs)


def get_plan(slug: str) -> dict:
    return _read(_STORE).get(slug, {"jobs": [], "updated_at": ""})


def all_slugs() -> List[str]:
    return list(_read(_STORE).keys())


# --- changelog ---
def append_changelog(slug: str, entry: dict) -> None:
    data = _read(_CHANGELOG)
    data.setdefault(slug, []).insert(0, entry)  # newest first
    data[slug] = data[slug][:50]
    _write(_CHANGELOG, data)


def get_changelog(slug: str) -> List[dict]:
    return _read(_CHANGELOG).get(slug, [])


# --- scheduler wiring ---
def set_runner(fn: Callable[[str, dict], Awaitable[dict]]) -> None:
    global _runner
    _runner = fn


def start_scheduler() -> bool:
    """Start the in-process scheduler and register every stored monitor. Best-effort."""
    global _scheduler
    if _scheduler is not None:
        return True
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
    except Exception:
        _scheduler = None
        return False
    for slug in all_slugs():
        _schedule_slug(slug, get_plan(slug).get("jobs", []))
    return True


def _job_id(slug: str, job: dict) -> str:
    return f"{slug}::{job.get('name', '')}"


def _schedule_slug(slug: str, jobs: List[dict]) -> None:
    if _scheduler is None:
        return
    from apscheduler.triggers.interval import IntervalTrigger
    for job in jobs:
        secs = CADENCE_SECONDS.get(job.get("cadence", "weekly"), 604800)
        jid = _job_id(slug, job)
        try:
            _scheduler.add_job(
                _fire, IntervalTrigger(seconds=secs), id=jid, replace_existing=True,
                args=[slug, job], misfire_grace_time=3600, coalesce=True,
            )
        except Exception:
            pass


async def _fire(slug: str, job: dict) -> None:
    if _runner is not None:
        try:
            await _runner(slug, job)
        except Exception:
            pass


async def run_now(slug: str) -> List[dict]:
    """Manually execute every monitor for a company and return the changelog entries produced."""
    if _runner is None:
        return []
    results = []
    for job in get_plan(slug).get("jobs", []):
        try:
            entry = await _runner(slug, job)
            if entry:
                results.append(entry)
        except Exception:
            pass
    return results
