"""Tests for backend/services/job_store.py (Story 15.4, updated for Story 40.8 async API).

Covers:
  - InMemoryJobStore: create, get, delete, evict_expired, all_jobs (async)
  - RedisJobStore: create, get, save, delete, all_jobs (mocked async Redis)
  - get_job_store factory: in-memory fallback when no REDIS_URL
  - recover_running_jobs: marks 'running' jobs as 'failed' (async)
  - _reset_job_store: test isolation helper
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

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job_id(suffix: str = "a") -> str:
    return f"00000000-0000-4000-8000-00000000000{suffix}"


# ---------------------------------------------------------------------------
# InMemoryJobStore tests (async)
# ---------------------------------------------------------------------------


class TestInMemoryJobStore:
    def setup_method(self):
        self.store = InMemoryJobStore()

    @pytest.mark.asyncio
    async def test_create_job_returns_state(self):
        job_id = _make_job_id("1")
        state = await self.store.create_job(job_id)
        assert state["status"] == "pending"
        assert state["result"] is None
        assert state["error"] is None
        assert isinstance(state["cancel_flag"], asyncio.Event)
        assert isinstance(state["new_event"], asyncio.Event)
        assert state["pipeline_done"] is False
        assert "created_at" in state

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
    async def test_delete_job(self):
        job_id = _make_job_id("3")
        await self.store.create_job(job_id)
        await self.store.delete_job(job_id)
        assert await self.store.get_job(job_id) is None

    @pytest.mark.asyncio
    async def test_all_jobs_returns_all(self):
        job_id1 = _make_job_id("4")
        job_id2 = _make_job_id("5")
        await self.store.create_job(job_id1)
        await self.store.create_job(job_id2)
        all_jobs = await self.store.all_jobs()
        assert job_id1 in all_jobs
        assert job_id2 in all_jobs

    @pytest.mark.asyncio
    async def test_evict_expired_removes_stale_completed_jobs(self):
        job_id = _make_job_id("6")
        state = await self.store.create_job(job_id)
        state["status"] = "completed"
        # Force created_at to be in the past (beyond TTL)
        state["created_at"] = time.time() - 9999
        removed = await self.store.evict_expired()
        assert removed == 1
        assert await self.store.get_job(job_id) is None

    @pytest.mark.asyncio
    async def test_evict_expired_keeps_running_jobs(self):
        job_id = _make_job_id("7")
        state = await self.store.create_job(job_id)
        state["status"] = "running"
        state["created_at"] = time.time() - 9999
        removed = await self.store.evict_expired()
        assert removed == 0
        assert await self.store.get_job(job_id) is not None

    @pytest.mark.asyncio
    async def test_evict_expired_keeps_recent_completed_jobs(self):
        job_id = _make_job_id("8")
        state = await self.store.create_job(job_id)
        state["status"] = "completed"
        state["created_at"] = time.time()  # very recent
        removed = await self.store.evict_expired()
        assert removed == 0


# ---------------------------------------------------------------------------
# RedisJobStore tests (mocked async Redis)
# ---------------------------------------------------------------------------


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
    return mock


class TestRedisJobStore:
    def setup_method(self):
        self.mock_redis = _make_mock_async_redis()
        with patch("redis.asyncio.from_url", return_value=self.mock_redis):
            self.store = RedisJobStore("redis://localhost:6379")

    @pytest.mark.asyncio
    async def test_create_job_persists_to_redis(self):
        job_id = _make_job_id("a")
        state = await self.store.create_job(job_id)
        assert state["status"] == "pending"
        # Verify data is in Redis
        raw = await self.mock_redis.get(f"migrador:job:{job_id}")
        assert raw is not None

    @pytest.mark.asyncio
    async def test_get_job_deserializes_from_redis(self):
        job_id = _make_job_id("b")
        await self.store.create_job(job_id)
        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_job_missing_returns_none(self):
        self.store._cache.clear()
        assert await self.store.get_job("nonexistent-id") is None

    @pytest.mark.asyncio
    async def test_save_job_updates_redis(self):
        job_id = _make_job_id("c")
        state = await self.store.create_job(job_id)
        state["status"] = "completed"
        await self.store.save_job(job_id, state)
        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert retrieved["status"] == "completed"

    @pytest.mark.asyncio
    async def test_delete_job_removes_from_redis(self):
        job_id = _make_job_id("d")
        await self.store.create_job(job_id)
        await self.store.delete_job(job_id)
        self.store._cache.clear()
        assert await self.store.get_job(job_id) is None

    @pytest.mark.asyncio
    async def test_local_asyncio_events_attached_on_get(self):
        job_id = _make_job_id("e")
        await self.store.create_job(job_id)
        self.store._cache.clear()
        retrieved = await self.store.get_job(job_id)
        assert retrieved is not None
        assert isinstance(retrieved["cancel_flag"], asyncio.Event)
        assert isinstance(retrieved["new_event"], asyncio.Event)

    @pytest.mark.asyncio
    async def test_evict_expired_returns_zero(self):
        """RedisJobStore delegates eviction to Redis TTL."""
        assert await self.store.evict_expired() == 0

    @pytest.mark.asyncio
    async def test_all_jobs_returns_dict(self):
        job_id = _make_job_id("f")
        await self.store.create_job(job_id)
        all_jobs = await self.store.all_jobs()
        assert isinstance(all_jobs, dict)
        assert job_id in all_jobs


# ---------------------------------------------------------------------------
# Factory tests
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


class TestRecoverRunningJobs:
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
