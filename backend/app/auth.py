"""Supabase JWT verification + tenant context resolution for FastAPI.

Auth is enabled when either SUPABASE_JWT_SECRET (legacy HS256) or SUPABASE_URL (for JWKS) is
configured; otherwise requests resolve to an anonymous identity with no org and the single-tenant
fallbacks elsewhere apply (local/demo mode). When enabled, a valid Supabase bearer token is
REQUIRED on protected endpoints.

Supabase can sign tokens two ways depending on the project's active signing key:
  - legacy HS256, verified with the shared SUPABASE_JWT_SECRET
  - asymmetric ES256/RS256 (the new "JWT signing keys"), verified via the project's JWKS
We pick the path from the token header's `alg`, so both work without reconfiguration.

The token may arrive as an `Authorization: Bearer <jwt>` header OR as an `?access_token=<jwt>`
query param — the query path exists because EventSource (used by the SSE analyze stream) cannot
send custom headers.
"""
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Query

from app import config, db

ANON = {"user_id": None, "email": None}

_jwks_client = None


def auth_enabled() -> bool:
    return bool(config.SUPABASE_JWT_SECRET or config.SUPABASE_URL)


def _jwks():
    """Lazily build a cached JWKS client for asymmetric token verification."""
    global _jwks_client
    if _jwks_client is None and config.SUPABASE_URL:
        url = config.SUPABASE_URL.rstrip("/") + "/auth/v1/.well-known/jwks.json"
        _jwks_client = jwt.PyJWKClient(url)
    return _jwks_client


def _decode(token: str) -> dict:
    try:
        alg = jwt.get_unverified_header(token).get("alg", "HS256")
        if alg == "HS256":
            if not config.SUPABASE_JWT_SECRET:
                raise HTTPException(status_code=401, detail="legacy token but no JWT secret configured")
            return jwt.decode(token, config.SUPABASE_JWT_SECRET, algorithms=["HS256"],
                              audience="authenticated")
        client = _jwks()
        if client is None:
            raise HTTPException(status_code=401, detail="asymmetric token but SUPABASE_URL not configured")
        key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(token, key, algorithms=[alg], audience="authenticated")
    except HTTPException:
        raise
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid or expired token")


async def current_user(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Query(None),
) -> dict:
    if not auth_enabled():
        return dict(ANON)  # auth disabled — local/demo single-tenant mode
    token = None
    if authorization:
        token = authorization.removeprefix("Bearer ").strip()
    elif access_token:
        token = access_token.strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    claims = _decode(token)
    return {"user_id": claims.get("sub"), "email": claims.get("email")}


async def current_context(user: dict = Depends(current_user)) -> dict:
    """Authenticated user + their active org_id (None in local/demo mode)."""
    org_id = db.primary_org_for(user["user_id"]) if user.get("user_id") else None
    return {**user, "org_id": org_id}
