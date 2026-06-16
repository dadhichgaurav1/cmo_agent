import os

from dotenv import load_dotenv

load_dotenv()


def _get(key: str) -> str:
    return os.getenv(key, "").strip()


ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")
# Pioneer: sponsor inference gateway (Anthropic/OpenAI-compatible). Primary LLM backend
# when present; native Anthropic/OpenAI are used as fallback. Scoped to this process only.
PIONEER_API_KEY = _get("PIONEER_API_KEY")
PIONEER_BASE_URL = _get("PIONEER_BASE_URL") or "https://api.pioneer.ai"
EXA_API_KEY = _get("EXA_API_KEY")
COMPOSIO_API_KEY = _get("COMPOSIO_API_KEY")
SYNAP_API_KEY = _get("SYNAP_API_KEY")
SYNAP_BASE_URL = _get("SYNAP_BASE_URL")
BROWSERBASE_API_KEY = _get("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = _get("BROWSERBASE_PROJECT_ID")
# Optional remote catalogue of per-channel writing skills (Addendum 2). When unset, the agent
# falls back to generating-and-caching a skill for any unknown channel at runtime.
SKILLS_CATALOG_URL = _get("SKILLS_CATALOG_URL")

# Supabase: auth (JWT verification) + Postgres-backed accounts/runs/monitors. When unset, the
# backend runs in single-tenant local mode (no auth enforced, JSON/-tmp fallbacks) so the demo
# path keeps working. SERVICE_ROLE_KEY bypasses RLS — never expose it to the frontend.
# Aliases accept the variable names the Supabase dashboard generates, so .env needs no renaming.
SUPABASE_URL = _get("SUPABASE_URL") or _get("SUPABASE_PROJECT_URL")
SUPABASE_SERVICE_ROLE_KEY = (_get("SUPABASE_SERVICE_ROLE_KEY") or _get("SUPABASE_SERVICE_ROLE_SECRET")
                             or _get("SUPABASE_SECRET_KEY"))
# Legacy HS256 secret (used to verify legacy-signed tokens). New asymmetric tokens are verified
# via JWKS from SUPABASE_URL instead — auth.py handles both.
SUPABASE_JWT_SECRET = _get("SUPABASE_JWT_SECRET") or _get("SUPABASE_LEGACY_JWT_SECRET")

# Redis / Arq background worker. When set, scheduled monitors run in a dedicated worker process
# (app/worker.py) and the in-process APScheduler is disabled. When unset, the in-process
# scheduler is used (single-instance; fine for local/demo).
REDIS_URL = _get("REDIS_URL")

# Stripe billing. When STRIPE_SECRET_KEY is unset, billing endpoints report disabled (503) and
# orgs stay on the free plan. STRIPE_PRICE_PRO is the recurring price id for the paid plan.
STRIPE_SECRET_KEY = _get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = _get("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_PRO = _get("STRIPE_PRICE_PRO")
# Public base URL of the app, for Stripe success/cancel/return redirects.
APP_BASE_URL = _get("APP_BASE_URL") or "http://localhost:5173"

# Observability + security + email. All optional — unset = disabled, app runs as before.
SENTRY_DSN = _get("SENTRY_DSN")
# Comma-separated allowed CORS origins for production. Empty => permissive "*" (local/demo).
ALLOWED_ORIGINS = _get("ALLOWED_ORIGINS")
# Resend transactional email. RESEND_FROM must be a verified sender/domain.
RESEND_API_KEY = _get("RESEND_API_KEY")
RESEND_FROM = _get("RESEND_FROM") or "StratCMO <noreply@stratcmo.app>"

# Product analytics (PostHog). Optional — unset = disabled, no events sent. POSTHOG_API_KEY is the
# project write key (same value the frontend uses as VITE_POSTHOG_KEY); HOST is the region host.
POSTHOG_API_KEY = _get("POSTHOG_API_KEY")
POSTHOG_HOST = _get("POSTHOG_HOST") or "https://us.i.posthog.com"

# NOTE: the Action Board daily feeder is controlled per-company (a toggle on the board,
# stored on the monitors row), not by a global env flag — see db.all_feeders / set_card_feeder.

# Momentum (founder activation score + streak + persona). On unless explicitly disabled, so the
# pre-launch team can use it; set MOMENTUM_ENABLED=0 to ship dark. When off, awards no-op and the
# frontend hides the chip/tab (the API returns {"momentum": null}).
MOMENTUM_ENABLED = _get("MOMENTUM_ENABLED") != "0"


def has(value: str) -> bool:
    return bool(value and value.strip())
