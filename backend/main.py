import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env da raiz do projeto, depois aplica backend/.env (override=False = não sobrescreve)
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent / ".env", override=False)

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from middleware.audit_logger import AuditLoggingMiddleware
from middleware.auth import require_auth
from middleware.security_headers import SecurityHeadersMiddleware
from routers import analyze, assets, auto_fix, export, font, generate, preview, upload
from services.job_store import recover_running_jobs

# CORS: read allowed origins from env var (comma-separated), fallback to localhost dev
_default_origins = "http://localhost:5173"
_allowed_origins = [
    origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",") if origin.strip()
]

# Rate limiting (configurable via env vars)
_RATE_LIMIT_GLOBAL = os.environ.get("RATE_LIMIT_GLOBAL", "30/minute")
_RATE_LIMIT_ANALYZE = os.environ.get("RATE_LIMIT_ANALYZE", "10/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[_RATE_LIMIT_GLOBAL])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event — runs cleanup on startup, nothing on shutdown."""
    import logging as _logging

    _log = _logging.getLogger(__name__)

    # Remove orphaned job directories from previous server runs (Story 11.9)
    analyze._cleanup_orphaned_dirs()
    # DB-016: Recover jobs left in 'running' state after server restart (Story 15.4)
    # Story 40.8: recover_running_jobs is now async
    recovered = await recover_running_jobs()
    if recovered:
        _log.info("Recovered %d stale running jobs on startup", recovered)
    # SYS-018: Validate spaCy model version at startup
    try:
        from services.stages.stage3_structural.multi_example_analysis import (
            validate_spacy_on_startup,
        )

        validate_spacy_on_startup()
    except Exception as _exc:
        _log.warning("SYS-018: spaCy startup validation skipped: %s", _exc)
    yield


app = FastAPI(title="Migrador Planet API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# SEC-004: Audit logging middleware (outermost — captures all events including auth failures)
app.add_middleware(AuditLoggingMiddleware)

# SYS-015: Security headers middleware (must be added before CORS so headers
# are present on all responses including CORS preflight)
app.add_middleware(SecurityHeadersMiddleware)

# SYS-015: Scoped CORS — specific methods and headers instead of wildcards
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# All API routes require authentication (except /api/v1/health below)
_auth_deps = [Depends(require_auth)]

# SYS-019: API versioning — canonical prefix is /api/v1/
# Backward-compatible /api/ aliases are registered below each v1 router
# to prevent breaking existing clients during the migration window.
app.include_router(analyze.router, prefix="/api/v1", dependencies=_auth_deps)
app.include_router(upload.router, prefix="/api/v1", dependencies=_auth_deps)
app.include_router(preview.router, prefix="/api/v1", dependencies=_auth_deps)
app.include_router(generate.router, prefix="/api/v1", dependencies=_auth_deps)
app.include_router(export.router, prefix="/api/v1", dependencies=_auth_deps)
app.include_router(auto_fix.router, prefix="/api/v1", dependencies=_auth_deps)
app.include_router(assets.router, prefix="/api/v1", dependencies=_auth_deps)
app.include_router(font.router, prefix="/api/v1", dependencies=_auth_deps)

# SYS-019: Backward-compatible /api/ aliases (deprecated — will be removed in v2).
# All routes are still accessible at their old paths so existing clients
# (frontend, integrations) don't break during the migration period.
# include_in_schema=False keeps them out of the OpenAPI docs to discourage new use.
app.include_router(analyze.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)
app.include_router(upload.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)
app.include_router(preview.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)
app.include_router(generate.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)
app.include_router(export.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)
app.include_router(auto_fix.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)
app.include_router(assets.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)
app.include_router(font.router, prefix="/api", dependencies=_auth_deps, include_in_schema=False)


@app.get("/api/v1/health")
async def health():
    """Deep health check endpoint.

    SYS-017: Verifies all dependencies (Redis, Supabase DB, Storage bucket,
    spaCy model) and returns per-component status with latency.
    Returns overall 'ok' only when all primary services are healthy.
    Returns 'degraded' when secondary services (spaCy) are unavailable.

    REDIS-002: Includes Redis connectivity status so load balancers and
    monitoring systems can detect when Redis is unreachable.

    SYS-019 (API versioning): Canonical path is /api/v1/health.
    Backward-compatible alias /api/health is registered below.
    """
    import time as _time

    from services.job_store import RedisJobStore, get_job_store

    _DEP_TIMEOUT = 2.0  # Max seconds per dependency check

    # ------------------------------------------------------------------
    # Helper — run a coroutine with a per-dependency timeout
    # ------------------------------------------------------------------
    async def _check(coro):
        try:
            return await asyncio.wait_for(coro, timeout=_DEP_TIMEOUT)
        except TimeoutError:
            return ("error", "timeout after 2s", None)
        except Exception as exc:
            return ("error", str(exc), None)

    # ------------------------------------------------------------------
    # Redis check (REDIS-002)
    # ------------------------------------------------------------------
    async def _check_redis():
        store = get_job_store()
        if not isinstance(store, RedisJobStore):
            return ("not_configured", None, None)
        t0 = _time.monotonic()
        try:
            await store._redis.ping()  # type: ignore[misc]
            latency = round((_time.monotonic() - t0) * 1000, 2)
            return ("ok", None, latency)
        except Exception as exc:
            return ("error", str(exc), None)

    # ------------------------------------------------------------------
    # Supabase DB check — lightweight query (select 1)
    # ------------------------------------------------------------------
    async def _check_supabase():
        supabase_url = os.environ.get("SUPABASE_URL")
        service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
        if not supabase_url or not service_role_key:
            return ("not_configured", None, None)
        t0 = _time.monotonic()
        try:
            from supabase import create_client

            client = create_client(supabase_url, service_role_key)
            # Lightweight ping: list buckets (admin op) wrapped in thread
            await asyncio.to_thread(client.storage.list_buckets)
            latency = round((_time.monotonic() - t0) * 1000, 2)
            return ("ok", None, latency)
        except ImportError:
            return ("not_configured", "supabase package not installed", None)
        except Exception as exc:
            return ("error", str(exc), None)

    # ------------------------------------------------------------------
    # Storage bucket check — list objects in 'jobs' bucket
    # ------------------------------------------------------------------
    async def _check_storage():
        storage_mode = os.environ.get("STORAGE_MODE", "")
        if storage_mode.lower() != "supabase":
            return ("not_configured", None, None)
        t0 = _time.monotonic()
        try:
            from services.storage import get_storage

            gateway = get_storage()
            # Probe: list bucket root (just metadata, no content)
            await asyncio.to_thread(gateway._admin.storage.from_("jobs").list, "", {"limit": 1})  # type: ignore[attr-defined]
            latency = round((_time.monotonic() - t0) * 1000, 2)
            return ("ok", None, latency)
        except Exception as exc:
            return ("error", str(exc), None)

    # ------------------------------------------------------------------
    # spaCy model check (SYS-018)
    # ------------------------------------------------------------------
    async def _check_spacy():
        t0 = _time.monotonic()
        try:
            from services.stages.stage3_structural.multi_example_analysis import (
                _EXPECTED_SPACY_MODEL,
                _get_nlp,
            )

            nlp = _get_nlp()
            if nlp is None or nlp is False:
                return ("degraded", "model not loaded — NER disabled", None)
            latency = round((_time.monotonic() - t0) * 1000, 2)
            # Verify loaded model matches expectation
            loaded_name = getattr(nlp, "meta", {}).get("name", "unknown")
            if loaded_name not in (_EXPECTED_SPACY_MODEL, "pt_core_news_sm", "pt_core_news_lg"):
                return (
                    "degraded",
                    f"unexpected model '{loaded_name}' (expected {_EXPECTED_SPACY_MODEL})",
                    latency,
                )
            return ("ok", None, latency)
        except Exception as exc:
            return ("degraded", str(exc), None)

    # ------------------------------------------------------------------
    # Run all checks concurrently
    # ------------------------------------------------------------------
    redis_result, supabase_result, storage_result, spacy_result = await asyncio.gather(
        _check(_check_redis()),
        _check(_check_supabase()),
        _check(_check_storage()),
        _check(_check_spacy()),
    )

    def _dep(result) -> dict:
        status, err, latency = result
        d: dict = {"status": status}
        if err:
            d["error"] = err
        if latency is not None:
            d["latency_ms"] = latency
        return d

    deps = {
        "redis": _dep(redis_result),
        "supabase": _dep(supabase_result),
        "storage": _dep(storage_result),
        "spacy": _dep(spacy_result),
    }

    # Overall status: 'ok' if all primary services healthy; 'degraded' if only
    # secondary (spaCy) has issues; 'error' if a primary service is down.
    primary_statuses = {deps["redis"]["status"], deps["supabase"]["status"], deps["storage"]["status"]}
    # not_configured is neutral — don't count as failure
    primary_errors = {s for s in primary_statuses if s not in ("ok", "not_configured")}
    secondary_degraded = deps["spacy"]["status"] == "degraded"

    if primary_errors:
        overall = "error"
    elif secondary_degraded:
        overall = "degraded"
    else:
        overall = "ok"

    return {"status": overall, **deps}


# SYS-019: Backward-compatible alias — old path /api/health redirects to v1
@app.get("/api/health", include_in_schema=False)
async def health_legacy():
    """Backward-compatible alias for /api/v1/health.

    SYS-019: Deprecated. Use /api/v1/health instead.
    This alias will be removed in a future version.
    """
    return await health()
