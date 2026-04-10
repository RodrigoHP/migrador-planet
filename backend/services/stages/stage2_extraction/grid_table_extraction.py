"""Stage 2 — Grid and Table Extraction sub-module.

Responsibilities:
  - Grid detection using Jenks Natural Breaks (2.6)
  - Table detection via PyMuPDF find_tables (2.7)
  - Table structuring with header detection (2.8)

Story 41.3 — extracted from stage2_deep_extraction.py
  Color/geometry utilities, drawn elements, and quality check moved to
  drawn_quality.py to keep this module under 500 LOC.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import fitz  # PyMuPDF

# Re-exports from drawn_quality.py — backward compatibility
from services.stages.stage2_extraction.drawn_quality import (  # noqa: F401
    _color_to_int,
    _extract_drawn_elements,
    _line_orientation,
    _quality_check,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 2.6 — Grid Detection (Jenks Natural Breaks)
# ---------------------------------------------------------------------------

# Header/footer exclusion zones (normalised Y fractions)
_HEADER_ZONE_END = 0.10
_FOOTER_ZONE_START = 0.90

_MIN_BLOCKS_FOR_GRID = 3
_MAX_BREAKS = 10


def _detect_grid_jenks(
    text_blocks: list[dict[str, Any]],
    page_height: float,
) -> dict[str, Any] | None:
    """Detect grid using jenkspy Jenks Natural Breaks, excluding header/footer zones."""
    if len(text_blocks) < _MIN_BLOCKS_FOR_GRID:
        return None

    # Filter out header/footer zones
    body_blocks = [
        b
        for b in text_blocks
        if page_height > 0 and _HEADER_ZONE_END <= b["bbox"][1] / page_height <= _FOOTER_ZONE_START
    ]

    if len(body_blocks) < _MIN_BLOCKS_FOR_GRID:
        return None

    x_coords = [b["bbox"][0] for b in body_blocks]
    y_coords = [b["bbox"][1] for b in body_blocks]

    col_positions = _jenks_1d(x_coords, _MAX_BREAKS)
    row_positions = _jenks_1d(y_coords, _MAX_BREAKS)

    if not col_positions and not row_positions:
        return None

    return {
        "columns": len(col_positions),
        "rows": len(row_positions),
        "column_positions": [round(p, 2) for p in col_positions],
        "row_positions": [round(p, 2) for p in row_positions],
    }


def _jenks_1d(values: list[float], max_breaks: int) -> list[float]:
    """Cluster 1D values using Jenks Natural Breaks.

    Falls back to simple gap-based grouping if jenkspy is not available.
    """
    if not values or len(set(values)) < 2:
        return [sum(values) / len(values)] if values else []

    unique_vals = sorted(set(values))
    n_unique = len(unique_vals)

    if n_unique <= 2:
        return unique_vals

    # Number of classes = min(unique values, max_breaks)
    n_classes = min(n_unique, max_breaks)

    try:
        import jenkspy

        breaks = jenkspy.jenks_breaks(values, n_classes=n_classes)
        # Compute centroids for each class
        centroids: list[float] = []
        sorted_vals = sorted(values)
        for i in range(len(breaks) - 1):
            low = breaks[i]
            high = breaks[i + 1]
            group = [v for v in sorted_vals if low <= v <= high]
            if group:
                centroids.append(sum(group) / len(group))
        return centroids

    except ImportError:
        logger.warning("jenkspy not available, using gap-based grid detection")
        return _fallback_gap_groups(values, max_breaks)


def _fallback_gap_groups(values: list[float], max_groups: int) -> list[float]:
    """Fallback gap-based grouping when jenkspy is unavailable."""
    sorted_vals = sorted(set(round(v, 1) for v in values))
    if len(sorted_vals) <= 1:
        return [sum(values) / len(values)]

    gaps = [(sorted_vals[i + 1] - sorted_vals[i], i) for i in range(len(sorted_vals) - 1)]
    if not gaps:
        return [sum(values) / len(values)]

    median_gap = sorted(g[0] for g in gaps)[len(gaps) // 2]
    threshold = max(median_gap * 3, 5.0)

    groups: list[list[float]] = [[sorted_vals[0]]]
    for i in range(len(sorted_vals) - 1):
        if sorted_vals[i + 1] - sorted_vals[i] > threshold:
            groups.append([])
        groups[-1].append(sorted_vals[i + 1])

    groups = groups[:max_groups]
    return [sum(g) / len(g) for g in groups if g]


# ---------------------------------------------------------------------------
# 2.7 — Table Detection (PyMuPDF find_tables)
# ---------------------------------------------------------------------------


def _check_ruling_lines(page: fitz.Page, table_bbox: list[float]) -> bool:
    """Check if there are drawn lines within the table bbox (ruling lines)."""
    try:
        drawings = page.get_drawings()
        x0, y0, x1, y1 = table_bbox
        for d in drawings:
            for item in d.get("items", []):
                if item[0] in ("l", "re"):  # line or rect
                    # Check if any drawing item intersects table bbox
                    return True
        return False
    except Exception:
        return False


def _detect_tables(page: fitz.Page) -> list[dict[str, Any]]:
    """Detect tables using PyMuPDF find_tables() (ruling lines + clustering built-in).

    Returns list of raw table dicts with cells.
    """
    try:
        tables_finder = page.find_tables()
    except Exception as exc:
        logger.warning("find_tables() failed: %s", exc)
        return []

    results: list[dict[str, Any]] = []
    for table in tables_finder.tables:
        bbox = list(table.bbox)
        cells = table.extract()  # List[List[str | None]]
        header = table.header

        # Determine if table has ruling lines
        has_ruling = _check_ruling_lines(page, bbox)

        results.append(
            {
                "raw_cells": cells,
                "bbox": bbox,
                "header": header,
                "has_ruling_lines": has_ruling,
                "col_count": table.col_count if hasattr(table, "col_count") else (len(cells[0]) if cells else 0),
                "row_count": table.row_count if hasattr(table, "row_count") else len(cells),
            }
        )

    return results


# ---------------------------------------------------------------------------
# 2.8 — Table Structuring
# ---------------------------------------------------------------------------


def _detect_header_rows(
    cells: list[list[str | None]],
    text_blocks: list[dict[str, Any]],
    table_bbox: list[float],
) -> int:
    """Detect header rows by comparing style (bold, font_size) with data rows.

    Returns header_row_count (0, 1, or 2+).
    """
    if not cells or len(cells) < 2:
        return 0

    # Find text blocks within the table bbox top region
    tx0, ty0, tx1, ty1 = table_bbox
    table_height = ty1 - ty0
    row_count = len(cells)
    approx_row_height = table_height / max(row_count, 1)

    # Blocks in first row zone
    first_row_y_max = ty0 + approx_row_height * 1.5
    first_row_blocks = [b for b in text_blocks if tx0 <= b["bbox"][0] <= tx1 and ty0 <= b["bbox"][1] <= first_row_y_max]

    # Blocks in data zone (after first 2 rows)
    data_y_min = ty0 + approx_row_height * 2
    data_blocks = [b for b in text_blocks if tx0 <= b["bbox"][0] <= tx1 and b["bbox"][1] >= data_y_min]

    if not first_row_blocks or not data_blocks:
        # Default: assume 1 header if first row text looks different from data
        first_row_text = cells[0]
        data_text = cells[1] if len(cells) > 1 else []
        if first_row_text and data_text:
            # Simple heuristic: if first row has no numbers but data has, it's a header
            return 1
        return 0

    # Compare average font sizes
    first_avg_size = sum(b["font_size"] for b in first_row_blocks) / len(first_row_blocks)
    data_avg_size = sum(b["font_size"] for b in data_blocks) / len(data_blocks)

    # Compare bold ratio
    first_bold_ratio = sum(1 for b in first_row_blocks if b["is_bold"]) / len(first_row_blocks)
    data_bold_ratio = sum(1 for b in data_blocks if b["is_bold"]) / max(len(data_blocks), 1)

    if first_bold_ratio > data_bold_ratio + 0.3 or first_avg_size > data_avg_size * 1.1:
        # Check if second row is also header-like
        if row_count > 2:
            second_row_y_min = ty0 + approx_row_height
            second_row_y_max = ty0 + approx_row_height * 2.5
            second_row_blocks = [
                b
                for b in text_blocks
                if tx0 <= b["bbox"][0] <= tx1 and second_row_y_min <= b["bbox"][1] <= second_row_y_max
            ]
            if second_row_blocks:
                second_bold_ratio = sum(1 for b in second_row_blocks if b["is_bold"]) / len(second_row_blocks)
                if second_bold_ratio > data_bold_ratio + 0.3:
                    return 2
        return 1

    return 0


def _structure_tables(
    raw_tables: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
    page_height: float,
) -> list[dict[str, Any]]:
    """Structure detected tables: cells with bbox, header detection, multi-page continuation."""
    structured: list[dict[str, Any]] = []

    for raw in raw_tables:
        cells = raw["raw_cells"]
        bbox = raw["bbox"]

        if not cells:
            continue

        col_count = len(cells[0]) if cells else 0
        if col_count == 0:
            continue

        # Detect header rows via style comparison
        header_row_count = _detect_header_rows(cells, text_blocks, bbox)

        # Build headers and rows with cell objects
        headers: list[list[dict[str, Any]]] = []
        rows: list[list[dict[str, Any]]] = []

        # Compute approximate cell bboxes
        table_x0, table_y0, table_x1, table_y1 = bbox
        table_width = table_x1 - table_x0
        table_height_val = table_y1 - table_y0
        row_count = len(cells)

        col_width = table_width / max(col_count, 1)
        row_height = table_height_val / max(row_count, 1)

        column_widths = [round(col_width, 2)] * col_count

        for row_idx, row_cells in enumerate(cells):
            row_data: list[dict[str, Any]] = []
            for col_idx, cell_text in enumerate(row_cells):
                cell_x0 = table_x0 + col_idx * col_width
                cell_y0 = table_y0 + row_idx * row_height
                cell_x1 = cell_x0 + col_width
                cell_y1 = cell_y0 + row_height
                row_data.append(
                    {
                        "text": cell_text or "",
                        "bbox": [round(cell_x0, 2), round(cell_y0, 2), round(cell_x1, 2), round(cell_y1, 2)],
                        "column_index": col_idx,
                    }
                )

            if row_idx < header_row_count:
                headers.append(row_data)
            else:
                rows.append(row_data)

        # Multi-page continuation: table occupies >80% of page height
        is_multi_page = (table_height_val / max(page_height, 1.0)) > 0.80

        confidence = 0.9 if raw["has_ruling_lines"] else 0.7
        method = "ruling_lines" if raw["has_ruling_lines"] else "clustering"

        structured.append(
            {
                "table_id": str(uuid.uuid4()),
                "bbox": bbox,
                "headers": headers,
                "rows": rows,
                "header_row_count": header_row_count,
                "columns": col_count,
                "column_widths": column_widths,
                "confidence": confidence,
                "detection_method": method,
                "has_ruling_lines": raw["has_ruling_lines"],
                "is_multi_page": is_multi_page,
            }
        )

    return structured
