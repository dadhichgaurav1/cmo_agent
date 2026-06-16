"""PostHog product analytics — server-side, the source of truth for the money/outcome/entitlement
events (runs completed, cards posted, quota gates, subscriptions). These can't be blocked by an
ad-blocker the way client events can, so they anchor the funnels.

Optional integration: every function is a no-op unless POSTHOG_API_KEY is set, mirroring the
Sentry/Resend pattern. Capture is fire-and-forget and wrapped so analytics can never break a
request path.
"""
from __future__ import annotations

import atexit
import logging
from typing import Optional

from app import config

log = logging.getLogger("analytics")

_client = None

if config.has(config.POSTHOG_API_KEY):
    try:
        from posthog import Posthog

        _client = Posthog(api_key=config.POSTHOG_API_KEY, host=config.POSTHOG_HOST)
        atexit.register(lambda: _client and _client.shutdown())
    except Exception as e:  # pragma: no cover - never block startup on analytics
        log.warning("posthog init failed: %s", e)
        _client = None


def enabled() -> bool:
    return _client is not None


def track(distinct_id: Optional[str], event: str, properties: Optional[dict] = None,
          org_id: Optional[str] = None) -> None:
    """Capture one event. `distinct_id` should be the user_id; it falls back to org_id then a
    constant so we never drop an event for lack of an id. When `org_id` is present we attach
    PostHog group analytics ('organization') so account-level funnels work."""
    if _client is None:
        return
    did = distinct_id or org_id or "anonymous"
    props = dict(properties or {})
    groups = {"organization": org_id} if org_id else None
    try:
        _client.capture(distinct_id=did, event=event, properties=props, groups=groups)
    except Exception as e:  # analytics must never raise into a request
        log.debug("posthog capture failed: %s", e)
