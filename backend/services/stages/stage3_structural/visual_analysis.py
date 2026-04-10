"""Stage 3 — Visual Analysis sub-module (Step 3.2).

Responsibilities:
  - GPT-4o Vision API calls for page region detection
  - Response parsing and validation
  - Fallback analysis using adaptive thresholds

Story 41.3 — extracted from stage3_structural_analysis.py
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Visual Analysis Prompt
# ---------------------------------------------------------------------------

_VISUAL_ANALYSIS_PROMPT = """\
Analyze this document page image. Return ONLY valid JSON with:

1. "regions": visual regions with bbox and type
2. For each region: "html_suggestion" (representative HTML snippet)
3. For chart_area: identify "chart_type" (bar|line|pie|doughnut|polarArea) and "confidence" (0-100)
4. For barcode_area: identify "barcode_format" (CODE128|CODE39|EAN13|EAN8|UPC|ITF|MSI) and "confidence" (0-100)
5. For svg_area: identify vector graphics (logos, icons, decorative shapes) and "confidence" (0-100)
6. Compare your visual analysis against this programmatic extraction:
   {extraction_summary}

   Provide a "consistency_score" (0-100).

JSON structure:
{{
  "regions": [
    {{
      "type": "header|body|footer|sidebar|table_area|chart_area|barcode_area|image_area|svg_area",
      "bbox": [x0, y0, x1, y1],
      "description": "brief description of content",
      "html_suggestion": "<suggested HTML for this region>",
      "chart_type": "bar",
      "barcode_format": "CODE128",
      "confidence": 85
    }}
  ],
  "consistency_score": 85,
  "consistency_notes": "brief notes on discrepancies"
}}
"""

VALID_REGION_TYPES = {
    "header",
    "body",
    "footer",
    "sidebar",
    "table_area",
    "chart_area",
    "barcode_area",
    "image_area",
    "svg_area",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _summarize_extraction(page_data: dict[str, Any]) -> str:
    """Build a brief summary of programmatic extraction for the prompt."""
    blocks = page_data.get("text_blocks", [])
    tables = page_data.get("tables", [])
    images = page_data.get("images", [])
    drawn = page_data.get("drawn_elements")

    parts = [f"Text blocks: {len(blocks)}"]
    if tables:
        parts.append(f"Tables: {len(tables)}")
    if images:
        parts.append(f"Images: {len(images)}")
    if drawn and isinstance(drawn, dict) and drawn.get("horizontal_lines"):
        parts.append(f"Horizontal lines: {len(drawn['horizontal_lines'])}")
    return "; ".join(parts)


def _parse_visual_response(raw_json: str) -> dict[str, Any]:
    """Parse GPT-4o JSON response into validated structure."""
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:\w*)\s*\n?", "", raw_json.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return {"regions": [], "consistency_score": 0, "consistency_notes": "parse_error"}

    # Defensive: model returned array directly instead of object
    if isinstance(data, list):
        data = {"regions": data, "consistency_score": 0, "consistency_notes": "auto_wrapped"}

    regions = data.get("regions", [])
    validated_regions = []
    for r in regions:
        if not isinstance(r, dict):
            continue
        rtype = r.get("type", "body")
        if rtype not in VALID_REGION_TYPES:
            rtype = "body"
        bbox = r.get("bbox", [0, 0, 100, 100])
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0, 0, 100, 100]
        validated_regions.append(
            {
                "type": rtype,
                "bbox": [int(v) if isinstance(v, (int, float)) else 0 for v in bbox],
                "description": str(r.get("description", "")),
                "html_suggestion": str(r.get("html_suggestion", "")),
                "chart_type": r.get("chart_type"),
                "barcode_format": r.get("barcode_format"),
                "confidence": r.get("confidence"),
            }
        )

    score = data.get("consistency_score", 0)
    if not isinstance(score, (int, float)):
        score = 0

    return {
        "regions": validated_regions,
        "consistency_score": int(score),
        "consistency_notes": str(data.get("consistency_notes", "")),
    }


def _fallback_visual_analysis(
    page_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate fallback visual analysis using adaptive thresholds.

    Used when GPT-4o Vision is unavailable.
    Top 10% = header, bottom 10% = footer, rest = body.
    """
    page_height = page_data.get("height", 842.0)
    page_width = page_data.get("width", 595.0)

    header_end = int(page_height * 0.10)
    footer_start = int(page_height * 0.90)

    regions = [
        {
            "type": "header",
            "bbox": [0, 0, int(page_width), header_end],
            "description": "Header region (threshold-based)",
            "html_suggestion": "<header></header>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
        {
            "type": "body",
            "bbox": [0, header_end, int(page_width), footer_start],
            "description": "Body region (threshold-based)",
            "html_suggestion": "<main></main>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
        {
            "type": "footer",
            "bbox": [0, footer_start, int(page_width), int(page_height)],
            "description": "Footer region (threshold-based)",
            "html_suggestion": "<footer></footer>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
    ]

    return {
        "regions": regions,
        "consistency_score": 50,
        "consistency_notes": "Fallback: threshold-based zones (no GPT-4o Vision)",
    }


# ---------------------------------------------------------------------------
# Sub-step 3.2 — Visual Analysis (GPT-4o Vision)
# ---------------------------------------------------------------------------


async def _run_3_2(
    clusters: list[dict[str, Any]],
    enriched_documents: list[dict[str, Any]],
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, dict[str, Any]]:
    """Sub-step 3.2 — Visual Analysis.

    1 combined GPT-4o Vision call per representative page.
    MANDATORY but with fallback via handle_service_failure().
    """
    visual_analysis: dict[str, dict[str, Any]] = {}

    # Build page lookup: {pdf_id}:{page_index} -> page_data
    page_lookup: dict[str, dict[str, Any]] = {}
    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            pk = f"{pdf_id}:{page['page_index']}"
            page_lookup[pk] = page

    # Get or create vision client
    vision_client = context.get("vision_client")
    vision_available = vision_client is not None

    if not vision_available:
        import os

        vision_enabled = os.environ.get("VISION_AI_ENABLED", "true").lower() not in ("false", "0", "no", "off")
        if not vision_enabled:
            context.setdefault("_pipeline_warnings", []).append(
                "Vision AI desabilitado via configuração (VISION_AI_ENABLED=false)."
            )
        else:
            try:
                from services.openrouter_client import get_client

                vision_client = get_client()
                vision_available = True
            except (ValueError, ImportError) as e:
                vision_available = False
                context.setdefault("_pipeline_warnings", []).append(
                    f"Vision AI desabilitado: {e}. Análise estrutural rodando em modo fallback (~75% qualidade)."
                )

    api_calls = 0
    api_cost_total = 0.0

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        if cluster_id.startswith("_"):
            continue

        rep = cluster["representative_page"]
        page_key = f"{rep['pdf_id']}:{rep['page_index']}"
        page_data = page_lookup.get(page_key)

        if page_data is None:
            visual_analysis[page_key] = _fallback_visual_analysis({"height": 842.0, "width": 595.0})
            continue

        if not vision_available:
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            continue

        screenshot_path = page_data.get("screenshot_path")
        if not screenshot_path:
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            continue

        # Try GPT-4o Vision call
        image_b64 = None
        try:
            from services.openrouter_client import chat_with_vision, load_image_as_base64

            image_b64 = load_image_as_base64(screenshot_path)
            extraction_summary = _summarize_extraction(page_data)
            prompt = _VISUAL_ANALYSIS_PROMPT.replace("{extraction_summary}", extraction_summary)

            raw_response, call_cost = await chat_with_vision(
                vision_client,
                image_b64=image_b64,
                prompt=prompt,
            )
            result = _parse_visual_response(raw_response)
            api_calls += 1
            api_cost_total += call_cost

            # Determine consistency level
            score = result["consistency_score"]
            if score >= 80:
                result["consistency_level"] = "consistent"
            elif score >= 50:
                result["consistency_level"] = "partial"
            else:
                result["consistency_level"] = "inconsistent"

            visual_analysis[page_key] = result

        except Exception as exc:
            logger.warning("Vision API call failed for %s: %s", page_key, exc)

            # Try handle_service_failure if job is available
            job = context.get("_job")
            if job is not None:
                try:
                    from services.pipeline_orchestrator_v2 import handle_service_failure

                    decision = await handle_service_failure(
                        context=context,
                        service_name="GPT-4o Vision",
                        stage_name="Stage 3.2 Visual Analysis",
                        error=exc,
                        fallback_description="Usar thresholds adaptativos (header 10%, footer 90%)",
                        impact_description="Qualidade reduzida (~75% vs ~95%)",
                        job=job,
                        emit_progress=emit_progress,
                    )
                    if decision == "retry" and image_b64 is not None:
                        # One retry
                        try:
                            from services.openrouter_client import chat_with_vision

                            extraction_summary = _summarize_extraction(page_data)
                            prompt = _VISUAL_ANALYSIS_PROMPT.replace("{extraction_summary}", extraction_summary)
                            raw_response, call_cost = await chat_with_vision(
                                vision_client,
                                image_b64=image_b64,
                                prompt=prompt,
                            )
                            result = _parse_visual_response(raw_response)
                            api_calls += 1
                            api_cost_total += call_cost
                            visual_analysis[page_key] = result
                        except Exception:
                            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
                    else:
                        visual_analysis[page_key] = _fallback_visual_analysis(page_data)
                except Exception:
                    visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            else:
                visual_analysis[page_key] = _fallback_visual_analysis(page_data)

    # Update context with API usage stats
    context["_vision_api_calls"] = context.get("_vision_api_calls", 0) + api_calls
    if api_cost_total > 0:
        context["_vision_api_cost"] = context.get("_vision_api_cost", 0.0) + api_cost_total

    return visual_analysis
