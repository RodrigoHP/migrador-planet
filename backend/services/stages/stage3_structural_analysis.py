"""Stage 3 — Structural Analysis (NER + GPT-4o Vision + Hierarchy).

Story 13.7 — Classifies blocks (label/dynamic), detects visual regions,
pairs label-value, and builds hierarchical document trees.

4 sub-steps:
  3.1 Multi-Example Analysis (statistical + regex + spaCy NER)
  3.2 Visual Analysis (GPT-4o Vision, 1 combined call per representative)
  3.3 Semantic Classification + Label-Value Pairing
  3.4 Hierarchy Builder (4 signals cascade)

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 7
Output contract: Section 3.3

Story 41.3 — Decomposed into sub-modules under stage3_structural/.
This file is now a thin orchestrator + backward-compatible re-exports.
"""

from __future__ import annotations

import asyncio
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

from services.stages.stage3_structural.constants import (  # noqa: E402, F401
    _COMPILED_DYNAMIC_PATTERNS,
    _DYNAMIC_PATTERNS,
)
from services.stages.stage3_structural.multi_example_analysis import (  # noqa: E402, F401
    _get_nlp,
    _run_3_1,
    _smart_classify,
)

# Backward-compat: tests patch `stage3_structural_analysis._nlp` directly.
# _get_nlp() checks this attribute via sys.modules for the mock to take effect.
_nlp = None
from services.stages.stage3_structural.classification import (  # noqa: E402, F401
    _find_adjacent_value,
    _find_position_match,
    _get_visual_zone,
    _get_zone_by_threshold,
    _run_3_3,
)
from services.stages.stage3_structural.section_utils import (  # noqa: E402, F401
    _assign_images_to_sections,
    _assign_tables_to_sections,
    _assign_visual_elements_to_sections,
    _barcode_bboxes_from_tree,
    _bbox_contains,
    _extract_barcode_value,
    _get_horizontal_separators,
    _line_inside_any_barcode,
    _split_by_drawn_lines,
    _split_by_gap,
    _zones_from_thresholds,
    _zones_from_visual_regions,
)
from services.stages.stage3_structural.semantic_utils import (  # noqa: E402, F401
    _apply_suggested_bindings,
    _extract_semantic_name,
    _get_conditional_pdfs,
    _infer_section_name,
    _levenshtein_similarity,
    _normalize_text,
    _section_variant,
    _suggest_xsd_binding,
)
from services.stages.stage3_structural.tree_builder import (  # noqa: E402, F401
    _build_tree,
    _run_3_4,
)
from services.stages.stage3_structural.visual_analysis import (  # noqa: E402, F401
    _VISUAL_ANALYSIS_PROMPT,
    VALID_REGION_TYPES,
    _fallback_visual_analysis,
    _parse_visual_response,
    _run_3_2,
    _summarize_extraction,
)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════


async def run_stage3(
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, Any]:
    """Stage 3: Structural Analysis — 4 sub-steps.

    3.1 and 3.2 run in parallel.
    3.3 depends on both.
    3.4 depends on 3.3.
    """
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    stage, name = 3, "Structural Analysis"
    context["_current_stage"] = stage
    context["_current_stage_name"] = name

    clusters: list[dict[str, Any]] = context.get("clusters", [])
    raw_text_blocks: dict[str, list[dict[str, Any]]] = context.get("_raw_text_blocks", {})
    enriched_documents: list[dict[str, Any]] = context.get("enriched_documents", [])

    # --- Parallel: 3.1 + 3.2 ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.05),
            sub_step="3.1+3.2 Parallel (Multi-Example + Visual)",
            sub_progress_pct=0.05,
        )
    )

    # 3.1 is synchronous (CPU-bound), wrap in executor
    loop = asyncio.get_event_loop()
    task_3_1 = loop.run_in_executor(None, _run_3_1, clusters, raw_text_blocks)
    task_3_2 = _run_3_2(clusters, enriched_documents, context, emit_progress)

    position_classifications, visual_analysis_result = await asyncio.gather(task_3_1, task_3_2)

    # Emit spaCy warning if NER layer is unavailable (once per pipeline run)
    if _get_nlp() is None and not context.get("_spacy_warning_emitted"):
        context.setdefault("_pipeline_warnings", []).append(
            {
                "code": "spacy_unavailable",
                "severity": "info",
                "message": ("NER layer desabilitado — modelo spaCy não encontrado. Classificação usando regex-only."),
                "stage": 3,
            }
        )
        context["_spacy_warning_emitted"] = True

    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.50),
            sub_step="3.1+3.2 Complete",
            sub_progress_pct=0.50,
        )
    )

    # --- Sequential: 3.3 ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.55),
            sub_step="3.3 Semantic Classification",
            sub_progress_pct=0.55,
        )
    )

    block_classifications, label_value_pairs = _run_3_3(
        enriched_documents, position_classifications, visual_analysis_result, clusters
    )

    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.75),
            sub_step="3.3 Complete",
            sub_progress_pct=0.75,
        )
    )

    # --- Sequential: 3.4 ---
    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.80),
            sub_step="3.4 Hierarchy Builder",
            sub_progress_pct=0.80,
        )
    )

    _raw_trees = _run_3_4(
        enriched_documents,
        block_classifications,
        visual_analysis_result,
        clusters,
        position_classifications,
    )
    # Normalize to dict keyed by cluster_id — all downstream stages (4, 5) expect this format
    document_trees: dict[str, dict[str, Any]] = {
        entry.get("cluster_id", ""): entry.get("tree", {}) for entry in _raw_trees
    }

    # Story 34.7: Auto-bind semantic — suggest XSD bindings based on name similarity
    field_tree = context.get("field_tree")
    if field_tree:
        flat_paths = field_tree.get("flat_paths", [])
        if flat_paths:
            total_suggestions = 0
            for _cid, tree in document_trees.items():
                total_suggestions += _apply_suggested_bindings(tree, flat_paths)
            if total_suggestions > 0:
                logger.info("Stage 3.4: Auto-bind semantic — %d suggested bindings", total_suggestions)

    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 0.95),
            sub_step="3.4 Complete",
            sub_progress_pct=0.95,
        )
    )

    # --- Build intelligence with derived views ---
    intelligence: dict[str, Any] = {}
    for cluster in clusters:
        cid = cluster["cluster_id"]
        if cid.startswith("_"):
            continue

        cluster_block_ids = set()
        for doc in enriched_documents:
            for page in doc.get("pages", []):
                if page.get("cluster_id") == cid and page.get("is_representative"):
                    for block in page.get("text_blocks", []):
                        bid = block.get("id", "")
                        if bid:
                            cluster_block_ids.add(bid)

        cluster_bc = {bid: block_classifications[bid] for bid in cluster_block_ids if bid in block_classifications}

        labels_list = [bid for bid, bc in cluster_bc.items() if bc.semantic == "label"]
        dynamic_list = [
            bid for bid, bc in cluster_bc.items() if bc.semantic in ("dynamic", "semi_dynamic", "likely_dynamic")
        ]
        optional_list = [bid for bid, bc in cluster_bc.items() if bc.variant in ("optional",)]
        conditional_list = [bid for bid, bc in cluster_bc.items() if bc.variant == "conditional"]

        cluster_quality = position_classifications.get(cid, {}).get(
            "classification_quality",
            {
                "total_pdfs": 0,
                "total_pages_in_cluster": 0,
                "statistical_strength": "none",
                "smart_override_count": 0,
                "uncertain_count": 0,
            },
        )

        # Story 42.5 — serialize BlockClassification to plain dicts at context boundary
        # (stage 4 and downstream access block_classifications as plain dicts)
        intelligence[cid] = {
            "block_classifications": {bid: bc.model_dump() for bid, bc in cluster_bc.items()},
            "labels": labels_list,
            "dynamic_fields": dynamic_list,
            "optional_fields": optional_list,
            "conditional_fields": conditional_list,
            "classification_quality": cluster_quality,
        }

    # Derive layout_types from intelligence + clusters for Stage 5 consumption.
    _page_dims: dict[str, dict[str, float]] = {}
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            cid = page.get("cluster_id", "")
            if cid and page.get("is_representative") and cid not in _page_dims:
                _page_dims[cid] = {
                    "width": float(page.get("width", 595.0)),
                    "height": float(page.get("height", 842.0)),
                }

    layout_types: list[dict[str, Any]] = []
    for cluster in clusters:
        cid = cluster["cluster_id"]
        if cid.startswith("_"):
            continue
        dims = _page_dims.get(cid, {"width": 595.0, "height": 842.0})
        layout_types.append(
            {
                "id": cid,
                "cluster_id": cid,
                "name": cid,
                "page_width_pts": dims["width"],
                "page_height_pts": dims["height"],
                "page_count": cluster.get("page_count", len(cluster.get("pages", []))),
            }
        )

    context["layout_types"] = layout_types
    context["document_trees"] = document_trees
    context["intelligence"] = intelligence
    context["visual_analysis"] = visual_analysis_result
    context["label_value_pairs"] = label_value_pairs
    context["stage_3_result"] = {
        "document_trees": document_trees,
        "intelligence": intelligence,
    }

    total_blocks = sum(len(v.get("block_classifications", {})) for v in intelligence.values())
    total_labels = sum(len(v.get("labels", [])) for v in intelligence.values())
    total_dynamic = sum(len(v.get("dynamic_fields", [])) for v in intelligence.values())
    total_pairs = len(label_value_pairs)

    await emit_progress(
        make_sub_progress_event(
            stage=stage,
            stage_name=name,
            status="running",
            progress_pct=compute_overall_progress(stage, 1.0),
            sub_step="3.done",
            sub_progress_pct=1.0,
            summary={
                "total_blocks_classified": total_blocks,
                "total_labels": total_labels,
                "total_dynamic": total_dynamic,
                "total_pairs": total_pairs,
                "trees_built": len(document_trees),
                "vision_api_calls": context.get("_vision_api_calls", 0),
            },
        )
    )

    return context
