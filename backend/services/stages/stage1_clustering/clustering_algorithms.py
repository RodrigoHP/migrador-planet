"""Stage 1 — Clustering Algorithms sub-module.

Responsibilities:
  - Tolerant similarity matrix computation
  - Graph-based clustering (networkx)
  - Consensus check (hierarchical vs graph)
  - Representative selection

Story 41.3 — extracted from stage1_layout_clustering.py
"""

from __future__ import annotations

import logging

from models.pipeline_context import BlockInfo
from services.stages.stage1_clustering.page_preprocessing import ClusteringConfig, PageInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1.6 — Similarity Matrix
# ---------------------------------------------------------------------------


def _geometry_similarity(
    core_a: list[BlockInfo],
    core_b: list[BlockInfo],
    tolerance: float = 0.05,
    region_tolerance: float = 0.10,
) -> float:
    """Weighted geometry similarity with block matching (tolerant).

    Uses min_blocks as denominator when all unmatched blocks are content
    variation (same Y region), max_blocks when structural differences exist.
    """
    if not core_a and not core_b:
        return 1.0
    if not core_a or not core_b:
        return 0.0

    max_blocks = max(len(core_a), len(core_b))

    # Phase 1: Greedy nearest-neighbor matching
    matched = 0
    used_b: set[int] = set()
    unmatched_a: list[BlockInfo] = []

    sorted_a = sorted(core_a, key=lambda b: (b.y_center, b.x_center))

    for a in sorted_a:
        best_dist = float("inf")
        best_j = -1
        for j, b in enumerate(core_b):
            if j in used_b:
                continue
            dx = abs(a.x_center - b.x_center)
            dy = abs(a.y_center - b.y_center)
            if dx <= tolerance and dy <= tolerance:
                dist = dx + dy
                if dist < best_dist:
                    best_dist = dist
                    best_j = j
        if best_j >= 0:
            matched += 1
            used_b.add(best_j)
        else:
            unmatched_a.append(a)

    unmatched_b = [b for j, b in enumerate(core_b) if j not in used_b]

    # Phase 2: Classify unmatched as content variation vs structural diff.
    # Check each unmatched block against ALL blocks in the other document (not
    # just unmatched ones). This correctly handles list expansion: if instance B
    # has more list items than A, those extra items fall in regions where A has
    # activity → content variation, not structural diff.
    structural_diffs = 0
    for ua in unmatched_a:
        has_nearby = any(abs(ua.y_center - b.y_center) < region_tolerance for b in core_b)
        if not has_nearby:
            structural_diffs += 1

    for ub in unmatched_b:
        has_nearby = any(abs(ub.y_center - a.y_center) < region_tolerance for a in core_a)
        if not has_nearby:
            structural_diffs += 1

    # Always use min-denominator as base: content variation (extra list items in
    # one instance) does not reduce structural similarity. Only truly alien blocks
    # (no counterpart region in the other doc) incur a penalty.
    min_blocks = min(len(core_a), len(core_b))
    if min_blocks == 0:
        return 1.0
    base_score = matched / min_blocks

    if structural_diffs == 0:
        return base_score
    else:
        structural_penalty = (structural_diffs / max_blocks) * 0.3
        return max(0.0, base_score - structural_penalty)


def _density_similarity(
    core_a: list[BlockInfo],
    core_b: list[BlockInfo],
    body_height: float,
) -> float:
    """Density similarity in the body region only."""

    def _compute_density(blocks: list[BlockInfo]) -> float:
        if not blocks or body_height <= 0:
            return 0.0
        total_area = sum((b.bbox_norm[2] - b.bbox_norm[0]) * (b.bbox_norm[3] - b.bbox_norm[1]) for b in blocks)
        return float(total_area / body_height)

    d_a = _compute_density(core_a)
    d_b = _compute_density(core_b)

    if max(d_a, d_b) == 0:
        return 1.0
    return 1.0 - abs(d_a - d_b) / max(d_a, d_b)


def _compute_similarity(
    pages: list[PageInfo],
    header_end: float,
    footer_start: float,
    config: ClusteringConfig,
) -> list[list[float]]:
    """Step 1.6 — Compute tolerant similarity matrix.

    geometry_similarity * 0.8 + density_similarity * 0.2
    """
    processable = [pi for pi in pages if pi.is_processable]
    n = len(processable)
    sim_matrix = [[0.0] * n for _ in range(n)]

    body_height = max(footer_start - header_end, 0.01)

    for i in range(n):
        sim_matrix[i][i] = 1.0
        for j in range(i + 1, n):
            geo = _geometry_similarity(
                processable[i].core_blocks,
                processable[j].core_blocks,
                config.position_tolerance,
                config.structural_region_tolerance,
            )
            den = _density_similarity(
                processable[i].core_blocks,
                processable[j].core_blocks,
                body_height,
            )
            sim = 0.8 * geo + 0.2 * den
            sim_matrix[i][j] = sim
            sim_matrix[j][i] = sim

    return sim_matrix


# ---------------------------------------------------------------------------
# 1.7 — Graph Clustering
# ---------------------------------------------------------------------------


def _cluster_graph(
    sim_matrix: list[list[float]],
    config: ClusteringConfig,
) -> list[set[int]]:
    """Step 1.7 — Graph clustering via NetworkX connected components."""
    import networkx as nx

    n = len(sim_matrix)
    G = nx.Graph()
    for i in range(n):
        G.add_node(i)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i][j] >= config.clustering_threshold:
                G.add_edge(i, j, weight=sim_matrix[i][j])

    clusters = [set(c) for c in nx.connected_components(G)]
    return clusters


# ---------------------------------------------------------------------------
# 1.8 — Consensus Check
# ---------------------------------------------------------------------------


def _clusterings_agree(a: list[set[int]], b: list[set[int]]) -> bool:
    """Check if two clusterings produce the same partition."""
    a_sorted = sorted(sorted(s) for s in a)
    b_sorted = sorted(sorted(s) for s in b)
    return a_sorted == b_sorted


def _intersect_clusterings(a: list[set[int]], b: list[set[int]]) -> list[set[int]]:
    """Conservative intersection: only group together if BOTH methods agree."""
    result: list[set[int]] = []
    for sa in a:
        for sb in b:
            intersection = sa & sb
            if intersection:
                result.append(intersection)
    # Remove duplicates
    unique: list[set[int]] = []
    for s in result:
        if s not in unique:
            unique.append(s)
    return unique


def _consensus_check(
    sim_matrix: list[list[float]],
    graph_clusters: list[set[int]],
    config: ClusteringConfig,
) -> tuple[list[set[int]], bool]:
    """Step 1.8 — Hierarchical clustering validates graph result.

    Returns (consensus_clusters, consensus_agreed).
    """
    n = len(sim_matrix)
    if n <= 1:
        return graph_clusters, True

    try:
        import numpy as np
        from scipy.cluster.hierarchy import fcluster, linkage
        from scipy.spatial.distance import squareform

        # Convert similarity to distance
        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dist_matrix[i][j] = 1.0 - sim_matrix[i][j]

        # Make it a proper condensed distance matrix
        condensed = squareform(dist_matrix)
        Z = linkage(condensed, method="average")
        labels = fcluster(Z, t=1.0 - config.clustering_threshold, criterion="distance")

        hier_clusters: dict[int, set[int]] = {}
        for idx, label in enumerate(labels):
            hier_clusters.setdefault(int(label), set()).add(idx)
        hier_cluster_list = list(hier_clusters.values())

        # Check consensus: both methods agree
        agreed = _clusterings_agree(graph_clusters, hier_cluster_list)

        if agreed:
            return graph_clusters, True
        else:
            # Conservative: use intersection (finer clusters)
            consensus = _intersect_clusterings(graph_clusters, hier_cluster_list)
            return consensus, False

    except ImportError:
        logger.warning("scipy not available, skipping consensus check")
        return graph_clusters, True


# ---------------------------------------------------------------------------
# 1.9 — Representative Selection
# ---------------------------------------------------------------------------


def _select_representatives(
    clusters: list[set[int]],
    sim_matrix: list[list[float]],
    processable_pages: list[PageInfo],
) -> dict[int, int]:
    """Step 1.9 — Select representative via weighted degree (most connections)."""
    import networkx as nx

    n = len(sim_matrix)
    G = nx.Graph()
    for i in range(n):
        G.add_node(i)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i][j] > 0:
                G.add_edge(i, j, weight=sim_matrix[i][j])

    representatives: dict[int, int] = {}
    for cluster_idx, members in enumerate(clusters):
        if len(members) == 1:
            representatives[cluster_idx] = next(iter(members))
            continue

        # Weighted degree within cluster
        best_node = -1
        best_degree = -1.0
        for node in members:
            degree = sum(sim_matrix[node][other] for other in members if other != node)
            if degree > best_degree:
                best_degree = degree
                best_node = node

        representatives[cluster_idx] = best_node

    return representatives
