"""Supabase-backed persistence (accounts, runs, monitors, usage).

Uses the supabase-py client with the SERVICE ROLE key, so it BYPASSES RLS — every query here
must scope by org_id itself. Mirrors the rest of the codebase's defensive style: when Supabase
isn't configured, every call is a safe no-op (returns None / [] / {}) so the app still boots and
the local JSON/-tmp fallbacks elsewhere take over.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import config

_client = None
_tried = False


def enabled() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY)


def _sb():
    global _client, _tried
    if _client is not None or _tried:
        return _client
    _tried = True
    if not enabled():
        return None
    try:
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    except Exception:
        _client = None
    return _client


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- org resolution -------------------------------------------------------
def primary_org_for(user_id: str) -> Optional[str]:
    """The user's default workspace (oldest membership). Org-switching can layer on later."""
    sb = _sb()
    if not sb or not user_id:
        return None
    try:
        r = (sb.table("org_members").select("org_id, created_at")
             .eq("user_id", user_id).order("created_at").limit(1).execute())
        rows = r.data or []
        return rows[0]["org_id"] if rows else None
    except Exception:
        return None


# --- runs (historical analyses) -------------------------------------------
def create_run(org_id: Optional[str], user_id: Optional[str], url: str, slug: str,
               scope: str, mode: str) -> Optional[str]:
    sb = _sb()
    if not sb or not org_id:
        return None
    try:
        r = sb.table("runs").insert({
            "org_id": org_id, "created_by": user_id, "company_url": url,
            "company_slug": slug, "synap_customer_id": scope, "mode": mode, "status": "running",
        }).execute()
        rows = r.data or []
        return rows[0]["id"] if rows else None
    except Exception:
        return None


def finish_run(run_id: Optional[str], status: str, summary: Optional[dict] = None,
               error: Optional[str] = None) -> None:
    sb = _sb()
    if not sb or not run_id:
        return
    try:
        sb.table("runs").update({
            "status": status, "summary": summary, "error": error, "finished_at": _now(),
        }).eq("id", run_id).execute()
    except Exception:
        pass


def list_runs(org_id: str, limit: int = 50) -> List[dict]:
    sb = _sb()
    if not sb or not org_id:
        return []
    try:
        r = (sb.table("runs").select("*").eq("org_id", org_id)
             .order("started_at", desc=True).limit(limit).execute())
        return r.data or []
    except Exception:
        return []


def latest_run(org_id: Optional[str], slug: str) -> dict:
    """The most recent completed run for a company — used to seed the Action Board."""
    sb = _sb()
    if not sb or not org_id:
        return {}
    try:
        r = (sb.table("runs").select("id, company_url, summary")
             .eq("org_id", org_id).eq("company_slug", slug).eq("status", "done")
             .order("started_at", desc=True).limit(1).execute())
        rows = r.data or []
        return rows[0] if rows else {}
    except Exception:
        return {}


# --- action board cards ---------------------------------------------------
def list_cards(org_id: Optional[str], slug: Optional[str] = None, limit: int = 300) -> List[dict]:
    sb = _sb()
    if not sb or not org_id:
        return []
    try:
        q = sb.table("action_cards").select("*").eq("org_id", org_id)
        if slug:
            q = q.eq("company_slug", slug)
        r = q.order("created_at", desc=True).limit(limit).execute()
        return r.data or []
    except Exception:
        return []


def create_card(org_id: Optional[str], card: dict) -> Optional[dict]:
    sb = _sb()
    if not sb or not org_id:
        return None
    try:
        r = sb.table("action_cards").insert({**card, "org_id": org_id}).execute()
        rows = r.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def bulk_create_cards(org_id: Optional[str], cards: List[dict]) -> List[dict]:
    sb = _sb()
    if not sb or not org_id or not cards:
        return []
    try:
        r = sb.table("action_cards").insert([{**c, "org_id": org_id} for c in cards]).execute()
        return r.data or []
    except Exception:
        return []


def update_card(org_id: Optional[str], card_id: str, patch: dict) -> Optional[dict]:
    sb = _sb()
    if not sb or not org_id or not card_id or not patch:
        return None
    try:
        r = (sb.table("action_cards").update(patch)
             .eq("org_id", org_id).eq("id", card_id).execute())   # scope by org_id AND id
        rows = r.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def delete_card(org_id: Optional[str], card_id: str) -> None:
    sb = _sb()
    if not sb or not org_id or not card_id:
        return
    try:
        sb.table("action_cards").delete().eq("org_id", org_id).eq("id", card_id).execute()
    except Exception:
        pass


def count_cards(org_id: Optional[str], slug: str) -> int:
    sb = _sb()
    if not sb or not org_id:
        return 0
    try:
        r = (sb.table("action_cards").select("id", count="exact")
             .eq("org_id", org_id).eq("company_slug", slug).execute())
        return r.count or 0
    except Exception:
        return 0


# --- CLI personal access tokens (long-lived, hashed) ----------------------
def create_cli_token(org_id: str, user_id: Optional[str], token_hash: str,
                     prefix: str, label: str) -> Optional[dict]:
    sb = _sb()
    if not sb or not org_id:
        return None
    try:
        r = sb.table("cli_tokens").insert({
            "org_id": org_id, "user_id": user_id, "token_hash": token_hash,
            "prefix": prefix, "label": label,
        }).execute()
        rows = r.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def cli_token_by_hash(token_hash: str) -> dict:
    """Resolve a raw token's hash to its org/user — the CLI auth path. Service role only."""
    sb = _sb()
    if not sb or not token_hash:
        return {}
    try:
        r = (sb.table("cli_tokens").select("id, org_id, user_id")
             .eq("token_hash", token_hash).limit(1).execute())
        rows = r.data or []
        return rows[0] if rows else {}
    except Exception:
        return {}


def touch_cli_token(token_id: str) -> None:
    sb = _sb()
    if not sb or not token_id:
        return
    try:
        sb.table("cli_tokens").update({"last_used_at": _now()}).eq("id", token_id).execute()
    except Exception:
        pass


def list_cli_tokens(org_id: Optional[str]) -> List[dict]:
    sb = _sb()
    if not sb or not org_id:
        return []
    try:
        r = (sb.table("cli_tokens").select("id, prefix, label, last_used_at, created_at")
             .eq("org_id", org_id).order("created_at", desc=True).execute())
        return r.data or []
    except Exception:
        return []


def delete_cli_token(org_id: Optional[str], token_id: str) -> None:
    sb = _sb()
    if not sb or not org_id or not token_id:
        return
    try:
        sb.table("cli_tokens").delete().eq("org_id", org_id).eq("id", token_id).execute()
    except Exception:
        pass


# --- monitors -------------------------------------------------------------
def get_monitor(org_id: str, slug: str) -> dict:
    sb = _sb()
    if not sb or not org_id:
        return {}
    try:
        r = (sb.table("monitors").select("*")
             .eq("org_id", org_id).eq("company_slug", slug).limit(1).execute())
        rows = r.data or []
        return rows[0] if rows else {}
    except Exception:
        return {}


def save_monitor(org_id: str, slug: str, jobs: List[dict]) -> None:
    sb = _sb()
    if not sb or not org_id:
        return
    try:
        sb.table("monitors").upsert(
            {"org_id": org_id, "company_slug": slug, "jobs": jobs, "updated_at": _now()},
            on_conflict="org_id,company_slug",
        ).execute()
    except Exception:
        pass


def all_monitors() -> List[dict]:
    """Every stored monitor across all orgs — used to register the scheduler at startup."""
    sb = _sb()
    if not sb:
        return []
    try:
        r = sb.table("monitors").select("org_id, company_slug, jobs").eq("enabled", True).execute()
        return r.data or []
    except Exception:
        return []


def append_monitor_event(org_id: str, slug: str, entry: dict) -> None:
    sb = _sb()
    if not sb or not org_id:
        return
    try:
        sb.table("monitor_events").insert(
            {"org_id": org_id, "company_slug": slug, "entry": entry}).execute()
    except Exception:
        pass


def get_monitor_events(org_id: str, slug: str, limit: int = 50) -> List[dict]:
    sb = _sb()
    if not sb or not org_id:
        return []
    try:
        r = (sb.table("monitor_events").select("entry, created_at")
             .eq("org_id", org_id).eq("company_slug", slug)
             .order("created_at", desc=True).limit(limit).execute())
        return [row["entry"] for row in (r.data or [])]
    except Exception:
        return []


# --- org lookups (plan / settings) ----------------------------------------
def get_org(org_id: Optional[str]) -> dict:
    sb = _sb()
    if not sb or not org_id:
        return {}
    try:
        r = (sb.table("organizations")
             .select("plan, subscription_status, stripe_customer_id")
             .eq("id", org_id).limit(1).execute())
        rows = r.data or []
        return rows[0] if rows else {}
    except Exception:
        return {}


def update_org(org_id: Optional[str], fields: Dict[str, Any]) -> None:
    sb = _sb()
    if not sb or not org_id or not fields:
        return
    try:
        sb.table("organizations").update(fields).eq("id", org_id).execute()
    except Exception:
        pass


def org_id_for_customer(customer_id: Optional[str]) -> Optional[str]:
    sb = _sb()
    if not sb or not customer_id:
        return None
    try:
        r = sb.table("organizations").select("id").eq("stripe_customer_id", customer_id).limit(1).execute()
        rows = r.data or []
        return rows[0]["id"] if rows else None
    except Exception:
        return None


def get_org_settings(org_id: Optional[str]) -> dict:
    sb = _sb()
    if not sb or not org_id:
        return {}
    try:
        r = sb.table("org_settings").select("settings").eq("org_id", org_id).limit(1).execute()
        rows = r.data or []
        return (rows[0].get("settings") or {}) if rows else {}
    except Exception:
        return {}


def usage_count(org_id: Optional[str], kind: str, since_iso: str) -> int:
    sb = _sb()
    if not sb or not org_id:
        return 0
    try:
        r = (sb.table("usage_events").select("id", count="exact")
             .eq("org_id", org_id).eq("kind", kind).gte("created_at", since_iso).execute())
        return r.count or 0
    except Exception:
        return 0


# --- integrations (per-org Composio connections) --------------------------
def list_integrations(org_id: Optional[str]) -> List[dict]:
    sb = _sb()
    if not sb or not org_id:
        return []
    try:
        r = sb.table("integrations").select("*").eq("org_id", org_id).execute()
        return r.data or []
    except Exception:
        return []


def upsert_integration(org_id: str, provider: str, connection_id: Optional[str],
                       status: str, metadata: Optional[dict] = None) -> None:
    sb = _sb()
    if not sb or not org_id:
        return
    try:
        sb.table("integrations").upsert({
            "org_id": org_id, "provider": provider, "connection_id": connection_id,
            "status": status, "metadata": metadata or {},
        }, on_conflict="org_id,provider").execute()
    except Exception:
        pass


def delete_integration(org_id: str, provider: str) -> None:
    sb = _sb()
    if not sb or not org_id:
        return
    try:
        sb.table("integrations").delete().eq("org_id", org_id).eq("provider", provider).execute()
    except Exception:
        pass


# --- account / workspace deletion + owner lookup ---------------------------
def org_owner_email(org_id: Optional[str]) -> Optional[str]:
    sb = _sb()
    if not sb or not org_id:
        return None
    try:
        r = (sb.table("org_members").select("user_id")
             .eq("org_id", org_id).eq("role", "owner").limit(1).execute())
        rows = r.data or []
        if not rows:
            return None
        p = sb.table("profiles").select("email").eq("id", rows[0]["user_id"]).limit(1).execute()
        prows = p.data or []
        return prows[0]["email"] if prows else None
    except Exception:
        return None


def owned_org_ids(user_id: Optional[str]) -> List[str]:
    sb = _sb()
    if not sb or not user_id:
        return []
    try:
        r = sb.table("org_members").select("org_id").eq("user_id", user_id).eq("role", "owner").execute()
        return [row["org_id"] for row in (r.data or [])]
    except Exception:
        return []


def delete_org(org_id: Optional[str]) -> None:
    """Deletes the org; FK ON DELETE CASCADE removes its runs/monitors/usage/etc."""
    sb = _sb()
    if not sb or not org_id:
        return
    try:
        sb.table("organizations").delete().eq("id", org_id).execute()
    except Exception:
        pass


def delete_user(user_id: Optional[str]) -> bool:
    """Deletes the Supabase auth user (service-role admin). Cascades profile + memberships."""
    sb = _sb()
    if not sb or not user_id:
        return False
    try:
        sb.auth.admin.delete_user(user_id)
        return True
    except Exception:
        return False


# --- usage metering (billing + cost caps) ---------------------------------
def record_usage(org_id: Optional[str], kind: str, quantity: float = 1,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
    sb = _sb()
    if not sb or not org_id:
        return
    try:
        sb.table("usage_events").insert({
            "org_id": org_id, "kind": kind, "quantity": quantity, "metadata": metadata or {},
        }).execute()
    except Exception:
        pass
