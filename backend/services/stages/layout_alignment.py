"""Stage 12 — Layout Alignment.

Normalises coordinate offsets between multiple PDFs within the same cluster.
When only one PDF is present, the stage is trivial (identity transform).

Reads:
    context["_layout_type_objects"]  — List[LayoutType]
    context["_skeleton_objects"]     — List[LayoutSkeleton]

Writes:
    context["alignment_offsets"]     — Dict[cluster_id → Dict[pdf_index → (dx, dy)]]
    context["_aligned"]              — True (flag for downstream stages)

Registers itself as Stage 12 (Block 4).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from models.layout_type import LayoutSkeleton, LayoutType


# ---------------------------------------------------------------------------
# Alignment helpers
# ---------------------------------------------------------------------------


def _compute_cluster_offsets(
    skeletons: List[LayoutSkeleton],
    cluster_pages: List[Dict[str, int]],
) -> Dict[int, Tuple[float, float]]:
    """Compute (dx, dy) offset per pdf_index within a cluster.

    The reference PDF is the one with pdf_index == min(pdf_indices).
    All other PDFs' median top-left bbox coordinates are shifted to match
    the reference.

    Returns a dict: pdf_index → (dx, dy) where dx/dy are added to normalise.
    """
    # Index skeletons by (pdf_index, page_number)
    skel_map: Dict[Tuple[int, int], LayoutSkeleton] = {
        (s.pdf_index, s.page_number): s for s in skeletons
    }

    # Group pages by pdf_index
    pdf_pages: Dict[int, List[LayoutSkeleton]] = {}
    for page_ref in cluster_pages:
        key = (page_ref["pdf_index"], page_ref["page_number"])
        skel = skel_map.get(key)
        if skel is None:
            continue
        pdf_pages.setdefault(page_ref["pdf_index"], []).append(skel)

    if not pdf_pages:
        return {}

    # Compute median first-block top-left per pdf_index
    def _median_origin(skels: List[LayoutSkeleton]) -> Tuple[float, float]:
        xs = []
        ys = []
        for s in skels:
            if s.text_blocks:
                _, bbox = s.text_blocks[0]
                xs.append(bbox[0])
                ys.append(bbox[1])
        if not xs:
            return 0.0, 0.0
        xs_sorted = sorted(xs)
        ys_sorted = sorted(ys)
        mid = len(xs_sorted) // 2
        return xs_sorted[mid], ys_sorted[mid]

    pdf_indices = sorted(pdf_pages.keys())
    ref_idx = pdf_indices[0]
    ref_x, ref_y = _median_origin(pdf_pages[ref_idx])

    offsets: Dict[int, Tuple[float, float]] = {}
    for pdf_idx in pdf_indices:
        ox, oy = _median_origin(pdf_pages[pdf_idx])
        offsets[pdf_idx] = (ref_x - ox, ref_y - oy)

    return offsets


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 12 executor — Layout Alignment.

    For each cluster, computes coordinate normalisation offsets so that
    equivalent positions across PDFs are comparable.
    With a single PDF the offsets are all (0, 0) (trivial).
    """
    emit = context.get("emit_progress")

    layout_types: List[LayoutType] = context.get("_layout_type_objects", [])
    skeletons: List[LayoutSkeleton] = context.get("_skeleton_objects", [])

    # Detect single-document mode
    pdf_indices = {s.pdf_index for s in skeletons}
    single_doc = len(pdf_indices) <= 1

    alignment_offsets: Dict[int, Dict[int, Tuple[float, float]]] = {}

    for lt in layout_types:
        cluster_id = lt.cluster_id
        if single_doc:
            # Trivial alignment — no transformation needed
            alignment_offsets[cluster_id] = {idx: (0.0, 0.0) for idx in pdf_indices}
        else:
            offsets = _compute_cluster_offsets(skeletons, lt.pages)
            alignment_offsets[cluster_id] = offsets

    context["alignment_offsets"] = alignment_offsets
    context["_aligned"] = True

    if single_doc:
        context.setdefault("intelligence_metadata", {})["single_document"] = True
        context["intelligence_metadata"]["reduced_accuracy"] = True

    summary = {
        "clusters_aligned": len(layout_types),
        "single_document": single_doc,
        "pdf_count": len(pdf_indices),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 12,
                    "stage_name": "Layout Alignment",
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
    """Replace stub Stage 12 with this implementation."""
    registry.remove_stage(12)
    registry.register_stage(
        stage_number=12,
        name="Layout Alignment",
        block_id=4,
        estimated_duration=1.5,
        execute_fn=execute,
    )
