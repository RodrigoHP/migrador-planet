"""Tests for Story 40.1 — DB Quick Wins & Security Patches.

Covers:
  - DB-012: AUTH_DISABLED production safeguard
  - DB-016: recover_running_jobs() called in lifespan
  - DB-004: updated_at trigger migration (SQL validation)
  - DB-005: CHECK constraint on jobs.status (SQL validation)
  - DB-009: Storage buckets migration (SQL validation)
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "supabase" / "migrations"


def _read_migration(filename: str) -> str:
    """Read a migration SQL file and return its content."""
    path = _MIGRATIONS_DIR / filename
    assert path.exists(), f"Migration file not found: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# DB-012: AUTH_DISABLED production safeguard
# ---------------------------------------------------------------------------


class TestAuthDisabledProductionSafeguard:
    """Verify that AUTH_DISABLED=true + ENVIRONMENT=production raises RuntimeError."""

    def test_auth_disabled_in_production_raises_error(self):
        """AUTH_DISABLED=true with ENVIRONMENT=production must raise RuntimeError."""
        env = {
            "AUTH_DISABLED": "true",
            "ENVIRONMENT": "production",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(RuntimeError, match="AUTH_DISABLED.*production"):
                # Force re-import to trigger module-level check
                import middleware.auth as auth_mod

                importlib.reload(auth_mod)

    def test_auth_disabled_in_development_is_allowed(self):
        """AUTH_DISABLED=true with ENVIRONMENT=development must NOT raise."""
        env = {
            "AUTH_DISABLED": "true",
            "ENVIRONMENT": "development",
        }
        with patch.dict(os.environ, env, clear=False):
            import middleware.auth as auth_mod

            importlib.reload(auth_mod)
            # Should not raise — module loads normally

    def test_auth_disabled_false_in_production_is_allowed(self):
        """AUTH_DISABLED=false with ENVIRONMENT=production must NOT raise."""
        env = {
            "AUTH_DISABLED": "false",
            "ENVIRONMENT": "production",
        }
        with patch.dict(os.environ, env, clear=False):
            import middleware.auth as auth_mod

            importlib.reload(auth_mod)
            # Should not raise

    def test_auth_disabled_default_environment_is_allowed(self):
        """AUTH_DISABLED=true with no ENVIRONMENT set defaults to development."""
        env = {"AUTH_DISABLED": "true"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("ENVIRONMENT", None)
            import middleware.auth as auth_mod

            importlib.reload(auth_mod)
            # Should not raise — defaults to 'development'


# ---------------------------------------------------------------------------
# DB-016: recover_running_jobs() called in lifespan
# ---------------------------------------------------------------------------


class TestRecoverRunningJobsInLifespan:
    """Verify that the FastAPI lifespan calls recover_running_jobs()."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_recover_running_jobs(self):
        """Lifespan startup must call recover_running_jobs()."""
        # Story 40.8: recover_running_jobs is now async
        mock_recover = AsyncMock(return_value=0)
        with patch("main.recover_running_jobs", mock_recover), patch("main.analyze") as mock_analyze:
            mock_analyze._cleanup_orphaned_dirs = MagicMock()
            from main import lifespan

            app = MagicMock()
            async with lifespan(app):
                pass
            mock_recover.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_logs_when_jobs_recovered(self):
        """Lifespan must log when recovered > 0."""
        # Story 40.8: recover_running_jobs is now async
        mock_recover = AsyncMock(return_value=3)
        with (
            patch("main.recover_running_jobs", mock_recover),
            patch("main.analyze") as mock_analyze,
            patch("logging.getLogger"),
        ):
            mock_analyze._cleanup_orphaned_dirs = MagicMock()
            from main import lifespan

            app = MagicMock()
            async with lifespan(app):
                pass
            mock_recover.assert_called_once()


# ---------------------------------------------------------------------------
# DB-004: updated_at trigger migration (SQL validation)
# ---------------------------------------------------------------------------


class TestUpdatedAtTriggerMigration:
    """Validate the SQL migration for the updated_at trigger."""

    def test_migration_file_exists(self):
        path = _MIGRATIONS_DIR / "20260409000001_jobs_trigger_and_check.sql"
        assert path.exists()

    def test_migration_creates_trigger_function(self):
        sql = _read_migration("20260409000001_jobs_trigger_and_check.sql")
        assert "update_updated_at_column" in sql
        assert "new.updated_at = now()" in sql

    def test_migration_creates_trigger_on_jobs(self):
        sql = _read_migration("20260409000001_jobs_trigger_and_check.sql")
        assert "create trigger trg_jobs_updated_at" in sql
        assert "before update on public.jobs" in sql

    def test_migration_uses_for_each_row(self):
        sql = _read_migration("20260409000001_jobs_trigger_and_check.sql")
        assert "for each row" in sql


# ---------------------------------------------------------------------------
# DB-005: CHECK constraint on jobs.status (SQL validation)
# ---------------------------------------------------------------------------


class TestStatusCheckConstraintMigration:
    """Validate the SQL migration for the jobs.status CHECK constraint."""

    def test_migration_normalizes_invalid_statuses(self):
        sql = _read_migration("20260409000001_jobs_trigger_and_check.sql")
        assert "update public.jobs" in sql
        assert "set status = 'failed'" in sql
        assert "where status not in" in sql

    def test_migration_adds_check_constraint(self):
        sql = _read_migration("20260409000001_jobs_trigger_and_check.sql")
        assert "add constraint chk_jobs_status" in sql
        assert "check (status in" in sql

    def test_constraint_includes_all_valid_statuses(self):
        sql = _read_migration("20260409000001_jobs_trigger_and_check.sql")
        for status in ("pending", "running", "completed", "failed", "cancelled"):
            assert f"'{status}'" in sql


# ---------------------------------------------------------------------------
# DB-009: Storage buckets migration (SQL validation)
# ---------------------------------------------------------------------------


class TestStorageBucketsMigration:
    """Validate the SQL migration for storage bucket creation."""

    def test_migration_file_exists(self):
        path = _MIGRATIONS_DIR / "20260409000002_create_storage_buckets.sql"
        assert path.exists()

    def test_migration_creates_jobs_bucket(self):
        sql = _read_migration("20260409000002_create_storage_buckets.sql")
        assert "'jobs'" in sql

    def test_migration_creates_templates_bucket(self):
        sql = _read_migration("20260409000002_create_storage_buckets.sql")
        assert "'templates'" in sql

    def test_migration_uses_on_conflict(self):
        sql = _read_migration("20260409000002_create_storage_buckets.sql")
        assert "on conflict" in sql
        assert "do nothing" in sql

    def test_migration_inserts_into_storage_buckets(self):
        sql = _read_migration("20260409000002_create_storage_buckets.sql")
        assert "insert into storage.buckets" in sql

    def test_buckets_are_private(self):
        sql = _read_migration("20260409000002_create_storage_buckets.sql")
        # Both buckets should have public=false
        assert "false" in sql
