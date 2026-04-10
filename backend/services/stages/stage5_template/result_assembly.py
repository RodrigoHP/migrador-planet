"""Stage 5 -- Result Assembly sub-module (Steps 5.6, 5.7).

Responsibilities:
  - Confidence normalization (_normalize_confidence)
  - Pipeline result assembly (_step_5_6_pipeline_result) (G18-G22)
  - Visual data extraction (_extract_visual_data)
  - StorageGateway persistence (_step_5_7_persist)
  - Helpers: _serialise_parsed_documents, _get_document_type, _build_page_config,
    _convert_tree_to_css_coords

Story 41.3 -- extracted from stage5_template_generation.py
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from services.stages.stage5_template.html_helpers import _A4_HEIGHT_PTS, _A4_WIDTH_PTS

logger = logging.getLogger(__name__)

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


def _normalize_confidence(
    confidence_scores: dict[str, Any],
    layout_types: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Normalize ALL confidence factors to 0-100 scale (G18).

    Stage 4 outputs factors as 0.0-1.0 floats. Frontend expects 0-100 integers.
    """
    normalized: dict[str, dict[str, Any]] = {}

    for layout in layout_types:
        layout_id = layout.get("id", "")
        raw = confidence_scores.get(layout_id, {})

        if not raw:
            # Fallback
            normalized[layout_id] = {
                "layout_stability": 50,
                "anchor_detection": 50,
                "grid_quality": 50,
                "field_variability": 50,
                "vision_agreement": 50,
                "overall": 50,
                "status": "review_recommended",
            }
            continue

        entry: dict[str, Any] = {}
        for key in ("layout_stability", "anchor_detection", "grid_quality", "field_variability", "vision_agreement"):
            val = raw.get(key, 0.5)
            # If already 0-100, keep; if 0-1, multiply by 100
            if isinstance(val, (int, float)):
                entry[key] = round(val * 100) if val <= 1.0 else round(val)
            else:
                entry[key] = 50

        overall = raw.get("overall", 0)
        if isinstance(overall, (int, float)):
            entry["overall"] = round(overall) if overall > 1.0 else round(overall * 100)
        else:
            entry["overall"] = 50

        entry["status"] = raw.get("status", "review_recommended")
        normalized[layout_id] = entry

    return normalized


def _serialise_parsed_documents(
    parsed_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a simplified serialisation of parsed_documents."""
    simplified = []
    for doc in parsed_documents:
        pages = []
        for page in doc.get("pages", []):
            pages.append(
                {
                    "page_number": page.get("page_number", page.get("page_index", 0)),
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


def _get_document_type(context: dict[str, Any]) -> str:
    """Detect document type from context or heuristic keyword matching."""
    doc_type = context.get("document_type", "")
    if doc_type:
        return str(doc_type)

    # Keyword matching fallback
    parts: list[str] = []
    for doc in context.get("enriched_documents", []):
        for page in doc.get("pages", []):
            for block in page.get("text_blocks", []):
                text = block.get("text", "")
                if text:
                    parts.append(text)
    all_text = " ".join(parts).lower()

    if any(kw in all_text for kw in ["boleto", "cobranca", "vencimento", "beneficiario", "cedente"]):
        return "boleto-bancario"
    elif any(kw in all_text for kw in ["nota fiscal", "nfe", "cnpj do emitente", "danfe"]):
        return "nota-fiscal"
    elif any(kw in all_text for kw in ["recibo", "comprovante de pagamento"]):
        return "recibo"
    return "documento-geral"


def _build_page_config(
    enriched_documents: list[dict[str, Any]],
    visual_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build page_config for usePagination (G17-S5)."""
    # Detect page size from first representative
    page_w = _A4_WIDTH_PTS
    page_h = _A4_HEIGHT_PTS
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            if page.get("is_representative", True):
                page_w = float(page.get("width", _A4_WIDTH_PTS) or _A4_WIDTH_PTS)
                page_h = float(page.get("height", _A4_HEIGHT_PTS) or _A4_HEIGHT_PTS)
                break
        break

    # Determine size and orientation
    if abs(page_w - 595) < 5 and abs(page_h - 842) < 5:
        size = "A4"
    elif abs(page_w - 612) < 5 and abs(page_h - 792) < 5:
        size = "letter"
    else:
        size = "custom"

    orientation = "landscape" if page_w > page_h else "portrait"

    # Header/footer from visual analysis
    header_h_px = round(1123 * 0.15)
    footer_h_px = round(1123 * 0.10)
    if visual_analysis:
        for page_key, va in visual_analysis.items():
            for region in va.get("regions", []):
                bbox = region.get("bbox")
                if bbox and len(bbox) >= 4:
                    h = abs(float(bbox[3]) - float(bbox[1]))
                    if region.get("type") == "header":
                        header_h_px = round(h)
                    elif region.get("type") == "footer":
                        footer_h_px = round(h)
            break  # use first page

    return {
        "size": size,
        "orientation": orientation,
        "header_height_px": header_h_px,
        "footer_height_px": footer_h_px,
        "margins": {"top": 0, "bottom": 0, "left": 0, "right": 0},
    }


def _convert_tree_to_css_coords(
    tree: dict[str, Any],
    layout: dict[str, Any],
) -> dict[str, Any]:
    """Convert tree node bbox coords to CSS pixels (recursive)."""
    page_h = float(layout.get("page_height_pts", _A4_HEIGHT_PTS))
    page_w = float(layout.get("page_width_pts", _A4_WIDTH_PTS))
    scale_x = 794.0 / page_w
    scale_y = 1123.0 / page_h

    result = dict(tree)
    # Ensure every node has an 'id' (required by frontend TreeNode.id).
    # Prefer block_id when available â€” preserves the field_mappings â†” node link
    # used by session.ts reconcileFieldBindings() to set node.binding + navItem.nodeId.
    # Without this, buildFlatMap() collapses all id-less nodes to key=undefined.
    if not result.get("id"):
        result["id"] = result.get("block_id") or str(uuid.uuid4())
    if "properties" not in result:
        result["properties"] = {}
    bbox = tree.get("bbox")
    if bbox and len(bbox) >= 4:
        try:
            x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            result["properties"] = dict(tree.get("properties", {}))
            result["properties"].update(
                {
                    "x": round(x0 * scale_x, 1),
                    "y": round(y0 * scale_y, 1),
                    "width": round((x1 - x0) * scale_x, 1),
                    "height": round((y1 - y0) * scale_y, 1),
                }
            )
        except (TypeError, ValueError):
            pass

    children = tree.get("children", [])
    if children:
        result["children"] = [_convert_tree_to_css_coords(child, layout) for child in children]
    elif "children" not in result:
        result["children"] = []

    return result


def _step_5_6_pipeline_result(
    context: dict[str, Any],
    html_by_layout: dict[str, str],
    css_global: str,
    coverage_by_layout: dict[str, dict[str, Any]],
    overlay_by_layout: dict[str, list[dict[str, Any]]],
    multi_doc: dict[str, Any],
    anchors_by_layout: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """5.6 â€” Assemble the complete PipelineResult for the frontend.

    Handles G18 (normalized confidence), G19 (enriched layout_types),
    G20 (8 new fields), G21 (monolithic template_draft), G22 (table overlays).
    """
    document_trees = context.get("document_trees", {})
    layout_types = context.get("layout_types", [])
    confidence_scores = context.get("confidence_scores", {})
    enriched_documents = context.get("enriched_documents", [])
    visual_analysis = context.get("visual_analysis")

    # trees_by_layout: hierarchical trees from Stage 3.4 (CSS coords)
    trees_by_layout: dict[str, dict[str, Any]] = {}
    for lt in layout_types:
        layout_id = lt.get("id", "")
        tree = document_trees.get(layout_id)
        if tree:
            trees_by_layout[layout_id] = _convert_tree_to_css_coords(tree, lt)

    # root: backward compat â€” first layout's tree
    first_layout = layout_types[0] if layout_types else None
    first_layout_id = first_layout.get("id") if isinstance(first_layout, dict) else None
    root = trees_by_layout.get(first_layout_id) if first_layout_id else None

    # G18: Normalize ALL confidence factors to 0-100
    normalized_confidence = _normalize_confidence(confidence_scores, layout_types)

    # G19: Enrich layout_types with documentTree, confidence, coverage
    enriched_layout_types = []
    for lt in layout_types:
        layout_id = lt.get("id", "")
        enriched = dict(lt)
        if layout_id in trees_by_layout:
            enriched["documentTree"] = {"root": trees_by_layout[layout_id]}
        if layout_id in coverage_by_layout:
            enriched["coverage"] = coverage_by_layout[layout_id]
        if layout_id in normalized_confidence:
            enriched["confidence"] = normalized_confidence[layout_id]
        # page_count from clusters
        for cluster in context.get("clusters", []):
            if cluster.get("cluster_id") == layout_id:
                enriched["page_count"] = cluster.get("page_count", len(cluster.get("pages", [])))
                break
        enriched_layout_types.append(enriched)

    # G21: monolithic template_draft â€” all layouts concatenated in order (Option B)
    layout_order = [lt.get("id", "") for lt in layout_types if lt.get("id")]
    all_html = "\n".join(html_by_layout[lid] for lid in layout_order if lid in html_by_layout)
    if not all_html and html_by_layout:
        all_html = next(iter(html_by_layout.values()))

    result_json: dict[str, Any] = {
        "document_structure": {
            "pages": _serialise_parsed_documents(context.get("parsed_documents", enriched_documents)),
            "layout_types": enriched_layout_types,
            "root": root,
            "trees_by_layout": trees_by_layout,
        },
        "field_mappings": context.get("field_mappings", []),
        "confidence_scores": normalized_confidence,
        "coverage": coverage_by_layout,
        "layout_types": enriched_layout_types,
        "template_draft": {
            "html": all_html,
            "css": css_global,
        },
        "ambiguous_fields": [m for m in context.get("field_mappings", []) if m.get("is_ambiguous")],
        "format_functions": context.get("format_functions", {}),
        "overlay_items": overlay_by_layout,
        "document_type": _get_document_type(context),
        "document_type_confidence": context.get("document_type_confidence", 0.0),
        "visual_analysis": visual_analysis,
        "intelligence": context.get("intelligence"),
        "validation_result": context.get("validation_result"),
        "block_classifications_confirmed": context.get("block_classifications_confirmed"),
        "multi_doc": multi_doc,
        "page_config": _build_page_config(enriched_documents, visual_analysis),
        "anchors": anchors_by_layout or {},
    }

    # Story 38.5: Include synthetic data generated from XSD field_tree
    field_tree_dict = context.get("field_tree")
    if field_tree_dict and isinstance(field_tree_dict, dict):
        try:
            from services.xsd_synthetic_generator import XSDSyntheticGenerator

            gen = XSDSyntheticGenerator(seed=42)
            result_json["synthetic_data"] = gen.generate_from_dict(field_tree_dict)
            result_json["synthetic_exemplo_js"] = gen.generate_exemplo_js_from_dict(field_tree_dict)
            logger.info("[Stage 5] Synthetic data generated from XSD field_tree")
        except Exception as exc:
            logger.warning("[Stage 5] Synthetic data generation failed (non-blocking): %s", exc)
            result_json["synthetic_data"] = None
            result_json["synthetic_exemplo_js"] = None
    else:
        result_json["synthetic_data"] = None
        result_json["synthetic_exemplo_js"] = None

    return result_json


# ---------------------------------------------------------------------------
# 5.7 Persistence
# ---------------------------------------------------------------------------


def _extract_visual_data(context: dict[str, Any]) -> dict:
    """Extract drawn_elements and text_blocks from enriched_documents for persistence."""
    pages: list[dict] = []
    for doc in context.get("enriched_documents", []):
        for page in doc.get("pages", []):
            pages.append(
                {
                    "page_index": page.get("page_index"),
                    "cluster_id": page.get("cluster_id"),
                    "drawn_elements": page.get("drawn_elements"),
                    "text_blocks": page.get("text_blocks"),
                }
            )
    return {"pages": pages}


async def _step_5_7_persist(
    context: dict[str, Any],
    result_json: dict[str, Any],
    emit_progress: EmitProgressFn,
    *,
    _retry_count: int = 0,
    max_retries: int = 3,
) -> None:
    """5.7 â€” Persist result_json via StorageGateway with handle_service_failure."""
    storage = context.get("_storage")
    job_id = context.get("job_id", "")

    if not storage or not job_id:
        logger.info("[Stage 5] No storage or job_id â€” skipping persistence (dev/local)")
        return

    try:
        await storage.save_result(job_id, result_json)
        logger.info("[Stage 5] Result persisted for job %s", job_id)

        # Save visual data (auxiliary â€” non-blocking)
        try:
            visual_data = _extract_visual_data(context)
            if visual_data["pages"]:
                await storage.save_visual_data(job_id, visual_data)
                logger.info("[Stage 5] Visual data persisted for job %s", job_id)
        except Exception as vd_exc:
            logger.warning("[Stage 5] Visual data persistence failed (non-blocking): %s", vd_exc)
    except Exception as exc:
        logger.error("[Stage 5] Persistence failed: %s", exc)
        # Use handle_service_failure if job context available
        job = context.get("_job")
        if job and emit_progress is not None:
            from services.pipeline_orchestrator_v2 import handle_service_failure

            decision = await handle_service_failure(
                context=context,
                service_name="Storage",
                stage_name="Template Generation",
                error=exc,
                fallback_description="Continuar sem salvar â€” resultado ficara apenas em memoria",
                impact_description="Se a sessao for encerrada, o resultado sera perdido",
                job=job,
                emit_progress=emit_progress,
                timeout=300,
            )
            if decision == "retry":
                if _retry_count >= max_retries:
                    logger.error(
                        "[Stage 5] Persistence max retries (%d) reached â€” giving up",
                        max_retries,
                    )
                else:
                    await _step_5_7_persist(
                        context,
                        result_json,
                        emit_progress,
                        _retry_count=_retry_count + 1,
                        max_retries=max_retries,
                    )
            # else: operator accepted fallback â€” continue without persistence
        else:
            # No job context for checkpoint â€” log warning and continue
            logger.warning(
                "[Stage 5] Persistence failed and no checkpoint available â€” result remains in memory only: %s",
                exc,
            )


# ---------------------------------------------------------------------------
# Main orchestrator: run_stage5
# ---------------------------------------------------------------------------
