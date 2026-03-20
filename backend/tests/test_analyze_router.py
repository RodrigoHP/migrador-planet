"""Tests for /api/analyze router endpoints — Story 10.5 + Story 10.14 (SSE replay buffer)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_mod():
    import routers.analyze as mod
    return mod


def _make_job_state(status: str = "completed") -> Dict[str, Any]:
    """Return a job state dict using the replay-buffer schema (Story 10.14)."""
    return {
        "status": status,
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_log": [],
        "new_event": asyncio.Event(),
        "pipeline_done": False,
        "created_at": 0,
    }


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
    mod._pipeline_jobs[job_id] = _make_job_state("completed")

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
    mod._pipeline_jobs[job_id] = _make_job_state("running")

    try:
        result = await mod.get_job_status(job_id)

        assert result["exists"] is True
        assert result["status"] == "running"
    finally:
        mod._pipeline_jobs.pop(job_id, None)


# ---------------------------------------------------------------------------
# Test: job state schema uses replay-buffer fields (AC #2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_job_state_has_replay_buffer_fields():
    """Job state dict contains event_log, new_event, and pipeline_done (AC #2)."""
    job_state = _make_job_state("pending")

    assert "event_log" in job_state, "event_log must exist in job state"
    assert isinstance(job_state["event_log"], list), "event_log must be a list"
    assert "new_event" in job_state, "new_event must exist in job state"
    assert isinstance(job_state["new_event"], asyncio.Event), "new_event must be asyncio.Event"
    assert "pipeline_done" in job_state, "pipeline_done must exist in job state"
    assert job_state["pipeline_done"] is False, "pipeline_done must start as False"
    # Old queue field must NOT be present (Story 10.14 removes it)
    assert "event_queue" not in job_state, "event_queue must be removed from job state"


# ---------------------------------------------------------------------------
# Test: _emit_event helper (AC #4)
# ---------------------------------------------------------------------------


def test_emit_event_appends_to_log_and_signals():
    """_emit_event appends to event_log and sets new_event (AC #4)."""
    mod = _get_mod()

    job_state = _make_job_state("running")
    event = {"stage": 1, "status": "running"}

    mod._emit_event(job_state, event)

    assert len(job_state["event_log"]) == 1
    assert job_state["event_log"][0] == event
    assert job_state["new_event"].is_set()
    assert job_state["pipeline_done"] is False


def test_emit_event_sentinel_sets_pipeline_done():
    """_emit_event with None appends sentinel and sets pipeline_done=True (AC #4)."""
    mod = _get_mod()

    job_state = _make_job_state("running")
    mod._emit_event(job_state, None)

    assert len(job_state["event_log"]) == 1
    assert job_state["event_log"][0] is None
    assert job_state["pipeline_done"] is True
    assert job_state["new_event"].is_set()


def test_emit_event_multiple_events_ordered():
    """_emit_event preserves insertion order in event_log."""
    mod = _get_mod()

    job_state = _make_job_state("running")
    events = [{"stage": i, "status": "running"} for i in range(5)]
    for ev in events:
        mod._emit_event(job_state, ev)

    assert job_state["event_log"] == events


# ---------------------------------------------------------------------------
# Test: _event_generator — replay and live events (AC #3, #5, #6)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_generator_replays_all_past_events():
    """Generator replays events already in log when client connects late (AC #3, #5)."""
    mod = _get_mod()

    job_id = "test-replay-past"
    job_state = _make_job_state("completed")
    # Pre-populate log as if pipeline already finished before SSE client connected
    events = [
        {"stage": 1, "status": "running"},
        {"stage": 1, "status": "completed"},
        {"stage": 2, "status": "running"},
        {"stage": 2, "status": "completed"},
        {"event": "pipeline_completed", "status": "completed"},
    ]
    for ev in events:
        job_state["event_log"].append(ev)
    job_state["event_log"].append(None)  # sentinel
    job_state["pipeline_done"] = True
    job_state["new_event"].set()

    mod._pipeline_jobs[job_id] = job_state

    try:
        collected: List[str] = []
        async for data in mod._event_generator(job_id):
            collected.append(data)

        assert len(collected) == len(events), (
            f"Expected {len(events)} events, got {len(collected)}"
        )
        for i, ev in enumerate(events):
            assert json.loads(collected[i]) == ev, (
                f"Event {i} mismatch: expected {ev}, got {collected[i]}"
            )
    finally:
        mod._pipeline_jobs.pop(job_id, None)


@pytest.mark.asyncio
async def test_event_generator_returns_error_for_unknown_job():
    """Generator yields error JSON when job_id is not found."""
    mod = _get_mod()

    job_id = "test-unknown-job-gen"
    mod._pipeline_jobs.pop(job_id, None)

    collected: List[str] = []
    async for data in mod._event_generator(job_id):
        collected.append(data)

    assert len(collected) == 1
    payload = json.loads(collected[0])
    assert "error" in payload


@pytest.mark.asyncio
async def test_event_generator_live_event_received_after_wait():
    """Generator waits for new_event signal and picks up event added while waiting (AC #3, #6)."""
    mod = _get_mod()

    job_id = "test-replay-live"
    job_state = _make_job_state("running")
    mod._pipeline_jobs[job_id] = job_state

    async def _push_events():
        """Emit two events then the sentinel after a short delay."""
        await asyncio.sleep(0.02)
        mod._emit_event(job_state, {"stage": 1, "status": "running"})
        await asyncio.sleep(0.02)
        mod._emit_event(job_state, {"stage": 1, "status": "completed"})
        await asyncio.sleep(0.02)
        mod._emit_event(job_state, None)  # sentinel

    try:
        producer = asyncio.create_task(_push_events())
        collected: List[str] = []
        async for data in mod._event_generator(job_id):
            collected.append(data)

        await producer
        assert len(collected) == 2
        assert json.loads(collected[0]) == {"stage": 1, "status": "running"}
        assert json.loads(collected[1]) == {"stage": 1, "status": "completed"}
    finally:
        mod._pipeline_jobs.pop(job_id, None)


@pytest.mark.asyncio
async def test_event_generator_race_condition_no_event_lost():
    """Race condition: event added after check but before wait is not lost (AC #6).

    Simulates: generator checks idx < len(log) → False, then an event is appended,
    then clear() is called. The re-check after clear() must catch the new event.
    """
    mod = _get_mod()

    job_id = "test-race-condition"
    job_state = _make_job_state("running")
    mod._pipeline_jobs[job_id] = job_state

    # Emit one real event plus sentinel with minimal delay to create a race window
    async def _push():
        await asyncio.sleep(0.005)
        mod._emit_event(job_state, {"stage": 1, "status": "completed"})
        mod._emit_event(job_state, None)

    try:
        task = asyncio.create_task(_push())
        collected: List[str] = []
        async for data in mod._event_generator(job_id):
            collected.append(data)
        await task

        # Must receive exactly the one real event (no loss, no hang)
        assert len(collected) == 1
        assert json.loads(collected[0]) == {"stage": 1, "status": "completed"}
    finally:
        mod._pipeline_jobs.pop(job_id, None)


@pytest.mark.asyncio
async def test_event_generator_late_client_gets_full_history_plus_completion():
    """Late-connecting client gets full history including pipeline_completed (AC #5)."""
    mod = _get_mod()

    job_id = "test-late-client"
    job_state = _make_job_state("completed")
    stage_events = [
        {"stage": i, "status": "completed"} for i in range(1, 6)
    ]
    completion_event = {"event": "pipeline_completed", "status": "completed"}

    for ev in stage_events + [completion_event]:
        job_state["event_log"].append(ev)
    job_state["event_log"].append(None)  # sentinel
    job_state["pipeline_done"] = True
    job_state["new_event"].set()

    mod._pipeline_jobs[job_id] = job_state

    try:
        collected: List[str] = []
        async for data in mod._event_generator(job_id):
            collected.append(data)

        all_expected = stage_events + [completion_event]
        assert len(collected) == len(all_expected)
        # Last received event must be the pipeline_completed marker
        assert json.loads(collected[-1]) == completion_event
    finally:
        mod._pipeline_jobs.pop(job_id, None)
