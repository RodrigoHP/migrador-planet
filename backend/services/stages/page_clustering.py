"""Stage 8 — Page Clustering.

Clusters all page skeletons into layout groups using KMeans on a 5-dimensional
feature vector:
    [num_blocks, avg_font_size, table_count, text_density, header_height_ratio]

The optimal number of clusters is chosen by maximising the silhouette score
over a candidate range [2, min(8, n_pages)].

For PDFs with 500+ total pages, a ~50-page sample is used for fitting; the
remaining pages are then assigned to the nearest centroid.

Registers itself in the default_registry as Stage 8 (Block 3).
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from models.layout_type import LayoutSkeleton

# Sampling threshold and target for large PDFs
_LARGE_PDF_THRESHOLD = 500
_SAMPLE_SIZE = 50

# KMeans cluster range
_MIN_CLUSTERS = 2
_MAX_CLUSTERS = 8


# ---------------------------------------------------------------------------
# Feature helpers
# ---------------------------------------------------------------------------


def _skeletons_to_feature_matrix(
    skeletons: List[LayoutSkeleton],
) -> "list[list[float]]":
    return [s.to_feature_vector() for s in skeletons]


# ---------------------------------------------------------------------------
# Clustering logic
# ---------------------------------------------------------------------------


def _best_k(X: "Any", max_k: int) -> int:  # X is numpy array
    """Return the k in [2, max_k] that maximises silhouette score.

    Falls back to k=1 when max_k < 2 (i.e. only 1 page).
    """
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
    except ImportError as exc:
        raise ImportError(
            "scikit-learn is required for clustering. "
            "Install with: pip install scikit-learn"
        ) from exc

    if max_k < 2:
        return 1

    # silhouette_score requires 2 <= n_labels <= n_samples - 1
    # For fewer than 3 samples we cannot evaluate silhouette at all
    if len(X) < 3:
        return 1

    best_k = 2
    best_score = -1.0
    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        n_unique = len(set(labels))
        # silhouette requires 2 <= n_labels <= n_samples - 1
        if n_unique < 2 or n_unique >= len(X):
            continue
        score = float(silhouette_score(X, labels))
        if score > best_score:
            best_score = score
            best_k = k
    return best_k


def _cluster_skeletons(
    skeletons: List[LayoutSkeleton],
) -> List[int]:
    """Return cluster label (int) for each skeleton, in the same order."""
    try:
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise ImportError(
            "numpy and scikit-learn are required. "
            "Install with: pip install numpy scikit-learn"
        ) from exc

    n = len(skeletons)
    if n == 0:
        return []
    if n == 1:
        return [0]

    feature_matrix = _skeletons_to_feature_matrix(skeletons)
    X = np.array(feature_matrix, dtype=float)

    # Standardise features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    large_pdf = n >= _LARGE_PDF_THRESHOLD

    if large_pdf:
        # Sample ~50 pages for fitting
        sample_indices = random.sample(range(n), min(_SAMPLE_SIZE, n))
        X_sample = X_scaled[sample_indices]
    else:
        sample_indices = list(range(n))
        X_sample = X_scaled

    max_k = min(_MAX_CLUSTERS, len(sample_indices))
    k = _best_k(X_sample, max_k)

    if k == 1:
        return [0] * n

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_sample)

    if large_pdf:
        # Assign all pages to nearest centroid
        labels = km.predict(X_scaled).tolist()
    else:
        labels = km.labels_.tolist()

    return [int(label) for label in labels]


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 8 executor — Page Clustering.

    Reads context["_skeleton_objects"] (list of LayoutSkeleton).
    Writes context["cluster_labels"] = list of int (one per skeleton).
    """
    emit = context.get("emit_progress")

    skeletons: List[LayoutSkeleton] = context.get("_skeleton_objects", [])

    if not skeletons:
        context["cluster_labels"] = []
        return {"num_clusters": 0, "total_pages": 0}

    labels = _cluster_skeletons(skeletons)
    context["cluster_labels"] = labels

    num_clusters = len(set(labels)) if labels else 0

    if emit:
        try:
            emit(
                {
                    "stage": 8,
                    "stage_name": "Page Clustering",
                    "status": "completed",
                    "summary": {
                        "num_clusters": num_clusters,
                        "total_pages": len(skeletons),
                    },
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return {
        "num_clusters": num_clusters,
        "total_pages": len(skeletons),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 8 in the given registry with this implementation."""
    registry.remove_stage(8)
    registry.register_stage(
        stage_number=8,
        name="Page Clustering",
        block_id=3,
        estimated_duration=1.0,
        execute_fn=execute,
    )
