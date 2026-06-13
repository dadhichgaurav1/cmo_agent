"""Lightweight fixed-window rate limiting.

In-memory per-process limiter keyed by org (or client IP in demo mode). This is intentionally
simple; it bounds bursts from a single instance. For correctness across multiple web instances,
back this with Redis (a shared counter keyed the same way) — noted in LAUNCH_PLAN Phase 3.
"""
import time
from collections import defaultdict
from threading import Lock

_hits: dict = defaultdict(list)
_lock = Lock()


def allow(key: str, limit: int, window: float = 60.0) -> bool:
    """True if `key` is under `limit` events within the trailing `window` seconds."""
    now = time.time()
    cutoff = now - window
    with _lock:
        q = _hits[key]
        # drop expired timestamps
        i = 0
        while i < len(q) and q[i] < cutoff:
            i += 1
        if i:
            del q[:i]
        if len(q) >= limit:
            return False
        q.append(now)
        return True
