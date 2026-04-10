"""Job state persistence — in-memory (dev) or Redis (production).

Story 15.4: Migrate _pipeline_jobs dict to a pluggable store so job state
survives server restarts in production (Railway Redis addon).

Story 40.8: Redis as SSOT with async client (redis.asyncio) and write-behind
to Supabase. In-memory dict reduced to read cache. Feature flag for dual-write
during transition.

Usage:
    from services.job_store import get_job_store
    store = get_job_store()

Configuration:
    REDIS_URL env var — if set, uses Redis; otherwise falls back to in-memory.
    FEATURE_DUAL_WRITE — if "true", enables write-behind to Supabase.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# TTL for completed/failed/cancelled jobs (seconds)
_JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", "3600"))

# Terminal statuses that must not be overwritten (DB-017 mitigation)
_TERMINAL_STATUSES = frozenset({"cancelled", "failed"})

# Feature flag: dual-write to both Redis and Supabase during transition
FEATURE_DUAL_WRITE = os.environ.get("FEATURE_DUAL_WRITE", "false").lower() == "true"


# ---------------------------------------------------------------------------
# In-memory store (dev / fallback)
# ---------------------------------------------------------------------------


class InMemoryJobStore:
    """Dict-backed job store — same as before, no persistence."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    async def create_job(self, job_id: str) -> dict[str, Any]:
        job = {
            "status": "pending",
            "result": None,
            "error": None,
            "cancel_flag": asyncio.Event(),
            "event_log": [],
            "new_event": asyncio.Event(),
            "pipeline_done": False,
            "created_at": time.time(),
        }
        self._jobs[job_id] = job
        return job

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)

    async def save_job(self, job_id: str, state: dict[str, Any]) -> None:
        """Persist current state. Guards against overwriting terminal statuses."""
        existing = self._jobs.get(job_id)
        if existing and existing.get("status") in _TERMINAL_STATUSES:
            incoming = state.get("status", "")
            if incoming not in _TERMINAL_STATUSES and incoming != existing.get("status"):
                logger.warning(
                    "Blocked status overwrite for job %s: %s -> %s",
                    job_id,
                    existing["status"],
                    incoming,
                )
                return
        self._jobs[job_id] = state

    async def delete_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    async def all_jobs(self) -> dict[str, dict[str, Any]]:
        return self._jobs

    async def evict_expired(self) -> int:
        """Remove jobs older than TTL. Returns count removed."""
        now = time.time()
        expired = [
            jid
            for jid, state in self._jobs.items()
            if state.get("status") in ("completed", "failed", "cancelled")
            and now - state.get("created_at", now) > _JOB_TTL_SECONDS
        ]
        for jid in expired:
            del self._jobs[jid]
        return len(expired)


# ---------------------------------------------------------------------------
# Redis store (production) — async client (Story 40.8: REDIS-004)
# ---------------------------------------------------------------------------


class RedisJobStore:
    """Redis-backed job store for production persistence.

    Story 40.8: Uses redis.asyncio for non-blocking operations.
    Redis is the SSOT (DB-008). Write-behind to Supabase is optional
    via FEATURE_DUAL_WRITE flag.

    Stores serialisable job state in Redis hashes.  Non-serialisable fields
    (cancel_flag, new_event) are kept in a local dict since they are
    process-local asyncio primitives.
    """

    # Fields that live only in-process (asyncio objects)
    _LOCAL_FIELDS = {"cancel_flag", "new_event", "confirmation_event"}

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._local: dict[str, dict[str, Any]] = {}
        # In-memory read cache for fast access during pipeline execution
        self._cache: dict[str, dict[str, Any]] = {}
        logger.info("RedisJobStore connected (async) to %s", redis_url.split("@")[-1])

    # Application-scoped key prefix to avoid collisions in shared Redis (REDIS-001)
    _KEY_PREFIX = "migrador:"

    def _key(self, job_id: str) -> str:
        return f"{self._KEY_PREFIX}job:{job_id}"

    def _serialize_state(self, state: dict[str, Any]) -> str:
        """Serialize job state (excluding local-only fields) to JSON."""
        serialisable = {k: v for k, v in state.items() if k not in self._LOCAL_FIELDS}
        return json.dumps(serialisable, default=str)

    def _deserialize_state(self, data: str, job_id: str) -> dict[str, Any]:
        """Deserialize job state and attach local asyncio objects."""
        state = json.loads(data)
        local = self._local.get(job_id, {})
        state["cancel_flag"] = local.get("cancel_flag", asyncio.Event())
        state["new_event"] = local.get("new_event", asyncio.Event())
        return state

    async def create_job(self, job_id: str) -> dict[str, Any]:
        cancel_flag = asyncio.Event()
        new_event = asyncio.Event()
        self._local[job_id] = {
            "cancel_flag": cancel_flag,
            "new_event": new_event,
        }
        job = {
            "status": "pending",
            "result": None,
            "error": None,
            "cancel_flag": cancel_flag,
            "event_log": [],
            "new_event": new_event,
            "pipeline_done": False,
            "created_at": time.time(),
        }
        await self._redis.setex(
            self._key(job_id),
            _JOB_TTL_SECONDS,
            self._serialize_state(job),
        )
        # Update read cache
        self._cache[job_id] = job
        return job

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        # Check read cache first
        if job_id in self._cache:
            return self._cache[job_id]
        data = await self._redis.get(self._key(job_id))
        if data is None:
            return None
        state = self._deserialize_state(data, job_id)
        self._cache[job_id] = state
        return state

    async def save_job(self, job_id: str, state: dict[str, Any]) -> None:
        """Persist current state to Redis.

        Guards against overwriting terminal statuses (DB-017).
        """
        # Check current status in Redis before overwriting
        current_data = await self._redis.get(self._key(job_id))
        if current_data is not None:
            current_state = json.loads(current_data)
            current_status = current_state.get("status")
            incoming_status = state.get("status", "")
            if (
                current_status in _TERMINAL_STATUSES
                and incoming_status not in _TERMINAL_STATUSES
                and incoming_status != current_status
            ):
                logger.warning(
                    "Blocked status overwrite for job %s: %s -> %s (DB-017 guard)",
                    job_id,
                    current_status,
                    incoming_status,
                )
                return

        await self._redis.setex(
            self._key(job_id),
            _JOB_TTL_SECONDS,
            self._serialize_state(state),
        )
        # Update read cache
        self._cache[job_id] = state

        # Write-behind to Supabase if dual-write enabled
        if FEATURE_DUAL_WRITE:
            asyncio.create_task(self._write_behind_supabase(job_id, state))

    async def _write_behind_supabase(self, job_id: str, state: dict[str, Any]) -> None:
        """Async write-behind: persist job state to Supabase (non-blocking).

        This is fire-and-forget — failures are logged but do not affect Redis SSOT.
        """
        try:
            from services.storage import get_storage
            from services.storage.supabase_gateway import SupabaseStorageGateway

            storage = get_storage()
            if isinstance(storage, SupabaseStorageGateway):
                status = state.get("status", "")
                result = state.get("result")
                if status == "completed" and result:
                    await storage.save_result(job_id, result)
                    logger.debug("Write-behind: persisted result for job %s to Supabase", job_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Write-behind to Supabase failed for job %s: %s", job_id, exc)

    async def delete_job(self, job_id: str) -> None:
        await self._redis.delete(self._key(job_id))
        self._local.pop(job_id, None)
        self._cache.pop(job_id, None)

    async def all_jobs(self) -> dict[str, dict[str, Any]]:
        """Return all jobs — for admin/debug only."""
        result = {}
        prefix = f"{self._KEY_PREFIX}job:"
        async for key in self._redis.scan_iter(f"{prefix}*"):
            job_id = key.removeprefix(prefix)
            data = await self._redis.get(key)
            if data:
                result[job_id] = self._deserialize_state(data, job_id)
        return result

    async def evict_expired(self) -> int:
        """Redis TTL handles expiration automatically."""
        return 0

    async def close(self) -> None:
        """Close the async Redis connection pool."""
        await self._redis.aclose()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_store_instance: InMemoryJobStore | RedisJobStore | None = None


def get_job_store() -> InMemoryJobStore | RedisJobStore:
    """Return the singleton job store (Redis if REDIS_URL set, else in-memory)."""
    global _store_instance  # noqa: PLW0603
    if _store_instance is None:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                _store_instance = RedisJobStore(redis_url)
            except Exception as exc:
                logger.warning("Redis unavailable (%s), falling back to in-memory", exc)
                _store_instance = InMemoryJobStore()
        else:
            _store_instance = InMemoryJobStore()
    return _store_instance


async def recover_running_jobs() -> int:
    """Mark any jobs with status 'running' as 'failed' on startup.

    Called during FastAPI lifespan startup to ensure consistency after a
    server restart or crash (Story 15.4 — AC: recover_running_jobs).

    Story 40.8: Now async to support async Redis client.

    Returns the count of jobs that were marked as failed.
    """
    store = get_job_store()
    recovered = 0
    try:
        all_jobs = await store.all_jobs()
        for job_id, state in all_jobs.items():
            if state.get("status") == "running":
                state["status"] = "failed"
                state["error"] = "Server restarted while job was running"
                await store.save_job(job_id, state)
                recovered += 1
                logger.info("Recovered job %s: running -> failed after restart", job_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("recover_running_jobs failed: %s", exc)
    return recovered


def _reset_job_store() -> None:
    """Reset singleton — for tests only."""
    global _store_instance  # noqa: PLW0603
    _store_instance = None
