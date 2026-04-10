import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env da raiz do projeto, depois aplica backend/.env (override=False = não sobrescreve)
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent / ".env", override=False)

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middleware.audit_logger import AuditLoggingMiddleware
from middleware.auth import require_auth
from middleware.security_headers import SecurityHeadersMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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
    # Remove orphaned job directories from previous server runs (Story 11.9)
    analyze._cleanup_orphaned_dirs()
    # DB-016: Recover jobs left in 'running' state after server restart (Story 15.4)
    recovered = recover_running_jobs()
    if recovered:
        import logging

        logging.getLogger(__name__).info("Recovered %d stale running jobs on startup", recovered)
    yield


app = FastAPI(title="Migrador Planet API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

# All API routes require authentication (except /api/health below)
_auth_deps = [Depends(require_auth)]

app.include_router(analyze.router, prefix="/api", dependencies=_auth_deps)
app.include_router(upload.router, prefix="/api", dependencies=_auth_deps)
app.include_router(preview.router, prefix="/api", dependencies=_auth_deps)
app.include_router(generate.router, prefix="/api", dependencies=_auth_deps)
app.include_router(export.router, prefix="/api", dependencies=_auth_deps)
app.include_router(auto_fix.router, prefix="/api", dependencies=_auth_deps)
app.include_router(assets.router, prefix="/api", dependencies=_auth_deps)
app.include_router(font.router, prefix="/api", dependencies=_auth_deps)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
