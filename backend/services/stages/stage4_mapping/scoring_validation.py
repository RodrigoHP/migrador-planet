"""Stage 4 — Scoring & Validation sub-module (Steps 4.6, 4.7).

Responsibilities:
  - Per-layout confidence scoring from 5 heuristic factors (4.6)
  - Consistency validation: orphans, unmapped required, type-format (4.7)

Story 41.3 — extracted from stage4_field_mapping.py
"""

from __future__ import annotations

import logging
from typing import Any

from models.pipeline_context import BlockClassification
from services.stages.stage4_mapping.constants import (  # noqa: F401
    _TYPE_FORMAT_COMPAT,
    THRESHOLD_APPROVED,
    THRESHOLD_REVIEW,
    WEIGHTS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-step 4.6 — Confidence Scoring
# ---------------------------------------------------------------------------


def _get_layout_stability(intelligence: dict[str, Any], layout_id: str) -> float:
    """Get layout stability factor for a layout."""
    layout_intel = intelligence.get(layout_id, {})
    cq = layout_intel.get("classification_quality", {})
    strength = cq.get("statistical_strength", "none")
    if strength == "strong":
        return 0.9
    elif strength == "weak":
        return 0.7
    return 0.5


def _get_anchor_detection(layout_mappings: list[dict[str, Any]]) -> float:
    """Fraction of mappings with non-empty label_text."""
    if not layout_mappings:
        return 0.5
    with_label = sum(1 for m in layout_mappings if m.get("label_text"))
    return round(with_label / len(layout_mappings), 4)


def _get_grid_quality(cluster: dict[str, Any]) -> float:
    """Grid quality from cluster info."""
    page_count = cluster.get("page_count", 1)
    return 0.7 if page_count > 1 else 0.5


def _get_field_variability(intelligence: dict[str, Any], layout_id: str) -> float:
    """Field variability factor from intelligence."""
    layout_intel = intelligence.get(layout_id, {})
    cq = layout_intel.get("classification_quality", {})
    uncertain: int = int(cq.get("uncertain_count", 0))
    total: int = int(cq.get("total_pages_in_cluster", 1))
    if total > 0:
        ratio = uncertain / max(total, 1)
        return float(round(max(0.3, 1.0 - ratio), 4))
    return 0.5


def _get_vision_agreement(visual_analysis: dict[str, Any], cluster: dict[str, Any]) -> float:
    """Vision agreement from visual_analysis consistency scores.

    Returns 0.0 (not 0.5) when no valid page scores are found, to avoid masking
    a silent Stage 3.2 Visual Analysis failure as a neutral score.
    """
    layout_id = cluster.get("cluster_id", "<unknown>")
    if not visual_analysis:
        logger.warning(
            "vision_agreement: visual_analysis ausente para layout %s — "
            "Stage 3.2 Visual Analysis pode ter falhado silenciosamente. "
            "Usando vision_agreement=0.",
            layout_id,
        )
        return 0.0
    scores = []
    for page_key, page_data in visual_analysis.items():
        if isinstance(page_data, dict):
            cs = page_data.get("consistency_score")
            if cs is not None:
                try:
                    scores.append(max(0.0, min(1.0, float(cs) / 100.0)))
                except (TypeError, ValueError):
                    pass
    if not scores:
        logger.warning(
            "vision_agreement: nenhum consistency_score valido encontrado para layout %s "
            "(visual_analysis nao vazio mas sem paginas com scores) — "
            "Stage 3.2 Visual Analysis pode ter falhado silenciosamente. "
            "Usando vision_agreement=0.",
            layout_id,
        )
        return 0.0
    return round(sum(scores) / len(scores), 4)


def _step_4_6_confidence_scoring(
    field_mappings: list[dict[str, Any]],
    intelligence: dict[str, Any],
    visual_analysis: dict[str, Any],
    clusters: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Confidence scoring per-layout. Heuristic (no LLM)."""
    confidence_scores: dict[str, dict[str, Any]] = {}

    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        layout_mappings = [m for m in field_mappings if m.get("layout_type_id") == layout_id]
        layout_intel = intelligence.get(layout_id, {})
        cq = layout_intel.get("classification_quality", {})

        factors = {
            "layout_stability": _get_layout_stability(intelligence, layout_id),
            "anchor_detection": _get_anchor_detection(layout_mappings),
            "grid_quality": _get_grid_quality(cluster),
            "field_variability": _get_field_variability(intelligence, layout_id),
            "vision_agreement": _get_vision_agreement(visual_analysis, cluster),
        }

        # Heuristic 1: Tabular + low anchor -> don't penalise anchor_detection
        if factors["anchor_detection"] < 0.4 and factors["grid_quality"] >= 0.7:
            factors["anchor_detection"] = max(factors["anchor_detection"], 0.6)

        # Heuristic 2 (PA1): smart_signals -> adjust field_variability
        if cq.get("smart_override_count", 0) > 0:
            factors["field_variability"] = max(0.0, factors["field_variability"] - 0.10)
        if cq.get("statistical_strength") == "none":
            factors["field_variability"] = max(0.0, factors["field_variability"] - 0.15)
        elif cq.get("statistical_strength") == "strong":
            factors["field_variability"] = min(1.0, factors["field_variability"] + 0.10)

        # Heuristic 3: Many ambiguous -> penalise
        ambiguous_ratio = sum(1 for m in layout_mappings if m.get("is_ambiguous")) / max(1, len(layout_mappings))
        if ambiguous_ratio > 0.3:
            factors["anchor_detection"] = max(0.0, factors["anchor_detection"] - 0.1)

        overall = sum(WEIGHTS[k] * factors[k] for k in WEIGHTS)
        overall = round(overall, 4)

        if overall >= THRESHOLD_APPROVED:
            status = "approved"
        elif overall >= THRESHOLD_REVIEW:
            status = "review_recommended"
        else:
            status = "human_review_required"

        confidence_scores[layout_id] = {
            **factors,
            "overall": round(overall * 100),
            "status": status,
        }

    return confidence_scores


# ---------------------------------------------------------------------------
# Sub-step 4.7 — Consistency Validation
# ---------------------------------------------------------------------------


def _get_required_paths(field_tree: dict[str, Any]) -> list[str]:
    """Extract flat_paths of fields with required=True."""
    if not field_tree:
        return []
    required: list[str] = []

    def _walk(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            if node.get("required", True) and node.get("type") != "complex":
                required.append(node.get("path", ""))
            _walk(node.get("children", []))

    _walk(field_tree.get("root_nodes", []))
    return required


def _validate_type_format(
    field_mappings: list[dict[str, Any]],
    warnings: list[str],
) -> list[dict[str, Any]]:
    """Cross-validate XSD type vs detected_format. Returns mismatches."""
    mismatches: list[dict[str, Any]] = []
    for m in field_mappings:
        xsd_type = m.get("xsd_type")
        fmt = m.get("detected_format")
        if not xsd_type or not fmt:
            continue
        compatible = _TYPE_FORMAT_COMPAT.get(xsd_type, {"string"})
        if fmt not in compatible:
            mismatches.append(
                {
                    "block_id": m.get("block_id", ""),
                    "xsd_type": xsd_type,
                    "detected_format": fmt,
                    "xsd_path": m.get("xsd_field_path", ""),
                }
            )
            warnings.append(
                f"type_format_mismatch: '{m.get('xsd_field_path', '')}' "
                f"is {xsd_type} in XSD but detected_format is {fmt}"
            )
    return mismatches


def _step_4_7_consistency_validation(
    field_mappings: list[dict[str, Any]],
    field_tree: dict[str, Any] | None,
    intelligence: dict[str, Any],
) -> dict[str, Any]:
    """Consistency validation: orphans, unmapped required, type-format."""
    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    flat_paths_set = set(p for p in flat_paths if p)

    warnings: list[str] = []
    errors: list[str] = []

    # 1. Dynamic blocks without mapping
    dynamic_count = 0
    _empty_bc = BlockClassification()
    for layout_id, layout_intel in intelligence.items():
        raw_bc = layout_intel.get("block_classifications", {})
        for block_id, block_raw in raw_bc.items():
            block_bc = BlockClassification(**block_raw) if isinstance(block_raw, dict) else block_raw or _empty_bc
            if block_bc.semantic in ("dynamic", "semi_dynamic", "likely_dynamic"):
                dynamic_count += 1

    mapped_count = len([m for m in field_mappings if m.get("xsd_field_path")])
    orphan_count = 0
    if dynamic_count > 0 and mapped_count < dynamic_count:
        orphan_count = dynamic_count - mapped_count
        warnings.append(
            f"skeleton_vs_result: {orphan_count} dynamic block(s) "
            f"without field_mapping ({mapped_count}/{dynamic_count} mapped)"
        )

    # 2. XSD coverage
    mapped_paths = {m.get("xsd_field_path", "") for m in field_mappings if m.get("xsd_field_path")}
    unmapped_xsd = [p for p in flat_paths if p not in mapped_paths]
    if unmapped_xsd:
        warnings.append(
            f"xsd_coverage: {len(unmapped_xsd)} XSD field(s) without mapping: " + ", ".join(unmapped_xsd[:10])
        )

    # 3. Orphan mappings (paths not in field_tree)
    for m in field_mappings:
        path = m.get("xsd_field_path", "")
        if path and path not in flat_paths_set:
            errors.append(f"orphan_mapping: '{path}' does not exist in field_tree")

    # 4. Required XSD fields without mapping
    required_paths = _get_required_paths(field_tree) if field_tree else []
    unmapped_required = [p for p in required_paths if p not in mapped_paths]
    if unmapped_required:
        errors.append(
            f"required_unmapped: {len(unmapped_required)} required XSD field(s) "
            f"without mapping: " + ", ".join(unmapped_required[:10])
        )

    # 5. Type-format mismatches
    type_format_mismatches = _validate_type_format(field_mappings, warnings)

    return {
        "warnings": warnings,
        "errors": errors,
        "orphan_count": orphan_count,
        "unmapped_xsd_fields": unmapped_required,
        "unmapped_required_xsd_fields": unmapped_required,
        "type_format_mismatches": type_format_mismatches,
    }
