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


def has(value: str) -> bool:
    return bool(value and value.strip())
