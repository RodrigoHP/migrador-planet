"""Stage 5 — Template Generation (Tree-Driven HTML + CSS-from-Extraction).

Story 13.10 — Generates hierarchical HTML from document_trees (Stage 3),
CSS from extracted visual data (fonts, colors, drawn_elements, visual_regions),
multidimensional coverage, per-layout overlays, VariationMatrix, and assembles
the complete PipelineResult for the frontend editor.

7 sub-steps:
  5.1 Tree-Driven HTML (walk document_trees -> hierarchical HTML)
  5.2 CSS-from-Extraction (fonts, colors, borders, backgrounds, zones)
  5.3 Coverage Calculation (fields 60% + tables 25% + images 15%)
  5.4 Overlay Items (per-layout, filtered by layout_type_id)
  5.5 VariationMatrix Assembly (variant + present_in_pdfs)
  5.6 PipelineResult Assembly (G18-G22, full contract)
  5.7 Persistence (StorageGateway with handle_service_failure)

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 8
Output contract: Section 3.5

Story 41.3 — Decomposed into sub-modules under stage5_template/.
This file is now a thin orchestrator + backward-compatible re-exports.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from models.pipeline_context import FieldMappingEntry, LayoutTypeInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Re-exports — backward compatibility for tests and other imports
# ---------------------------------------------------------------------------

from services.stages.stage5_template.coverage_overlay import (  # noqa: E402, F401
    _add_table_container_overlays,
    _count_mapped_charts,
    _count_mapped_tables,
    _count_nodes_by_type,
    _generate_anchors,
    _get_page_dimensions,
    _step_5_3_coverage,
    _step_5_4_overlay_items,
)
from services.stages.stage5_template.css_generation import (  # noqa: E402, F401
    _step_5_2_css_from_extraction,
)
from services.stages.stage5_template.html_helpers import (  # noqa: E402, F401
    _A4_HEIGHT_PTS,
    _A4_WIDTH_PTS,
    _BASE_CSS_RESET,
    _SCALE_X,
    _SCALE_Y,
    _barcode_placeholder_html,
    _barcode_to_svg_content,
    _bbox_to_absolute_style,
    _color_int_to_hex,
    _font_class_with_style,
    _generate_field_html,
    _generate_table_html,
    _is_array_field,
    _node_is_array,
    _sanitize_font_class,
    _sanitize_name,
)
from services.stages.stage5_template.html_tree import (  # noqa: E402, F401
    _step_5_1_tree_driven_html,
    _tree_to_html,
)
from services.stages.stage5_template.result_assembly import (  # noqa: E402, F401
    _build_page_config,
    _convert_tree_to_css_coords,
    _extract_visual_data,
    _get_document_type,
    _normalize_confidence,
    _serialise_parsed_documents,
    _step_5_6_pipeline_result,
    _step_5_7_persist,
)
from services.stages.stage5_template.variation_matrix import (  # noqa: E402, F401
    _step_5_5_variation_matrix,
)

# ===========================================================================
# MAIN ENTRY POINT
# ===========================================================================


async def run_stage5(
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, Any]:
    """Stage 5: Template Generation — 7 sub-steps.

    Reads:
        context["document_trees"], context["intelligence"],
        context["visual_analysis"], context["enriched_documents"],
        context["field_mappings"], context["field_tree"],
        context["layout_types"], context["clusters"],
        context["confidence_scores"], context["validation_result"],
        context["block_classifications_confirmed"],
        context["format_functions"], context["pdf_documents"],
        context["_storage"], context["job_id"]

    Writes:
        context["result_json"], context["stage_5_result"]
    """
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    stage = 5
    name = "Template Generation"
    context["_current_stage"] = stage
    context["_current_stage_name"] = name

    # Read inputs
    document_trees: dict[str, dict[str, Any]] = context.get("document_trees", {})

    intelligence = context.get("intelligence", {})
    enriched_documents = context.get("enriched_documents", [])
    visual_analysis = context.get("visual_analysis")
    raw_field_mappings = context.get("field_mappings", [])
    field_mappings: list[FieldMappingEntry] = [FieldMappingEntry.model_validate(m) for m in raw_field_mappings]
    field_tree = context.get("field_tree")
    raw_layout_types = context.get("layout_types", [])
    layout_types: list[LayoutTypeInfo] = [LayoutTypeInfo.model_validate(lt) for lt in raw_layout_types]
    clusters = context.get("clusters", [])
    pdf_documents = context.get("pdf_documents", [])

    # --- 5.2 CSS-from-Extraction (run before 5.1 to produce class maps) ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.10),
            sub_step="5.2 CSS-from-Extraction",
            sub_progress_pct=0.10,
        )
    )

    css_global, border_class_map, bg_class_map = _step_5_2_css_from_extraction(
        enriched_documents,
        visual_analysis,
        layout_types,
    )
    logger.info(
        "[Stage 5] 5.2 CSS generated: %d chars, %d border classes, %d bg classes",
        len(css_global),
        len(border_class_map),
        len(bg_class_map),
    )

    # --- 5.1 Tree-Driven HTML (uses class maps from 5.2) ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.30),
            sub_step="5.1 Tree-Driven HTML",
            sub_progress_pct=0.30,
        )
    )

    html_by_layout = _step_5_1_tree_driven_html(
        document_trees,
        field_mappings,
        field_tree,
        layout_types,
        border_class_map,
        bg_class_map,
    )
    logger.info(
        "[Stage 5] 5.1 HTML generated for %d layouts, sizes: %s",
        len(html_by_layout),
        {k: len(v) for k, v in html_by_layout.items()},
    )

    # --- 5.3 Coverage ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.50),
            sub_step="5.3 Coverage Calculation",
            sub_progress_pct=0.50,
        )
    )

    # Story 48.6: pass list_bindings to coverage calculation (AC5)
    list_bindings_raw: list[dict[str, Any]] = context.get("list_bindings", [])
    coverage_by_layout = _step_5_3_coverage(
        field_mappings,
        field_tree,
        document_trees,
        layout_types,
        list_bindings=list_bindings_raw,
    )
    logger.info("[Stage 5] 5.3 Coverage: %s", coverage_by_layout)

    # --- 5.4 Overlay Items ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.60),
            sub_step="5.4 Overlay Items",
            sub_progress_pct=0.60,
        )
    )

    overlay_by_layout = _step_5_4_overlay_items(
        field_mappings,
        layout_types,
        enriched_documents,
        document_trees,
    )
    anchors_by_layout = _generate_anchors(overlay_by_layout)
    logger.info(
        "[Stage 5] 5.4 Overlays: %s, Anchors: %s",
        {k: len(v) for k, v in overlay_by_layout.items()},
        {k: len(v) for k, v in anchors_by_layout.items()},
    )

    # --- 5.5 VariationMatrix ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.70),
            sub_step="5.5 VariationMatrix",
            sub_progress_pct=0.70,
        )
    )

    multi_doc = _step_5_5_variation_matrix(
        intelligence,
        clusters,
        layout_types,
        pdf_documents,
        enriched_documents,
    )
    logger.info(
        "[Stage 5] 5.5 VariationMatrix: %d pdfs, %d detections",
        len(multi_doc.get("pdfs", [])),
        len(multi_doc.get("detections", [])),
    )

    # --- 5.6 PipelineResult Assembly ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.85),
            sub_step="5.6 PipelineResult Assembly",
            sub_progress_pct=0.85,
        )
    )

    result_json = _step_5_6_pipeline_result(
        context,
        html_by_layout,
        css_global,
        coverage_by_layout,
        overlay_by_layout,
        multi_doc,
        anchors_by_layout,
    )
    context["result_json"] = result_json

    # --- 5.7 Persistence ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.95),
            sub_step="5.7 Persistence",
            sub_progress_pct=0.95,
        )
    )

    await _step_5_7_persist(context, result_json, emit_progress)

    # --- Done ---
    context["stage_5_result"] = {
        "template_draft": result_json.get("template_draft", {}),
        "coverage": coverage_by_layout,
        "overlay_count": sum(len(v) for v in overlay_by_layout.values()),
        "multi_doc_pdfs": len(multi_doc.get("pdfs", [])),
    }

    logger.info(
        "[Stage 5] Complete: html=%d chars, css=%d chars, layouts=%d",
        len(result_json.get("template_draft", {}).get("html", "")),
        len(result_json.get("template_draft", {}).get("css", "")),
        len(layout_types),
    )

    # Emit final summary for the accordion
    real_layout_types = [lt for lt in layout_types if not str(lt.cluster_id).startswith("_")]
    overlay_count = sum(len(v) for v in overlay_by_layout.values())
    html_size = len(result_json.get("template_draft", {}).get("html", ""))
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 1.0),
            sub_step="5.7 Persistence",
            sub_progress_pct=1.0,
            summary={
                "layouts_detected": len(real_layout_types),
                "fields_mapped": overlay_count,
                "html_size_bytes": html_size,
            },
        )
    )

    return context
