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
