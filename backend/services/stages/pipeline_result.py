"""Stage 28 — Pipeline Result Consolidation.

Consolidates all upstream stage outputs into a single canonical result_json
that matches the agreed-upon schema. Optionally persists the result to the
Supabase ``jobs`` table via ``context["supabase_client"]``.

Schema of result_json:
    {
      "document_structure": {
          "pages": <simplified serialisation of parsed_documents>,
          "layout_types": <list[dict]>
      },
      "field_mappings": <list[dict]>,
      "confidence_scores": <dict>,
      "coverage": <dict>,
      "layout_types": <list[dict]>,
      "template_draft": {"html": str, "css": str},
      "ambiguous_fields": <list[dict]>,  # only is_ambiguous==True
      "format_functions": <list or dict>,
    }

Reads:
    context["parsed_documents"]  — optional
    context["layout_types"]      — optional
    context["field_mappings"]    — optional
    context["confidence_result"] — optional (legacy key)
    context["confidence_scores"] — optional (preferred key from Stage 25)
    context["template_draft"]    — optional (from Stage 27)
    context["format_functions"]  — optional (from Stage 24)
    context["supabase_client"]   — optional; used to persist result_json
    context["job_id"]            — optional; used as Supabase row key

Writes:
    context["result_json"]  — the canonical result dict

Registers itself as Stage 28 (Block 8).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _serialise_parsed_documents(parsed_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a simplified (non-binary) serialisation of parsed_documents."""
    simplified = []
    for doc in parsed_documents:
        pages = []
        for page in doc.get("pages", []):
            pages.append(
                {
                    "page_number": page.get("page_number"),
                    "block_count": len(page.get("text_blocks", [])),
                    "image_count": len(page.get("images", [])),
                }
            )
        simplified.append(
            {
                "pdf_name": doc.get("pdf_name", ""),
                "pdf_index": doc.get("pdf_index", 0),
                "page_count": len(pages),
                "pages": pages,
            }
        )
    return simplified


def _get_confidence_scores(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return confidence scores dict, supporting both legacy and current keys."""
    # Prefer the key written by Stage 25 (confidence_scores)
    scores = context.get("confidence_scores")
    if scores:
        return scores
    # Legacy key used in earlier stories
    confidence_result = context.get("confidence_result") or {}
    return confidence_result.get("scores", {})


def _get_coverage(context: Dict[str, Any]) -> Dict[str, Any]:
    template_draft = context.get("template_draft") or {}
    return template_draft.get("coverage", {})


def _get_template_draft_output(context: Dict[str, Any]) -> Dict[str, str]:
    template_draft = context.get("template_draft") or {}
    return {
        "html": template_draft.get("html", ""),
        "css": template_draft.get("css", ""),
    }


def _get_ambiguous_fields(field_mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [m for m in field_mappings if m.get("is_ambiguous")]


# ---------------------------------------------------------------------------
# Supabase persistence (optional, fail-safe)
# ---------------------------------------------------------------------------


async def _persist_to_supabase(
    supabase_client: Any,
    job_id: str,
    result_json: Dict[str, Any],
) -> None:
    """Attempt to persist result_json to Supabase jobs table. Never raises."""
    try:
        import json

        payload = {"result_json": json.dumps(result_json)}
        # Supabase Python client pattern: table("jobs").update(payload).eq("id", job_id).execute()
        response = (
            supabase_client.table("jobs")
            .update(payload)
            .eq("id", job_id)
            .execute()
        )
        logger.debug("Supabase update response: %s", response)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase persist failed (ignored): %s", exc)


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 28 executor — Pipeline Result Consolidation."""
    emit = context.get("emit_progress")

    if emit:
        try:
            emit(
                {
                    "stage": 28,
                    "stage_name": "Pipeline Result",
                    "status": "running",
                    "summary": {},
                }
            )
        except Exception:  # noqa: BLE001
            pass

    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents") or []
    layout_types: List[Dict[str, Any]] = context.get("layout_types") or []
    field_mappings: List[Dict[str, Any]] = context.get("field_mappings") or []
    format_functions = context.get("format_functions") or {}

    result_json: Dict[str, Any] = {
        "document_structure": {
            "pages": _serialise_parsed_documents(parsed_documents),
            "layout_types": layout_types,
        },
        "field_mappings": field_mappings,
        "confidence_scores": _get_confidence_scores(context),
        "coverage": _get_coverage(context),
        "layout_types": layout_types,
        "template_draft": _get_template_draft_output(context),
        "ambiguous_fields": _get_ambiguous_fields(field_mappings),
        "format_functions": format_functions,
    }

    context["result_json"] = result_json

    # Optional Supabase persistence
    supabase_client = context.get("supabase_client")
    job_id: str = context.get("job_id", "")
    if supabase_client and job_id:
        await _persist_to_supabase(supabase_client, job_id, result_json)

    summary = {
        "field_mappings_count": len(field_mappings),
        "ambiguous_count": len(result_json["ambiguous_fields"]),
        "has_template_draft": bool(result_json["template_draft"]["html"]),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 28,
                    "stage_name": "Pipeline Result",
                    "status": "completed",
                    "summary": summary,
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return summary


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace stub Stage 28 with this implementation."""
    registry.remove_stage(28)
    registry.register_stage(
        stage_number=28,
        name="Pipeline Result",
        block_id=8,
        estimated_duration=0.5,
        execute_fn=execute,
    )
