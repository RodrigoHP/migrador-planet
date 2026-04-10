"""Tests for Story 40.8 — Backend Async & State Unification.

Covers:
  - RedisJobStore async API: create, get, save, delete, all_jobs
  - DB-017 guard: save_job refuses to overwrite cancelled/failed -> completed
  - InMemoryJobStore async API with same guards
  - Crash recovery via async recover_running_jobs
  - Concurrent pipeline runs don't block each other
  - Feature flag for dual-write
  - Supabase asyncio.to_thread wrapping (DB-007)
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.job_store import (
    InMemoryJobStore,
    RedisJobStore,
    _reset_job_store,
    get_job_store,
    recover_running_jobs,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job_id(suffix: str = "a") -> str:
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
    mock.scan_iter = scan_iter
    mock.aclose = AsyncMock(side_effect=aclose)
    mock._store = store  # expose for test inspection
    return mock


# ---------------------------------------------------------------------------
# InMemoryJobStore async tests
# ---------------------------------------------------------------------------


class TestInMemoryJobStoreAsync:
    def setup_method(self):
        self.store = InMemoryJobStore()

    @pytest.mark.asyncio
    async def test_create_job_returns_state(self):
        job_id = _make_job_id("1")
        state = await self.store.create_job(job_id)
        assert state["status"] == "pending"
        assert state["result"] is None
        assert isinstance(state["cancel_flag"], asyncio.Event)
        assert isinstance(state["new_event"], asyncio.Event)

    @pytest.mark.asyncio
    async def test_get_job_returns_state(self):
        job_id = _make_job_id("2")
        await self.store.create_job(job_id)
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_job_missing_returns_none(self):
        assert await self.store.get_job("nonexistent") is None

    @pytest.mark.asyncio
    async def test_save_job_persists_state(self):
        job_id = _make_job_id("3")
        state = await self.store.create_job(job_id)
        state["status"] = "completed"
        await self.store.save_job(job_id, state)
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "completed"

    @pytest.mark.asyncio
    async def test_delete_job(self):
        job_id = _make_job_id("4")
        await self.store.create_job(job_id)
        await self.store.delete_job(job_id)
        assert await self.store.get_job(job_id) is None

    @pytest.mark.asyncio
    async def test_all_jobs_returns_all(self):
        j1, j2 = _make_job_id("5"), _make_job_id("6")
        await self.store.create_job(j1)
        await self.store.create_job(j2)
        all_jobs = await self.store.all_jobs()
        assert j1 in all_jobs
        assert j2 in all_jobs

    @pytest.mark.asyncio
    async def test_evict_expired_removes_stale(self):
        job_id = _make_job_id("7")
        state = await self.store.create_job(job_id)
        state["status"] = "completed"
        state["created_at"] = time.time() - 9999
        removed = await self.store.evict_expired()
        assert removed == 1

    @pytest.mark.asyncio
    async def test_db017_guard_blocks_overwrite_cancelled(self):
        """DB-017: save_job must NOT overwrite cancelled status to completed."""
        job_id = _make_job_id("8")
        state = await self.store.create_job(job_id)
        state["status"] = "cancelled"
        await self.store.save_job(job_id, state)

        # Try to overwrite to completed
        overwrite = {**state, "status": "completed"}
        await self.store.save_job(job_id, overwrite)

        # Status should remain cancelled
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_db017_guard_blocks_overwrite_failed(self):
        """DB-017: save_job must NOT overwrite failed status to completed."""
        job_id = _make_job_id("9")
        state = await self.store.create_job(job_id)
        state["status"] = "failed"
        await self.store.save_job(job_id, state)

        overwrite = {**state, "status": "completed"}
        await self.store.save_job(job_id, overwrite)

        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "failed"

    @pytest.mark.asyncio
    async def test_db017_allows_same_terminal_status(self):
        """DB-017: Saving with same terminal status is allowed (idempotent)."""
        job_id = _make_job_id("a")
        state = await self.store.create_job(job_id)
        state["status"] = "failed"
        state["error"] = "original error"
        await self.store.save_job(job_id, state)

        # Same status with updated error is fine
        updated = {**state, "status": "failed", "error": "updated error"}
        await self.store.save_job(job_id, updated)

        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "failed"
        assert retrieved["error"] == "updated error"


# ---------------------------------------------------------------------------
# RedisJobStore async tests (mocked async Redis)
# ---------------------------------------------------------------------------


class TestRedisJobStoreAsync:
    def setup_method(self):
        self.mock_redis = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=self.mock_redis):
            self.store = RedisJobStore("redis://localhost:6379")

    @pytest.mark.asyncio
    async def test_create_job_persists_to_redis(self):
        job_id = _make_job_id("a")
        state = await self.store.create_job(job_id)
        assert state["status"] == "pending"
        # Verify data is in Redis mock
        raw = await self.mock_redis.get(f"migrador:job:{job_id}")
        assert raw is not None

    @pytest.mark.asyncio
    async def test_get_job_deserializes_from_redis(self):
        job_id = _make_job_id("b")
        await self.store.create_job(job_id)
        # Clear cache to force Redis read
        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_job_uses_cache(self):
        job_id = _make_job_id("c")
        await self.store.create_job(job_id)
        # Second get should use cache (no additional Redis call)
        call_count_before = self.mock_redis.get.call_count
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert self.mock_redis.get.call_count == call_count_before

    @pytest.mark.asyncio
    async def test_get_job_missing_returns_none(self):
        self.store._cache.clear()
        assert await self.store.get_job("nonexistent-id") is None

    @pytest.mark.asyncio
    async def test_save_job_updates_redis(self):
        job_id = _make_job_id("d")
        state = await self.store.create_job(job_id)
        state["status"] = "completed"
        await self.store.save_job(job_id, state)
        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "completed"

    @pytest.mark.asyncio
    async def test_delete_job_removes_from_redis(self):
        job_id = _make_job_id("e")
        await self.store.create_job(job_id)
        await self.store.delete_job(job_id)
        self.store._cache.clear()
        assert await self.store.get_job(job_id) is None

    @pytest.mark.asyncio
    async def test_local_asyncio_events_attached_on_get(self):
        job_id = _make_job_id("f")
        await self.store.create_job(job_id)
        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert isinstance(retrieved["cancel_flag"], asyncio.Event)
        assert isinstance(retrieved["new_event"], asyncio.Event)

    @pytest.mark.asyncio
    async def test_db017_guard_blocks_overwrite_cancelled(self):
        """DB-017: Redis save_job must NOT overwrite cancelled -> completed."""
        job_id = _make_job_id("g")
        state = await self.store.create_job(job_id)
        state["status"] = "cancelled"
        await self.store.save_job(job_id, state)

        overwrite = {**state, "status": "completed"}
        await self.store.save_job(job_id, overwrite)

        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_db017_guard_blocks_overwrite_failed(self):
        """DB-017: Redis save_job must NOT overwrite failed -> completed."""
        job_id = _make_job_id("h")
        state = await self.store.create_job(job_id)
        state["status"] = "failed"
        await self.store.save_job(job_id, state)

        overwrite = {**state, "status": "completed"}
        await self.store.save_job(job_id, overwrite)

        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "failed"

    @pytest.mark.asyncio
    async def test_all_jobs_returns_dict(self):
        job_id = _make_job_id("i")
        await self.store.create_job(job_id)
        all_jobs = await self.store.all_jobs()
        assert isinstance(all_jobs, dict)
        assert job_id in all_jobs

    @pytest.mark.asyncio
    async def test_evict_expired_returns_zero(self):
        """RedisJobStore delegates eviction to Redis TTL."""
        assert await self.store.evict_expired() == 0

    @pytest.mark.asyncio
    async def test_close_calls_aclose(self):
        await self.store.close()
        self.mock_redis.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# Factory tests (async)
# ---------------------------------------------------------------------------


class TestGetJobStoreFactory:
    def setup_method(self):
        _reset_job_store()

    def teardown_method(self):
        _reset_job_store()

    def test_returns_in_memory_when_no_redis_url(self):
        import os

        os.environ.pop("REDIS_URL", None)
        store = get_job_store()
        assert isinstance(store, InMemoryJobStore)

    def test_returns_same_singleton_on_repeated_calls(self):
        store1 = get_job_store()
        store2 = get_job_store()
        assert store1 is store2

    def test_falls_back_to_in_memory_on_redis_failure(self):
        with patch.dict("os.environ", {"REDIS_URL": "redis://bad-host:6379"}):
            _reset_job_store()
            with patch("redis.asyncio.from_url", side_effect=Exception("connection refused")):
                store = get_job_store()
                assert isinstance(store, InMemoryJobStore)


# ---------------------------------------------------------------------------
# recover_running_jobs tests (async)
# ---------------------------------------------------------------------------


class TestRecoverRunningJobsAsync:
    def setup_method(self):
        _reset_job_store()

    def teardown_method(self):
        _reset_job_store()

    @pytest.mark.asyncio
    async def test_marks_running_jobs_as_failed(self):
        store = get_job_store()
        assert isinstance(store, InMemoryJobStore)
        job_id = _make_job_id("r")
        state = await store.create_job(job_id)
        state["status"] = "running"

        recovered = await recover_running_jobs()
        assert recovered == 1
        updated = await store.get_job(job_id)
        assert updated is not None
        assert updated["status"] == "failed"
        assert "restarted" in updated["error"].lower()

    @pytest.mark.asyncio
    async def test_does_not_touch_non_running_jobs(self):
        store = get_job_store()
        assert isinstance(store, InMemoryJobStore)

        for suffix, status in [("1", "completed"), ("2", "failed"), ("3", "pending")]:
            job_id = _make_job_id(suffix)
            state = await store.create_job(job_id)
            state["status"] = status

        recovered = await recover_running_jobs()
        assert recovered == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_jobs(self):
        assert await recover_running_jobs() == 0


# ---------------------------------------------------------------------------
# Concurrent pipeline simulation tests
# ---------------------------------------------------------------------------


class TestConcurrentPipelines:
    """Verify that concurrent pipeline runs don't block each other."""

    def setup_method(self):
        self.store = InMemoryJobStore()

    @pytest.mark.asyncio
    async def test_concurrent_creates_dont_block(self):
        """Multiple create_job calls can run concurrently without blocking."""
        job_ids = [_make_job_id(str(i)) for i in range(5)]
        results = await asyncio.gather(*(self.store.create_job(jid) for jid in job_ids))
        assert len(results) == 5
        for state in results:
            assert state["status"] == "pending"

    @pytest.mark.asyncio
    async def test_concurrent_saves_dont_block(self):
        """Multiple save_job calls to different jobs can run concurrently."""
        job_ids = [_make_job_id(str(i)) for i in range(5)]
        for jid in job_ids:
            await self.store.create_job(jid)

        async def update_job(jid: str, status: str):
            state = await self.store.get_job(jid)
            assert state is not None
            state["status"] = status
            await self.store.save_job(jid, state)

        await asyncio.gather(*(update_job(jid, "running") for jid in job_ids))

        for jid in job_ids:
            state = await self.store.get_job(jid)
            assert state is not None
            assert state["status"] == "running"

    @pytest.mark.asyncio
    async def test_concurrent_read_write_isolation(self):
        """Reads and writes to different jobs don't interfere."""
        j1, j2 = _make_job_id("x"), _make_job_id("y")
        state1 = await self.store.create_job(j1)
        state2 = await self.store.create_job(j2)

        state1["status"] = "completed"
        state1["result"] = {"data": "job1"}
        await self.store.save_job(j1, state1)

        state2["status"] = "running"
        await self.store.save_job(j2, state2)

        r1 = await self.store.get_job(j1)
        assert r1 is not None
        r2 = await self.store.get_job(j2)
        assert r2 is not None
        assert r1["status"] == "completed"
        assert r2["status"] == "running"


# ---------------------------------------------------------------------------
# Feature flag dual-write test
# ---------------------------------------------------------------------------


class TestFeatureDualWrite:
    @pytest.mark.asyncio
    async def test_dual_write_fires_write_behind(self):
        """When FEATURE_DUAL_WRITE is enabled, save_job triggers write-behind."""
        mock_redis = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisJobStore("redis://localhost:6379")

        job_id = _make_job_id("dw")
        state = await store.create_job(job_id)
        state["status"] = "completed"
        state["result"] = {"key": "value"}

        with patch.object(store, "_write_behind_supabase", new_callable=AsyncMock) as mock_wb:
            with patch("services.job_store.FEATURE_DUAL_WRITE", True):
                await store.save_job(job_id, state)
                # write_behind should have been scheduled
                # Give the event loop a chance to run the task
                await asyncio.sleep(0)
                mock_wb.assert_called_once_with(job_id, state)

    @pytest.mark.asyncio
    async def test_no_dual_write_when_disabled(self):
        """When FEATURE_DUAL_WRITE is disabled, no write-behind occurs."""
        mock_redis = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisJobStore("redis://localhost:6379")

        job_id = _make_job_id("nd")
        state = await store.create_job(job_id)
        state["status"] = "completed"

        with patch.object(store, "_write_behind_supabase", new_callable=AsyncMock) as mock_wb:
            with patch("services.job_store.FEATURE_DUAL_WRITE", False):
                await store.save_job(job_id, state)
                await asyncio.sleep(0)
                mock_wb.assert_not_called()


# ---------------------------------------------------------------------------
# Supabase asyncio.to_thread wrapping test (DB-007)
# ---------------------------------------------------------------------------


class TestSupabaseAsyncWrapping:
    """Verify that SupabaseStorageGateway wraps sync SDK calls with asyncio.to_thread."""

    @pytest.mark.asyncio
    async def test_save_result_uses_to_thread(self):
        from services.storage.supabase_gateway import SupabaseStorageGateway

        mock_client = MagicMock()
        # Mock the table().select().eq().is_().execute() chain for status check
        # Story 41.4: .is_("deleted_at", "null") added for soft-delete filtering
        mock_execute = MagicMock()
        mock_execute.data = []  # no existing row
        mock_is = MagicMock()
        mock_is.execute.return_value = mock_execute
        mock_eq = MagicMock()
        mock_eq.is_.return_value = mock_is
        mock_eq.execute.return_value = mock_execute  # fallback
        mock_select = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_table = MagicMock()
        mock_table.select.return_value = mock_select
        # Mock for upsert
        mock_upsert_exec = MagicMock()
        mock_upsert = MagicMock()
        mock_upsert.execute.return_value = mock_upsert_exec
        mock_table.upsert.return_value = mock_upsert
        mock_client.table.return_value = mock_table

        gw = SupabaseStorageGateway(admin_client=mock_client)

        to_thread_calls = []

        async def tracking_to_thread(fn, *args, **kwargs):
            to_thread_calls.append(fn)
            # Execute the callable synchronously (it's a lambda or sync func)
            return fn(*args, **kwargs) if callable(fn) else fn

        with patch("services.storage.supabase_gateway.asyncio.to_thread", side_effect=tracking_to_thread):
            await gw.save_result("test-job", {"foo": "bar"})
            # Two calls: status check + upsert
            assert len(to_thread_calls) == 2

    @pytest.mark.asyncio
    async def test_save_result_db017_blocks_terminal(self):
        """DB-017: save_result checks status and blocks overwriting terminal statuses."""
        from services.storage.supabase_gateway import SupabaseStorageGateway

        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = [{"status": "cancelled"}]
        # Chain: table().select().eq().is_().execute()
        # Story 41.4: added .is_("deleted_at", "null") for soft-delete filtering
        mock_is = MagicMock()
        mock_is.execute.return_value = mock_execute
        mock_eq = MagicMock()
        mock_eq.is_.return_value = mock_is
        mock_eq.execute.return_value = mock_execute  # fallback
        mock_select = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_table = MagicMock()
        mock_table.select.return_value = mock_select
        mock_client.table.return_value = mock_table

        gw = SupabaseStorageGateway(admin_client=mock_client)

        to_thread_calls = []

        async def tracking_to_thread(fn, *args, **kwargs):
            to_thread_calls.append(fn)
            return fn(*args, **kwargs) if callable(fn) else fn

        with patch("services.storage.supabase_gateway.asyncio.to_thread", side_effect=tracking_to_thread):
            await gw.save_result("test-job", {"foo": "bar"})
            # Should have only the status check call, NOT the upsert
            assert len(to_thread_calls) == 1


# ---------------------------------------------------------------------------
# Crash recovery with Redis (simulated)
# ---------------------------------------------------------------------------


class TestCrashRecovery:
    """Simulate server crash and verify job state is recoverable from Redis."""

    @pytest.mark.asyncio
    async def test_job_survives_cache_loss(self):
        """Job state in Redis survives if in-memory cache is lost (simulating crash)."""
        mock_redis = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisJobStore("redis://localhost:6379")

        job_id = _make_job_id("cr")
        state = await store.create_job(job_id)
        state["status"] = "completed"
        state["result"] = {"data": "important"}
        await store.save_job(job_id, state)

        # Simulate crash: clear in-memory cache and local data
        store._cache.clear()
        store._local.clear()

        # Job should still be recoverable from Redis
        recovered = await store.get_job(job_id)
        assert recovered is not None
        assert recovered["status"] == "completed"
        assert recovered["result"] == {"data": "important"}

    @pytest.mark.asyncio
    async def test_running_job_recovery_after_crash(self):
        """Jobs left in 'running' state are recovered to 'failed' on startup."""
        _reset_job_store()
        mock_redis = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
                _reset_job_store()
                store = get_job_store()

                job_id = _make_job_id("rr")
                state = await store.create_job(job_id)
                state["status"] = "running"
                await store.save_job(job_id, state)

                # Simulate restart: recover running jobs
                recovered = await recover_running_jobs()
                assert recovered == 1

                result = await store.get_job(job_id)
                assert result is not None
                assert result["status"] == "failed"
                assert "restarted" in result["error"].lower()
        _reset_job_store()
