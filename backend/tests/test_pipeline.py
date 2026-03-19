"""Tests for the pipeline orchestrator (Story 5.4)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _get_registry():
    from models.pipeline import build_default_registry
    return build_default_registry()


def _get_executor_module():
    import routers.analyze as mod
    return mod


# ---------------------------------------------------------------------------
# Test 1 — Stage execution order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_execution_order():
    """Stages must execute in ascending stage_number order across blocks."""
    registry = _get_registry()
    pipeline = registry.build_pipeline()
    all_stages = registry.all_stages()

    assert pipeline.total_stages == 28, f"Expected 28 stages, got {pipeline.total_stages}"

    numbers = [s.stage_number for s in all_stages]
    assert numbers == list(range(1, 29)), f"Stage numbers not sequential: {numbers}"

    # Block IDs must be non-decreasing
    block_ids = [s.block_id for s in all_stages]
    assert block_ids == sorted(block_ids), "Stages are not sorted by block_id"

    # Verify block stage counts
    from models.pipeline import BlockDefinition
    expected_counts = {1: 1, 2: 5, 3: 5, 4: 5, 5: 2, 6: 4, 7: 2, 8: 4}
    for block in pipeline.blocks:
        assert len(block.stages) == expected_counts[block.block_id], (
            f"Block {block.block_id} expected {expected_counts[block.block_id]} stages, "
            f"got {len(block.stages)}"
        )


# ---------------------------------------------------------------------------
# Test 2 — SSE event format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_event_format():
    """Pipeline events must contain required SSE fields with correct types."""
    import routers.analyze as mod

    # Monkeypatch TMP_BASE to avoid filesystem dependency
    from pathlib import Path
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_job_dir = Path(tmpdir) / "test-job-sse"
        fake_job_dir.mkdir()

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = Path(tmpdir)

        job_id = "test-job-sse"

        try:
            # Initialise the job state directly (bypass HTTP layer)
            mod._pipeline_jobs[job_id] = {
                "status": "pending",
                "result": None,
                "error": None,
                "cancel_flag": asyncio.Event(),
                "event_queue": asyncio.Queue(),
            }

            # Run the pipeline to completion
            await mod._run_pipeline(job_id)

            queue = mod._pipeline_jobs[job_id]["event_queue"]
            collected: List[Dict[str, Any]] = []
            while not queue.empty():
                item = queue.get_nowait()
                if item is not None:
                    collected.append(item)

            assert len(collected) > 0, "No SSE events emitted"

            required_keys = {"block", "stage", "stage_name", "status", "progress_pct", "summary"}

            # Separate stage events from the pipeline_completed meta-event (Story 10.4)
            stage_events = [e for e in collected if e.get("event") != "pipeline_completed"]
            completion_events = [e for e in collected if e.get("event") == "pipeline_completed"]

            for event in stage_events:
                missing = required_keys - event.keys()
                assert not missing, f"Event missing keys {missing}: {event}"

                assert isinstance(event["block"], int)
                assert isinstance(event["stage"], int)
                assert isinstance(event["stage_name"], str)
                assert event["status"] in ("running", "completed", "failed", "cancelled")
                assert isinstance(event["progress_pct"], float)
                assert isinstance(event["summary"], dict)

            # Verify pipeline_completed event is emitted exactly once
            assert len(completion_events) == 1, "Expected exactly one pipeline_completed event"
            assert completion_events[0]["status"] == "completed"
            assert completion_events[0]["progress_pct"] == 100.0

            # Each stage should emit at least 2 events (running + completed)
            statuses = [e["status"] for e in stage_events]
            assert "running" in statuses
            assert "completed" in statuses

        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)


# ---------------------------------------------------------------------------
# Test 3 — Cancellation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancellation():
    """Pipeline must stop executing after cancel_flag is set."""
    import routers.analyze as mod
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        job_id = "test-job-cancel"
        cancel_flag = asyncio.Event()
        queue: asyncio.Queue = asyncio.Queue()

        mod._pipeline_jobs[job_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "cancel_flag": cancel_flag,
            "event_queue": queue,
        }

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = Path(tmpdir)

        # Set cancel flag immediately before pipeline starts
        cancel_flag.set()

        try:
            await mod._run_pipeline(job_id)

            state = mod._pipeline_jobs[job_id]
            assert state["status"] == "cancelled", (
                f"Expected 'cancelled', got '{state['status']}'"
            )

            # Collect events
            events: List[Dict[str, Any]] = []
            while not queue.empty():
                item = queue.get_nowait()
                if item is not None:
                    events.append(item)

            statuses = [e["status"] for e in events]
            assert "cancelled" in statuses, f"No cancelled event found in {statuses}"

            # No completed or running events after cancellation at start
            running_events = [e for e in events if e["status"] in ("running", "completed")]
            assert len(running_events) == 0, (
                f"Unexpected running/completed events after immediate cancel: {running_events}"
            )

        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)


# ---------------------------------------------------------------------------
# Test 4 — Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_handling():
    """A stage that raises an exception must emit a 'failed' SSE event and stop the pipeline."""
    import routers.analyze as mod
    from pathlib import Path
    import tempfile
    from models.pipeline import StageRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        job_id = "test-job-error"
        queue: asyncio.Queue = asyncio.Queue()

        mod._pipeline_jobs[job_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "cancel_flag": asyncio.Event(),
            "event_queue": queue,
        }

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = Path(tmpdir)

        # Build a minimal registry with a single failing stage
        async def _failing_execute(ctx):
            raise RuntimeError("intentional test failure")

        error_registry = StageRegistry()
        error_registry.register_block(1, "Test Block")
        error_registry.register_stage(
            stage_number=1,
            name="Failing Stage",
            block_id=1,
            execute_fn=_failing_execute,
        )

        original_registry = mod.default_registry
        mod.default_registry = error_registry

        try:
            await mod._run_pipeline(job_id)

            state = mod._pipeline_jobs[job_id]
            assert state["status"] == "failed", f"Expected 'failed', got '{state['status']}'"
            assert state["error"] is not None
            assert "intentional test failure" in state["error"]

            # Collect events
            events: List[Dict[str, Any]] = []
            while not queue.empty():
                item = queue.get_nowait()
                if item is not None:
                    events.append(item)

            fail_events = [e for e in events if e["status"] == "failed"]
            assert len(fail_events) >= 1, "No 'failed' event found in SSE stream"

            fail_event = fail_events[0]
            assert "error" in fail_event["summary"], "Failed event missing 'error' in summary"

        finally:
            mod.TMP_BASE = original_tmp
            mod.default_registry = original_registry
            mod._pipeline_jobs.pop(job_id, None)


# ---------------------------------------------------------------------------
# Test 5 — StageRegistry add/remove
# ---------------------------------------------------------------------------


def test_registry_add_remove_stage():
    """StageRegistry must support dynamic registration and removal of stages."""
    from models.pipeline import StageRegistry

    registry = StageRegistry()
    registry.register_block(1, "Test Block")
    stage = registry.register_stage(99, "Custom Stage", block_id=1)

    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 1

    removed = registry.remove_stage(99)
    assert removed is True

    pipeline_after = registry.build_pipeline()
    assert pipeline_after.total_stages == 0

    # Remove non-existent stage returns False
    assert registry.remove_stage(999) is False
