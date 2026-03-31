"""Pipeline Orchestrator v2 — 5 stages with SSE sub-progress and service failure checkpoints.

Story 13.3 — Replaces the 28-stage pipeline with 5 substantial stages.
Each stage is a stub for now (real implementations come in stories 13.4-13.10).

Architecture reference: docs/architecture/pipeline-redesign-v3.md
- Section 9: SSE sub-progress format
- Section 12: handle_service_failure pattern
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional

from services.openrouter_client import ESTIMATED_COST_PER_VISION_CALL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------

STAGE_DEFINITIONS: List[Dict[str, Any]] = [
    {"stage": 1, "name": "Layout Clustering", "weight": 0.20},
    {"stage": 2, "name": "Deep Extraction", "weight": 0.20},
    {"stage": 3, "name": "Structural Analysis", "weight": 0.20},
    {"stage": 4, "name": "Field Mapping", "weight": 0.20},
    {"stage": 5, "name": "Template Generation", "weight": 0.20},
]

# Type alias for the emit_progress callback
EmitProgressFn = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class PipelineAbortError(Exception):
    """Raised when the operator aborts the pipeline via a service failure checkpoint."""


# ---------------------------------------------------------------------------
# SSE Sub-Progress Helper
# ---------------------------------------------------------------------------


def make_sub_progress_event(
    stage: int,
    stage_name: str,
    status: str,
    progress_pct: float,
    sub_step: str = "",
    sub_progress_pct: float = 0.0,
    summary: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build an SSE event dict in the v2 sub-progress format (Section 9)."""
    event: Dict[str, Any] = {
        "stage": stage,
        "stage_name": stage_name,
        "status": status,
        "progress_pct": round(progress_pct, 4),
        "sub_step": sub_step,
        "sub_progress_pct": round(sub_progress_pct, 4),
        "summary": summary or {},
    }
    event.update(extra)
    return event


def compute_overall_progress(stage: int, sub_progress_pct: float) -> float:
    """Compute overall pipeline progress (0.0 - 1.0) from stage number and sub-progress.

    Each stage contributes 20% (0.20) to the overall progress.
    """
    stage_base = (stage - 1) * 0.20
    return stage_base + 0.20 * sub_progress_pct


# ---------------------------------------------------------------------------
# Service Failure Checkpoint (Section 12)
# ---------------------------------------------------------------------------

# Default timeout for operator decisions (seconds)
DEFAULT_FAILURE_TIMEOUT = 300


async def handle_service_failure(
    context: Dict[str, Any],
    service_name: str,
    stage_name: str,
    error: Exception,
    fallback_description: str,
    impact_description: str,
    job: Dict[str, Any],
    emit_progress: EmitProgressFn,
    timeout: int = DEFAULT_FAILURE_TIMEOUT,
) -> Literal["retry", "fallback"]:
    """Notify the operator about a service failure and wait for a decision.

    Emits a ``service_failure`` SSE event with a checkpoint, then blocks until
    the operator responds (via ``POST /jobs/{job_id}/handle-failure``) or the
    timeout expires.

    Returns
    -------
    "retry"
        The operator chose to retry the failed operation.
    "fallback"
        The operator chose to continue with degraded quality, OR the timeout expired.

    Raises
    ------
    PipelineAbortError
        If the operator chooses to abort the pipeline.
    """
    current_stage = context.get("_current_stage", 0)

    checkpoint: Dict[str, Any] = {
        "type": "service_failure",
        "service": service_name,
        "stage": stage_name,
        "error": str(error),
        "options": [
            {
                "action": "retry",
                "label": f"Tentar {service_name} novamente",
                "description": "Re-executa a chamada ao servico",
            },
            {
                "action": "fallback",
                "label": f"Continuar sem {service_name}",
                "description": fallback_description,
                "warning": impact_description,
            },
            {
                "action": "abort",
                "label": "Cancelar pipeline",
                "description": "Para a execucao para investigar o problema",
            },
        ],
        "timeout_seconds": timeout,
        "timeout_action": "fallback",
        "message": f"{service_name} falhou no {stage_name}: {error}",
    }

    # Emit checkpoint via SSE
    event = make_sub_progress_event(
        stage=current_stage,
        stage_name=stage_name,
        status="service_failure",
        progress_pct=compute_overall_progress(current_stage, 0.0),
        checkpoint=checkpoint,
    )
    await emit_progress(event)

    # Set up confirmation event and wait
    job["confirmation_event"] = asyncio.Event()
    job["status"] = "awaiting_confirmation"

    confirmation = await _wait_for_confirmation(job, timeout=timeout)

    action = confirmation.get("action", "fallback")
    if action == "retry":
        job["status"] = "running"
        return "retry"
    elif action == "abort":
        job["status"] = "failed"
        raise PipelineAbortError(f"Operador cancelou: {service_name} falhou")
    else:
        # fallback (explicit or timeout)
        job["status"] = "running"
        return "fallback"


async def _wait_for_confirmation(
    job: Dict[str, Any],
    timeout: int = DEFAULT_FAILURE_TIMEOUT,
) -> Dict[str, Any]:
    """Wait for operator confirmation or timeout.

    If the timeout expires, returns the default action (fallback).
    """
    confirmation_event: asyncio.Event = job["confirmation_event"]

    try:
        await asyncio.wait_for(confirmation_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(
            "Timeout (%ds) waiting for operator confirmation — defaulting to fallback",
            timeout,
        )
        return {"action": "fallback", "by": "timeout"}

    # Operator responded via the handle-failure endpoint
    return job.get("failure_response", {"action": "fallback", "by": "timeout"})


# ---------------------------------------------------------------------------
# Stage stubs — real implementations come in stories 13.4-13.10
# ---------------------------------------------------------------------------


async def _run_stage_1(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 1: Layout Clustering — real implementation (Story 13.4)."""
    from services.stages.stage1_layout_clustering import run_stage1

    return await run_stage1(context, emit_progress)


async def _run_stage_2(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 2: Deep Extraction — real implementation (Story 13.5)."""
    from services.stages.stage2_deep_extraction import run_stage2

    return await run_stage2(context, emit_progress)


async def _run_stage_3(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 3: Structural Analysis — real implementation (Story 13.7)."""
    from services.stages.stage3_structural_analysis import run_stage3

    return await run_stage3(context, emit_progress)


async def _run_stage_4(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 4: Field Mapping — real implementation (Story 13.8)."""
    from services.stages.stage4_field_mapping import run_stage4

    return await run_stage4(context, emit_progress)


async def _run_stage_5(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 5: Template Generation — real implementation (Story 13.10)."""
    from services.stages.stage5_template_generation import run_stage5

    return await run_stage5(context, emit_progress)


# Stage function registry
STAGE_FUNCTIONS = [
    _run_stage_1,
    _run_stage_2,
    _run_stage_3,
    _run_stage_4,
    _run_stage_5,
]


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def run_pipeline_v2(
    pdf_documents: List[Dict[str, str]],
    xsd_path: str,
    storage: Any,
    job: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Execute the 5-stage pipeline v2.

    Parameters
    ----------
    pdf_documents
        List of dicts with ``id`` (str), ``path`` (str), ``name`` (str).
    xsd_path
        Path to the XSD schema file.
    storage
        StorageGateway instance.
    job
        Mutable job state dict (from ``_pipeline_jobs``).
    emit_progress
        Async callback to emit SSE events (uses the replay-buffer pattern
        from ``analyze.py``).

    Returns
    -------
    dict
        The pipeline result (context after all stages).
    """
    # Initialize context
    context: Dict[str, Any] = {
        "_storage": storage,
        "_current_stage": 0,
        "_current_stage_name": "",
        "pdf_documents": pdf_documents,
        "xsd_path": xsd_path,
        "job_id": job.get("job_id", ""),
        "_job": job,
    }

    # Emit pipeline start
    start_event = make_sub_progress_event(
        stage=0,
        stage_name="Pipeline v2",
        status="started",
        progress_pct=0.0,
        summary={"total_stages": 5, "pdf_count": len(pdf_documents)},
    )
    await emit_progress(start_event)

    # Execute stages sequentially
    for i, stage_fn in enumerate(STAGE_FUNCTIONS):
        stage_def = STAGE_DEFINITIONS[i]
        stage_num = stage_def["stage"]
        stage_name = stage_def["name"]

        # Check cancellation
        cancel_flag = job.get("cancel_flag")
        if cancel_flag and cancel_flag.is_set():
            cancel_event = make_sub_progress_event(
                stage=stage_num,
                stage_name=stage_name,
                status="cancelled",
                progress_pct=compute_overall_progress(stage_num, 0.0),
            )
            await emit_progress(cancel_event)
            return context

        # Emit stage running
        running_event = make_sub_progress_event(
            stage=stage_num,
            stage_name=stage_name,
            status="running",
            progress_pct=compute_overall_progress(stage_num, 0.0),
            sub_step=f"{stage_num}.0 Starting",
            sub_progress_pct=0.0,
        )
        await emit_progress(running_event)

        try:
            context = await stage_fn(context, emit_progress)
        except PipelineAbortError:
            raise
        except Exception as exc:
            # Emit stage failure
            fail_event = make_sub_progress_event(
                stage=stage_num,
                stage_name=stage_name,
                status="failed",
                progress_pct=compute_overall_progress(stage_num, 0.0),
                summary={"error": str(exc)},
            )
            await emit_progress(fail_event)
            raise

        # Emit stage completed
        completed_event = make_sub_progress_event(
            stage=stage_num,
            stage_name=stage_name,
            status="completed",
            progress_pct=compute_overall_progress(stage_num, 1.0),
            sub_step=f"{stage_num}.done",
            sub_progress_pct=1.0,
        )
        await emit_progress(completed_event)

    # Emit pipeline completion with summary metrics derived from stage results
    clusters = context.get("clusters", [])
    # Exclude special clusters (_blank, _scanned) from layout count
    real_clusters = [c for c in clusters if not str(c.get("cluster_id", "")).startswith("_")]
    # Use cluster page counts if available; fall back to raw_text_blocks key count
    raw_text_blocks = context.get("_raw_text_blocks", {})
    total_pages = sum(c.get("page_count", 0) for c in clusters) or len(raw_text_blocks)
    completion_event = make_sub_progress_event(
        stage=5,
        stage_name="Pipeline v2",
        status="completed",
        progress_pct=1.0,
        event="pipeline_completed",
        summary={
            "layouts_detected": len(real_clusters),
            "page_count": total_pages,
            "api_cost": round(
                context.get("_vision_api_cost") or
                context.get("_vision_api_calls", 0) * ESTIMATED_COST_PER_VISION_CALL,
                4
            ),
            "vision_ai_used": context.get("_vision_api_calls", 0) > 0,
            "warnings": context.get("_pipeline_warnings", []),
        },
    )
    await emit_progress(completion_event)

    # Build result from context.
    # result_json is the authoritative flat contract built by Stage 5 (_step_5_6_pipeline_result).
    # It contains all keys the frontend expects: layout_types, field_mappings, trees_by_layout,
    # document_structure, confidence_scores, coverage, template_draft, etc.
    # _debug_stages preserves per-stage summaries for introspection/logging.
    result_json = context.get("result_json", {})
    result = {
        **result_json,
        "_debug_stages": {
            "stage_1": context.get("stage_1_result", {}),
            "stage_2": context.get("stage_2_result", {}),
            "stage_3": context.get("stage_3_result", {}),
            "stage_4": context.get("stage_4_result", {}),
            "stage_5": context.get("stage_5_result", {}),
        },
    }

    return result
