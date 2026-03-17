"""Router for /api/analyze — pipeline orchestration with SSE progress streaming."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from models.pipeline import PipelineDefinition, StageDefinition, default_registry

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory job state store
# ---------------------------------------------------------------------------

# Structure per job_id:
# {
#   "status": "pending"|"running"|"completed"|"failed"|"cancelled",
#   "result": dict | None,
#   "error": str | None,
#   "cancel_flag": asyncio.Event,
#   "event_queue": asyncio.Queue,   # SSE events
# }

_pipeline_jobs: Dict[str, Dict[str, Any]] = {}

TMP_BASE = Path("/tmp/jobs")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    job_id: str


# ---------------------------------------------------------------------------
# SSE event helpers
# ---------------------------------------------------------------------------

def _make_event(
    block: int,
    stage: int,
    stage_name: str,
    status: str,
    progress_pct: float,
    summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "block": block,
        "stage": stage,
        "stage_name": stage_name,
        "status": status,
        "progress_pct": round(progress_pct, 2),
        "summary": summary or {},
    }


# ---------------------------------------------------------------------------
# Pipeline executor
# ---------------------------------------------------------------------------

async def _run_pipeline(job_id: str) -> None:
    """Execute the full 27-stage pipeline for the given job_id.

    Publishes SSE events to the job's event_queue and stores the final
    result (or error) in _pipeline_jobs.
    """
    job_state = _pipeline_jobs[job_id]
    queue: asyncio.Queue = job_state["event_queue"]
    cancel_flag: asyncio.Event = job_state["cancel_flag"]

    pipeline: PipelineDefinition = default_registry.build_pipeline()
    total_stages = pipeline.total_stages

    job_state["status"] = "running"
    context: Dict[str, Any] = {"job_id": job_id}
    stage_counter = 0  # global stage counter (1-indexed)

    try:
        for block in pipeline.blocks:
            for stage_def in block.stages:
                stage_counter += 1

                # Check cancellation before starting each stage
                if cancel_flag.is_set():
                    cancel_event = _make_event(
                        block=block.block_id,
                        stage=stage_def.stage_number,
                        stage_name=stage_def.name,
                        status="cancelled",
                        progress_pct=(stage_counter - 1) / total_stages * 100,
                    )
                    await queue.put(cancel_event)
                    job_state["status"] = "cancelled"
                    await queue.put(None)  # sentinel
                    return

                progress_start = (stage_counter - 1) / total_stages * 100

                # Emit "running" event
                running_event = _make_event(
                    block=block.block_id,
                    stage=stage_def.stage_number,
                    stage_name=stage_def.name,
                    status="running",
                    progress_pct=progress_start,
                )
                await queue.put(running_event)

                # Execute the stage
                try:
                    stage_result = await stage_def.execute(context)
                    context[f"stage_{stage_def.stage_number}"] = stage_result
                except Exception as exc:  # noqa: BLE001
                    error_detail = f"Stage {stage_def.stage_number} ({stage_def.name}) failed: {exc!s}"
                    fail_event = _make_event(
                        block=block.block_id,
                        stage=stage_def.stage_number,
                        stage_name=stage_def.name,
                        status="failed",
                        progress_pct=progress_start,
                        summary={"error": error_detail},
                    )
                    await queue.put(fail_event)
                    job_state["status"] = "failed"
                    job_state["error"] = error_detail
                    await queue.put(None)  # sentinel
                    return

                progress_end = stage_counter / total_stages * 100

                # Emit "completed" event
                completed_event = _make_event(
                    block=block.block_id,
                    stage=stage_def.stage_number,
                    stage_name=stage_def.name,
                    status="completed",
                    progress_pct=progress_end,
                    summary=stage_result,
                )
                await queue.put(completed_event)

        # All stages completed — store result
        # Prefer the canonical result_json assembled by Stage 28 (pipeline_result)
        result_json = context.get("result_json")
        if result_json is None:
            result_json = {
                "document_structure": context.get("stage_7", {}),
                "field_mappings": context.get("field_mappings", []),
                "confidence_scores": context.get("confidence_scores", context.get("stage_25", {})),
                "coverage": context.get("template_draft", {}).get("coverage", {}),
                "layout_types": context.get("layout_types", []),
                "template_draft": context.get("stage_27", context.get("template_draft", {"html": "", "css": ""})),
                "ambiguous_fields": [m for m in context.get("field_mappings", []) if m.get("is_ambiguous")],
                "format_functions": context.get("format_functions", {}),
            }
        job_state["status"] = "completed"
        job_state["result"] = result_json

    except Exception as exc:  # noqa: BLE001
        job_state["status"] = "failed"
        job_state["error"] = str(exc)

    finally:
        await queue.put(None)  # sentinel signals stream end


# ---------------------------------------------------------------------------
# SSE generator
# ---------------------------------------------------------------------------

async def _event_generator(job_id: str) -> AsyncIterator[str]:
    """Yield SSE-formatted data strings from the job's event queue."""
    job_state = _pipeline_jobs.get(job_id)
    if job_state is None:
        yield json.dumps({"error": "job not found"})
        return

    queue: asyncio.Queue = job_state["event_queue"]

    while True:
        event = await queue.get()
        if event is None:
            # Pipeline finished (completed, failed, or cancelled)
            break
        yield json.dumps(event)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze")
async def start_analyze(body: AnalyzeRequest) -> Dict[str, Any]:
    """Start the analysis pipeline for an uploaded job.

    Returns immediately with status 'started'; progress is streamed via SSE.
    """
    job_id = body.job_id

    # Validate that the job directory exists (upload must have happened first)
    job_dir = TMP_BASE / job_id
    if not job_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. Upload files first.",
        )

    # Prevent duplicate pipeline runs
    if job_id in _pipeline_jobs and _pipeline_jobs[job_id]["status"] == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running for job '{job_id}'.",
        )

    # Initialise job state
    _pipeline_jobs[job_id] = {
        "status": "pending",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_queue": asyncio.Queue(),
    }

    # Start pipeline as a background coroutine (non-blocking)
    asyncio.create_task(_run_pipeline(job_id))

    return {"status": "started", "job_id": job_id}


@router.get("/analyze/{job_id}/progress")
async def stream_progress(job_id: str) -> EventSourceResponse:
    """Stream pipeline progress events via Server-Sent Events."""
    if job_id not in _pipeline_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline found for job '{job_id}'. Call POST /api/analyze first.",
        )

    return EventSourceResponse(_event_generator(job_id))


@router.post("/analyze/{job_id}/cancel")
async def cancel_pipeline(job_id: str) -> Dict[str, Any]:
    """Request cancellation of a running pipeline."""
    if job_id not in _pipeline_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline found for job '{job_id}'.",
        )

    job_state = _pipeline_jobs[job_id]
    if job_state["status"] not in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline is not running (status={job_state['status']}).",
        )

    job_state["cancel_flag"].set()
    return {"status": "cancellation_requested", "job_id": job_id}


@router.get("/analyze/{job_id}/result")
async def get_result(job_id: str) -> Dict[str, Any]:
    """Return the pipeline result for a completed job."""
    if job_id not in _pipeline_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline result found for job '{job_id}'.",
        )

    job_state = _pipeline_jobs[job_id]
    status = job_state["status"]

    if status == "running":
        raise HTTPException(status_code=202, detail="Pipeline still running.")

    if status == "failed":
        return {
            "job_id": job_id,
            "status": "failed",
            "error": job_state.get("error"),
            "result": None,
        }

    if status == "cancelled":
        return {
            "job_id": job_id,
            "status": "cancelled",
            "result": None,
        }

    return {
        "job_id": job_id,
        "status": status,
        "result": job_state.get("result"),
    }
