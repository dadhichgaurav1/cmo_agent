"""Arq background worker — runs scheduled monitors off the web process.

Enabled when REDIS_URL is set. Run it as a separate process:

    arq app.worker.WorkerSettings

A cron job (`sweep_monitors`) wakes every 15 minutes, loads every monitor from the DB, and
enqueues the ones that are due based on their cadence (last-fire timestamp tracked in Redis).
Each due monitor runs as a `run_monitor_task`, which calls the same graph.run_monitor used by the
manual "run now" path — so behavior is identical, just off the request path and durable across
restarts / multiple web instances.

When REDIS_URL is unset the web process falls back to the in-process APScheduler (see monitors.py).
"""
from datetime import datetime, timezone

from arq import cron
from arq.connections import RedisSettings

from app import config, monitors
from app.tenancy import customer_scope


async def run_monitor_task(ctx, org_id, slug, job):
    # Lazy import to keep the worker boot light and avoid an import cycle.
    from app import graph
    return await graph.run_monitor(org_id, slug, job)


async def sweep_monitors(ctx):
    """Enqueue every monitor whose cadence is due. Idempotent within a window via Redis stamps."""
    redis = ctx["redis"]
    now_ts = datetime.now(timezone.utc).timestamp()
    enqueued = 0
    for m in monitors.all_monitors():
        org_id, slug, jobs = m.get("org_id"), m.get("slug"), m.get("jobs", [])
        if not slug:
            continue
        for job in jobs:
            secs = monitors.CADENCE_SECONDS.get(job.get("cadence", "weekly"), 604800)
            key = f"monitor:last:{customer_scope(org_id, slug)}::{job.get('name', '')}"
            last = await redis.get(key)
            last_ts = float(last) if last else 0.0
            if now_ts - last_ts >= secs:
                await redis.enqueue_job("run_monitor_task", org_id, slug, job)
                await redis.set(key, now_ts)
                enqueued += 1
    return enqueued


def _redis_settings() -> RedisSettings:
    # Falls back to localhost so the module imports cleanly in tests without REDIS_URL.
    return RedisSettings.from_dsn(config.REDIS_URL or "redis://localhost:6379")


class WorkerSettings:
    functions = [run_monitor_task]
    cron_jobs = [cron(sweep_monitors, minute={0, 15, 30, 45})]
    redis_settings = _redis_settings()
