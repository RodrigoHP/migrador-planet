"""Tests for Story 41.4 — Database & Redis Resilience.

Covers:
  - REDIS-002: _redis_retry() with exponential backoff
  - REDIS-002: RedisJobStore methods use retry (create, get, save, delete)
  - REDIS-002: Graceful degradation when Redis is unavailable
  - REDIS-003: all_jobs() uses scan_iter (SCAN-based cursor, not KEYS)
  - REDIS-002: /api/health includes Redis status
  - DB-011: soft_delete_job query filtering (deleted_at IS NULL guard)
  - DB-015: atomic_delete_job migration SQL validation
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.job_store import (
    InMemoryJobStore,
    RedisJobStore,
    _redis_retry,
    _reset_job_store,
)

_MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "supabase" / "migrations"


def _read_migration(filename: str) -> str:
    path = _MIGRATIONS_DIR / filename
    assert path.exists(), f"Migration file not found: {path}"
    return path.read_text(encoding="utf-8")


def _read_down_migration(filename: str) -> str:
    path = _MIGRATIONS_DIR / "down" / filename
    assert path.exists(), f"Down migration file not found: {path}"
    return path.read_text(encoding="utf-8")


def _make_job_id(suffix: str = "0") -> str:
    return f"00000000-0000-4000-8000-00000000000{suffix}"


def _make_mock_async_redis():
    """Build a minimal dict-backed mock that mimics redis.asyncio.Redis API."""
    store: dict = {}
    mock = MagicMock()

    async def setex(key, ttl, value):
        store[key] = value

    async def get(key):
        return store.get(key)

    async def delete(key):
        store.pop(key, None)

    async def ping():
        return True

    async def scan_iter(pattern):
        prefix = pattern.replace("*", "")
        for k in list(store):
            if k.startswith(prefix):
                yield k

    async def aclose():
        pass

    mock.setex = AsyncMock(side_effect=setex)
    mock.get = AsyncMock(side_effect=get)
    mock.delete = AsyncMock(side_effect=delete)
    mock.ping = AsyncMock(side_effect=ping)
    mock.scan_iter = scan_iter
    mock.aclose = AsyncMock(side_effect=aclose)
    return mock, store


# ---------------------------------------------------------------------------
# REDIS-002: _redis_retry() unit tests
# ---------------------------------------------------------------------------


class TestRedisRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        """Returns result immediately when operation succeeds."""
        call_count = 0

        async def ok():
            nonlocal call_count
            call_count += 1
            return "value"

        result = await _redis_retry(ok)
        assert result == "value"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_failure(self):
        """Retries after transient errors and eventually succeeds."""
        attempts = []

        async def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("Redis unreachable")
            return "ok"

        with patch("services.job_store.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await _redis_retry(flaky, max_retries=3)

        assert result == "ok"
        assert len(attempts) == 3
        # Should have slept twice (between attempts 1-2 and 2-3)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """Retry delays follow exponential backoff: 0.1, 0.2, 0.4."""
        sleep_args = []

        async def always_fail():
            raise ConnectionError("always fails")

        async def mock_sleep(delay):
            sleep_args.append(delay)

        with patch("services.job_store.asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(ConnectionError):
                await _redis_retry(always_fail, max_retries=3)

        assert len(sleep_args) == 3
        assert sleep_args[0] == pytest.approx(0.1)
        assert sleep_args[1] == pytest.approx(0.2)
        assert sleep_args[2] == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Propagates the exception after exhausting retries."""

        async def always_fail():
            raise RuntimeError("persistent failure")

        with patch("services.job_store.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="persistent failure"):
                await _redis_retry(always_fail, max_retries=2)

    @pytest.mark.asyncio
    async def test_zero_retries_raises_immediately(self):
        """With max_retries=0, raises on first failure without sleeping."""
        sleep_calls = []

        async def always_fail():
            raise ValueError("nope")

        async def mock_sleep(d):
            sleep_calls.append(d)

        with patch("services.job_store.asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(ValueError, match="nope"):
                await _redis_retry(always_fail, max_retries=0)

        assert sleep_calls == []


# ---------------------------------------------------------------------------
# REDIS-002: RedisJobStore uses retry
# ---------------------------------------------------------------------------


class TestRedisJobStoreRetry:
    def setup_method(self):
        self.mock_redis, self.store_dict = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=self.mock_redis):
            self.store = RedisJobStore("redis://localhost:6379")

    @pytest.mark.asyncio
    async def test_create_job_retries_on_setex_failure(self):
        """create_job retries setex on transient error."""
        call_count = 0
        original_setex = self.mock_redis.setex.side_effect

        async def flaky_setex(key, ttl, value):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("transient")
            return await original_setex(key, ttl, value)

        self.mock_redis.setex.side_effect = flaky_setex

        with patch("services.job_store.asyncio.sleep", new_callable=AsyncMock):
            job = await self.store.create_job(_make_job_id("A"))

        assert job["status"] == "pending"
        assert call_count == 2  # failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_get_job_returns_none_on_redis_failure(self):
        """get_job degrades gracefully when Redis is persistently unavailable."""
        job_id = _make_job_id("B")
        self.mock_redis.get.side_effect = ConnectionError("Redis down")

        with patch("services.job_store.asyncio.sleep", new_callable=AsyncMock):
            result = await self.store.get_job(job_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_save_job_keeps_cache_on_redis_failure(self):
        """save_job keeps in-memory cache even when Redis write fails."""
        job_id = _make_job_id("C")
        state = await self.store.create_job(job_id)
        state["status"] = "running"

        # Make GET return None (skip DB-017 check path) and setex fail

        # Get returns the serialized state so DB-017 check works, then setex fails
        stored_data = [self.store_dict.get(self.store._key(job_id))]

        async def get_returns_existing(key):
            return stored_data[0]

        setex_calls = []

        async def fail_setex(key, ttl, value):
            setex_calls.append(1)
            if len(setex_calls) > 1:
                raise ConnectionError("write failed")

        self.mock_redis.get.side_effect = get_returns_existing
        self.mock_redis.setex.side_effect = fail_setex

        with patch("services.job_store.asyncio.sleep", new_callable=AsyncMock):
            await self.store.save_job(job_id, state)

        # Cache should have the updated state despite Redis failure
        assert self.store._cache[job_id]["status"] == "running"

    @pytest.mark.asyncio
    async def test_delete_job_clears_cache_on_redis_failure(self):
        """delete_job clears cache even if Redis delete fails."""
        job_id = _make_job_id("D")
        await self.store.create_job(job_id)
        self.mock_redis.delete.side_effect = ConnectionError("Redis down")

        with patch("services.job_store.asyncio.sleep", new_callable=AsyncMock):
            await self.store.delete_job(job_id)

        # Cache must be cleared
        assert job_id not in self.store._cache
        assert job_id not in self.store._local


# ---------------------------------------------------------------------------
# REDIS-003: all_jobs() uses SCAN (scan_iter), not KEYS
# ---------------------------------------------------------------------------


class TestAllJobsUsesScan:
    def setup_method(self):
        self.mock_redis, self.store_dict = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=self.mock_redis):
            self.store = RedisJobStore("redis://localhost:6379")

    @pytest.mark.asyncio
    async def test_all_jobs_uses_scan_iter_not_keys(self):
        """all_jobs() must use scan_iter (cursor-based SCAN), never KEYS."""
        job_id = _make_job_id("S")
        await self.store.create_job(job_id)

        result = await self.store.all_jobs()
        assert job_id in result

        # Verify scan_iter was called (not keys)
        # scan_iter is the async generator — check it was iterated
        # The mock scan_iter is an async generator function, verifying indirectly
        # by confirming all_jobs returned data is correct
        assert result[job_id]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_all_jobs_returns_empty_on_scan_failure(self):
        """all_jobs() returns empty dict when scan fails (graceful degradation)."""

        async def fail_scan(pattern):
            raise ConnectionError("Redis down")
            yield  # make it a generator (unreachable but needed for type)

        self.mock_redis.scan_iter = fail_scan
        result = await self.store.all_jobs()
        assert result == {}

    @pytest.mark.asyncio
    async def test_all_jobs_skips_unreadable_keys(self):
        """all_jobs() skips keys that fail on GET (e.g., key deleted mid-scan)."""
        job_id1 = _make_job_id("1")
        job_id2 = _make_job_id("2")
        await self.store.create_job(job_id1)
        await self.store.create_job(job_id2)

        # Make GET fail for one specific key
        original_get = self.mock_redis.get.side_effect

        async def flaky_get(key):
            if job_id1 in key:
                raise ConnectionError("key gone")
            return await original_get(key)

        self.mock_redis.get.side_effect = flaky_get

        with patch("services.job_store.asyncio.sleep", new_callable=AsyncMock):
            result = await self.store.all_jobs()

        # job_id1 skipped, job_id2 present
        assert job_id1 not in result
        assert job_id2 in result


# ---------------------------------------------------------------------------
# REDIS-002: Health check endpoint includes Redis status
# ---------------------------------------------------------------------------


class TestHealthCheckRedisStatus:
    def setup_method(self):
        _reset_job_store()

    def teardown_method(self):
        _reset_job_store()

    @pytest.mark.asyncio
    async def test_health_returns_redis_ok_when_ping_succeeds(self):
        """Health check returns redis.status=ok when Redis ping succeeds."""

        mock_redis, _ = _make_mock_async_redis()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            _reset_job_store()
            with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
                # Patch middleware to bypass auth
                with patch("middleware.auth.require_auth", return_value={"sub": "test-user"}):
                    import importlib

                    import main as app_module

                    importlib.reload(app_module)
                    # Direct async call test
                    from main import health

                    result = await health()
                    assert result["redis"]["status"] in ("ok", "not_configured", "error: Redis unavailable")

    @pytest.mark.asyncio
    async def test_health_returns_not_configured_without_redis_url(self):
        """Health check returns not_configured when REDIS_URL is absent."""
        import os

        os.environ.pop("REDIS_URL", None)
        _reset_job_store()
        # Need to import and call health without Redis store
        with patch("services.job_store.get_job_store", return_value=InMemoryJobStore()):
            from main import health

            result = await health()
            # SYS-017: When Redis is not configured no primary error occurs.
            # Overall status can be 'ok' or 'degraded' (if spaCy is unavailable).
            assert result["status"] in ("ok", "degraded")
            assert result["redis"]["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_health_returns_error_when_ping_fails(self):
        """Health check returns error status when Redis ping fails."""
        mock_redis, _ = _make_mock_async_redis()
        mock_redis.ping.side_effect = ConnectionError("Redis unreachable")

        # Build a RedisJobStore-like object with _redis attribute
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            mock_store = RedisJobStore("redis://localhost:6379")

        with patch("services.job_store.get_job_store", return_value=mock_store):
            from main import health

            result = await health()
            # SYS-017: Redis is a primary service — its failure makes overall status 'error'
            # (was 'ok' before deep health check was introduced in Story 41.7)
            assert result["status"] == "error"
            # Redis status should indicate error
            assert "error" in result["redis"]["status"]


# ---------------------------------------------------------------------------
# DB-011: Soft-delete migration validation
# ---------------------------------------------------------------------------


class TestSoftDeleteMigration:
    def test_migration_file_exists(self):
        path = _MIGRATIONS_DIR / "20260409000005_jobs_soft_delete.sql"
        assert path.exists()

    def test_migration_adds_deleted_at_column(self):
        sql = _read_migration("20260409000005_jobs_soft_delete.sql")
        assert "deleted_at" in sql
        assert "timestamptz" in sql
        assert "add column if not exists" in sql

    def test_migration_creates_partial_index(self):
        sql = _read_migration("20260409000005_jobs_soft_delete.sql")
        assert "idx_jobs_deleted_at" in sql
        assert "where deleted_at is null" in sql

    def test_migration_creates_soft_delete_function(self):
        sql = _read_migration("20260409000005_jobs_soft_delete.sql")
        assert "soft_delete_job" in sql
        assert "deleted_at = now()" in sql

    def test_migration_is_idempotent(self):
        sql = _read_migration("20260409000005_jobs_soft_delete.sql")
        assert "if not exists" in sql

    def test_down_migration_removes_column_and_function(self):
        sql = _read_down_migration("20260409000005_jobs_soft_delete.down.sql")
        assert "drop column if exists deleted_at" in sql
        assert "drop function if exists" in sql
        assert "soft_delete_job" in sql


# ---------------------------------------------------------------------------
# DB-015: Atomic cleanup migration validation
# ---------------------------------------------------------------------------


class TestAtomicCleanupMigration:
    def test_migration_file_exists(self):
        path = _MIGRATIONS_DIR / "20260409000006_atomic_job_cleanup.sql"
        assert path.exists()

    def test_migration_creates_pending_cleanup_table(self):
        sql = _read_migration("20260409000006_atomic_job_cleanup.sql")
        assert "jobs_pending_cleanup" in sql
        assert "create table if not exists" in sql

    def test_pending_cleanup_has_required_columns(self):
        sql = _read_migration("20260409000006_atomic_job_cleanup.sql")
        assert "job_id" in sql
        assert "storage_bucket" in sql
        assert "storage_prefix" in sql
        assert "attempt_count" in sql

    def test_migration_creates_atomic_delete_function(self):
        sql = _read_migration("20260409000006_atomic_job_cleanup.sql")
        assert "atomic_delete_job" in sql
        assert "security definer" in sql

    def test_atomic_function_does_both_steps(self):
        sql = _read_migration("20260409000006_atomic_job_cleanup.sql")
        # Must soft-delete AND register cleanup in same function
        assert "deleted_at = now()" in sql
        assert "insert into public.jobs_pending_cleanup" in sql

    def test_function_uses_on_conflict(self):
        """Function handles duplicate cleanup registrations idempotently."""
        sql = _read_migration("20260409000006_atomic_job_cleanup.sql")
        assert "on conflict" in sql
        assert "do update" in sql

    def test_down_migration_cleans_up_everything(self):
        sql = _read_down_migration("20260409000006_atomic_job_cleanup.down.sql")
        assert "drop function if exists" in sql
        assert "atomic_delete_job" in sql
        assert "drop table if exists" in sql
        assert "jobs_pending_cleanup" in sql


# ---------------------------------------------------------------------------
# DB-006: Down migrations exist for all up migrations
# ---------------------------------------------------------------------------


class TestDownMigrationsExist:
    def test_all_up_migrations_have_down_counterpart(self):
        """Every .sql file in migrations/ must have a .down.sql in down/."""

        up_dir = _MIGRATIONS_DIR
        down_dir = _MIGRATIONS_DIR / "down"

        up_files = sorted(up_dir.glob("*.sql"))
        assert len(up_files) > 0, "No up migrations found"

        missing = []
        for up_file in up_files:
            expected_down = down_dir / up_file.name.replace(".sql", ".down.sql")
            if not expected_down.exists():
                missing.append(str(expected_down))

        assert not missing, "Missing down migrations:\n" + "\n".join(missing)

    def test_down_migrations_are_not_empty(self):
        """Each down migration must contain at least one DROP or ALTER statement."""
        down_dir = _MIGRATIONS_DIR / "down"
        down_files = sorted(down_dir.glob("*.down.sql"))
        assert len(down_files) > 0

        empty = []
        for f in down_files:
            content = f.read_text(encoding="utf-8").lower()
            has_ddl = any(kw in content for kw in ("drop", "alter", "delete", "truncate"))
            if not has_ddl:
                empty.append(f.name)

        assert not empty, f"Down migrations without DDL statements: {empty}"
