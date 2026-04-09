"""Security headers middleware for FastAPI.

Story 40.2 — SYS-015: Add security response headers to all API responses.

Adds the following headers:
- Content-Security-Policy (permissive to start, tighten incrementally)
- Strict-Transport-Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- X-XSS-Protection: 0 (deprecated in modern browsers, but harmless)
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# CSP policy — intentionally permissive to start. Tighten incrementally.
# Using report-only initially would be ideal but requires a reporting endpoint.
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://*.supabase.co wss://*.supabase.co; "
    "frame-ancestors 'none';"
)

# Allow override via env var for production fine-tuning
_CSP_POLICY = os.environ.get("CSP_POLICY", _DEFAULT_CSP)

# HSTS: 1 year max-age, include subdomains
_HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["Content-Security-Policy"] = _CSP_POLICY
        response.headers["Strict-Transport-Security"] = _HSTS_VALUE
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "0"

        return response
