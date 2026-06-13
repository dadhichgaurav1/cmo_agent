"""Multi-tenant scoping helpers.

Everything the agent persists (Synap brains, monitors, conversations) is scoped to an
organization so two orgs analyzing the same company never share state. The Synap customer_id
and the monitor key are derived from (org_id, company_slug); when there is no org (local/demo
mode, no auth configured) we fall back to the bare slug so single-tenant behavior is preserved.
"""
from typing import Optional


def customer_scope(org_id: Optional[str], slug: str) -> str:
    """Synap customer_id / memory scope key for a company within an org."""
    return f"{org_id}:{slug}" if org_id else slug
