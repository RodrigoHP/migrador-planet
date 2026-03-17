"""Stage 6 — Grid Detection.

Clusters the X and Y coordinates of all TextBlocks on each page using
KMeans (scikit-learn) to detect the column and row grid structure.

Registers itself in the default_registry as Stage 6 (Block 2).
"""

from __future__ import annotations

from typing import Any, Dict, List

from models.parsed_document import GridInfo, ParsedDocument, ParsedPage, TextBlock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CLUSTERS = 10
MIN_BLOCKS_FOR_CLUSTERING = 3


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _optimal_k(values: List[float], max_k: int) -> int:
    """Estimate the number of natural clusters using gap analysis.

    Groups values that are within a threshold of each other, then counts
    how many distinct groups there are (up to max_k).
    """
    if not values:
        return 1
    sorted_vals = sorted(set(round(v, 1) for v in values))
    if len(sorted_vals) <= 1:
        return 1

    # Compute the median gap between consecutive unique values
    gaps = [sorted_vals[i + 1] - sorted_vals[i] for i in range(len(sorted_vals) - 1)]
    median_gap = sorted(gaps)[len(gaps) // 2]
    # Natural gap threshold: a gap is "large" if it is > 3x the median gap
    threshold = max(median_gap * 3, 5.0)  # at least 5 pts

    groups = 1
    for gap in gaps:
        if gap > threshold:
            groups += 1

    return min(groups, max_k)


def _cluster_1d(values: List[float], max_k: int) -> List[float]:
    """Cluster a 1-D list of coordinates; return sorted cluster centroids."""
    if not values:
        return []

    n_clusters = _optimal_k(values, max_k)

    if n_clusters <= 1:
        return [float(sum(values) / len(values))]

    try:
        from sklearn.cluster import KMeans
        import numpy as np

        X = np.array(values).reshape(-1, 1)
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        km.fit(X)
        centers = sorted(float(c[0]) for c in km.cluster_centers_)
        return centers
    except ImportError:
        # Fallback: use gap-based natural groups without sklearn
        sorted_vals = sorted(values)
        gaps = [sorted_vals[i + 1] - sorted_vals[i] for i in range(len(sorted_vals) - 1)]
        median_gap = sorted(gaps)[len(gaps) // 2]
        threshold = max(median_gap * 3, 5.0)

        groups: List[List[float]] = [[sorted_vals[0]]]
        for i, gap in enumerate(gaps):
            if gap > threshold:
                groups.append([])
            groups[-1].append(sorted_vals[i + 1])

        return [sum(g) / len(g) for g in groups]


def detect_grid(text_blocks: List[TextBlock]) -> GridInfo:
    """Compute GridInfo from a list of TextBlocks."""
    if len(text_blocks) < MIN_BLOCKS_FOR_CLUSTERING:
        return GridInfo(
            columns=1,
            rows=1,
            column_positions=[],
            row_positions=[],
        )

    x_coords = [b.bbox[0] for b in text_blocks]  # left edge
    y_coords = [b.bbox[1] for b in text_blocks]  # top edge

    col_positions = _cluster_1d(x_coords, MAX_CLUSTERS)
    row_positions = _cluster_1d(y_coords, MAX_CLUSTERS)

    return GridInfo(
        columns=len(col_positions),
        rows=len(row_positions),
        column_positions=[round(p, 2) for p in col_positions],
        row_positions=[round(p, 2) for p in row_positions],
    )


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 6 executor — Grid Detection."""
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])

    updated_docs: List[Dict[str, Any]] = []
    total_cols = 0
    total_rows = 0
    page_count = 0

    for doc_dict in parsed_documents:
        parsed = ParsedDocument(**doc_dict)
        new_pages: List[ParsedPage] = []

        for page in parsed.pages:
            grid = detect_grid(page.text_blocks)
            total_cols += grid.columns
            total_rows += grid.rows
            page_count += 1

            new_pages.append(
                ParsedPage(
                    page_number=page.page_number,
                    text_blocks=page.text_blocks,
                    images=page.images,
                    fonts=page.fonts,
                    grid_info=grid,
                    screenshot_path=page.screenshot_path,
                )
            )

        parsed.pages = new_pages
        updated_docs.append(parsed.to_context_dict())

    context["parsed_documents"] = updated_docs

    avg_cols = round(total_cols / max(page_count, 1), 2)
    avg_rows = round(total_rows / max(page_count, 1), 2)

    return {
        "pages_analysed": page_count,
        "avg_columns": avg_cols,
        "avg_rows": avg_rows,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 6 in the given registry with this implementation."""
    registry.remove_stage(6)
    registry.register_stage(
        stage_number=6,
        name="Grid Detection",
        block_id=2,
        estimated_duration=1.5,
        execute_fn=execute,
    )
