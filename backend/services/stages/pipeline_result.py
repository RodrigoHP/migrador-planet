"""Stage 28 — Pipeline Result Consolidation.

Consolidates all upstream stage outputs into a single canonical result_json
that matches the agreed-upon schema. Optionally persists the result to the
Supabase ``jobs`` table via ``context["supabase_client"]``.

Schema of result_json:
    {
      "document_structure": {
          "pages": <simplified serialisation of parsed_documents>,
          "layout_types": <list[dict]>,
          "root": <DocumentTree root TreeNode | null>
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
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


# Mapping from semantic_label (backend) to NodeType (frontend)
_LABEL_TO_NODE_TYPE: Dict[str, str] = {
    "header": "header",
    "footer_text": "footer",
    "page_number": "footer",
    "title": "section",
    "table_header": "table",
    "table_cell": "table",
    "value": "text",
    "field": "field",
    "image": "image",
}


def _bbox_to_layout(bbox) -> Dict[str, Optional[float]]:
    """Convert a (x0, y0, x1, y1) bbox tuple/list to x/y/width/height dict.

    Returns a dict with None values when bbox is absent or malformed.
    """
    if bbox and len(bbox) == 4:
        x0, y0, x1, y1 = bbox
        return {
            "x": round(float(x0), 2),
            "y": round(float(y0), 2),
            "width": round(float(x1 - x0), 2),
            "height": round(float(y1 - y0), 2),
        }
    return {"x": None, "y": None, "width": None, "height": None}


def _build_document_tree_root(
    parsed_documents: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Build a DocumentTree root node from parsed_documents.

    Returns a TreeNode-compatible dict (type='document') with one child per
    page.  Each page node contains children derived from the text_blocks'
    semantic_label.  Returns None when parsed_documents is empty.
    """
    if not parsed_documents:
        return None

    page_nodes: List[Dict[str, Any]] = []

    for doc in parsed_documents:
        pdf_name: str = doc.get("pdf_name", "document")
        for page in doc.get("pages", []):
            page_number: int = page.get("page_number", 0)
            page_node_id = f"page-{doc.get('pdf_index', 0)}-{page_number}"
            # Use 1-based display number: page_number from PyMuPDF is 0-indexed.
            display_number = page_number + 1

            block_nodes: List[Dict[str, Any]] = []
            for block in page.get("text_blocks", []):
                label: str = block.get("semantic_label", "value")
                node_type: str = _LABEL_TO_NODE_TYPE.get(label, "text")
                text: str = block.get("text", "")
                block_id: str = block.get("id") or str(uuid.uuid4())

                layout = _bbox_to_layout(block.get("bbox"))
                block_nodes.append(
                    {
                        "id": f"block-{block_id}",
                        "type": node_type,
                        "name": text[:60] if text else label,
                        "binding": None,
                        "isOptional": False,
                        "children": [],
                        "properties": {
                            "semantic_label": label,
                            "text": text,
                            # Layout coordinates (mapped from bbox for ElementInspector)
                            "x": layout["x"],
                            "y": layout["y"],
                            "width": layout["width"],
                            "height": layout["height"],
                            # Typography (from PyMuPDF span extraction)
                            "font_family": block.get("font_name") or None,
                            "font_size": block.get("font_size") or None,
                        },
                        "visibility": True,
                    }
                )

            page_nodes.append(
                {
                    "id": page_node_id,
                    "type": "section",
                    "name": f"Página {display_number}",
                    "binding": None,
                    "isOptional": False,
                    "children": block_nodes,
                    "properties": {
                        "page_number": page_number,
                        "pdf_name": pdf_name,
                    },
                    "visibility": True,
                }
            )

    if not page_nodes:
        return None

    return {
        "id": "document-root",
        "type": "document",
        "name": "Document",
        "binding": None,
        "isOptional": False,
        "children": page_nodes,
        "properties": {},
        "visibility": True,
    }


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
    """Return confidence scores keyed by layoutId (frontend-compatible format).

    Frontend expects: Record<layoutId, ConfidenceFactors> where ConfidenceFactors has
    {layout_stability, anchor_detection, grid_quality, field_variability, vision_agreement, overall}.

    Backend Stage 25 writes: {factors: {layout_stability, ...}, global_score: float, ...}
    This function transforms the flat backend structure into the layout-keyed frontend format.
    """
    # Prefer the key written by Stage 25 (confidence_scores)
    raw = context.get("confidence_scores")
    if not raw:
        # Legacy key used in earlier stories
        confidence_result = context.get("confidence_result") or {}
        raw = confidence_result.get("scores", {})

    # Build frontend-compatible ConfidenceFactors entry from the raw Stage 25 structure.
    # Stage 25 outputs: {"factors": {layout_stability, ...}, "global_score": float, ...}
    # If raw already looks like the keyed format (e.g. from a saved project), return as-is.
    if raw and "factors" in raw:
        factors = raw.get("factors", {})
        global_score: float = raw.get("global_score", raw.get("local_weighted_average", 0.0))
        confidence_entry = {
            "layout_stability": factors.get("layout_stability", 0.5),
            "anchor_detection": factors.get("anchor_detection", 0.5),
            "grid_quality": factors.get("grid_quality", 0.5),
            "field_variability": factors.get("field_variability", 0.5),
            "vision_agreement": factors.get("vision_agreement", 0.5),
            # Frontend reads .overall as a 0-100 integer; Stage 25 uses 0-1 float
            "overall": round(global_score * 100),
        }
    elif raw:
        # Already keyed by layoutId (saved-project format or future format) — return as-is
        return raw
    else:
        confidence_entry = {
            "layout_stability": 0.5,
            "anchor_detection": 0.5,
            "grid_quality": 0.5,
            "field_variability": 0.5,
            "vision_agreement": 0.5,
            "overall": 50,
        }

    # Key by each layout_type id so frontend confidenceByLayout.get(activeLayoutId) works.
    layout_types: List[Dict[str, Any]] = context.get("layout_types") or []
    if layout_types:
        return {lt.get("id", f"layout-{i}"): confidence_entry for i, lt in enumerate(layout_types)}
    # Fallback: no layout types yet — use "global" so at least something is stored
    return {"global": confidence_entry}


def _get_coverage(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return coverage keyed by layoutId (frontend-compatible format).

    Frontend expects: Record<layoutId, CoverageData> where CoverageData has
    {fields: {mapped, total}, tables: {...}, images: {...}, charts: {...}, percentage: number}.

    Backend Stage 27 writes: {fields: {mapped, total}} inside template_draft["coverage"].
    """
    template_draft = context.get("template_draft") or {}
    raw_coverage = template_draft.get("coverage", {})

    fields_data: Dict[str, Any] = raw_coverage.get("fields", {})
    mapped: int = fields_data.get("mapped", 0)
    total: int = fields_data.get("total", 0)
    percentage: int = round(mapped / total * 100) if total > 0 else 0

    coverage_entry = {
        "fields": {"mapped": mapped, "total": total},
        "tables": {"mapped": 0, "total": 0},
        "images": {"mapped": 0, "total": 0},
        "charts": {"mapped": 0, "total": 0},
        "percentage": percentage,
    }

    layout_types: List[Dict[str, Any]] = context.get("layout_types") or []
    if layout_types:
        return {lt.get("id", f"layout-{i}"): coverage_entry for i, lt in enumerate(layout_types)}
    return {"global": coverage_entry}


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
            "root": _build_document_tree_root(parsed_documents),
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
