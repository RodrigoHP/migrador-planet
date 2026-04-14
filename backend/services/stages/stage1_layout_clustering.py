"""Stage 1 — Layout Clustering (Pool Unico + 3 Camadas).

Story 13.4 — Groups pages with identical layouts via tolerant clustering
with 3 defense layers: Prevention (1.1-1.9), Detection (1.10-1.13),
Correction (1.14-1.15), plus Validation (1.16 Homogeneity Check).

Story 41.3 — Decomposed into sub-modules under stage1_clustering/:
  - page_preprocessing.py  : ClusteringConfig, PageInfo, classify/extract/normalize
  - clustering_algorithms.py: similarity, graph clustering, consensus
  - cluster_validation.py  : quality score, phash, llm validate, auto-correct

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 5
Output contract: Section 3.1

Story 41.3 — Decomposed into sub-modules under stage1_clustering/.
This file is now a thin orchestrator + backward-compatible re-exports.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

# ---------------------------------------------------------------------------
# Re-exports — backward compatibility
# ---------------------------------------------------------------------------
from services.stages.stage1_clustering.cluster_validation import (  # noqa: F401
    _auto_correct,
    _cluster_quality_score,
    _compute_confidence,
    _homogeneity_check,
    _llm_validate,
    _phash_crosscheck,
    _validate_representatives,
)
from services.stages.stage1_clustering.clustering_algorithms import (  # noqa: F401
    _cluster_graph,
    _clusterings_agree,
    _compute_similarity,
    _consensus_check,
    _density_similarity,
    _geometry_similarity,
    _intersect_clusterings,
    _select_representatives,
)
from services.stages.stage1_clustering.page_preprocessing import (  # noqa: F401
    ABSTRACTION_PATTERNS,
    ClusteringConfig,
    PageInfo,
    _abstract_content,
    _abstract_text,
    _classify_pages,
    _detect_body_region,
    _extract_blocks,
    _filter_regions,
    _normalize,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Sub-progress helper
# ---------------------------------------------------------------------------


async def _emit_sub(
    emit: EmitProgressFn,
    sub_step: str,
    sub_pct: float,
) -> None:
    """Emit a Stage 1 sub-progress event."""
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    event = make_sub_progress_event(
        stage=1,
        stage_name="Layout Clustering",
        status="running",
        progress_pct=compute_overall_progress(1, sub_pct),
        sub_step=sub_step,
        sub_progress_pct=sub_pct,
    )
    await emit(event)


# ---------------------------------------------------------------------------
# Stage entry point
# ---------------------------------------------------------------------------


async def run_stage1(
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, Any]:
    """Stage 1: Layout Clustering — Pool Unico + 3 Camadas.

    Args:
        context: Pipeline context with pdf_documents, _storage, job_id, etc.
        emit_progress: Async callback for SSE events.

    Returns:
        Updated context with clusters, _raw_text_blocks, etc.
    """
    context["_current_stage"] = 1
    context["_current_stage_name"] = "Layout Clustering"

    pdf_documents: list[dict[str, str]] = context.get("pdf_documents", [])
    job = context.get("_job", {})
    config = ClusteringConfig.from_job_config(job.get("config", {}))

    if not pdf_documents:
        context["clusters"] = []
        context["_raw_text_blocks"] = {}
        return context

    # Build pdf_id -> path map
    pdf_docs_map: dict[str, str] = {}
    for doc in pdf_documents:
        pdf_docs_map[str(doc["id"])] = doc["path"]

    # ===================================================
    # LAYER 1 — PREVENTION (steps 1.1-1.9)
    # ===================================================

    all_pages: list[PageInfo] = []
    all_raw_text_blocks: dict[str, list[dict[str, Any]]] = {}

    # Step 1.1 + 1.2: Classify pages and extract blocks per PDF
    await _emit_sub(emit_progress, "1.1 Page Classification", 0.05)

    for pdf_doc in pdf_documents:
        pdf_id = str(pdf_doc["id"])
        pdf_path = pdf_doc["path"]

        pages = _classify_pages(pdf_path, pdf_id)
        raw_blocks = _extract_blocks(pdf_path, pages)
        all_raw_text_blocks.update(raw_blocks)
        all_pages.extend(pages)

    await _emit_sub(emit_progress, "1.2 Block Extraction", 0.12)

    # Step 1.3: Normalization
    await _emit_sub(emit_progress, "1.3 Normalization", 0.17)
    _normalize(all_pages)

    # Step 1.4: Content Abstraction
    await _emit_sub(emit_progress, "1.4 Content Abstraction", 0.22)
    _abstract_content(all_pages)

    # Step 1.5: Region Filtering
    await _emit_sub(emit_progress, "1.5 Region Filtering", 0.27)
    header_end, footer_start = _filter_regions(all_pages, config)

    # Build processable pages list (for indexing in similarity matrix)
    processable_pages = [pi for pi in all_pages if pi.is_processable]

    if not processable_pages:
        # All pages are blank/scanned — still produce cluster output
        context["clusters"] = []
        context["_raw_text_blocks"] = all_raw_text_blocks
        from services.pipeline_orchestrator_v2 import compute_overall_progress, make_sub_progress_event

        await emit_progress(
            make_sub_progress_event(
                stage=1,
                stage_name="Layout Clustering",
                status="running",
                progress_pct=compute_overall_progress(1, 1.0),
                sub_step="1.0 Complete",
                sub_progress_pct=1.0,
                summary={"layouts_detected": 0, "pages_processed": len(all_pages)},
            )
        )
        return context

    # Step 1.6: Tolerant Similarity Matrix
    await _emit_sub(emit_progress, "1.6 Similarity Matrix", 0.35)
    sim_matrix = _compute_similarity(all_pages, header_end, footer_start, config)

    # Step 1.7: Graph Clustering
    await _emit_sub(emit_progress, "1.7 Graph Clustering", 0.42)
    graph_clusters = _cluster_graph(sim_matrix, config)

    # Step 1.8: Consensus Check
    await _emit_sub(emit_progress, "1.8 Consensus Check", 0.48)
    consensus_clusters, consensus_agreed = _consensus_check(sim_matrix, graph_clusters, config)

    # Step 1.9: Representative Selection
    await _emit_sub(emit_progress, "1.9 Representative Selection", 0.52)
    representatives = _select_representatives(consensus_clusters, sim_matrix, processable_pages)

    # ===================================================
    # LAYER 2 — DETECTION (steps 1.10-1.13)
    # ===================================================

    # Step 1.10: Cluster Quality Score
    await _emit_sub(emit_progress, "1.10 Cluster Quality", 0.58)
    quality_scores = _cluster_quality_score(consensus_clusters, sim_matrix, config)

    # Step 1.11: pHash Cross-Check
    await _emit_sub(emit_progress, "1.11 pHash Cross-Check", 0.65)
    visual_warnings = _phash_crosscheck(consensus_clusters, processable_pages, pdf_docs_map, config)

    # Step 1.12: Representative Validation
    await _emit_sub(emit_progress, "1.12 Representative Validation", 0.70)
    _validate_representatives(consensus_clusters, representatives, sim_matrix)

    # Step 1.13: LLM Cluster Validation (conditional)
    await _emit_sub(emit_progress, "1.13 LLM Validation", 0.75)
    llm_result = await _llm_validate(consensus_clusters, processable_pages, pdf_docs_map, context, emit_progress)
    if llm_result is None:
        logger.warning("Stage 1: clusters com layouts muito divergentes detectados — possível mistura de templates")

    # ===================================================
    # LAYER 3 — CORRECTION (steps 1.14-1.15)
    # ===================================================

    # Step 1.14: Auto-correction
    await _emit_sub(emit_progress, "1.14 Auto-correction", 0.80)
    corrected_clusters, corrections = _auto_correct(
        consensus_clusters, quality_scores, visual_warnings, sim_matrix, config
    )

    # Step 1.15: Confidence Score
    await _emit_sub(emit_progress, "1.15 Confidence Score", 0.85)

    # Build final cluster output conforming to contract 3.1
    cluster_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    final_clusters: list[dict[str, Any]] = []

    for idx, members in enumerate(corrected_clusters):
        cluster_id = cluster_labels[idx] if idx < len(cluster_labels) else f"C{idx}"

        pages_list = []
        for member_idx in sorted(members):
            pi = processable_pages[member_idx]
            pages_list.append({"pdf_id": pi.pdf_id, "page_index": pi.page_index})

        # Representative
        rep_idx = representatives.get(idx)
        if rep_idx is None or rep_idx not in members:
            rep_idx = next(iter(members))
        rep_pi = processable_pages[rep_idx]

        # Quality score for this cluster
        qs = 1.0
        for q in quality_scores:
            if q["cluster_idx"] == idx:
                qs = q["score"]
                break

        confidence = _compute_confidence(idx, qs, visual_warnings, consensus_agreed, llm_result)

        final_clusters.append(
            {
                "cluster_id": cluster_id,
                "pages": pages_list,
                "representative_page": {
                    "pdf_id": rep_pi.pdf_id,
                    "page_index": rep_pi.page_index,
                },
                "page_count": len(pages_list),
                "confidence": confidence,
            }
        )

    # Add non-processable pages to special clusters
    non_processable = [pi for pi in all_pages if not pi.is_processable]
    if non_processable:
        blank_pages = [pi for pi in non_processable if pi.page_type == "blank"]
        scanned_pages = [pi for pi in non_processable if pi.page_type == "scanned"]

        if blank_pages:
            final_clusters.append(
                {
                    "cluster_id": "_blank",
                    "pages": [{"pdf_id": pi.pdf_id, "page_index": pi.page_index} for pi in blank_pages],
                    "representative_page": {
                        "pdf_id": blank_pages[0].pdf_id,
                        "page_index": blank_pages[0].page_index,
                    },
                    "page_count": len(blank_pages),
                    "confidence": {"confidence": 1.0, "level": "high", "factors": {}},
                }
            )

        if scanned_pages:
            final_clusters.append(
                {
                    "cluster_id": "_scanned",
                    "pages": [{"pdf_id": pi.pdf_id, "page_index": pi.page_index} for pi in scanned_pages],
                    "representative_page": {
                        "pdf_id": scanned_pages[0].pdf_id,
                        "page_index": scanned_pages[0].page_index,
                    },
                    "page_count": len(scanned_pages),
                    "confidence": {"confidence": 1.0, "level": "high", "factors": {}},
                }
            )

    # ===================================================
    # VALIDATION — Homogeneity Check (step 1.16)
    # ===================================================

    await _emit_sub(emit_progress, "1.16 Homogeneity Check", 0.90)
    pdf_ids = [str(doc["id"]) for doc in pdf_documents]
    mismatched_pdfs = _homogeneity_check(final_clusters, pdf_ids, config)

    if mismatched_pdfs:
        logger.warning("Homogeneity check: %d mismatched PDF(s) detected", len(mismatched_pdfs))

        # 48.2: Se TODOS os PDFs estão em clusters exclusivos, é mistura completa de templates
        # → falha imediata com mensagem clara (sem esperar checkpoint SSE)
        if len(pdf_ids) > 1 and len(mismatched_pdfs) == len(pdf_ids):
            raise ValueError("PDFs parecem ser de templates diferentes — envie PDFs do mesmo template")

        try:
            from services.pipeline_orchestrator_v2 import handle_service_failure

            mismatch_error = Exception(
                f"Template mismatch detected: {len(mismatched_pdfs)} PDF(s) appear to be from a different template"
            )
            decision = await handle_service_failure(
                context=context,
                service_name="Homogeneity Check",
                stage_name="Layout Clustering",
                error=mismatch_error,
                fallback_description="Continuar com todos os PDFs — clustering pode ser impreciso",
                impact_description=(
                    f"{len(mismatched_pdfs)} documento(s) parecem ser de template diferente. "
                    "Manter pode degradar a qualidade dos clusters."
                ),
                job=job,
                emit_progress=emit_progress,
            )
            if decision == "fallback":
                removed_pdf_ids = {m["pdf_id"] for m in mismatched_pdfs}
                for cluster in final_clusters:
                    cluster["pages"] = [p for p in cluster["pages"] if p["pdf_id"] not in removed_pdf_ids]
                final_clusters = [c for c in final_clusters if c["pages"]]
                for cluster in final_clusters:
                    cluster["page_count"] = len(cluster["pages"])
                all_raw_text_blocks = {
                    k: v for k, v in all_raw_text_blocks.items() if k.split(":")[0] not in removed_pdf_ids
                }
        except Exception as exc:
            logger.warning("Failed to handle homogeneity mismatch checkpoint: %s", exc)

    # Write to context
    context["clusters"] = final_clusters
    context["_raw_text_blocks"] = all_raw_text_blocks

    await _emit_sub(emit_progress, "1.16 Complete", 1.0)

    # Emit final summary for the accordion
    from services.pipeline_orchestrator_v2 import compute_overall_progress, make_sub_progress_event

    real_clusters = [c for c in final_clusters if not c.get("cluster_id", "").startswith("_")]
    avg_confidence_pct = 0
    if real_clusters:
        raw_scores = [
            c["confidence"]
            if isinstance(c.get("confidence"), (int, float))
            else c["confidence"].get("confidence", 0)
            if isinstance(c.get("confidence"), dict)
            else 0
            for c in real_clusters
        ]
        avg_confidence_pct = round(sum(raw_scores) / len(raw_scores) * 100)
    await emit_progress(
        make_sub_progress_event(
            stage=1,
            stage_name="Layout Clustering",
            status="running",
            progress_pct=compute_overall_progress(1, 1.0),
            sub_step="1.16 Complete",
            sub_progress_pct=1.0,
            summary={
                "layouts_detected": len(real_clusters),
                "pages_processed": len(all_pages),
                "confidence": avg_confidence_pct,
                "corrections": len(corrections) if isinstance(corrections, (list, tuple)) else 0,
            },
        )
    )

    return context
