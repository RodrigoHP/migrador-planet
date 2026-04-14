"""Stage 4 — Field Mapping (Batch LLM + Two-Pass + Section Scoping).

Story 13.8 — Maps PDF fields to XSD paths via batch LLM, section scoping,
two-pass disambiguation, and heuristic confidence scoring.

7 sub-steps:
  4.1 XSD Parsing (lxml — reuses xsd_parser.py)
  4.2 Pair Validation (consume Stage 3.3 field_pair, pair remaining)
  4.3 Format Pre-Detection (regex BEFORE matching — enriches LLM prompt)
  4.4 Section-XSD Matching (fuzzy match sections to XSD complex nodes)
  4.5 Batch Field Matching (1 Gemini Flash call per layout, two-pass)
  4.6 Confidence Scoring (5 heuristic factors, per-layout)
  4.7 Consistency Validation (orphans, unmapped required, type-format)

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 7b
Output contract: Section 3.4

Story 41.3 — Decomposed into sub-modules under stage4_mapping/.
This file is now a thin orchestrator + backward-compatible re-exports.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Re-exports — backward compatibility for tests and other imports
# ---------------------------------------------------------------------------

from services.stages.stage4_mapping.scoring_validation import (  # noqa: E402, F401
    _TYPE_FORMAT_COMPAT,
    THRESHOLD_APPROVED,
    THRESHOLD_REVIEW,
    WEIGHTS,
    _get_anchor_detection,
    _get_field_variability,
    _get_grid_quality,
    _get_layout_stability,
    _get_required_paths,
    _get_vision_agreement,
    _step_4_6_confidence_scoring,
    _step_4_7_consistency_validation,
    _validate_type_format,
)
from services.stages.stage4_mapping.section_matching import (  # noqa: E402, F401
    AMBIGUITY_THRESHOLD,
    GEMINI_FLASH_MODEL,
    HIGH_CONFIDENCE_THRESHOLD,
    SECTION_MATCH_MIN_SCORE,
    _extract_sections,
    _fuzzy_batch_match,
    _fuzzy_match_single,
    _get_complex_nodes,
    _get_pair_section,
    _get_xsd_type,
    _group_pairs_by_section,
    _llm_batch_match_scoped,
    _make_mapping_v2,
    _section_xsd_similarity,
    _step_4_4_section_xsd_matching,
    _step_4_5_field_matching,
)
from services.stages.stage4_mapping.xsd_integration import (  # noqa: E402, F401
    _FORMAT_PATTERNS,
    _JS_FUNCTIONS,
    _detect_format,
    _find_nearest_label_block,
    _get_block_bbox,
    _get_block_info,
    _get_block_text,
    _step_4_1_xsd_parsing,
    _step_4_2_pair_validation,
    _step_4_3_format_pre_detection,
)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════


async def run_stage4(
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, Any]:
    """Stage 4: Field Mapping — 7 sub-steps."""
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    stage = 4
    name = "Field Mapping"
    context["_current_stage"] = stage
    context["_current_stage_name"] = name

    intelligence = context.get("intelligence", {})
    clusters = context.get("clusters", [])
    visual_analysis = context.get("visual_analysis", {})
    document_trees: dict[str, dict[str, Any]] = context.get("document_trees", {})

    import os

    api_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_client = context.get("openrouter_client")
    if api_key and openrouter_client is None:
        try:
            from services.openrouter_client import get_client

            openrouter_client = get_client(api_key=api_key)
        except Exception as exc:
            logger.warning("Cannot create OpenRouter client: %s. Using fuzzy fallback.", exc)
            openrouter_client = None

    # --- 4.1 XSD Parsing ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.05),
            sub_step="4.1 XSD Parsing",
            sub_progress_pct=0.05,
        )
    )

    field_tree = _step_4_1_xsd_parsing(context)
    context["field_tree"] = field_tree

    # --- 4.2 Pair Validation ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.15),
            sub_step="4.2 Pair Validation",
            sub_progress_pct=0.15,
        )
    )

    validated_pairs = _step_4_2_pair_validation(context)

    # --- 4.3 + 4.4 ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.30),
            sub_step="4.3 Format Pre-Detection + 4.4 Section-XSD Matching",
            sub_progress_pct=0.30,
        )
    )

    validated_pairs, format_functions = _step_4_3_format_pre_detection(validated_pairs)
    context["format_functions"] = format_functions

    section_xsd_map = _step_4_4_section_xsd_matching(document_trees, field_tree)

    # --- 4.5 Batch Field Matching ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.55),
            sub_step="4.5 Batch Field Matching",
            sub_progress_pct=0.55,
        )
    )

    _fm_typed, ambiguous_fields, confirmations = await _step_4_5_field_matching(
        validated_pairs,
        field_tree,
        intelligence,
        section_xsd_map,
        document_trees,
        openrouter_client,
    )
    # Story 42.6: serialize FieldMappingEntry objects to plain dicts at context boundary
    # (downstream stages 4.6, 4.7 and stage 5 consume plain dicts)
    field_mappings = [m.model_dump() for m in _fm_typed]
    context["field_mappings"] = field_mappings
    context["ambiguous_fields"] = ambiguous_fields
    context["block_classifications_confirmed"] = confirmations

    # --- 4.5b List Binding (Story 48.5) ---
    from services.stages.stage4_mapping.list_binding import run_list_binding

    list_bindings = run_list_binding(document_trees, field_tree)
    if list_bindings:
        logger.info("Step 4.5b: %d ListBinding(s) gerado(s)", len(list_bindings))
        context["list_bindings"] = [lb.model_dump() for lb in list_bindings]
    else:
        context["list_bindings"] = []

    # --- 4.6 + 4.7 ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.80),
            sub_step="4.6 Confidence Scoring + 4.7 Consistency Validation",
            sub_progress_pct=0.80,
        )
    )

    confidence_scores = _step_4_6_confidence_scoring(
        field_mappings,
        intelligence,
        visual_analysis,
        clusters,
    )
    context["confidence_scores"] = confidence_scores

    validation_result = _step_4_7_consistency_validation(
        field_mappings,
        field_tree,
        intelligence,
    )
    context["validation_result"] = validation_result

    mapping_stats: dict[str, dict[str, Any]] = {}
    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        layout_mappings = [m for m in field_mappings if m.get("layout_type_id") == layout_id]
        total = len(layout_mappings)
        mapped = len([m for m in layout_mappings if m.get("xsd_field_path")])
        accuracy_est = round(mapped / max(total, 1), 4)
        mapping_stats[layout_id] = {
            "total_fields": total,
            "mapped_fields": mapped,
            "accuracy_estimate": accuracy_est,
        }

    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="completed",
            progress_pct=compute_overall_progress(stage, 1.0),
            sub_step="4.7 Done",
            sub_progress_pct=1.0,
            summary={
                "total_mappings": len(field_mappings),
                "ambiguous_count": len(ambiguous_fields),
                "confirmations": len(confirmations),
                "warnings": len(validation_result.get("warnings", [])),
                "errors": len(validation_result.get("errors", [])),
                "list_bindings": len(context.get("list_bindings", [])),
            },
        )
    )

    context["stage_4_result"] = {
        "field_mappings": field_mappings,
        "confidence_scores": confidence_scores,
        "validation_result": validation_result,
        "mapping_stats": mapping_stats,
    }

    return context
