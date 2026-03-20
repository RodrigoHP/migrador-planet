"""Router for /api/analyze — pipeline orchestration with SSE progress streaming.

SSE Architecture (Replay Buffer):
    Events are stored in an ordered list (event_log) instead of a consumed queue.
    _event_generator replays all past events first, then waits for new ones via
    asyncio.Event. This ensures late-connecting SSE clients (e.g., after POST
    /api/analyze returns) receive the full history without missing early stages.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set

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
#   "event_log": list,          # Append-only log of all SSE events (replay buffer)
#   "new_event": asyncio.Event, # Signalled whenever a new event is appended
#   "pipeline_done": bool,      # True after sentinel None appended to event_log
#   "created_at": float,        # unix timestamp for TTL eviction
# }

_pipeline_jobs: Dict[str, Dict[str, Any]] = {}

# Retained references to background tasks — prevents GC before completion.
_pipeline_tasks: Set[asyncio.Task] = set()  # type: ignore[type-arg]

# TTL for completed/failed/cancelled jobs (seconds)
_JOB_TTL_SECONDS = 3600  # 1 hour


def _evict_stale_jobs() -> None:
    """Remove jobs older than _JOB_TTL_SECONDS that are no longer running."""
    cutoff = time.monotonic() - _JOB_TTL_SECONDS
    stale = [
        jid
        for jid, state in _pipeline_jobs.items()
        if state.get("created_at", 0) < cutoff
        and state.get("status") not in ("pending", "running")
    ]
    for jid in stale:
        del _pipeline_jobs[jid]

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


def _emit_event(job_state: Dict[str, Any], event: Optional[Dict[str, Any]]) -> None:
    """Append event to the replay log and signal waiting generators.

    Passing event=None appends the sentinel that signals end-of-stream.
    """
    job_state["event_log"].append(event)
    if event is None:
        job_state["pipeline_done"] = True
    job_state["new_event"].set()


# ---------------------------------------------------------------------------
# Pipeline executor
# ---------------------------------------------------------------------------

async def _run_pipeline(job_id: str) -> None:
    """Execute the full 28-stage pipeline for the given job_id.

    Publishes SSE events via _emit_event (replay-buffer pattern) and stores
    the final result (or error) in _pipeline_jobs.
    """
    job_state = _pipeline_jobs[job_id]
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
                    _emit_event(job_state, cancel_event)
                    job_state["status"] = "cancelled"
                    _emit_event(job_state, None)  # sentinel
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
                _emit_event(job_state, running_event)

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
                    _emit_event(job_state, fail_event)
                    job_state["status"] = "failed"
                    job_state["error"] = error_detail
                    _emit_event(job_state, None)  # sentinel
                    return

                progress_end = stage_counter / total_stages * 100

                # Check if stage was skipped (e.g. Vision AI disabled)
                stage_was_skipped = (
                    isinstance(stage_result, dict) and stage_result.get("skipped") is True
                )

                # Emit "completed" or "skipped" event
                completed_event = _make_event(
                    block=block.block_id,
                    stage=stage_def.stage_number,
                    stage_name=stage_def.name,
                    status="skipped" if stage_was_skipped else "completed",
                    progress_pct=progress_end,
                    summary=stage_result,
                )
                _emit_event(job_state, completed_event)

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

        # Emit explicit pipeline completion event before the sentinel
        completion_event = {
            "event": "pipeline_completed",
            "status": "completed",
            "block": None,
            "stage": None,
            "stage_name": "pipeline_completed",
            "progress_pct": 100.0,
            "summary": {},
        }
        _emit_event(job_state, completion_event)

    except Exception as exc:  # noqa: BLE001
        job_state["status"] = "failed"
        job_state["error"] = str(exc)

    finally:
        _emit_event(job_state, None)  # sentinel signals stream end


# ---------------------------------------------------------------------------
# SSE generator — replay buffer pattern
# ---------------------------------------------------------------------------

async def _event_generator(job_id: str) -> AsyncIterator[str]:
    """Yield SSE-formatted data strings using the replay-buffer pattern.

    Replays all past events first (so late-connecting clients get full history),
    then waits for new events via asyncio.Event until pipeline_done is True.

    Race condition handled: after clearing new_event, re-checks log length before
    waiting to avoid missing events appended between the check and the wait.
    """
    job_state = _pipeline_jobs.get(job_id)
    if job_state is None:
        yield json.dumps({"error": "job not found"})
        return

    event_log: List[Optional[Dict[str, Any]]] = job_state["event_log"]
    new_event: asyncio.Event = job_state["new_event"]
    idx = 0

    while True:
        if idx < len(event_log):
            event = event_log[idx]
            idx += 1
            if event is None:  # sentinel — pipeline done
                break
            yield json.dumps(event)
        else:
            # No new events yet — wait for pipeline to emit one.
            # Clear the signal, then re-check to handle events added between
            # the length check above and the clear() below (race-free pattern).
            new_event.clear()
            if idx < len(event_log):
                # Event was added between the outer check and clear(); loop again
                continue
            if job_state.get("pipeline_done"):
                break
            await new_event.wait()


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

    # Evict completed/failed jobs older than TTL before adding a new entry
    _evict_stale_jobs()

    # Initialise job state with replay-buffer fields
    _pipeline_jobs[job_id] = {
        "status": "pending",
        "result": None,
        "error": None,
        "cancel_flag": asyncio.Event(),
        "event_log": [],           # Replay buffer — append-only list of events
        "new_event": asyncio.Event(),  # Signalled on each new event
        "pipeline_done": False,    # True after sentinel appended
        "created_at": time.monotonic(),
    }

    # Start pipeline as a background coroutine (non-blocking).
    # The task reference is retained in _pipeline_tasks to prevent GC before
    # completion; the done-callback removes it once the task finishes.
    task = asyncio.create_task(_run_pipeline(job_id))
    _pipeline_tasks.add(task)
    task.add_done_callback(_pipeline_tasks.discard)

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


@router.get("/analyze/{job_id}/status")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Check if a job exists in the current server session."""
    if job_id not in _pipeline_jobs:
        return {"job_id": job_id, "exists": False, "status": None}
    return {
        "job_id": job_id,
        "exists": True,
        "status": _pipeline_jobs[job_id]["status"],
    }


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
