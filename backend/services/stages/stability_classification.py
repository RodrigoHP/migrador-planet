"""Stage 14 — Stability Classification.

For every element position in a cluster, classifies the element as:

  * stable   — same position AND same content in ALL documents
  * variable — same position, but content differs across documents
  * absent   — present in some documents, missing in others

Also computes a stability_score (0.0–1.0) per element representing the
fraction of documents in which the element appears.

With a single PDF, all elements are classified as "unknown" with an
inferred stability_score of 1.0 (best-effort).

Reads:
    context["_element_labels"]       — Dict[cluster_id → List[element_analysis]]
                                       (from Stage 13)
    context["_layout_type_objects"]  — List[LayoutType]
    context["intelligence_metadata"] — may contain single_document flag

Writes:
    context["_stability_map"]        — Dict[cluster_id → Dict[bbox_key → stability_info]]
      stability_info = {
          "classification": "stable" | "variable" | "absent" | "unknown",
          "stability_score": float,  # 0.0 – 1.0
          "doc_count": int,          # number of docs where element appears
          "total_docs": int,
      }

Registers itself as Stage 14 (Block 4).
"""

from __future__ import annotations

from typing import Any, Dict, List

from models.layout_type import LayoutSkeleton, LayoutType


# ---------------------------------------------------------------------------
# Core classification
# ---------------------------------------------------------------------------


def _classify_stability(
    element_analysis: List[Dict[str, Any]],
    layout_type: LayoutType,
    skeletons: List[LayoutSkeleton],
    single_doc: bool,
) -> Dict[str, Dict[str, Any]]:
    """Build stability_map for one cluster.

    Parameters
    ----------
    element_analysis:
        Output from Stage 13 for this cluster.
    layout_type:
        The LayoutType for this cluster (used for total page/doc count).
    skeletons:
        All LayoutSkeleton objects (used to count PDFs in cluster).
    single_doc:
        True when only one PDF was provided.
    """
    # Count distinct PDFs contributing to this cluster
    cluster_pdf_indices = {p["pdf_index"] for p in layout_type.pages}
    total_docs = max(len(cluster_pdf_indices), 1)

    stability_map: Dict[str, Dict[str, Any]] = {}

    for elem in element_analysis:
        bbox_key: str = elem["bbox_key"]
        classification_from_13: str = elem["classification"]
        samples: List[str] = elem.get("text_samples", [])

        if single_doc:
            # Cannot determine true presence across docs
            stability_map[bbox_key] = {
                "classification": "unknown",
                "stability_score": 1.0,
                "doc_count": 1,
                "total_docs": 1,
                "confidence": "inferred",
            }
            continue

        # doc_count is approximated from how many unique samples were seen
        # (text_samples are deduplicated across docs in Stage 13).
        # A more precise count would require re-scanning skeletons, but for
        # the intelligence pipeline the sample count gives a good proxy.
        doc_count = min(len(samples), total_docs) if samples else 0
        # If we have confirmed classification from Stage 13, all docs had this element
        if elem.get("confidence") == "confirmed":
            doc_count = total_docs

        stability_score = doc_count / total_docs if total_docs > 0 else 0.0

        if doc_count < total_docs:
            classification = "absent"
        elif classification_from_13 == "label":
            # Label means same text → stable
            classification = "stable"
        else:
            # Dynamic means varying text → variable
            classification = "variable"

        stability_map[bbox_key] = {
            "classification": classification,
            "stability_score": round(stability_score, 4),
            "doc_count": doc_count,
            "total_docs": total_docs,
            "confidence": elem.get("confidence", "confirmed"),
        }

    return stability_map


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 14 executor — Stability Classification."""
    emit = context.get("emit_progress")

    element_labels: Dict[int, List[Dict[str, Any]]] = context.get("_element_labels", {})
    layout_types: List[LayoutType] = context.get("_layout_type_objects", [])
    skeletons: List[LayoutSkeleton] = context.get("_skeleton_objects", [])
    intel_meta: Dict[str, Any] = context.get("intelligence_metadata", {})
    single_doc: bool = intel_meta.get("single_document", False)

    stability_maps: Dict[int, Dict[str, Dict[str, Any]]] = {}
    total_stable = 0
    total_variable = 0
    total_absent = 0
    total_unknown = 0

    for lt in layout_types:
        cluster_id = lt.cluster_id
        analysis = element_labels.get(cluster_id, [])

        smap = _classify_stability(analysis, lt, skeletons, single_doc)
        stability_maps[cluster_id] = smap

        for info in smap.values():
            c = info["classification"]
            if c == "stable":
                total_stable += 1
            elif c == "variable":
                total_variable += 1
            elif c == "absent":
                total_absent += 1
            else:
                total_unknown += 1

    context["_stability_map"] = stability_maps

    summary = {
        "clusters_classified": len(layout_types),
        "total_stable": total_stable,
        "total_variable": total_variable,
        "total_absent": total_absent,
        "total_unknown": total_unknown,
        "single_document": single_doc,
    }

    if emit:
        try:
            emit(
                {
                    "stage": 14,
                    "stage_name": "Stability Classification",
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
    """Replace stub Stage 14 with this implementation."""
    registry.remove_stage(14)
    registry.register_stage(
        stage_number=14,
        name="Stability Classification",
        block_id=4,
        estimated_duration=1.0,
        execute_fn=execute,
    )
