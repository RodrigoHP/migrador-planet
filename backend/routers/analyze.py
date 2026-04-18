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
import os
import re
import shutil
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from middleware.auth import require_auth
from models.pipeline_context import PipelineResultResponse
from services.job_store import get_job_store
from services.storage import get_storage
from utils.validation import TMP_BASE, validate_job_id

_RATE_LIMIT_ANALYZE = os.environ.get("RATE_LIMIT_ANALYZE", "10/minute")
_limiter = Limiter(key_func=get_remote_address)

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

_pipeline_jobs: dict[str, dict[str, Any]] = {}

# Retained references to background tasks — prevents GC before completion.
_pipeline_tasks: set[asyncio.Task[Any]] = set()

# TTL for completed/failed/cancelled jobs (seconds)
_JOB_TTL_SECONDS = 3600  # 1 hour

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


async def _evict_stale_jobs() -> None:
    """Remove jobs older than _JOB_TTL_SECONDS that are no longer running.

    For each evicted job the corresponding directory under TMP_BASE is also
    removed from disk (Story 11.9 — TTL disk cleanup).

    Story 40.8: Now async to support async store operations.
    """
    cutoff = time.monotonic() - _JOB_TTL_SECONDS
    stale = [
        jid
        for jid, state in _pipeline_jobs.items()
        if state.get("created_at", 0) < cutoff and state.get("status") not in ("pending", "running")
    ]
    store = get_job_store()
    for jid in stale:
        del _pipeline_jobs[jid]
        try:
            await store.delete_job(jid)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to evict job %s from store", jid)
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

    _uuid_re = _re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
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


class FailureResponse(BaseModel):
    """Operator response to a service failure checkpoint (Section 12)."""

    action: Literal["retry", "fallback", "abort"]


# ---------------------------------------------------------------------------
# Pipeline version — v2 is the only supported version (Epic 13 redesign)
# ---------------------------------------------------------------------------


def _get_pipeline_version() -> str:
    """Return the active pipeline version. Always 'v2' (28-stage v1 removed in Epic 15)."""
    return "v2"


# ---------------------------------------------------------------------------
# SSE event helpers
# ---------------------------------------------------------------------------


def _make_event(
    block: int,
    stage: int,
    stage_name: str,
    status: str,
    progress_pct: float,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "block": block,
        "stage": stage,
        "stage_name": stage_name,
        "status": status,
        "progress_pct": round(progress_pct, 2),
        "summary": summary or {},
    }


def _emit_event(job_state: dict[str, Any], event: dict[str, Any] | None) -> None:
    """Append event to the replay log and signal waiting generators.

    Passing event=None appends the sentinel that signals end-of-stream.
    """
    job_state["event_log"].append(event)
    if event is None:
        job_state["pipeline_done"] = True
    job_state["new_event"].set()


# ---------------------------------------------------------------------------
# Pipeline v2 executor (Story 13.3, sole pipeline since Epic 15)
# ---------------------------------------------------------------------------


async def _run_pipeline_v2(job_id: str, user_id: str | None = None, auth_token: str | None = None) -> None:
    """Execute the 5-stage pipeline v2 for the given job_id.

    Uses the same replay-buffer SSE mechanism as v1.  The orchestrator logic
    lives in ``services.pipeline_orchestrator_v2``.

    DB-002: user_id is propagated to storage gateway for inclusion in DB writes.
    """
    from services.pipeline_orchestrator_v2 import (
        PipelineAbortError,
        run_pipeline_v2,
    )

    job_state = _pipeline_jobs[job_id]
    job_state["status"] = "running"
    job_state["job_id"] = job_id
    storage = get_storage()

    # DB-002/DB-003: Set user context on storage gateway for RLS + user_id writes
    if user_id and hasattr(storage, "set_auth_context"):
        storage.set_auth_context(user_id=user_id, token=auth_token)

    # Build pdf_documents list from the job directory
    job_dir = TMP_BASE / job_id
    pdf_documents: list[dict[str, str]] = []
    if job_dir.exists():
        # input.pdf → index 0, input_2.pdf → index 1, etc.
        idx = 0
        while True:
            if idx == 0:
                pdf_path = job_dir / "input.pdf"
            else:
                pdf_path = job_dir / f"input_{idx + 1}.pdf"
            if not pdf_path.exists():
                break
            pdf_documents.append(
                {
                    "id": str(idx),
                    "path": str(pdf_path),
                    "name": pdf_path.name,
                }
            )
            idx += 1

    xsd_local = await storage.get_asset_local_path(job_id, "schema.xsd")
    xsd_path = str(xsd_local) if xsd_local.exists() else ""

    async def emit_progress(event: dict[str, Any]) -> None:
        """Emit a v2 SSE event via the replay buffer."""
        _emit_event(job_state, event)

    try:
        result = await run_pipeline_v2(
            pdf_documents=pdf_documents,
            xsd_path=xsd_path,
            storage=storage,
            job=job_state,
            emit_progress=emit_progress,
        )
        if job_state["cancel_flag"].is_set():
            job_state["status"] = "cancelled"
        else:
            job_state["status"] = "completed"
            job_state["result"] = result
    except PipelineAbortError as exc:
        job_state["status"] = "failed"
        job_state["error"] = str(exc)
    except Exception as exc:  # noqa: BLE001
        job_state["status"] = "failed"
        job_state["error"] = str(exc)
    finally:
        # Story 40.8: Persist final state to Redis SSOT via async store
        store = get_job_store()
        try:
            await store.save_job(job_id, job_state)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to persist job %s to store", job_id)
        try:
            await storage.cleanup_local(job_id)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to cleanup local files for job %s", job_id)
        _emit_event(job_state, None)  # sentinel


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

    event_log: list[dict[str, Any] | None] = job_state["event_log"]
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
@_limiter.limit(_RATE_LIMIT_ANALYZE)
async def start_analyze(
    request: Request,
    body: AnalyzeRequest,
    user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Start the analysis pipeline for an uploaded job.

    Returns immediately with status 'started'; progress is streamed via SSE.
    DB-002: Captures user_id from JWT for multi-tenancy.
    """
    job_id = body.job_id
    # DB-002: Extract user_id from JWT payload ('sub' claim)
    user_id = user.get("sub")
    auth_token = getattr(request.state, "_auth_token", None)

    # Validate UUID v4 format and prevent path traversal before any disk access
    validate_job_id(job_id)

    # Validate that the job directory exists (upload must have happened first).
    # Use storage gateway's get_local_path to verify — this also works with
    # cloud storage (downloads to local cache if needed).
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
    await _evict_stale_jobs()

    # Initialise job state with replay-buffer fields (Story 40.8: async store)
    store = get_job_store()
    job_state = await store.create_job(job_id)

    # Story 38.6: Read template_name from upload metadata and persist in job_state
    # upload_asset stores files under assets/ subdirectory
    template_name_path = job_dir / "assets" / "template_name.txt"
    if template_name_path.exists():
        try:
            job_state["template_name"] = template_name_path.read_text(encoding="utf-8").strip()
        except Exception:  # noqa: BLE001
            job_state["template_name"] = ""
    else:
        job_state["template_name"] = ""

    _pipeline_jobs[job_id] = job_state

    # Start pipeline v2 as a background coroutine (non-blocking).
    # DB-002: Pass user_id so storage gateway includes it in DB writes
    task = asyncio.create_task(_run_pipeline_v2(job_id, user_id=user_id, auth_token=auth_token))
    _pipeline_tasks.add(task)
    task.add_done_callback(_pipeline_tasks.discard)

    return {"status": "started", "job_id": job_id, "pipeline_version": "v2"}


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
async def cancel_pipeline(job_id: str) -> dict[str, Any]:
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


@router.post("/jobs/{job_id}/handle-failure")
async def handle_failure(job_id: str, body: FailureResponse) -> dict[str, Any]:
    """Operator responds to a service failure checkpoint (Section 12).

    The pipeline v2 orchestrator emits a ``service_failure`` SSE event and
    blocks on ``confirmation_event``.  This endpoint sets the response and
    unblocks the pipeline.
    """
    if job_id not in _pipeline_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline found for job '{job_id}'.",
        )

    job_state = _pipeline_jobs[job_id]
    if job_state.get("status") != "awaiting_confirmation":
        raise HTTPException(
            status_code=409,
            detail="Job is not awaiting confirmation.",
        )

    job_state["failure_response"] = {
        "action": body.action,
        "by": "human",
    }

    confirmation_event = job_state.get("confirmation_event")
    if confirmation_event:
        confirmation_event.set()

    return {"status": "accepted", "action": body.action}


@router.get("/analyze/{job_id}/status")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Check if a job exists in the current server session or store."""
    if job_id in _pipeline_jobs:
        return {
            "job_id": job_id,
            "exists": True,
            "status": _pipeline_jobs[job_id]["status"],
        }
    # Fallback: check persistent store (Redis) — Story 40.8: async
    store = get_job_store()
    stored = await store.get_job(job_id)
    if stored is not None:
        return {
            "job_id": job_id,
            "exists": True,
            "status": stored.get("status"),
        }
    return {"job_id": job_id, "exists": False, "status": None}


@router.get("/analyze/{job_id}/result", response_model=PipelineResultResponse)
async def get_result(job_id: str) -> dict[str, Any]:
    """Return the pipeline result for a completed job."""
    job_state = _pipeline_jobs.get(job_id)
    if job_state is None:
        # Fallback: check persistent store (Redis) — Story 40.8: async
        store = get_job_store()
        job_state = await store.get_job(job_id)
    if job_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline result found for job '{job_id}'.",
        )
    status = job_state["status"]

    if status == "running":
        raise HTTPException(status_code=202, detail="Pipeline still running.")

    template_name = job_state.get("template_name") or None

    if status == "failed":
        return {
            "job_id": job_id,
            "status": "failed",
            "template_name": template_name,
            "error": job_state.get("error"),
            "result": None,
        }

    if status == "cancelled":
        return {
            "job_id": job_id,
            "status": "cancelled",
            "template_name": template_name,
            "result": None,
        }

    return {
        "job_id": job_id,
        "status": status,
        "template_name": template_name,
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


# ---------------------------------------------------------------------------
# Story 13.2 — Screenshot proxy endpoint
# ---------------------------------------------------------------------------


_SAFE_PAGE_KEY_RE = re.compile(r"^page_\d+_\d+$")


@router.get("/jobs/{job_id}/screenshot/{page_key}")
async def get_screenshot(job_id: str, page_key: str) -> dict[str, Any]:
    """Return a signed URL (or local path) for a page screenshot.

    The frontend calls this instead of using a local filesystem path directly.
    """
    validate_job_id(job_id)
    if not _SAFE_PAGE_KEY_RE.match(page_key):
        raise HTTPException(
            status_code=400,
            detail="page_key inválido: formato esperado 'page_{pdfIndex}_{pageNum}'.",
        )
    storage = get_storage()
    url = await storage.get_signed_url("jobs", f"jobs/{job_id}/screenshots/{page_key}.png")
    return {"url": url}
