"""Tests for pipeline_orchestrator_v2 — Story 13.3.

Covers:
- Orchestrator v2 executes stub stages and emits SSE events
- handle_service_failure with retry, fallback, abort
- Feature flag v1 vs v2
- Timeout defaults to fallback
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import fitz
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_orchestrator():
    import services.pipeline_orchestrator_v2 as mod
    return mod


def _make_job_state(job_id: str = "test-job") -> Dict[str, Any]:
    """Create a minimal job state dict matching _pipeline_jobs structure."""
    return {
        "job_id": job_id,
        "status": "running",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_log": [],
        "new_event": asyncio.Event(),
        "pipeline_done": False,
        "created_at": 0,
    }


def _create_test_pdf(path: str, num_pages: int = 2) -> str:
    """Create a simple PDF for orchestrator tests."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 120), f"Test content page {i+1}", fontsize=12)
        page.insert_text((50, 200), "Some body text for the page here", fontsize=10)
    doc.save(path)
    doc.close()
    return path


class EventCollector:
    """Async callback that collects emitted SSE events."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    async def __call__(self, event: Dict[str, Any]) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# Test: Orchestrator v2 runs all 5 stub stages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_pipeline_v2_executes_all_stages(tmp_path):
    """run_pipeline_v2 executes 5 stages sequentially and returns result."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()
    storage = MagicMock()
    storage.cleanup_local = AsyncMock()

    pdf_path = _create_test_pdf(str(tmp_path / "input.pdf"))
    pdf_docs = [
        {"id": "0", "path": pdf_path, "name": "input.pdf"},
    ]

    result = await mod.run_pipeline_v2(
        pdf_documents=pdf_docs,
        xsd_path="",
        storage=storage,
        job=job,
        emit_progress=collector,
    )

    # Should have emitted events for all 5 stages
    stage_numbers = {e["stage"] for e in collector.events if e.get("stage")}
    assert {1, 2, 3, 4, 5} <= stage_numbers

    # Should have start event
    start_events = [e for e in collector.events if e.get("status") == "started"]
    assert len(start_events) >= 1

    # Should have completion events for all 5 stages
    completed_events = [
        e for e in collector.events
        if e.get("status") == "completed" and e.get("stage") in (1, 2, 3, 4, 5)
    ]
    assert len(completed_events) >= 5

    # Result should contain stage results
    assert "stage_5" in result
    assert "template_draft" in result


@pytest.mark.asyncio
async def test_run_pipeline_v2_emits_sub_progress(tmp_path):
    """run_pipeline_v2 emits sub-progress events with sub_step and sub_progress_pct."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()
    storage = MagicMock()
    storage.cleanup_local = AsyncMock()

    pdf_path = _create_test_pdf(str(tmp_path / "input.pdf"))

    await mod.run_pipeline_v2(
        pdf_documents=[{"id": "0", "path": pdf_path, "name": "input.pdf"}],
        xsd_path="",
        storage=storage,
        job=job,
        emit_progress=collector,
    )

    # Find running events with sub_step
    sub_events = [
        e for e in collector.events
        if e.get("status") == "running" and e.get("sub_step")
    ]
    assert len(sub_events) > 0

    # Verify sub_progress_pct is present
    for evt in sub_events:
        assert "sub_progress_pct" in evt
        assert 0.0 <= evt["sub_progress_pct"] <= 1.0


@pytest.mark.asyncio
async def test_run_pipeline_v2_progress_pct_range(tmp_path):
    """Overall progress_pct goes from 0 to 1.0 across all events."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()
    storage = MagicMock()
    storage.cleanup_local = AsyncMock()

    pdf_path = _create_test_pdf(str(tmp_path / "input.pdf"))

    await mod.run_pipeline_v2(
        pdf_documents=[{"id": "0", "path": pdf_path, "name": "input.pdf"}],
        xsd_path="",
        storage=storage,
        job=job,
        emit_progress=collector,
    )

    pcts = [e["progress_pct"] for e in collector.events if "progress_pct" in e]
    assert min(pcts) == 0.0
    assert max(pcts) == 1.0


@pytest.mark.asyncio
async def test_run_pipeline_v2_cancellation():
    """Pipeline respects cancel_flag and stops early."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()
    job["cancel_flag"].set()  # Pre-cancel
    storage = MagicMock()
    storage.cleanup_local = AsyncMock()

    result = await mod.run_pipeline_v2(
        pdf_documents=[{"id": "0", "path": "/tmp/test/input.pdf", "name": "input.pdf"}],
        xsd_path="",
        storage=storage,
        job=job,
        emit_progress=collector,
    )

    # Should have a cancelled event
    cancel_events = [e for e in collector.events if e.get("status") == "cancelled"]
    assert len(cancel_events) >= 1

    # Should not have completed all stages
    completed_stages = {
        e["stage"] for e in collector.events
        if e.get("status") == "completed" and e["stage"] in (1, 2, 3, 4, 5)
    }
    assert len(completed_stages) < 5


@pytest.mark.asyncio
async def test_run_pipeline_v2_sse_format(tmp_path):
    """Events match the v2 SSE format from Section 9."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()
    storage = MagicMock()
    storage.cleanup_local = AsyncMock()

    pdf_path = _create_test_pdf(str(tmp_path / "input.pdf"))

    await mod.run_pipeline_v2(
        pdf_documents=[{"id": "0", "path": pdf_path, "name": "input.pdf"}],
        xsd_path="",
        storage=storage,
        job=job,
        emit_progress=collector,
    )

    # Pick a running event from stage 1
    running = [e for e in collector.events if e.get("stage") == 1 and e.get("status") == "running"]
    assert len(running) > 0
    sample = running[0]

    # Verify required fields
    assert "stage" in sample
    assert "stage_name" in sample
    assert "status" in sample
    assert "progress_pct" in sample
    assert "sub_step" in sample
    assert "sub_progress_pct" in sample
    assert "summary" in sample
    assert sample["stage_name"] == "Layout Clustering"


# ---------------------------------------------------------------------------
# Test: handle_service_failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_service_failure_retry():
    """handle_service_failure returns 'retry' when operator chooses retry."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()

    context = {"_current_stage": 1}

    # Simulate operator response in background
    async def respond_retry():
        await asyncio.sleep(0.05)
        job["failure_response"] = {"action": "retry", "by": "human"}
        job["confirmation_event"].set()

    asyncio.create_task(respond_retry())

    result = await mod.handle_service_failure(
        context=context,
        service_name="Test Service",
        stage_name="Layout Clustering",
        error=Exception("test error"),
        fallback_description="Continue without service",
        impact_description="Quality reduced",
        job=job,
        emit_progress=collector,
        timeout=5,
    )

    assert result == "retry"

    # Should have emitted a service_failure event
    failure_events = [e for e in collector.events if e.get("status") == "service_failure"]
    assert len(failure_events) == 1
    assert "checkpoint" in failure_events[0]


@pytest.mark.asyncio
async def test_handle_service_failure_fallback():
    """handle_service_failure returns 'fallback' when operator chooses fallback."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()

    context = {"_current_stage": 2}

    async def respond_fallback():
        await asyncio.sleep(0.05)
        job["failure_response"] = {"action": "fallback", "by": "human"}
        job["confirmation_event"].set()

    asyncio.create_task(respond_fallback())

    result = await mod.handle_service_failure(
        context=context,
        service_name="Test Service",
        stage_name="Deep Extraction",
        error=Exception("connection error"),
        fallback_description="Skip extraction",
        impact_description="Missing data",
        job=job,
        emit_progress=collector,
        timeout=5,
    )

    assert result == "fallback"


@pytest.mark.asyncio
async def test_handle_service_failure_abort():
    """handle_service_failure raises PipelineAbortError when operator chooses abort."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()

    context = {"_current_stage": 3}

    async def respond_abort():
        await asyncio.sleep(0.05)
        job["failure_response"] = {"action": "abort", "by": "human"}
        job["confirmation_event"].set()

    asyncio.create_task(respond_abort())

    with pytest.raises(mod.PipelineAbortError):
        await mod.handle_service_failure(
            context=context,
            service_name="Test Service",
            stage_name="Structural Analysis",
            error=Exception("api error"),
            fallback_description="Skip analysis",
            impact_description="Reduced quality",
            job=job,
            emit_progress=collector,
            timeout=5,
        )


@pytest.mark.asyncio
async def test_handle_service_failure_timeout_defaults_to_fallback():
    """When timeout expires without operator response, default to fallback."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()

    context = {"_current_stage": 4}

    # No response will come — timeout should trigger
    result = await mod.handle_service_failure(
        context=context,
        service_name="Test Service",
        stage_name="Field Mapping",
        error=Exception("timeout error"),
        fallback_description="Use heuristics",
        impact_description="Lower accuracy",
        job=job,
        emit_progress=collector,
        timeout=1,  # 1 second timeout for test speed
    )

    assert result == "fallback"


@pytest.mark.asyncio
async def test_handle_service_failure_checkpoint_format():
    """The service_failure SSE event contains proper checkpoint structure."""
    mod = _get_orchestrator()
    collector = EventCollector()
    job = _make_job_state()

    context = {"_current_stage": 1}

    async def respond():
        await asyncio.sleep(0.05)
        job["failure_response"] = {"action": "fallback", "by": "human"}
        job["confirmation_event"].set()

    asyncio.create_task(respond())

    await mod.handle_service_failure(
        context=context,
        service_name="LLM Vision",
        stage_name="Layout Clustering",
        error=Exception("API rate limit"),
        fallback_description="Continue without LLM",
        impact_description="Lower clustering accuracy",
        job=job,
        emit_progress=collector,
        timeout=5,
    )

    failure_events = [e for e in collector.events if e.get("status") == "service_failure"]
    assert len(failure_events) == 1

    checkpoint = failure_events[0]["checkpoint"]
    assert checkpoint["type"] == "service_failure"
    assert checkpoint["service"] == "LLM Vision"
    assert checkpoint["stage"] == "Layout Clustering"
    assert "API rate limit" in checkpoint["error"]
    assert len(checkpoint["options"]) == 3

    actions = [o["action"] for o in checkpoint["options"]]
    assert "retry" in actions
    assert "fallback" in actions
    assert "abort" in actions
    assert checkpoint["timeout_seconds"] == 5
    assert checkpoint["timeout_action"] == "fallback"


# ---------------------------------------------------------------------------
# Test: Feature flag
# ---------------------------------------------------------------------------


def test_pipeline_version_always_v2():
    """Pipeline version is always v2 — v1 removed in Epic 15."""
    import routers.analyze as analyze_mod
    assert analyze_mod._get_pipeline_version() == "v2"

    # Env var is ignored — always v2
    old = os.environ.get("PIPELINE_VERSION")
    try:
        os.environ["PIPELINE_VERSION"] = "v1"
        assert analyze_mod._get_pipeline_version() == "v2"
    finally:
        if old is not None:
            os.environ["PIPELINE_VERSION"] = old
        else:
            os.environ.pop("PIPELINE_VERSION", None)


# ---------------------------------------------------------------------------
# Test: compute_overall_progress
# ---------------------------------------------------------------------------


def test_compute_overall_progress_stage_1_start():
    mod = _get_orchestrator()
    assert mod.compute_overall_progress(1, 0.0) == 0.0


def test_compute_overall_progress_stage_1_half():
    mod = _get_orchestrator()
    assert abs(mod.compute_overall_progress(1, 0.5) - 0.10) < 1e-9


def test_compute_overall_progress_stage_3_full():
    mod = _get_orchestrator()
    assert abs(mod.compute_overall_progress(3, 1.0) - 0.60) < 1e-9


def test_compute_overall_progress_stage_5_full():
    mod = _get_orchestrator()
    assert abs(mod.compute_overall_progress(5, 1.0) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Test: handle-failure endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_failure_endpoint_accepts_valid_action():
    """POST /jobs/{job_id}/handle-failure sets failure_response and unblocks."""
    import routers.analyze as mod

    job_id = "handle-failure-test"
    job_state = {
        "status": "awaiting_confirmation",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_log": [],
        "new_event": asyncio.Event(),
        "pipeline_done": False,
        "created_at": 0,
        "confirmation_event": asyncio.Event(),
    }
    mod._pipeline_jobs[job_id] = job_state

    try:
        body = mod.FailureResponse(action="retry")
        result = await mod.handle_failure(job_id, body)

        assert result["status"] == "accepted"
        assert result["action"] == "retry"
        assert job_state["failure_response"]["action"] == "retry"
        assert job_state["confirmation_event"].is_set()
    finally:
        mod._pipeline_jobs.pop(job_id, None)


@pytest.mark.asyncio
async def test_handle_failure_endpoint_rejects_non_awaiting():
    """POST /jobs/{job_id}/handle-failure returns 409 if not awaiting confirmation."""
    import routers.analyze as mod
    from fastapi import HTTPException

    job_id = "non-awaiting-test"
    mod._pipeline_jobs[job_id] = {
        "status": "running",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_log": [],
        "new_event": asyncio.Event(),
        "pipeline_done": False,
        "created_at": 0,
    }

    try:
        body = mod.FailureResponse(action="fallback")
        with pytest.raises(HTTPException) as exc_info:
            await mod.handle_failure(job_id, body)
        assert exc_info.value.status_code == 409
    finally:
        mod._pipeline_jobs.pop(job_id, None)


@pytest.mark.asyncio
async def test_handle_failure_endpoint_rejects_unknown_job():
    """POST /jobs/{unknown}/handle-failure returns 404."""
    import routers.analyze as mod
    from fastapi import HTTPException

    body = mod.FailureResponse(action="abort")
    with pytest.raises(HTTPException) as exc_info:
        await mod.handle_failure("nonexistent-job-id", body)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: Story 15.16 — _job present in context (checkpoint mechanism)
# ---------------------------------------------------------------------------


def test_run_pipeline_v2_context_includes_job():
    """run_pipeline_v2 context dict must include '_job' for handle_service_failure.

    Story 15.16: Stages 1 and 3 read context.get('_job') to call handle_service_failure.
    Without '_job' in context, checkpoints are inoperative (300s timeout).

    This test inspects the source code of run_pipeline_v2 to verify that '_job'
    is included in the context initialisation dict.
    """
    import inspect
    import services.pipeline_orchestrator_v2 as mod

    source = inspect.getsource(mod.run_pipeline_v2)
    assert '"_job": job' in source or "'_job': job" in source, (
        "'_job': job must be present in the context initialisation dict of run_pipeline_v2. "
        "Without it, handle_service_failure in stages 1 and 3 will never receive the job object."
    )
