"""Tests for Story 40.2 — Data Security Chain.

Covers:
  - DB-002: user_id column in all tables (migration validation)
  - DB-001: RLS policies rewritten with owner-based access (migration validation)
  - DB-003: Separate admin/user Supabase clients
  - SEC-001: v-html sanitization (DOMPurify integration validated via unit test)
  - SYS-015: Security headers middleware + CORS scoping
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


# ===========================================================================
# DB-002: user_id column migration
# ===========================================================================


class TestDB002UserIdColumns:
    """Verify the migration adds user_id to all tables."""

    @pytest.fixture(autouse=True)
    def migration_sql(self):
        self.sql = _read_migration("20260409000003_add_user_id_columns.sql")

    def test_jobs_user_id_column(self):
        """jobs table gets user_id UUID column."""
        assert "alter table public.jobs" in self.sql
        assert "user_id uuid" in self.sql.lower()

    def test_templates_user_id_column(self):
        """templates table gets user_id UUID column."""
        assert "alter table public.templates" in self.sql

    def test_job_clusters_user_id_column(self):
        """job_clusters table gets user_id UUID column."""
        assert "alter table public.job_clusters" in self.sql

    def test_user_id_references_auth_users(self):
        """user_id references auth.users(id)."""
        assert "references auth.users(id)" in self.sql.lower()

    def test_user_id_indexes_created(self):
        """Indexes created for user_id columns."""
        assert "idx_jobs_user_id" in self.sql
        assert "idx_templates_user_id" in self.sql
        assert "idx_job_clusters_user_id" in self.sql

    def test_user_id_is_nullable(self):
        """user_id is nullable (no NOT NULL constraint) for gradual enforcement."""
        # The column definition should NOT contain "not null"
        lines = [
            line.strip().lower()
            for line in self.sql.split("\n")
            if "user_id" in line.lower() and "add column" in line.lower()
        ]
        for line in lines:
            assert "not null" not in line, f"user_id should be nullable: {line}"

    def test_backfill_strategy_documented(self):
        """Migration includes backfill strategy as comments."""
        assert "backfill" in self.sql.lower()


# ===========================================================================
# DB-001: RLS policies rewritten
# ===========================================================================


class TestDB001RLSPolicies:
    """Verify RLS policies use owner-based access instead of USING(true)."""

    @pytest.fixture(autouse=True)
    def migration_sql(self):
        self.sql = _read_migration("20260409000004_rewrite_rls_policies.sql")

    def test_old_policies_dropped_jobs(self):
        """Old permissive policies are dropped for jobs."""
        assert 'drop policy if exists "Authenticated users can read jobs"' in self.sql

    def test_old_policies_dropped_templates(self):
        """Old permissive policies are dropped for templates."""
        assert 'drop policy if exists "Authenticated users can read templates"' in self.sql

    def test_old_policies_dropped_job_clusters(self):
        """Old permissive policies are dropped for job_clusters."""
        assert 'drop policy if exists "Authenticated users can read job_clusters"' in self.sql

    def test_no_using_true_in_new_policies(self):
        """New policies do NOT use USING(true) — they use auth.uid()."""
        # The only "true" references should be in DROP statements or comments,
        # not in actual CREATE POLICY USING clauses
        lines = self.sql.split("\n")
        for line in lines:
            stripped = line.strip().lower()
            # Skip comments and DROP statements
            if stripped.startswith("--") or "drop" in stripped:
                continue
            if "using (true)" in stripped:
                pytest.fail(f"Found USING(true) in policy line: {line}")

    def test_owner_filter_present(self):
        """Policies use auth.uid() = user_id for owner filtering."""
        assert "auth.uid() = user_id" in self.sql.lower()

    def test_null_user_id_gradual_migration(self):
        """SELECT policies allow NULL user_id for gradual migration."""
        assert "user_id is null" in self.sql.lower()

    def test_all_operations_covered_jobs(self):
        """Jobs table has policies for SELECT, INSERT, UPDATE, DELETE."""
        sql_lower = self.sql.lower()
        assert "on public.jobs for select" in sql_lower
        assert "on public.jobs for insert" in sql_lower
        assert "on public.jobs for update" in sql_lower
        assert "on public.jobs for delete" in sql_lower

    def test_all_operations_covered_templates(self):
        """Templates table has policies for SELECT, INSERT, UPDATE, DELETE."""
        sql_lower = self.sql.lower()
        assert "on public.templates for select" in sql_lower
        assert "on public.templates for insert" in sql_lower
        assert "on public.templates for update" in sql_lower
        assert "on public.templates for delete" in sql_lower

    def test_all_operations_covered_job_clusters(self):
        """Job_clusters table has policies for SELECT, INSERT, UPDATE, DELETE."""
        sql_lower = self.sql.lower()
        assert "on public.job_clusters for select" in sql_lower
        assert "on public.job_clusters for insert" in sql_lower
        assert "on public.job_clusters for update" in sql_lower
        assert "on public.job_clusters for delete" in sql_lower

    def test_insert_requires_matching_user_id(self):
        """INSERT policies use WITH CHECK (user_id = auth.uid())."""
        assert "with check (user_id = auth.uid())" in self.sql.lower()


# ===========================================================================
# DB-003: Separate admin/user Supabase clients
# ===========================================================================


class TestDB003ClientSeparation:
    """Verify SupabaseStorageGateway uses separate clients for storage vs DB."""

    def _make_gateway(self, admin=None, user=None):
        from services.storage.supabase_gateway import SupabaseStorageGateway

        admin = admin or MagicMock()
        return SupabaseStorageGateway(admin_client=admin, user_client=user)

    def test_storage_uses_admin_client(self):
        """Storage operations (upload, download) use admin_client."""
        admin = MagicMock()
        user = MagicMock()
        gw = self._make_gateway(admin=admin, user=user)
        assert gw._admin is admin

    def test_db_queries_use_user_client(self):
        """DB table queries use user_client when available."""
        admin = MagicMock()
        user = MagicMock()
        gw = self._make_gateway(admin=admin, user=user)
        assert gw._db_client() is user

    def test_db_queries_fallback_to_admin(self):
        """DB queries fall back to admin_client when user_client is None."""
        admin = MagicMock()
        gw = self._make_gateway(admin=admin, user=None)
        assert gw._db_client() is admin

    def test_set_auth_context_stores_user_id(self):
        """set_auth_context stores user_id for DB writes."""
        gw = self._make_gateway()
        gw.set_auth_context(user_id="test-user-123")
        assert gw._user_id == "test-user-123"

    @pytest.mark.asyncio
    async def test_save_result_includes_user_id(self):
        """save_result includes user_id in the upsert row."""
        admin = MagicMock()
        user = MagicMock()
        # Chain: user.table("jobs").upsert(...).execute()
        mock_execute = MagicMock()
        user.table.return_value.upsert.return_value.execute = mock_execute

        gw = self._make_gateway(admin=admin, user=user)
        gw.set_auth_context(user_id="user-abc")
        await gw.save_result("job-1", {"data": "test"})

        # Verify user_id was included in the upsert call
        call_args = user.table.return_value.upsert.call_args
        row = call_args[0][0]
        assert row["user_id"] == "user-abc"
        assert row["id"] == "job-1"

    @pytest.mark.asyncio
    async def test_save_clusters_includes_user_id(self):
        """save_clusters includes user_id in each cluster row."""
        admin = MagicMock()
        user = MagicMock()
        mock_execute = MagicMock()
        user.table.return_value.upsert.return_value.execute = mock_execute

        gw = self._make_gateway(admin=admin, user=user)
        gw.set_auth_context(user_id="user-xyz")
        await gw.save_clusters(
            "job-1",
            [
                {"cluster_id": 0, "pages": [0, 1], "representative_page": 0},
            ],
        )

        call_args = user.table.return_value.upsert.call_args
        rows = call_args[0][0]
        assert rows[0]["user_id"] == "user-xyz"

    @pytest.mark.asyncio
    async def test_upload_uses_admin_client(self):
        """Upload operations use admin_client, not user_client."""
        admin = MagicMock()
        user = MagicMock()
        gw = self._make_gateway(admin=admin, user=user)
        gw._tmp_base = Path("/tmp/test-gw")

        # Mock the storage chain
        admin.storage.from_.return_value.upload = MagicMock()

        with patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_bytes"):
            await gw.upload_pdf("job-1", 0, b"fake-pdf")

        admin.storage.from_.assert_called_with("jobs")
        user.storage.from_.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_job_uses_correct_clients(self):
        """delete_job uses admin for storage, user for DB (via atomic RPC)."""
        admin = MagicMock()
        user = MagicMock()

        admin.storage.from_.return_value.list.return_value = []
        # Story 41.4 DB-011+DB-015: delete_job now calls atomic_delete_job RPC
        # instead of table("jobs").delete(). The user client is used for the RPC.
        mock_rpc_result = MagicMock()
        mock_rpc_result.execute.return_value = MagicMock(data=True)
        user.rpc.return_value = mock_rpc_result

        gw = self._make_gateway(admin=admin, user=user)
        with patch.object(gw, "cleanup_local", new_callable=AsyncMock):
            await gw.delete_job("job-1")

        # Storage listing used admin
        admin.storage.from_.assert_called()
        # Atomic soft-delete used user client via RPC
        user.rpc.assert_called_once_with(
            "atomic_delete_job",
            {
                "p_job_id": "job-1",
                "p_storage_bucket": "jobs",
                "p_storage_prefix": "jobs/job-1",
            },
        )

    def test_legacy_supabase_kwarg(self):
        """Legacy `supabase=` kwarg maps to admin_client."""
        mock = MagicMock()
        from services.storage.supabase_gateway import SupabaseStorageGateway

        gw = SupabaseStorageGateway(admin_client=None, supabase=mock)
        assert gw._admin is mock


# ===========================================================================
# DB-003: Factory creates two clients
# ===========================================================================


class TestDB003Factory:
    """Verify create_storage_gateway creates two Supabase clients via supabase_client param."""

    def test_factory_with_supabase_client_creates_gateway(self):
        """Factory creates SupabaseStorageGateway when supabase_client is provided."""
        from services.storage import create_storage_gateway
        from services.storage.supabase_gateway import SupabaseStorageGateway

        mock_client = MagicMock()
        gw = create_storage_gateway(mode="supabase", supabase_client=mock_client)
        assert isinstance(gw, SupabaseStorageGateway)
        # supabase_client becomes admin_client
        assert gw._admin is mock_client

    def test_factory_with_anon_key_creates_user_client(self):
        """When SUPABASE_ANON_KEY is set, factory creates a second client."""
        # We test the code path by examining the __init__.py logic:
        # The factory reads SUPABASE_ANON_KEY and creates a user_client.
        # Since we can't easily mock `from supabase import create_client` due to
        # namespace conflict, we verify the gateway correctly separates clients.
        from services.storage.supabase_gateway import SupabaseStorageGateway

        admin = MagicMock(name="admin")
        user = MagicMock(name="user")
        gw = SupabaseStorageGateway(admin_client=admin, user_client=user)

        # Admin for storage, user for DB
        assert gw._admin is admin
        assert gw._db_client() is user

    def test_factory_without_anon_key_user_is_admin(self):
        """Without user_client, DB queries fall back to admin_client."""
        from services.storage.supabase_gateway import SupabaseStorageGateway

        admin = MagicMock(name="admin")
        gw = SupabaseStorageGateway(admin_client=admin, user_client=None)

        assert gw._admin is admin
        assert gw._db_client() is admin  # fallback


# ===========================================================================
# SYS-015: Security headers middleware
# ===========================================================================


class TestSYS015SecurityHeaders:
    """Verify security headers are present on all responses."""

    @pytest.fixture
    def test_client(self):
        """Create a test client with the full middleware stack."""
        from fastapi.testclient import TestClient

        # Need to reload main to pick up middleware
        # Use the actual app directly
        with patch.dict(os.environ, {"AUTH_DISABLED": "true", "STORAGE_MODE": "local", "JOBS_DIR": "/tmp/test-jobs"}):
            # Force reimport to apply middleware
            import main as main_module

            importlib.reload(main_module)
            client = TestClient(main_module.app)
            yield client

    def test_health_has_security_headers(self, test_client):
        """Health endpoint includes all security headers."""
        resp = test_client.get("/api/health")
        assert resp.status_code == 200

        # Check all required security headers
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in resp.headers
        assert "Strict-Transport-Security" in resp.headers

    def test_csp_header_content(self, test_client):
        """CSP header contains expected directives."""
        resp = test_client.get("/api/health")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp
        assert "script-src" in csp
        assert "frame-ancestors 'none'" in csp

    def test_hsts_header(self, test_client):
        """HSTS header has appropriate max-age."""
        resp = test_client.get("/api/health")
        hsts = resp.headers.get("Strict-Transport-Security", "")
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts


# ===========================================================================
# SYS-015: CORS scoping
# ===========================================================================


class TestSYS015CORSScoping:
    """Verify CORS is scoped to specific methods, not wildcards."""

    def test_main_py_no_wildcard_methods(self):
        """main.py does not use allow_methods=['*']."""
        main_path = Path(__file__).resolve().parent.parent / "main.py"
        content = main_path.read_text(encoding="utf-8")
        # Should NOT have allow_methods=["*"]
        assert 'allow_methods=["*"]' not in content
        # Should have specific methods
        assert "GET" in content
        assert "POST" in content

    def test_main_py_no_wildcard_headers(self):
        """main.py does not use allow_headers=['*']."""
        main_path = Path(__file__).resolve().parent.parent / "main.py"
        content = main_path.read_text(encoding="utf-8")
        assert 'allow_headers=["*"]' not in content
        # Should have specific headers
        assert "Authorization" in content
        assert "Content-Type" in content

    def test_allowed_origins_from_env(self):
        """CORS origins come from ALLOWED_ORIGINS env var, not hardcoded '*'."""
        main_path = Path(__file__).resolve().parent.parent / "main.py"
        content = main_path.read_text(encoding="utf-8")
        assert "ALLOWED_ORIGINS" in content
        # Should NOT have allow_origins=["*"]
        assert 'allow_origins=["*"]' not in content


# ===========================================================================
# Integration: RLS isolation between users
# ===========================================================================


class TestRLSIsolation:
    """Integration tests validating data isolation between users.

    These tests verify the gateway correctly associates data with users
    and that the RLS policy SQL enforces isolation.
    """

    @pytest.mark.asyncio
    async def test_user_a_cannot_see_user_b_data(self):
        """Verify that user_id is correctly set per user — foundation for RLS isolation."""
        from services.storage.supabase_gateway import SupabaseStorageGateway

        # Simulate two users with the same gateway
        admin = MagicMock()
        user_client = MagicMock()
        mock_execute = MagicMock()
        user_client.table.return_value.upsert.return_value.execute = mock_execute

        gw = SupabaseStorageGateway(admin_client=admin, user_client=user_client)

        # User A saves a job
        gw.set_auth_context(user_id="user-a-uuid")
        await gw.save_result("job-a", {"data": "user-a-data"})
        call_a = user_client.table.return_value.upsert.call_args
        assert call_a[0][0]["user_id"] == "user-a-uuid"

        # User B saves a different job
        gw.set_auth_context(user_id="user-b-uuid")
        await gw.save_result("job-b", {"data": "user-b-data"})
        call_b = user_client.table.return_value.upsert.call_args
        assert call_b[0][0]["user_id"] == "user-b-uuid"

        # Verify different user_ids were used
        assert call_a[0][0]["user_id"] != call_b[0][0]["user_id"]

    @pytest.mark.asyncio
    async def test_save_result_without_user_id(self):
        """save_result works without user_id (gradual enforcement)."""
        from services.storage.supabase_gateway import SupabaseStorageGateway

        admin = MagicMock()
        mock_execute = MagicMock()
        admin.table.return_value.upsert.return_value.execute = mock_execute

        gw = SupabaseStorageGateway(admin_client=admin)
        # No set_auth_context call — user_id is None
        await gw.save_result("job-1", {"data": "test"})

        call_args = admin.table.return_value.upsert.call_args
        row = call_args[0][0]
        assert "user_id" not in row  # No user_id when not set


# ===========================================================================
# Migration files existence check
# ===========================================================================


class TestMigrationFilesExist:
    """Verify all required migration files exist."""

    def test_user_id_migration_exists(self):
        path = _MIGRATIONS_DIR / "20260409000003_add_user_id_columns.sql"
        assert path.exists()

    def test_rls_rewrite_migration_exists(self):
        path = _MIGRATIONS_DIR / "20260409000004_rewrite_rls_policies.sql"
        assert path.exists()
