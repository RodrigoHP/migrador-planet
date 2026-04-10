"""Supabase JWT authentication middleware for FastAPI.

Story 15.3: Validates JWT tokens from Supabase Auth.
Story 15.8: Updated to support ES256 tokens via JWKS endpoint.

Usage as a FastAPI dependency:
    from middleware.auth import require_auth

    @router.post("/api/analyze")
    async def start_analyze(user=Depends(require_auth)):
        ...

Configuration:
    SUPABASE_URL — the Supabase project URL (used to build JWKS endpoint).
    AUTH_DISABLED — set to "true" to skip auth (local dev).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_AUTH_DISABLED = os.environ.get("AUTH_DISABLED", "false").lower() in ("true", "1", "yes")

# DB-012: Block AUTH_DISABLED in production to prevent accidental exposure
_ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()
if _AUTH_DISABLED and _ENVIRONMENT == "production":
    raise RuntimeError(
        "FATAL: AUTH_DISABLED=true is not allowed when ENVIRONMENT=production. "
        "Remove AUTH_DISABLED or set ENVIRONMENT to a non-production value."
    )

_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        supabase_url = os.environ.get("SUPABASE_URL")
        if not supabase_url:
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: SUPABASE_URL not set.",
            )
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwks_client


def _decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a Supabase JWT token using JWKS (ES256/RS256)."""
    client = _get_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """FastAPI dependency — returns decoded JWT payload or raises 401.

    When AUTH_DISABLED=true (local dev), returns a stub user payload.
    """
    if _AUTH_DISABLED:
        return {"sub": "dev-user", "email": "dev@localhost", "role": "authenticated"}

    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing.")

    return _decode_token(credentials.credentials)
