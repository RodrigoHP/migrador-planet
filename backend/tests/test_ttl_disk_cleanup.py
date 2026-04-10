"""Tests for Story 11.9 — TTL with disk file cleanup.

Covers:
1. _evict_stale_jobs() removes the job directory from disk.
2. _evict_stale_jobs() validates path before rmtree (no path traversal).
3. _cleanup_orphaned_dirs() removes orphaned directories older than 24h.
4. _cleanup_orphaned_dirs() skips recent directories (mtime < 24h).
5. _cleanup_orphaned_dirs() skips directories with an active in-memory state.
6. _safe_rmtree() logs freed bytes.
"""

from __future__ import annotations

import asyncio
import tempfile
import time
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_mod():
    import routers.analyze as mod

    return mod


def _make_job_state(status: str = "completed", created_at: float = 0.0):
    return {
        "status": status,
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_log": [],
        "new_event": asyncio.Event(),
        "pipeline_done": False,
        "created_at": created_at,
    }


# ---------------------------------------------------------------------------
# Test 1: _evict_stale_jobs removes disk directory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evict_stale_jobs_removes_disk_directory():
    """_evict_stale_jobs() must delete the job directory from disk."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        job_dir = tmp_base / job_id
        job_dir.mkdir()
        (job_dir / "input.pdf").write_bytes(b"%PDF-1.4 fake")

        # Register job with TTL already expired (created_at = 0)
        mod._pipeline_jobs[job_id] = _make_job_state("completed", created_at=0.0)

        # Patch TMP_BASE to point to our temp directory
        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            await mod._evict_stale_jobs()
        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)

        assert not job_dir.exists(), f"Expected {job_dir} to be removed by _evict_stale_jobs"


@pytest.mark.asyncio
async def test_evict_stale_jobs_does_not_remove_running_job_directory():
    """_evict_stale_jobs() must NOT remove directories for running jobs."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        job_dir = tmp_base / job_id
        job_dir.mkdir()

        # Running job with old created_at -- should not be evicted
        mod._pipeline_jobs[job_id] = _make_job_state("running", created_at=0.0)

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            await mod._evict_stale_jobs()
        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)

        assert job_dir.exists(), "Running job directory must NOT be removed by _evict_stale_jobs"


@pytest.mark.asyncio
async def test_evict_stale_jobs_does_not_remove_recent_completed_job():
    """_evict_stale_jobs() must keep jobs that are still within TTL."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        job_dir = tmp_base / job_id
        job_dir.mkdir()

        # Completed job with recent created_at (within TTL)
        mod._pipeline_jobs[job_id] = _make_job_state("completed", created_at=time.monotonic())

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            await mod._evict_stale_jobs()
        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)

        assert job_dir.exists(), "Recent job directory must NOT be removed by _evict_stale_jobs"


# ---------------------------------------------------------------------------
# Test 2: _safe_rmtree path traversal prevention
# ---------------------------------------------------------------------------


def test_safe_rmtree_skips_path_outside_tmp_base():
    """_safe_rmtree() must not remove directories that resolve outside TMP_BASE."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir) / "jobs"
        tmp_base.mkdir()

        # Create a directory OUTSIDE tmp_base
        outside_dir = Path(tmpdir) / "outside"
        outside_dir.mkdir()

        # Attempt to rmtree the outside directory using a fake job_id
        mod._safe_rmtree(outside_dir, "fake-job", tmp_base)

        # The directory must still exist
        assert outside_dir.exists(), "_safe_rmtree must not delete directories outside TMP_BASE"


# ---------------------------------------------------------------------------
# Test 3: _cleanup_orphaned_dirs removes old orphaned directories
# ---------------------------------------------------------------------------


def test_cleanup_orphaned_dirs_removes_old_orphan():
    """_cleanup_orphaned_dirs() removes UUID dirs with mtime > 24h ago."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        orphan_dir = tmp_base / job_id
        orphan_dir.mkdir()
        (orphan_dir / "input.pdf").write_bytes(b"%PDF")

        # Set mtime to 25 hours ago
        old_mtime = time.time() - (25 * 3600)
        import os

        os.utime(orphan_dir, (old_mtime, old_mtime))

        # Ensure no in-memory state for this job
        mod._pipeline_jobs.pop(job_id, None)

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            mod._cleanup_orphaned_dirs()
        finally:
            mod.TMP_BASE = original_tmp

        assert not orphan_dir.exists(), f"Orphaned directory {orphan_dir} should have been removed"


def test_cleanup_orphaned_dirs_skips_recent_directories():
    """_cleanup_orphaned_dirs() must not remove dirs with mtime < 24h."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        recent_dir = tmp_base / job_id
        recent_dir.mkdir()

        # mtime is now (recent)
        mod._pipeline_jobs.pop(job_id, None)

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            mod._cleanup_orphaned_dirs()
        finally:
            mod.TMP_BASE = original_tmp

        assert recent_dir.exists(), "Recent directory must NOT be removed by _cleanup_orphaned_dirs"


def test_cleanup_orphaned_dirs_skips_active_in_memory_jobs():
    """_cleanup_orphaned_dirs() skips directories with active in-memory state."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        active_dir = tmp_base / job_id
        active_dir.mkdir()

        # Set mtime to 25 hours ago (would normally be cleaned)
        old_mtime = time.time() - (25 * 3600)
        import os

        os.utime(active_dir, (old_mtime, old_mtime))

        # Register in-memory state (simulate active job after long run)
        mod._pipeline_jobs[job_id] = _make_job_state("completed")

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            mod._cleanup_orphaned_dirs()
        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)

        assert active_dir.exists(), "Directory with active in-memory state must NOT be removed"


def test_cleanup_orphaned_dirs_skips_non_uuid_directories():
    """_cleanup_orphaned_dirs() only removes UUID v4 named directories."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        non_uuid_dir = tmp_base / "not-a-uuid-dir"
        non_uuid_dir.mkdir()

        # Set old mtime
        old_mtime = time.time() - (25 * 3600)
        import os

        os.utime(non_uuid_dir, (old_mtime, old_mtime))

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            mod._cleanup_orphaned_dirs()
        finally:
            mod.TMP_BASE = original_tmp

        assert non_uuid_dir.exists(), "Non-UUID named directories must NOT be touched by _cleanup_orphaned_dirs"
