"""Tests for the pipeline orchestrator v2 (Story 5.4, updated for v2-only in Epic 15).

Tests 1 (StageRegistry execution order) and 4 (StageRegistry add/remove) removed
in Story 15.9 — StageRegistry, BlockDefinition, and build_default_registry removed
from models/pipeline.py as v1 dead code.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest


def _get_executor_module():
    import routers.analyze as mod

    return mod


# ---------------------------------------------------------------------------
# Test 2 — SSE event format (v2 pipeline)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_event_format():
    """Pipeline v2 events must contain required SSE fields with correct types."""
    import os
    import tempfile
    from pathlib import Path

    import routers.analyze as mod

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_job_dir = Path(tmpdir) / "test-job-sse"
        fake_job_dir.mkdir()

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = Path(tmpdir)

        # Ensure STORAGE_MODE is set for get_storage()
        original_storage_mode = os.environ.get("STORAGE_MODE")
        os.environ["STORAGE_MODE"] = "local"
        from services.storage import _reset_storage

        _reset_storage()

        job_id = "test-job-sse"

        try:
            mod._pipeline_jobs[job_id] = {
                "status": "pending",
                "result": None,
                "error": None,
                "cancel_flag": asyncio.Event(),
                "event_log": [],
                "new_event": asyncio.Event(),
                "pipeline_done": False,
            }

            await mod._run_pipeline_v2(job_id)

            collected: list[dict[str, Any]] = [e for e in mod._pipeline_jobs[job_id]["event_log"] if e is not None]

            assert len(collected) > 0, "No SSE events emitted"

            # v2 events use "stage" and "stage_name" keys
            stage_events = [e for e in collected if e.get("event") != "pipeline_completed"]
            completion_events = [e for e in collected if e.get("event") == "pipeline_completed"]

            assert len(completion_events) == 1, "Expected exactly one pipeline_completed event"
            assert completion_events[0]["status"] == "completed"
            assert completion_events[0]["progress_pct"] == 1.0

            statuses = [e.get("status") for e in stage_events]
            assert "running" in statuses
            assert "completed" in statuses

        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)
            if original_storage_mode is not None:
                os.environ["STORAGE_MODE"] = original_storage_mode
            else:
                os.environ.pop("STORAGE_MODE", None)
            _reset_storage()


# ---------------------------------------------------------------------------
# Test 3 — Cancellation (v2 pipeline)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancellation():
    """Pipeline v2 must stop executing after cancel_flag is set."""
    import tempfile
    from pathlib import Path

    import routers.analyze as mod

    with tempfile.TemporaryDirectory() as tmpdir:
        job_id = "test-job-cancel"
        cancel_flag = asyncio.Event()

        mod._pipeline_jobs[job_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "cancel_flag": cancel_flag,
            "event_log": [],
            "new_event": asyncio.Event(),
            "pipeline_done": False,
        }

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = Path(tmpdir)

        original_storage_mode = os.environ.get("STORAGE_MODE")
        os.environ["STORAGE_MODE"] = "local"
        from services.storage import _reset_storage

        _reset_storage()

        cancel_flag.set()

        try:
            await mod._run_pipeline_v2(job_id)

            state = mod._pipeline_jobs[job_id]
            assert state["status"] == "cancelled", f"Expected 'cancelled', got '{state['status']}'"

            events: list[dict[str, Any]] = [e for e in state["event_log"] if e is not None]

            statuses = [e["status"] for e in events]
            assert "cancelled" in statuses, f"No cancelled event found in {statuses}"

        finally:
            mod.TMP_BASE = original_tmp
            mod._pipeline_jobs.pop(job_id, None)
            if original_storage_mode is not None:
                os.environ["STORAGE_MODE"] = original_storage_mode
            else:
                os.environ.pop("STORAGE_MODE", None)
            _reset_storage()
