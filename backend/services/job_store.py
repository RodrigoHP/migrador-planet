"""Job state persistence — in-memory (dev) or Redis (production).

Story 15.4: Migrate _pipeline_jobs dict to a pluggable store so job state
survives server restarts in production (Railway Redis addon).

Usage:
    from services.job_store import get_job_store
    store = get_job_store()

Configuration:
    REDIS_URL env var — if set, uses Redis; otherwise falls back to in-memory.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# TTL for completed/failed/cancelled jobs (seconds)
_JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", "3600"))


# ---------------------------------------------------------------------------
# In-memory store (dev / fallback)
# ---------------------------------------------------------------------------

class InMemoryJobStore:
    """Dict-backed job store — same as before, no persistence."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, job_id: str) -> Dict[str, Any]:
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

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def delete_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    def all_jobs(self) -> Dict[str, Dict[str, Any]]:
        return self._jobs

    def evict_expired(self) -> int:
        """Remove jobs older than TTL. Returns count removed."""
        now = time.time()
        expired = [
            jid for jid, state in self._jobs.items()
            if state.get("status") in ("completed", "failed", "cancelled")
            and now - state.get("created_at", now) > _JOB_TTL_SECONDS
        ]
        for jid in expired:
            del self._jobs[jid]
        return len(expired)


# ---------------------------------------------------------------------------
# Redis store (production)
# ---------------------------------------------------------------------------

class RedisJobStore:
    """Redis-backed job store for production persistence.

    Stores serialisable job state in Redis hashes.  Non-serialisable fields
    (cancel_flag, new_event) are kept in a local dict since they are
    process-local asyncio primitives.
    """

    # Fields that live only in-process (asyncio objects)
    _LOCAL_FIELDS = {"cancel_flag", "new_event"}

    def __init__(self, redis_url: str) -> None:
        import redis as redis_lib
        self._redis = redis_lib.from_url(redis_url, decode_responses=True)
        self._local: Dict[str, Dict[str, Any]] = {}
        logger.info("RedisJobStore connected to %s", redis_url.split("@")[-1])

    def _key(self, job_id: str) -> str:
        return f"job:{job_id}"

    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """Serialize job state (excluding local-only fields) to JSON."""
        serialisable = {
            k: v for k, v in state.items()
            if k not in self._LOCAL_FIELDS
        }
        return json.dumps(serialisable, default=str)

    def _deserialize_state(self, data: str, job_id: str) -> Dict[str, Any]:
        """Deserialize job state and attach local asyncio objects."""
        state = json.loads(data)
        local = self._local.get(job_id, {})
        state["cancel_flag"] = local.get("cancel_flag", asyncio.Event())
        state["new_event"] = local.get("new_event", asyncio.Event())
        return state

    def create_job(self, job_id: str) -> Dict[str, Any]:
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
        self._redis.setex(
            self._key(job_id),
            _JOB_TTL_SECONDS,
            self._serialize_state(job),
        )
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        data = self._redis.get(self._key(job_id))
        if data is None:
            return None
        return self._deserialize_state(data, job_id)

    def save_job(self, job_id: str, state: Dict[str, Any]) -> None:
        """Persist current state to Redis."""
        self._redis.setex(
            self._key(job_id),
            _JOB_TTL_SECONDS,
            self._serialize_state(state),
        )

    def delete_job(self, job_id: str) -> None:
        self._redis.delete(self._key(job_id))
        self._local.pop(job_id, None)

    def all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Return all jobs — for admin/debug only."""
        result = {}
        for key in self._redis.scan_iter("job:*"):
            job_id = key.removeprefix("job:")
            data = self._redis.get(key)
            if data:
                result[job_id] = self._deserialize_state(data, job_id)
        return result

    def evict_expired(self) -> int:
        """Redis TTL handles expiration automatically."""
        return 0


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_store_instance: Optional[InMemoryJobStore | RedisJobStore] = None


def get_job_store() -> InMemoryJobStore | RedisJobStore:
    """Return the singleton job store (Redis if REDIS_URL set, else in-memory)."""
    global _store_instance
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


def recover_running_jobs() -> int:
    """Mark any jobs with status 'running' as 'failed' on startup.

    Called during FastAPI lifespan startup to ensure consistency after a
    server restart or crash (Story 15.4 — AC: recover_running_jobs).

    Returns the count of jobs that were marked as failed.
    """
    store = get_job_store()
    recovered = 0
    try:
        all_jobs = store.all_jobs()
        for job_id, state in all_jobs.items():
            if state.get("status") == "running":
                state["status"] = "failed"
                state["error"] = "Server restarted while job was running"
                if hasattr(store, "save_job"):
                    store.save_job(job_id, state)
                recovered += 1
                logger.info("Recovered job %s: running → failed after restart", job_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("recover_running_jobs failed: %s", exc)
    return recovered


def _reset_job_store() -> None:
    """Reset singleton — for tests only."""
    global _store_instance
    _store_instance = None
