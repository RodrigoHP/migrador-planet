"""Tests for /api/analyze router endpoints — Story 10.5."""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_mod():
    import routers.analyze as mod
    return mod


# ---------------------------------------------------------------------------
# Test: GET /api/analyze/{job_id}/status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_returns_exists_false_for_unknown_job():
    """GET /api/analyze/inexistente/status returns { exists: false, status: null }."""
    mod = _get_mod()

    # Ensure the job is NOT in the store
    mod._pipeline_jobs.pop("inexistente", None)

    result = await mod.get_job_status("inexistente")

    assert result["job_id"] == "inexistente"
    assert result["exists"] is False
    assert result["status"] is None


@pytest.mark.asyncio
async def test_status_returns_exists_true_for_known_job():
    """GET /api/analyze/{job_id}/status returns { exists: true } when job is known."""
    mod = _get_mod()

    job_id = "test-status-known"
    mod._pipeline_jobs[job_id] = {
        "status": "completed",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_queue": asyncio.Queue(),
        "created_at": 0,
    }

    try:
        result = await mod.get_job_status(job_id)

        assert result["job_id"] == job_id
        assert result["exists"] is True
        assert result["status"] == "completed"
    finally:
        mod._pipeline_jobs.pop(job_id, None)


@pytest.mark.asyncio
async def test_status_reflects_current_job_status():
    """Status endpoint reflects the current job status (running, pending, etc.)."""
    mod = _get_mod()

    job_id = "test-status-running"
    mod._pipeline_jobs[job_id] = {
        "status": "running",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_queue": asyncio.Queue(),
        "created_at": 0,
    }

    try:
        result = await mod.get_job_status(job_id)

        assert result["exists"] is True
        assert result["status"] == "running"
    finally:
        mod._pipeline_jobs.pop(job_id, None)
