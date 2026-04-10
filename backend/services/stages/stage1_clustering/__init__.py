"""Stage 1 Clustering package.

Re-exports all public symbols for backward-compatible access.

Story 41.3 — stage1_layout_clustering.py decomposed into sub-modules.
"""

from services.stages.stage1_clustering.cluster_validation import (
    _auto_correct,
    _cluster_quality_score,
    _compute_confidence,
    _homogeneity_check,
    _llm_validate,
    _phash_crosscheck,
    _validate_representatives,
)
from services.stages.stage1_clustering.clustering_algorithms import (
    _cluster_graph,
    _clusterings_agree,
    _compute_similarity,
    _consensus_check,
    _density_similarity,
    _geometry_similarity,
    _intersect_clusterings,
    _select_representatives,
)
from services.stages.stage1_clustering.page_preprocessing import (
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

__all__ = [
    # page_preprocessing
    "ABSTRACTION_PATTERNS",
    "ClusteringConfig",
    "PageInfo",
    "_abstract_content",
    "_abstract_text",
    "_classify_pages",
    "_detect_body_region",
    "_extract_blocks",
    "_filter_regions",
    "_normalize",
    # clustering_algorithms
    "_cluster_graph",
    "_clusterings_agree",
    "_compute_similarity",
    "_consensus_check",
    "_density_similarity",
    "_geometry_similarity",
    "_intersect_clusterings",
    "_select_representatives",
    # cluster_validation
    "_auto_correct",
    "_cluster_quality_score",
    "_compute_confidence",
    "_homogeneity_check",
    "_llm_validate",
    "_phash_crosscheck",
    "_validate_representatives",
]
