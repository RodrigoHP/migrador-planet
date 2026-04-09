"""Storage Gateway package -- factory and StorageMode enum.

Usage::

    from services.storage import create_storage_gateway, StorageMode

    gateway = create_storage_gateway()   # reads STORAGE_MODE from env
    path = await gateway.upload_pdf(job_id, 0, pdf_bytes)

CARDINAL RULE: No automatic fallback.  If ``STORAGE_MODE=supabase`` and
Supabase is unavailable, the pipeline FAILS.  Local storage is an explicit
configuration choice, never a silent degradation.
"""

from __future__ import annotations

import os
from enum import Enum

from .gateway import StorageGateway

__all__ = [
    "StorageGateway",
    "StorageMode",
    "create_storage_gateway",
    "get_storage",
    "ConfigurationError",
]

# Module-level singleton — lazy-initialised on first call to get_storage().
_storage_instance: StorageGateway | None = None


def get_storage() -> StorageGateway:
    """Return the module-level StorageGateway singleton.

    Creates the instance on first call using ``create_storage_gateway()``
    (which reads ``STORAGE_MODE`` from env).  Thread-safe for the typical
    single-threaded asyncio server; for tests, call ``_reset_storage()`` to
    force re-creation.
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = create_storage_gateway()
    return _storage_instance


def _reset_storage(instance: StorageGateway | None = None) -> None:
    """Replace the singleton (for tests).  Pass *None* to force re-creation."""
    global _storage_instance
    _storage_instance = instance


class ConfigurationError(Exception):
    """Raised when required storage configuration is missing or invalid."""


class StorageMode(str, Enum):
    """Explicit storage backend selection."""

    SUPABASE = "supabase"  # Production -- Supabase Storage + DB
    LOCAL = "local"  # Dev/tests -- local disk


def create_storage_gateway(
    *,
    mode: StorageMode | str | None = None,
    supabase_client: object | None = None,
) -> StorageGateway:
    """Factory -- choose implementation based on EXPLICIT config.

    Parameters
    ----------
    mode:
        Override for ``STORAGE_MODE`` env var.  When *None* the env var is read.
    supabase_client:
        Pre-built Supabase client instance.  Required when *mode* is
        ``SUPABASE`` and no client can be auto-created.

    Raises
    ------
    ConfigurationError
        - ``STORAGE_MODE`` is not set and *mode* is not provided.
        - ``STORAGE_MODE=supabase`` but ``SUPABASE_URL`` / ``SUPABASE_KEY`` are
          missing and no *supabase_client* is provided.
        - ``STORAGE_MODE`` has an unrecognised value.
    """
    if mode is None:
        raw = os.environ.get("STORAGE_MODE")
        if not raw:
            raise ConfigurationError(
                "STORAGE_MODE is not set.  "
                "Set STORAGE_MODE='local' or STORAGE_MODE='supabase' in your .env file."
            )
        try:
            mode = StorageMode(raw.lower())
        except ValueError:
            raise ConfigurationError(
                f"STORAGE_MODE='{raw}' is invalid.  Use 'supabase' or 'local'."
            )
    elif isinstance(mode, str):
        try:
            mode = StorageMode(mode.lower())
        except ValueError:
            raise ConfigurationError(
                f"STORAGE_MODE='{mode}' is invalid.  Use 'supabase' or 'local'."
            )

    if mode == StorageMode.SUPABASE:
        from .supabase_gateway import SupabaseStorageGateway

        # Legacy shortcut: pre-built client passed directly (tests, backward compat)
        if supabase_client is not None:
            return SupabaseStorageGateway(admin_client=supabase_client)

        # DB-003: Two Supabase clients — admin (service role) for storage ops,
        # user (anon key) for DB queries that respect RLS.
        supabase_url = os.environ.get("SUPABASE_URL")
        service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
            "SUPABASE_KEY"
        )
        anon_key = os.environ.get("SUPABASE_ANON_KEY")

        if not supabase_url or not service_role_key:
            raise ConfigurationError(
                "STORAGE_MODE=supabase requires SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) to be set."
            )

        # Lazy import -- supabase SDK is only needed in production
        try:
            from supabase import create_client
        except ImportError:
            raise ConfigurationError(
                "STORAGE_MODE=supabase requires the 'supabase' package.  "
                "Install it with: pip install supabase"
            )

        # Admin client: service role key — bypasses RLS, used ONLY for storage ops
        admin_client = create_client(supabase_url, service_role_key)

        # User client: anon key — respects RLS, used for all DB table queries.
        # Falls back to admin_client if SUPABASE_ANON_KEY is not set (gradual migration).
        user_client = None
        if anon_key:
            user_client = create_client(supabase_url, anon_key)

        return SupabaseStorageGateway(
            admin_client=admin_client,
            user_client=user_client,
        )

    if mode == StorageMode.LOCAL:
        from .local_gateway import LocalStorageGateway

        return LocalStorageGateway()

    # Unreachable due to enum validation above, but kept for safety
    raise ConfigurationError(
        f"STORAGE_MODE='{mode}' is invalid.  Use 'supabase' or 'local'."
    )
