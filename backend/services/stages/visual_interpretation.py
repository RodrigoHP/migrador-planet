"""Stage 21 — Visual Interpretation.

For each representative page that has visual_regions (from Stage 20), sends
the screenshot to GPT-4o again and asks for a richer interpretation of each
region: content description and suggested HTML structure.

The call can be combined with Stage 20 in a single prompt to save API costs;
here we issue a second targeted call so the two stages remain independently
composable.

Reads:
    context["visual_analysis"]      — Dict keyed by "{pdf_index}:{page_number}"
    context["parsed_documents"]     — List[Dict]
    context["job_id"]               — str
    context["vision_client"]        — AsyncOpenAI (optional)

Writes:
    context["visual_analysis"][page_key]["visual_interpretations"]
        — List[Dict] each: { region_type, description, html_suggestion }

Registers itself as Stage 21 (Block 6).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_INTERPRETATION_PROMPT = """\
You are a document-to-HTML conversion assistant. Analyze this document page.

For each visual region you identify, provide a detailed interpretation.

Return ONLY valid JSON with this structure:
{
  "interpretations": [
    {
      "region_type": "table_area",
      "description": "Table with 3 columns: Date, Description, Amount",
      "html_suggestion": "<table><thead><tr><th>Date</th><th>Description</th><th>Amount</th></tr></thead><tbody>...</tbody></table>"
    }
  ]
}

Provide interpretations for: header, body, footer, sidebar, table_area, chart_area, image_area, form_area regions.
Focus on content structure. html_suggestion should be a representative HTML snippet.
"""


def _parse_interpretations(raw_json: str) -> List[Dict[str, Any]]:
    """Parse GPT-4o interpretation response into a list of interpretation dicts."""
    from services.openrouter_client import strip_markdown_fences

    try:
        data = json.loads(strip_markdown_fences(raw_json))
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse interpretation JSON: %s", exc)
        return []

    items = data.get("interpretations", [])
    if not isinstance(items, list):
        return []

    validated = []
    for item in items:
        if not isinstance(item, dict):
            continue
        validated.append(
            {
                "region_type": str(item.get("region_type", "body")),
                "description": str(item.get("description", "")),
                "html_suggestion": str(item.get("html_suggestion", "")),
            }
        )
    return validated


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 21 executor — Visual Interpretation."""
    emit = context.get("emit_progress")

    # Check if Vision AI is enabled
    vision_enabled = os.environ.get("VISION_AI_ENABLED", "true").lower() not in (
        "false", "0", "no", "off"
    )
    if not vision_enabled or context.get("vision_unavailable"):
        if emit:
            try:
                emit({
                    "stage": 21,
                    "stage_name": "Visual Interpretation",
                    "status": "skipped",
                    "warning": "Vision AI desabilitado ou indisponível",
                })
            except Exception:
                pass
        return {"pages_interpreted": 0, "skipped": True}

    visual_analysis: Dict[str, Any] = context.get("visual_analysis", {})
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    job_id: str = context.get("job_id", "unknown")

    pages_interpreted = 0
    api_calls = 0

    # Get or create OpenRouter client
    client = context.get("vision_client")
    if client is None:
        try:
            from services.openrouter_client import get_client
            client = get_client()
        except ValueError as exc:
            logger.warning("Cannot create Vision AI client: %s", exc)
            if emit:
                try:
                    emit({
                        "stage": 21,
                        "stage_name": "Visual Interpretation",
                        "status": "warning",
                        "warning": "Vision AI indisponível, análise apenas por texto",
                    })
                except Exception:
                    pass
            return {"pages_interpreted": 0, "api_error": str(exc)}

    from services.openrouter_client import load_image_as_base64, chat_with_vision

    for page_key, page_data in visual_analysis.items():
        # Skip pages that already have interpretations or are unavailable
        if page_data.get("vision_unavailable"):
            continue
        if page_data.get("visual_interpretations"):
            continue

        # Parse page key to find screenshot
        try:
            pdf_index_str, page_number_str = page_key.split(":", 1)
            pdf_index = int(pdf_index_str)
            page_number = int(page_number_str)
        except (ValueError, AttributeError):
            continue

        screenshot_path = _find_screenshot(job_id, pdf_index, page_number, parsed_documents)

        try:
            image_b64 = load_image_as_base64(screenshot_path)
        except (FileNotFoundError, OSError) as exc:
            logger.warning("Screenshot not found for interpretation %s: %s", page_key, exc)
            page_data["visual_interpretations"] = []
            continue

        try:
            raw_response = await chat_with_vision(
                client,
                image_b64=image_b64,
                prompt=_INTERPRETATION_PROMPT,
            )
            interpretations = _parse_interpretations(raw_response)
            api_calls += 1
        except Exception as exc:
            logger.warning("Vision AI interpretation failed for %s: %s", page_key, exc)
            page_data["visual_interpretations"] = []
            continue

        page_data["visual_interpretations"] = interpretations
        pages_interpreted += 1

    context["visual_analysis"] = visual_analysis
    context["_vision_api_calls"] = context.get("_vision_api_calls", 0) + api_calls

    summary = {
        "pages_interpreted": pages_interpreted,
        "api_calls": api_calls,
    }

    if emit:
        try:
            emit({
                "stage": 21,
                "stage_name": "Visual Interpretation",
                "status": "completed",
                "summary": summary,
            })
        except Exception:
            pass

    return summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_screenshot(
    job_id: str,
    pdf_index: int,
    page_number: int,
    parsed_documents: List[Dict[str, Any]],
) -> str:
    for doc in parsed_documents:
        if doc.get("pdf_index") != pdf_index:
            continue
        for page in doc.get("pages", []):
            if page.get("page_number") == page_number:
                path = page.get("screenshot_path")
                if path:
                    return path
    return f"/tmp/{job_id}/screenshots/page_{pdf_index}_{page_number}.png"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace stub Stage 21 with this implementation."""
    registry.remove_stage(21)
    registry.register_stage(
        stage_number=21,
        name="Visual Interpretation",
        block_id=6,
        estimated_duration=2.0,
        execute_fn=execute,
    )
