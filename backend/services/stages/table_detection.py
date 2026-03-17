"""Stage 17 — Table Detection.

Identifies table regions within each page of each ParsedDocument by combining
three evidence sources:

1. Grid lines  — GridInfo.columns > 1 and rows > 2 on a page (strong evidence).
2. X-alignment — TextBlocks whose left-x coordinates cluster into >= 2 columns,
   and whose top-y coordinates show >= 2 distinct rows.
3. Repeating pattern — groups of consecutive TextBlocks with similar widths and
   vertical spacing (typical of table rows).

Each evidence source contributes a partial score (0.0–1.0).  The combined score
determines whether a region qualifies as a table (threshold 0.5).

Reads:  context["parsed_documents"]  — List[Dict] (ParsedDocument serialised)
Writes: context["tables"]            — List[Dict] (DetectedTable serialised)
        context["parsed_documents"]  — unchanged (pass-through)

Registers itself as Stage 17 (Block 5).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Tuple

from models.detected_table import DetectedTable, TableCell, TableRow
from models.parsed_document import GridInfo, ParsedDocument, ParsedPage, TextBlock


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TABLE_SCORE_THRESHOLD = 0.5
MIN_COLUMNS_FOR_TABLE = 2
MIN_ROWS_FOR_TABLE = 2
CLUSTER_GAP_THRESHOLD = 15.0   # pts — minimum gap to form a new column/row cluster
PATTERN_REPEAT_MIN = 3         # consecutive blocks with similar structure


# ---------------------------------------------------------------------------
# Helpers — clustering
# ---------------------------------------------------------------------------


def _cluster_positions(values: List[float], gap: float = CLUSTER_GAP_THRESHOLD) -> List[List[float]]:
    """Group sorted float values into clusters separated by at least *gap* pts."""
    if not values:
        return []
    sorted_vals = sorted(values)
    clusters: List[List[float]] = [[sorted_vals[0]]]
    for v in sorted_vals[1:]:
        if v - clusters[-1][-1] > gap:
            clusters.append([])
        clusters[-1].append(v)
    return clusters


def _centroid(group: List[float]) -> float:
    return sum(group) / len(group)


# ---------------------------------------------------------------------------
# Evidence source 1 — grid_info
# ---------------------------------------------------------------------------


def _score_grid(grid: GridInfo | None) -> float:
    """Score from 0.0 to 1.0 based on grid_info columns/rows."""
    if grid is None:
        return 0.0
    if grid.columns >= MIN_COLUMNS_FOR_TABLE and grid.rows >= MIN_ROWS_FOR_TABLE:
        # More columns / rows → higher confidence, capped at 1.0
        col_factor = min(grid.columns / 4.0, 1.0)
        row_factor = min(grid.rows / 6.0, 1.0)
        return round((col_factor + row_factor) / 2.0, 3)
    return 0.0


# ---------------------------------------------------------------------------
# Evidence source 2 — X/Y alignment of TextBlocks
# ---------------------------------------------------------------------------


def _score_alignment(text_blocks: List[TextBlock]) -> Tuple[float, List[float], List[float]]:
    """Return (score, col_centroids, row_centroids) from block positions.

    Only rows with at least MIN_COLUMNS_FOR_TABLE blocks are kept as valid
    table rows to avoid treating isolated blocks as table rows.
    """
    if len(text_blocks) < 4:
        return 0.0, [], []

    x_vals = [b.bbox[0] for b in text_blocks]
    y_vals = [b.bbox[1] for b in text_blocks]

    col_clusters = _cluster_positions(x_vals)
    all_row_clusters = _cluster_positions(y_vals, gap=5.0)

    # Determine which column centroids exist (for row density check)
    n_cols_total = len(col_clusters)

    # Only count rows that have at least MIN_COLUMNS_FOR_TABLE blocks
    # (filters out isolated blocks that form spurious singleton rows)
    min_blocks_per_row = max(MIN_COLUMNS_FOR_TABLE, round(n_cols_total * 0.5))
    valid_row_clusters = [g for g in all_row_clusters if len(g) >= min_blocks_per_row]

    n_cols = n_cols_total
    n_rows = len(valid_row_clusters)

    if n_cols < MIN_COLUMNS_FOR_TABLE or n_rows < MIN_ROWS_FOR_TABLE:
        return 0.0, [], []

    col_centroids = [_centroid(g) for g in col_clusters]
    row_centroids = [_centroid(g) for g in valid_row_clusters]

    col_factor = min(n_cols / 4.0, 1.0)
    row_factor = min(n_rows / 8.0, 1.0)
    score = round((col_factor + row_factor) / 2.0, 3)
    return score, col_centroids, row_centroids


# ---------------------------------------------------------------------------
# Evidence source 3 — repeating pattern
# ---------------------------------------------------------------------------


def _score_pattern(text_blocks: List[TextBlock]) -> float:
    """Detect repeating block-width/spacing pattern typical of table rows."""
    if len(text_blocks) < PATTERN_REPEAT_MIN:
        return 0.0

    # Sort by y then x
    sorted_blocks = sorted(text_blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

    # Group blocks into rows by y proximity
    row_groups: List[List[TextBlock]] = []
    for blk in sorted_blocks:
        if not row_groups or blk.bbox[1] - row_groups[-1][0].bbox[1] > 5.0:
            row_groups.append([blk])
        else:
            row_groups[-1].append(blk)

    if len(row_groups) < PATTERN_REPEAT_MIN:
        return 0.0

    # Compare column counts across consecutive rows
    col_counts = [len(g) for g in row_groups]
    dominant = max(set(col_counts), key=col_counts.count)
    if dominant < MIN_COLUMNS_FOR_TABLE:
        return 0.0

    matching_rows = sum(1 for c in col_counts if c == dominant)
    consistency = matching_rows / len(col_counts)

    # Score: consistency weighted by row count
    row_factor = min(len(row_groups) / 8.0, 1.0)
    return round(consistency * row_factor, 3)


# ---------------------------------------------------------------------------
# Bounding box of a group of TextBlocks
# ---------------------------------------------------------------------------


def _bbox_of_blocks(blocks: List[TextBlock]) -> Tuple[float, float, float, float]:
    x0 = min(b.bbox[0] for b in blocks)
    y0 = min(b.bbox[1] for b in blocks)
    x1 = max(b.bbox[2] for b in blocks)
    y1 = max(b.bbox[3] for b in blocks)
    return (x0, y0, x1, y1)


# ---------------------------------------------------------------------------
# Core detection per page
# ---------------------------------------------------------------------------


def detect_tables_on_page(
    page: ParsedPage,
    pdf_index: int,
) -> List[DetectedTable]:
    """Run all three evidence sources and return DetectedTable objects for this page."""
    blocks = page.text_blocks
    if not blocks:
        return []

    grid_score = _score_grid(page.grid_info)
    align_score, col_centroids, row_centroids = _score_alignment(blocks)
    pattern_score = _score_pattern(blocks)

    # Weighted combination: re-normalise weights when grid_info is absent so
    # that alignment + pattern can still exceed the threshold on their own.
    if grid_score > 0:
        combined_score = round(
            grid_score * 0.45 + align_score * 0.35 + pattern_score * 0.20,
            3,
        )
    else:
        # No grid lines available — rely on alignment (65%) + pattern (35%)
        combined_score = round(align_score * 0.65 + pattern_score * 0.35, 3)

    if combined_score < TABLE_SCORE_THRESHOLD:
        return []

    # Determine primary detection method for metadata
    scores = {
        "grid_lines": grid_score,
        "alignment": align_score,
        "pattern": pattern_score,
    }
    method = max(scores, key=scores.__getitem__)
    if sum(s > 0 for s in scores.values()) > 1:
        method = "combined"

    # Only include blocks that fit within the detected column/row alignment pattern
    # when alignment was a primary signal (avoids bloating bbox with outliers).
    if col_centroids and row_centroids:
        table_blocks = _filter_aligned_blocks(blocks, col_centroids, row_centroids)
        if len(table_blocks) < 4:
            table_blocks = blocks
    else:
        table_blocks = blocks

    table_bbox = _bbox_of_blocks(table_blocks)

    # Build structured rows from alignment clusters (or simple grouping)
    if col_centroids and row_centroids:
        structured_rows, headers = _structure_rows(table_blocks, col_centroids, row_centroids)
        col_widths = _column_widths(col_centroids, table_bbox)
    else:
        structured_rows, headers = _simple_rows(table_blocks)
        col_widths = []

    table = DetectedTable(
        table_id=str(uuid.uuid4()),
        page_number=page.page_number,
        pdf_index=pdf_index,
        bbox=table_bbox,
        headers=headers,
        rows=structured_rows,
        column_widths=col_widths,
        is_multi_page=False,
        continuation_pages=[],
        confidence=combined_score,
        detection_method=method,
    )
    return [table]


# ---------------------------------------------------------------------------
# Row/cell structuring helpers
# ---------------------------------------------------------------------------


def _structure_rows(
    blocks: List[TextBlock],
    col_centroids: List[float],
    row_centroids: List[float],
) -> Tuple[List[List[str]], List[str]]:
    """Assign each block to (row_index, col_index) and build a 2-D list."""
    n_rows = len(row_centroids)
    n_cols = len(col_centroids)

    grid: List[List[str]] = [[""] * n_cols for _ in range(n_rows)]

    for blk in blocks:
        bx = blk.bbox[0]
        by = blk.bbox[1]

        # Find nearest column centroid
        col_idx = min(range(n_cols), key=lambda i: abs(col_centroids[i] - bx))
        # Find nearest row centroid
        row_idx = min(range(n_rows), key=lambda i: abs(row_centroids[i] - by))

        existing = grid[row_idx][col_idx]
        grid[row_idx][col_idx] = (existing + " " + blk.text).strip() if existing else blk.text

    # Heuristic: first row is header if it has significantly larger/bolder text
    # (simplified: always treat first row as header when there are >= 2 rows)
    if n_rows >= 2:
        headers = grid[0]
        data_rows = grid[1:]
    else:
        headers = []
        data_rows = grid

    return data_rows, headers


def _simple_rows(blocks: List[TextBlock]) -> Tuple[List[List[str]], List[str]]:
    """Fallback: one block per row, single column."""
    sorted_blocks = sorted(blocks, key=lambda b: b.bbox[1])
    rows = [[b.text] for b in sorted_blocks]
    if len(rows) >= 2:
        return rows[1:], rows[0]
    return rows, []


def _filter_aligned_blocks(
    blocks: List[TextBlock],
    col_centroids: List[float],
    row_centroids: List[float],
    col_tolerance: float = 40.0,
    row_tolerance: float = 15.0,
) -> List[TextBlock]:
    """Return only blocks whose x/y coords are close to at least one centroid pair."""
    result = []
    for blk in blocks:
        bx = blk.bbox[0]
        by = blk.bbox[1]
        near_col = any(abs(bx - cx) <= col_tolerance for cx in col_centroids)
        near_row = any(abs(by - ry) <= row_tolerance for ry in row_centroids)
        if near_col and near_row:
            result.append(blk)
    return result


def _column_widths(col_centroids: List[float], table_bbox: Tuple[float, float, float, float]) -> List[float]:
    """Estimate column widths from centroid spacing."""
    if len(col_centroids) < 2:
        return [table_bbox[2] - table_bbox[0]]
    widths = []
    for i in range(len(col_centroids) - 1):
        widths.append(round(col_centroids[i + 1] - col_centroids[i], 2))
    # Last column: from last centroid to right edge
    widths.append(round(table_bbox[2] - col_centroids[-1], 2))
    return widths


# ---------------------------------------------------------------------------
# Multi-page linking
# ---------------------------------------------------------------------------


def _link_multi_page(tables: List[DetectedTable]) -> None:
    """Mark tables that span multiple pages by checking structural similarity.

    A table on page N is considered to continue on page N+1 if:
    - The table on page N ends within 15% of the page height from the bottom
      (approximated: y1 of bbox is > 80% of typical page height 842pts).
    - The next page has a table with a similar number of columns.
    """
    by_page: Dict[int, List[DetectedTable]] = {}
    for t in tables:
        by_page.setdefault(t.page_number, []).append(t)

    page_numbers = sorted(by_page.keys())
    for i, pg in enumerate(page_numbers[:-1]):
        next_pg = page_numbers[i + 1]
        if next_pg != pg + 1:
            continue  # non-consecutive pages
        for tbl in by_page[pg]:
            # Check if table ends near the bottom of the page (y1 > 700 pts)
            if tbl.bbox[3] < 700.0:
                continue
            # Find a matching table on the next page with same column count
            n_cols = len(tbl.column_widths)
            for next_tbl in by_page[next_pg]:
                if abs(len(next_tbl.column_widths) - n_cols) <= 1:
                    tbl.is_multi_page = True
                    if next_pg not in tbl.continuation_pages:
                        tbl.continuation_pages.append(next_pg)
                    break


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 17 executor — Table Detection."""
    emit = context.get("emit_progress")
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])

    all_tables: List[Dict[str, Any]] = []
    total_detected = 0
    multi_page_count = 0

    for doc_dict in parsed_documents:
        parsed = ParsedDocument(**doc_dict)
        doc_tables: List[DetectedTable] = []

        for page in parsed.pages:
            page_tables = detect_tables_on_page(page, parsed.pdf_index)
            doc_tables.extend(page_tables)

        # Link multi-page tables within this document
        _link_multi_page(doc_tables)

        total_detected += len(doc_tables)
        multi_page_count += sum(1 for t in doc_tables if t.is_multi_page)

        for t in doc_tables:
            all_tables.append(t.model_dump())

    context["tables"] = all_tables

    summary = {
        "tables_detected": total_detected,
        "multi_page_tables": multi_page_count,
        "documents_processed": len(parsed_documents),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 17,
                    "stage_name": "Table Detection",
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
    """Replace stub Stage 17 with this implementation."""
    registry.remove_stage(17)
    registry.register_stage(
        stage_number=17,
        name="Table Detection",
        block_id=5,
        estimated_duration=1.5,
        execute_fn=execute,
    )
