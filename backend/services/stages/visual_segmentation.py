"""Stage 20 — Visual Segmentation.

For each representative page (one per LayoutType cluster), sends the page
screenshot to GPT-4o via OpenRouter and identifies visual regions:

    header, body, footer, sidebar, table_area, chart_area, image_area, form_area

Reads:
    context["layout_types"]         — List[Dict] (LayoutType serialised)
    context["parsed_documents"]     — List[Dict] (ParsedDocument serialised)
    context["job_id"]               — str
    context["vision_client"]        — AsyncOpenAI (injected; created if absent)

Writes:
    context["visual_analysis"]      — Dict[str, VisualPageAnalysis dict]
                                      keyed by "{pdf_index}:{page_number}"

Registers itself as Stage 20 (Block 6).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_REGION_TYPES = {
    "header",
    "body",
    "footer",
    "sidebar",
    "table_area",
    "chart_area",
    "image_area",
    "form_area",
}

_SEGMENTATION_PROMPT = """\
You are a document layout analyzer. Analyze this document page image and identify visual regions.

Return ONLY valid JSON with this structure:
{
  "regions": [
    {
      "type": "header",
      "bbox": [x0, y0, x1, y1],
      "description": "brief description"
    }
  ]
}

Valid region types: header, body, footer, sidebar, table_area, chart_area, image_area, form_area.
bbox coordinates should be pixel values (integers) relative to image dimensions.
Identify all distinct visual regions. Return at least a "body" region.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _screenshot_path_for_page(
    job_id: str,
    pdf_index: int,
    page_number: int,
    parsed_documents: List[Dict[str, Any]],
) -> Optional[str]:
    """Find screenshot path from parsed_documents or build a fallback path."""
    for doc in parsed_documents:
        if doc.get("pdf_index") != pdf_index:
            continue
        for page in doc.get("pages", []):
            if page.get("page_number") == page_number:
                path = page.get("screenshot_path")
                if path:
                    return path

    # Fallback: conventional tmp path
    return f"/tmp/{job_id}/screenshots/page_{pdf_index}_{page_number}.png"


def _parse_regions(raw_json: str) -> List[Dict[str, Any]]:
    """Parse and validate GPT-4o JSON response into a list of region dicts."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse Vision AI JSON response: %s", exc)
        return []

    regions = data.get("regions", [])
    if not isinstance(regions, list):
        return []

    validated = []
    for region in regions:
        if not isinstance(region, dict):
            continue
        region_type = region.get("type", "body")
        if region_type not in VALID_REGION_TYPES:
            region_type = "body"
        bbox = region.get("bbox", [0, 0, 100, 100])
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0, 0, 100, 100]
        validated.append(
            {
                "type": region_type,
                "bbox": [int(v) for v in bbox],
                "description": str(region.get("description", "")),
            }
        )
    return validated


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 20 executor — Visual Segmentation."""
    emit = context.get("emit_progress")

    # Check if Vision AI is enabled
    vision_enabled = os.environ.get("VISION_AI_ENABLED", "true").lower() not in (
        "false", "0", "no", "off"
    )
    if not vision_enabled:
        if emit:
            try:
                emit({
                    "stage": 20,
                    "stage_name": "Visual Segmentation",
                    "status": "skipped",
                    "warning": "Vision AI desabilitado via configuração",
                })
            except Exception:
                pass
        context.setdefault("visual_analysis", {})
        context["vision_unavailable"] = True
        return {"pages_processed": 0, "skipped": True, "reason": "VISION_AI_ENABLED=false"}

    layout_types: List[Dict[str, Any]] = context.get("layout_types", [])
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    job_id: str = context.get("job_id", "unknown")

    visual_analysis: Dict[str, Any] = context.get("visual_analysis", {})
    pages_processed = 0
    api_calls = 0
    vision_unavailable = False

    # Get or create OpenRouter client
    client = context.get("vision_client")
    if client is None:
        try:
            from services.openrouter_client import get_client
            client = get_client()
        except ValueError as exc:
            logger.warning("Cannot create Vision AI client: %s", exc)
            vision_unavailable = True

    if not vision_unavailable:
        from services.openrouter_client import load_image_as_base64, chat_with_vision

        for lt in layout_types:
            rep_page = lt.get("representative_page", {})
            pdf_index = rep_page.get("pdf_index", 0)
            page_number = rep_page.get("page_number", 0)
            page_key = f"{pdf_index}:{page_number}"

            if page_key in visual_analysis:
                # Already processed (e.g. retry scenario)
                continue

            screenshot_path = _screenshot_path_for_page(
                job_id, pdf_index, page_number, parsed_documents
            )

            # Load image
            try:
                image_b64 = load_image_as_base64(screenshot_path)
            except (FileNotFoundError, OSError) as exc:
                logger.warning("Screenshot not found for %s: %s", page_key, exc)
                visual_analysis[page_key] = {
                    "visual_regions": [],
                    "visual_interpretations": [],
                    "consistency_score": None,
                    "vision_unavailable": True,
                }
                continue

            # Call Vision AI
            try:
                raw_response = await chat_with_vision(
                    client,
                    image_b64=image_b64,
                    prompt=_SEGMENTATION_PROMPT,
                )
                regions = _parse_regions(raw_response)
                api_calls += 1
            except Exception as exc:
                logger.warning("Vision AI call failed for page %s: %s", page_key, exc)
                visual_analysis[page_key] = {
                    "visual_regions": [],
                    "visual_interpretations": [],
                    "consistency_score": None,
                    "vision_unavailable": True,
                }
                if emit:
                    try:
                        emit({
                            "stage": 20,
                            "stage_name": "Visual Segmentation",
                            "status": "warning",
                            "warning": f"Vision AI indisponível para página {page_key}, análise apenas por texto",
                            "page_key": page_key,
                        })
                    except Exception:
                        pass
                continue

            visual_analysis[page_key] = {
                "visual_regions": regions,
                "visual_interpretations": [],   # filled by Stage 21
                "consistency_score": None,       # filled by Stage 22
                "vision_unavailable": False,
            }
            pages_processed += 1

    # Check overall availability
    all_unavailable = all(
        v.get("vision_unavailable", False) for v in visual_analysis.values()
    ) if visual_analysis else vision_unavailable

    if all_unavailable and visual_analysis:
        context["vision_unavailable"] = True
        if emit:
            try:
                emit({
                    "stage": 20,
                    "stage_name": "Visual Segmentation",
                    "status": "warning",
                    "warning": "Vision AI indisponível, análise apenas por texto",
                })
            except Exception:
                pass

    context["visual_analysis"] = visual_analysis
    context["_vision_api_calls"] = context.get("_vision_api_calls", 0) + api_calls

    summary = {
        "pages_processed": pages_processed,
        "api_calls": api_calls,
        "layout_types_found": len(layout_types),
    }

    if emit:
        try:
            emit({
                "stage": 20,
                "stage_name": "Visual Segmentation",
                "status": "completed",
                "summary": summary,
            })
        except Exception:
            pass

    return summary


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace stub Stage 20 with this implementation."""
    registry.remove_stage(20)
    registry.register_stage(
        stage_number=20,
        name="Visual Segmentation",
        block_id=6,
        estimated_duration=2.0,
        execute_fn=execute,
    )


# Module-level constant (re-exported for tests)
SEGMENTATION_PROMPT = _SEGMENTATION_PROMPT
