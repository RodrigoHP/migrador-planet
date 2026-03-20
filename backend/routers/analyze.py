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
import logging
import shutil
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from models.pipeline import PipelineDefinition, StageDefinition, default_registry
from utils.validation import validate_job_id

logger = logging.getLogger(__name__)

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

# Base directory for all job files on disk
TMP_BASE = Path("/tmp/jobs")

# Orphaned directory cleanup threshold: 24 hours in seconds
_ORPHAN_TTL_SECONDS = 86_400


def _safe_disk_size(path: Path) -> int:
    """Return the total size in bytes of *path* (directory or file), or 0 on error."""
    try:
        if path.is_dir():
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return path.stat().st_size
    except OSError:
        return 0


def _safe_rmtree(job_dir: Path, job_id: str, tmp_base: Path) -> None:
    """Remove *job_dir* from disk after verifying it is inside *tmp_base*.

    Logs the freed disk space and skips silently when the path cannot be
    confirmed to be within *tmp_base* (path-traversal prevention).
    """
    try:
        resolved = job_dir.resolve()
        if not str(resolved).startswith(str(tmp_base.resolve())):
            logger.warning(
                "Eviction skipped for job %s — resolved path %s escapes TMP_BASE %s",
                job_id,
                resolved,
                tmp_base,
            )
            return
        freed_bytes = _safe_disk_size(resolved)
        if resolved.exists():
            shutil.rmtree(resolved)
            logger.info(
                "Evicted job %s — disk cleaned (%d bytes freed) at %s",
                job_id,
                freed_bytes,
                resolved,
            )
    except OSError as exc:
        logger.error("Failed to remove disk files for job %s: %s", job_id, exc)


def _evict_stale_jobs() -> None:
    """Remove jobs older than _JOB_TTL_SECONDS that are no longer running.

    For each evicted job the corresponding directory under TMP_BASE is also
    removed from disk (Story 11.9 — TTL disk cleanup).
    """
    cutoff = time.monotonic() - _JOB_TTL_SECONDS
    stale = [
        jid
        for jid, state in _pipeline_jobs.items()
        if state.get("created_at", 0) < cutoff
        and state.get("status") not in ("pending", "running")
    ]
    for jid in stale:
        del _pipeline_jobs[jid]
        # Remove files from disk — validated against TMP_BASE before deletion
        _safe_rmtree(TMP_BASE / jid, jid, TMP_BASE)


def _cleanup_orphaned_dirs() -> None:
    """Remove job directories on disk that have no corresponding in-memory state.

    A directory is considered orphaned when:
    - It is a direct child of TMP_BASE.
    - Its name is a valid UUID v4 (so we only touch job dirs).
    - It has no entry in ``_pipeline_jobs`` (no in-memory state).
    - Its last modification time is older than ``_ORPHAN_TTL_SECONDS`` (24 h).

    This handles the case where the server was restarted and job state was lost
    while job files remain on disk.
    """
    if not TMP_BASE.exists():
        return

    import re as _re
    _uuid_re = _re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    cutoff_mtime = time.time() - _ORPHAN_TTL_SECONDS

    try:
        for entry in TMP_BASE.iterdir():
            if not entry.is_dir():
                continue
            if not _uuid_re.match(entry.name.lower()):
                continue
            if entry.name in _pipeline_jobs:
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime > cutoff_mtime:
                # Directory is recent — do not touch it (could be from a fresh upload)
                continue
            _safe_rmtree(entry, entry.name, TMP_BASE)
    except OSError as exc:
        logger.error("_cleanup_orphaned_dirs failed to iterate TMP_BASE: %s", exc)


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
    # Number of events already in the log when this client connected.
    # These are "historical" events that need an explicit inter-event delay so
    # uvicorn flushes each one as a separate TCP segment and the browser fires
    # individual SSE message events (instead of processing a single burst chunk
    # that causes Vue to batch all DOM updates and render all stages at once).
    initial_log_size = len(event_log)

    while True:
        if idx < len(event_log):
            event = event_log[idx]
            is_historical = idx < initial_log_size
            idx += 1
            if event is None:  # sentinel — pipeline done
                break
            yield json.dumps(event)
            if is_historical:
                # 150 ms delay between replayed events guarantees that uvicorn
                # flushes each chunk to the network before the next event is
                # yielded. asyncio.sleep(0) alone is not enough — the ASGI layer
                # can still coalesce several consecutive yields into one TCP write.
                # 150 ms (instead of 50 ms) gives the frontend enough time to
                # render each stage badge individually before the next event
                # arrives, preventing the "all stages at once" visual glitch.
                await asyncio.sleep(0.15)
            else:
                # Live events arrive at pipeline speed (seconds apart); just
                # yield control so uvicorn can flush without artificial delay.
                await asyncio.sleep(0)
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

    # Validate UUID v4 format and prevent path traversal before any disk access
    validate_job_id(job_id)

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


# ---------------------------------------------------------------------------
# Story 11.8 — PDF serving endpoint
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/pdf")
async def get_pdf(job_id: str, index: int = 0) -> FileResponse:
    """Serve the original PDF file for a given job from disk.

    This endpoint allows the frontend to retrieve the uploaded PDF after a
    page refresh (when the in-memory ``session.uploadedPdfs`` bytes are lost).

    Args:
        job_id: UUID v4 of the job. Validated with path-traversal prevention.
        index: Zero-based index of the PDF to retrieve (default 0).
               index=0 → ``input.pdf``, index=1 → ``input_2.pdf``, etc.

    Returns:
        The PDF file as a ``FileResponse`` with ``application/pdf`` media type.

    Raises:
        HTTP 400: If *job_id* is not a valid UUID v4.
        HTTP 404: If the job directory or the requested PDF file does not exist.
    """
    validate_job_id(job_id)

    job_dir = TMP_BASE / job_id
    if not job_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found.",
        )

    # Determine the filename: index 0 → input.pdf, index N → input_{N+1}.pdf
    if index == 0:
        pdf_filename = "input.pdf"
    else:
        pdf_filename = f"input_{index + 1}.pdf"

    pdf_path = job_dir / pdf_filename
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF index {index} not found for job '{job_id}'.",
        )

    return FileResponse(pdf_path, media_type="application/pdf")
