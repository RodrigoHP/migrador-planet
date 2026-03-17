"""Stage 16 — Intelligence Normalization.

Consolidates outputs from Stages 12-15 into structured metadata on each
LayoutType:

  labels[]              — TextBlock-like dicts classified as static labels
  dynamic_fields[]      — TextBlock-like dicts classified as dynamic values
  stability_map         — Dict[bbox_key → stability_info]
  variants[]            — detected optional_field / conditional_section / dynamic_table
  conditional_sections[]— groups of conditionally-present fields

The enriched metadata is written back to each LayoutType in
context["_layout_type_objects"] AND serialised to context["layout_types"].

Also stores context["intelligence"] with the consolidated dict for all clusters.

Reads:
    context["_layout_type_objects"]  — List[LayoutType]
    context["_element_labels"]       — Dict[cluster_id → List[element_analysis]]
    context["_stability_map"]        — Dict[cluster_id → Dict[bbox_key → stability_info]]
    context["_variants"]             — Dict[cluster_id → List[variant]]
    context["_conditional_sections"] — Dict[cluster_id → List[section]]
    context["intelligence_metadata"] — {single_document, reduced_accuracy}

Writes:
    context["intelligence"]          — Dict[cluster_id → intelligence_dict]
    context["layout_types"]          — re-serialised LayoutType list (enriched)

Registers itself as Stage 16 (Block 4).
"""

from __future__ import annotations

from typing import Any, Dict, List

from models.layout_type import LayoutType


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------


def _build_intelligence_for_cluster(
    cluster_id: int,
    element_labels: List[Dict[str, Any]],
    stability_map: Dict[str, Dict[str, Any]],
    variants: List[Dict[str, Any]],
    conditional_sections: List[Dict[str, Any]],
    single_doc: bool,
) -> Dict[str, Any]:
    """Build the consolidated intelligence dict for one cluster."""

    labels: List[Dict[str, Any]] = []
    dynamic_fields: List[Dict[str, Any]] = []

    for elem in element_labels:
        entry = {
            "bbox_key": elem["bbox_key"],
            "text_samples": elem.get("text_samples", []),
            "confidence": elem.get("confidence", "confirmed"),
        }
        if elem["classification"] == "label":
            labels.append(entry)
        else:
            dynamic_fields.append(entry)

    return {
        "cluster_id": cluster_id,
        "labels": labels,
        "dynamic_fields": dynamic_fields,
        "stability_map": stability_map,
        "variants": variants,
        "conditional_sections": conditional_sections,
        "metadata": {
            "single_document": single_doc,
            "reduced_accuracy": single_doc,
            "label_count": len(labels),
            "dynamic_count": len(dynamic_fields),
            "variant_count": len(variants),
        },
    }


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 16 executor — Intelligence Normalization."""
    emit = context.get("emit_progress")

    layout_types: List[LayoutType] = context.get("_layout_type_objects", [])
    element_labels_all: Dict[int, List[Dict[str, Any]]] = context.get(
        "_element_labels", {}
    )
    stability_maps: Dict[int, Dict[str, Dict[str, Any]]] = context.get(
        "_stability_map", {}
    )
    variants_all: Dict[int, List[Dict[str, Any]]] = context.get("_variants", {})
    cond_sections_all: Dict[int, List[Dict[str, Any]]] = context.get(
        "_conditional_sections", {}
    )
    intel_meta: Dict[str, Any] = context.get("intelligence_metadata", {})
    single_doc: bool = intel_meta.get("single_document", False)

    intelligence: Dict[int, Dict[str, Any]] = {}
    total_labels = 0
    total_dynamic = 0
    total_variants = 0

    for lt in layout_types:
        cluster_id = lt.cluster_id

        intel = _build_intelligence_for_cluster(
            cluster_id=cluster_id,
            element_labels=element_labels_all.get(cluster_id, []),
            stability_map=stability_maps.get(cluster_id, {}),
            variants=variants_all.get(cluster_id, []),
            conditional_sections=cond_sections_all.get(cluster_id, []),
            single_doc=single_doc,
        )

        intelligence[cluster_id] = intel
        total_labels += intel["metadata"]["label_count"]
        total_dynamic += intel["metadata"]["dynamic_count"]
        total_variants += intel["metadata"]["variant_count"]

        # Attach intelligence to the LayoutType object as a dynamic attribute
        # so downstream stages can access it without model changes.
        lt._intelligence = intel  # type: ignore[attr-defined]

    context["intelligence"] = intelligence

    # Re-serialise layout_types (enriched)
    context["layout_types"] = [lt.to_dict() for lt in layout_types]

    summary = {
        "clusters_normalised": len(layout_types),
        "total_labels": total_labels,
        "total_dynamic_fields": total_dynamic,
        "total_variants": total_variants,
        "single_document": single_doc,
        "reduced_accuracy": single_doc,
    }

    if emit:
        try:
            emit(
                {
                    "stage": 16,
                    "stage_name": "Intelligence Normalization",
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
    """Replace stub Stage 16 (Normalization) with this implementation."""
    registry.remove_stage(16)
    registry.register_stage(
        stage_number=16,
        name="Intelligence Normalization",
        block_id=4,
        estimated_duration=0.5,
        execute_fn=execute,
    )
