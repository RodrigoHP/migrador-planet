"""Audit logging middleware for security-relevant events.

Story 40.4 — SEC-004: Structured JSON logging for privileged operations.

Logs:
- Login attempts (success/failure via auth middleware)
- Access denied events (401/403 responses)
- Service role operations (Supabase admin client usage)
- Auth context changes

Uses Python's logging module with a JSON formatter so events can be
ingested by any log aggregation system (ELK, CloudWatch, Datadog, etc.).

This middleware is designed to be non-blocking: it logs after the response
is produced, so it does not add latency to request processing.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ─── JSON Formatter ──────────────────────────────────────────────────────────


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter for audit events."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge extra audit fields if present
        if hasattr(record, "audit"):
            log_data.update(record.audit)  # type: ignore[attr-defined]
        return json.dumps(log_data, default=str)


# ─── Audit Logger Setup ─────────────────────────────────────────────────────

audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False

# Add JSON handler if not already configured (avoid duplicate handlers on reload)
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    audit_logger.addHandler(handler)


# ─── Helper: emit structured audit event ─────────────────────────────────────


def log_audit_event(
    event_type: str,
    *,
    user_id: str | None = None,
    ip_address: str | None = None,
    resource: str | None = None,
    action: str | None = None,
    result: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Emit a structured audit log entry.

    Can be called from anywhere (middleware, route handlers, services)
    to log security-relevant events.
    """
    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        "resource": resource,
        "action": action,
        "result": result,
    }
    if details:
        event["details"] = details

    audit_logger.info(
        "%s: %s %s -> %s",
        event_type,
        action or "N/A",
        resource or "N/A",
        result,
        extra={"audit": event},
    )


# ─── Middleware ───────────────────────────────────────────────────────────────


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Log security-relevant HTTP events without adding request latency.

    Captures:
    - All 401 (Unauthorized) responses → event_type: "access_denied"
    - All 403 (Forbidden) responses → event_type: "access_denied"
    - POST to /auth paths → event_type: "login_attempt"
    - Service role header usage → event_type: "service_role_operation"
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        # Extract client IP (respect X-Forwarded-For for proxied setups)
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not ip:
            ip = request.client.host if request.client else "unknown"

        # Extract user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        path = request.url.path
        method = request.method

        # ── Access denied (401 / 403) ─────────────────────────────────────
        if response.status_code in (401, 403):
            log_audit_event(
                "access_denied",
                user_id=user_id,
                ip_address=ip,
                resource=path,
                action=method,
                result="denied",
                details={"status_code": response.status_code, "duration_ms": duration_ms},
            )

        # ── Login attempts (auth-related endpoints) ───────────────────────
        elif "auth" in path.lower() and method == "POST":
            result = "success" if response.status_code < 400 else "failure"
            log_audit_event(
                "login_attempt",
                user_id=user_id,
                ip_address=ip,
                resource=path,
                action="login",
                result=result,
                details={"status_code": response.status_code, "duration_ms": duration_ms},
            )

        # ── Service role operations (apikey / service_role header) ────────
        elif request.headers.get("apikey") or request.headers.get("x-service-role"):
            log_audit_event(
                "service_role_operation",
                user_id=user_id,
                ip_address=ip,
                resource=path,
                action=method,
                result="success" if response.status_code < 400 else "failure",
                details={"status_code": response.status_code, "duration_ms": duration_ms},
            )

        return response
