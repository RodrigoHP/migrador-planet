"""Stage 9 — Representative Selection.

For each cluster produced by Stage 8 (Page Clustering), selects:
    - 1 primary representative — the page closest to the cluster centroid,
      preferring pages from different PDFs when multiple PDFs are present.
    - Up to 2 secondary representatives for broader coverage.

Writes context["layout_types"] as a list of LayoutType objects (kept as
Python objects in context["_layout_type_objects"] and serialised to dicts
in context["layout_types"]).

Registers itself in the default_registry as Stage 9 (Block 3).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from models.layout_type import LayoutFingerprint, LayoutSkeleton, LayoutType

# Maximum secondary representatives per cluster
_MAX_SECONDARY = 2

# Heuristic name mapping based on cluster characteristics
_NAME_HEURISTICS = [
    # (condition_fn, name)
    (lambda fp: fp.table_count >= 2.0, "Transações"),
    (lambda fp: fp.table_count >= 1.0, "Extrato"),
    (lambda fp: fp.header_blocks >= 5.0, "Cabeçalho"),
    (lambda fp: fp.column_count >= 3, "Detalhamento"),
    (lambda fp: fp.footer_present, "Rodapé Legal"),
    (lambda fp: fp.header_blocks <= 1.0 and fp.table_count < 1.0, "Capa"),
    (lambda fp: fp.body_zone_ratio >= 0.8, "Resumo"),
]

_DEFAULT_NAMES = ["Layout A", "Layout B", "Layout C", "Layout D",
                  "Layout E", "Layout F", "Layout G", "Layout H"]


def _name_for_fingerprint(fp: LayoutFingerprint, cluster_id: int) -> str:
    for condition, name in _NAME_HEURISTICS:
        try:
            if condition(fp):
                return name
        except Exception:  # noqa: BLE001
            continue
    idx = cluster_id % len(_DEFAULT_NAMES)
    return _DEFAULT_NAMES[idx]


# ---------------------------------------------------------------------------
# Distance helper
# ---------------------------------------------------------------------------


def _euclidean(a: List[float], b: List[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


# ---------------------------------------------------------------------------
# Centroid computation
# ---------------------------------------------------------------------------


def _compute_centroid(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []
    n = len(vectors)
    dim = len(vectors[0])
    centroid = [0.0] * dim
    for v in vectors:
        for i, val in enumerate(v):
            centroid[i] += val
    return [c / n for c in centroid]


# ---------------------------------------------------------------------------
# Representative selection
# ---------------------------------------------------------------------------


def _select_representatives(
    cluster_id: int,
    skeletons_in_cluster: List[LayoutSkeleton],
    centroid: List[float],
    n_secondary: int = _MAX_SECONDARY,
) -> Tuple[Dict[str, int], List[Dict[str, int]]]:
    """Return (primary_rep, secondary_reps) for the given cluster."""
    if not skeletons_in_cluster:
        return {"pdf_index": 0, "page_number": 0}, []

    # Gather unique pdf indices present in this cluster
    pdf_indices = list({s.pdf_index for s in skeletons_in_cluster})
    multiple_pdfs = len(pdf_indices) > 1

    # Score each skeleton: (distance_to_centroid, pdf_index, skeleton)
    scored: List[Tuple[float, int, LayoutSkeleton]] = []
    for s in skeletons_in_cluster:
        vec = s.to_feature_vector()
        dist = _euclidean(vec, centroid) if centroid else 0.0
        scored.append((dist, s.pdf_index, s))

    scored.sort(key=lambda t: t[0])

    # Primary: closest to centroid; if multiple PDFs, prefer diverse pdf_index
    primary_skeleton: Optional[LayoutSkeleton] = None
    if multiple_pdfs:
        # Try to pick a primary from each distinct pdf (first unique)
        seen_pdfs: set = set()
        for dist, pdf_idx, s in scored:
            if pdf_idx not in seen_pdfs:
                primary_skeleton = s
                seen_pdfs.add(pdf_idx)
                break
    if primary_skeleton is None:
        primary_skeleton = scored[0][2]

    primary_rep = {
        "pdf_index": primary_skeleton.pdf_index,
        "page_number": primary_skeleton.page_number,
    }

    # Secondaries: next closest, preferring different PDFs when possible
    secondaries: List[Dict[str, int]] = []
    used_pdf_indices = {primary_skeleton.pdf_index}
    for dist, pdf_idx, s in scored[1:]:
        if len(secondaries) >= n_secondary:
            break
        if s is primary_skeleton:
            continue
        # Prefer a page from a different PDF than what we already have
        if multiple_pdfs and pdf_idx in used_pdf_indices and len(scored) > n_secondary + 1:
            continue
        secondaries.append(
            {"pdf_index": s.pdf_index, "page_number": s.page_number}
        )
        used_pdf_indices.add(pdf_idx)

    return primary_rep, secondaries


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 9 executor — Representative Selection.

    Reads:
        context["_skeleton_objects"] — list of LayoutSkeleton
        context["cluster_labels"]    — list of int (same length)

    Writes:
        context["_layout_type_objects"] — list of LayoutType (Python)
        context["layout_types"]         — list of dicts (serialised)
    """
    emit = context.get("emit_progress")

    skeletons: List[LayoutSkeleton] = context.get("_skeleton_objects", [])
    labels: List[int] = context.get("cluster_labels", [])

    if not skeletons or not labels:
        context["_layout_type_objects"] = []
        context["layout_types"] = []
        return {"num_layout_types": 0}

    # Group skeletons by cluster label
    cluster_map: Dict[int, List[LayoutSkeleton]] = {}
    for skeleton, label in zip(skeletons, labels):
        cluster_map.setdefault(label, []).append(skeleton)

    layout_types: List[LayoutType] = []

    for cluster_id in sorted(cluster_map.keys()):
        cluster_skeletons = cluster_map[cluster_id]

        # Feature vectors for centroid calculation
        vectors = [s.to_feature_vector() for s in cluster_skeletons]
        centroid = _compute_centroid(vectors)

        # Build a temporary fingerprint placeholder (filled in by Stage 10)
        fp = LayoutFingerprint()

        primary_rep, secondary_reps = _select_representatives(
            cluster_id, cluster_skeletons, centroid
        )

        all_pages = [
            {"pdf_index": s.pdf_index, "page_number": s.page_number}
            for s in cluster_skeletons
        ]

        name = _name_for_fingerprint(fp, cluster_id)

        lt = LayoutType(
            cluster_id=cluster_id,
            name=name,
            representative_page=primary_rep,
            fingerprint=fp,
            page_count=len(cluster_skeletons),
            pages=all_pages,
        )
        # Store centroid on the object for use by Stage 10
        lt._centroid = centroid
        lt._cluster_skeletons = cluster_skeletons

        layout_types.append(lt)

    context["_layout_type_objects"] = layout_types
    context["layout_types"] = [lt.to_dict() for lt in layout_types]

    if emit:
        try:
            emit(
                {
                    "stage": 9,
                    "stage_name": "Representative Selection",
                    "status": "completed",
                    "summary": {"num_layout_types": len(layout_types)},
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return {"num_layout_types": len(layout_types)}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 9 in the given registry with this implementation."""
    registry.remove_stage(9)
    registry.register_stage(
        stage_number=9,
        name="Representative Selection",
        block_id=3,
        estimated_duration=0.5,
        execute_fn=execute,
    )
