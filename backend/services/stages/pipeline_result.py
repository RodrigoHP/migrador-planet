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

            block_nodes: List[Dict[str, Any]] = []
            for block in page.get("text_blocks", []):
                label: str = block.get("semantic_label", "value")
                node_type: str = _LABEL_TO_NODE_TYPE.get(label, "text")
                text: str = block.get("text", "")
                block_id: str = block.get("id") or str(uuid.uuid4())
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
                            "bbox": block.get("bbox"),
                        },
                        "visibility": True,
                    }
                )

            page_nodes.append(
                {
                    "id": page_node_id,
                    "type": "section",
                    "name": f"{pdf_name} — p{page_number}",
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
