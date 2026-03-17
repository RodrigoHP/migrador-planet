"""Stage 22 — Self-Check.

Compares Vision AI output (Stage 20/21) against text extraction output
(Stages 2–6) to produce a consistency_score (0–100) for each representative
page.

Scoring heuristics (each dimension contributes up to 33 points):
    1. Text coverage: text blocks detected visually vs. extracted
    2. Table agreement: table_area regions vs. detected tables
    3. Image agreement: image_area / chart_area regions vs. extracted images

Thresholds:
    >= 80  — consistent; use both outputs
    50–79  — partially consistent; flag for review
    < 50   — inconsistent; retry once; if still fails, mark vision_low_confidence

Reads:
    context["visual_analysis"]   — Dict keyed by "{pdf_index}:{page_number}"
    context["parsed_documents"]  — List[Dict]
    context["tables"]            — List[Dict]  (optional)
    context["vision_client"]     — AsyncOpenAI (used for retry)

Writes:
    context["visual_analysis"][page_key]["consistency_score"] — int 0-100
    context["visual_analysis"][page_key]["consistency_level"] — "consistent" | "partial" | "low"

Registers itself as Stage 22 (Block 6).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONSISTENT_THRESHOLD = 80
PARTIAL_THRESHOLD = 50

_CONSISTENCY_LEVELS = {
    "consistent": CONSISTENT_THRESHOLD,
    "partial": PARTIAL_THRESHOLD,
    "low": 0,
}


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _text_coverage_score(
    visual_regions: List[Dict[str, Any]],
    page_text_blocks: int,
) -> float:
    """Score 0-33 based on whether text regions were detected visually."""
    if page_text_blocks == 0:
        return 33.0  # No text to compare — neutral

    text_region_types = {"header", "body", "footer", "form_area"}
    visual_text_regions = sum(
        1 for r in visual_regions if r.get("type") in text_region_types
    )
    # If at least one text region detected, give a proportional score
    if visual_text_regions > 0:
        return min(33.0, 33.0 * (visual_text_regions / max(1, len(visual_regions))))
    return 0.0


def _table_agreement_score(
    visual_regions: List[Dict[str, Any]],
    page_number: int,
    pdf_index: int,
    tables: List[Dict[str, Any]],
) -> float:
    """Score 0-33 based on table_area regions vs. detected tables."""
    visual_tables = sum(1 for r in visual_regions if r.get("type") == "table_area")
    detected_tables = sum(
        1
        for t in tables
        if t.get("page_number") == page_number and t.get("pdf_index") == pdf_index
    )

    if visual_tables == 0 and detected_tables == 0:
        return 33.0  # Both agree: no tables
    if visual_tables == 0 or detected_tables == 0:
        return 16.0  # One found tables, the other didn't

    # Both found tables — score by ratio agreement
    ratio = min(visual_tables, detected_tables) / max(visual_tables, detected_tables)
    return 33.0 * ratio


def _image_agreement_score(
    visual_regions: List[Dict[str, Any]],
    page_images: int,
) -> float:
    """Score 0-34 based on image/chart regions vs. extracted images."""
    visual_images = sum(
        1 for r in visual_regions if r.get("type") in ("image_area", "chart_area")
    )

    if visual_images == 0 and page_images == 0:
        return 34.0  # Both agree: no images
    if visual_images == 0 or page_images == 0:
        return 17.0  # One found images, the other didn't

    ratio = min(visual_images, page_images) / max(visual_images, page_images)
    return 34.0 * ratio


def _compute_consistency_score(
    page_key: str,
    page_data: Dict[str, Any],
    parsed_documents: List[Dict[str, Any]],
    tables: List[Dict[str, Any]],
) -> int:
    """Compute an integer consistency score (0–100) for a page."""
    visual_regions: List[Dict[str, Any]] = page_data.get("visual_regions", [])
    if not visual_regions:
        return 0

    # Parse page key
    try:
        pdf_index_str, page_number_str = page_key.split(":", 1)
        pdf_index = int(pdf_index_str)
        page_number = int(page_number_str)
    except (ValueError, AttributeError):
        return 0

    # Get page data from parsed documents
    page_text_blocks = 0
    page_images = 0
    for doc in parsed_documents:
        if doc.get("pdf_index") != pdf_index:
            continue
        for page in doc.get("pages", []):
            if page.get("page_number") == page_number:
                page_text_blocks = len(page.get("text_blocks", []))
                page_images = len(page.get("images", []))
                break

    score = (
        _text_coverage_score(visual_regions, page_text_blocks)
        + _table_agreement_score(visual_regions, page_number, pdf_index, tables)
        + _image_agreement_score(visual_regions, page_images)
    )
    return min(100, max(0, int(round(score))))


def _level_for_score(score: int) -> str:
    if score >= CONSISTENT_THRESHOLD:
        return "consistent"
    if score >= PARTIAL_THRESHOLD:
        return "partial"
    return "low"


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 22 executor — Self-Check."""
    emit = context.get("emit_progress")

    # Check if Vision AI is enabled
    vision_enabled = os.environ.get("VISION_AI_ENABLED", "true").lower() not in (
        "false", "0", "no", "off"
    )
    if not vision_enabled or context.get("vision_unavailable"):
        if emit:
            try:
                emit({
                    "stage": 22,
                    "stage_name": "Self-Check",
                    "status": "skipped",
                    "warning": "Vision AI desabilitado ou indisponível",
                })
            except Exception:
                pass
        return {"pages_checked": 0, "skipped": True}

    visual_analysis: Dict[str, Any] = context.get("visual_analysis", {})
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    tables: List[Dict[str, Any]] = context.get("tables", [])

    pages_checked = 0
    retried = 0
    low_confidence_pages: List[str] = []

    for page_key, page_data in visual_analysis.items():
        if page_data.get("vision_unavailable"):
            continue

        score = _compute_consistency_score(
            page_key, page_data, parsed_documents, tables
        )

        if score < PARTIAL_THRESHOLD:
            # Retry once by re-running segmentation
            retry_score = await _retry_segmentation(
                page_key, page_data, context
            )
            if retry_score is not None:
                retried += 1
                if retry_score >= score:
                    score = retry_score
                else:
                    # Retry made things worse — keep higher score
                    pass

            if score < PARTIAL_THRESHOLD:
                page_data["vision_low_confidence"] = True
                low_confidence_pages.append(page_key)

        level = _level_for_score(score)
        page_data["consistency_score"] = score
        page_data["consistency_level"] = level
        pages_checked += 1

    context["visual_analysis"] = visual_analysis

    # Emit final cost summary
    total_api_calls = context.get("_vision_api_calls", 0)
    from services.openrouter_client import format_cost_summary
    cost_summary = format_cost_summary(total_api_calls)

    summary = {
        "pages_checked": pages_checked,
        "retried": retried,
        "low_confidence_pages": low_confidence_pages,
        "cost_summary": cost_summary,
    }

    if emit:
        try:
            emit({
                "stage": 22,
                "stage_name": "Self-Check",
                "status": "completed",
                "summary": summary,
                "cost_summary": cost_summary,
            })
        except Exception:
            pass

    return summary


async def _retry_segmentation(
    page_key: str,
    page_data: Dict[str, Any],
    context: Dict[str, Any],
) -> Optional[int]:
    """Attempt one retry of visual segmentation for a low-score page.

    Returns the new consistency score, or None if the retry failed.
    """
    from services.stages.visual_segmentation import _parse_regions, _SEGMENTATION_PROMPT

    client = context.get("vision_client")
    if client is None:
        try:
            from services.openrouter_client import get_client
            client = get_client()
        except ValueError:
            return None

    # Locate screenshot path
    try:
        pdf_index_str, page_number_str = page_key.split(":", 1)
        pdf_index = int(pdf_index_str)
        page_number = int(page_number_str)
    except (ValueError, AttributeError):
        return None

    job_id = context.get("job_id", "unknown")
    parsed_documents = context.get("parsed_documents", [])
    tables = context.get("tables", [])

    from services.stages.visual_segmentation import _screenshot_path_for_page
    screenshot_path = _screenshot_path_for_page(
        job_id, pdf_index, page_number, parsed_documents
    )

    from services.openrouter_client import load_image_as_base64, chat_with_vision
    try:
        image_b64 = load_image_as_base64(screenshot_path)
        raw_response = await chat_with_vision(
            client, image_b64=image_b64, prompt=_SEGMENTATION_PROMPT
        )
        regions = _parse_regions(raw_response)
        context["_vision_api_calls"] = context.get("_vision_api_calls", 0) + 1
    except Exception as exc:
        logger.warning("Retry segmentation failed for %s: %s", page_key, exc)
        return None

    if regions:
        page_data["visual_regions"] = regions

    return _compute_consistency_score(page_key, page_data, parsed_documents, tables)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace stub Stage 22 with this implementation."""
    registry.remove_stage(22)
    registry.register_stage(
        stage_number=22,
        name="Self-Check",
        block_id=6,
        estimated_duration=1.0,
        execute_fn=execute,
    )
