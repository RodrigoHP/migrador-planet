"""Supabase JWT authentication middleware for FastAPI.

Story 15.3: Validates JWT tokens from Supabase Auth.

Usage as a FastAPI dependency:
    from middleware.auth import require_auth

    @router.post("/api/analyze")
    async def start_analyze(user=Depends(require_auth)):
        ...

Configuration:
    SUPABASE_JWT_SECRET — the JWT secret from Supabase project settings.
    AUTH_DISABLED — set to "true" to skip auth (local dev).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_AUTH_DISABLED = os.environ.get("AUTH_DISABLED", "false").lower() in ("true", "1", "yes")


def _get_jwt_secret() -> Optional[str]:
    return os.environ.get("SUPABASE_JWT_SECRET")


def _decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a Supabase JWT token."""
    import jwt  # PyJWT

    secret = _get_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: SUPABASE_JWT_SECRET not set.",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
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
