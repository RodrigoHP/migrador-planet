"""Stage 2 — Drawn Elements & Quality Check sub-module.

Responsibilities:
  - Color conversion utilities (_color_to_int)
  - Geometry utilities (_line_orientation)
  - Drawn elements extraction via get_drawings() (2.9a)
  - Quality check validation of extracted page data (2.9b)

Story 41.3 — split from grid_table_extraction.py to keep files under 500 LOC.
"""

from __future__ import annotations

import logging
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Color / Geometry Utilities
# ---------------------------------------------------------------------------


def _color_to_int(color: Any) -> int | None:
    """Convert PyMuPDF color (tuple of 0-1 floats) to RGB int."""
    if color is None:
        return None
    if isinstance(color, (int, float)):
        # Grayscale
        v = int(round(float(color) * 255))
        return (v << 16) | (v << 8) | v
    if isinstance(color, (tuple, list)):
        if len(color) == 1:
            v = int(round(color[0] * 255))
            return (v << 16) | (v << 8) | v
        if len(color) >= 3:
            r = int(round(color[0] * 255))
            g = int(round(color[1] * 255))
            b = int(round(color[2] * 255))
            return (r << 16) | (g << 8) | b
    return None


def _line_orientation(p1: Any, p2: Any) -> str | None:
    """Determine line orientation: horizontal, vertical, or diagonal."""
    threshold = 2.0  # points
    dx = abs(p1.x - p2.x)
    dy = abs(p1.y - p2.y)

    if dy < threshold and dx > threshold:
        return "horizontal"
    if dx < threshold and dy > threshold:
        return "vertical"
    if dx > threshold and dy > threshold:
        return "diagonal"
    return None


# ---------------------------------------------------------------------------
# 2.9a — Drawn Elements
# ---------------------------------------------------------------------------


def _extract_drawn_elements(page: fitz.Page) -> list[dict[str, Any]] | None:
    """Extract drawn elements (lines, rects, curves) via get_drawings()."""
    try:
        drawings = page.get_drawings()
    except Exception:
        return None

    if not drawings:
        return None

    elements: list[dict[str, Any]] = []
    for d in drawings:
        fill_color = d.get("fill")
        stroke_color = d.get("color")
        width = d.get("width", 0.0)

        fill_int = _color_to_int(fill_color) if fill_color else None
        stroke_int = _color_to_int(stroke_color) if stroke_color else None
        # width may be None for filled shapes without explicit stroke width
        safe_width = round(float(width or 0.0), 2)

        for item in d.get("items", []):
            kind = item[0]  # "l" = line, "re" = rect, "c" = curve, "qu" = quad
            if kind == "l":
                p1, p2 = item[1], item[2]
                bbox = [
                    min(p1.x, p2.x),
                    min(p1.y, p2.y),
                    max(p1.x, p2.x),
                    max(p1.y, p2.y),
                ]
                orientation = _line_orientation(p1, p2)
                elements.append(
                    {
                        "type": "line",
                        "bbox": [round(v, 2) for v in bbox],
                        "orientation": orientation,
                        "fill_color": fill_int,
                        "stroke_color": stroke_int,
                        "width": safe_width,
                    }
                )
            elif kind == "re":
                rect = item[1]
                elements.append(
                    {
                        "type": "rect",
                        "bbox": [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)],
                        "orientation": None,
                        "fill_color": fill_int,
                        "stroke_color": stroke_int,
                        "width": safe_width,
                    }
                )
            elif kind == "c":
                # Curve: use bounding points
                points = item[1:]
                if points:
                    xs = [p.x for p in points if hasattr(p, "x")]
                    ys = [p.y for p in points if hasattr(p, "y")]
                    if xs and ys:
                        elements.append(
                            {
                                "type": "curve",
                                "bbox": [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)],
                                "orientation": None,
                                "fill_color": fill_int,
                                "stroke_color": stroke_int,
                                "width": safe_width,
                            }
                        )

    return elements if elements else None


# ---------------------------------------------------------------------------
# 2.9b — Quality Check
# ---------------------------------------------------------------------------


def _quality_check(
    page_data: dict[str, Any],
    page_index: int,
    pdf_id: str,
) -> list[dict[str, Any]]:
    """Run 5 quality validations on extracted page data.

    1. text_blocks not empty
    2. encoding OK (no replacement chars)
    3. no duplicate text blocks
    4. tables valid (if any)
    5. images have bbox (if any)
    """
    warnings: list[dict[str, Any]] = []
    page_key = f"{pdf_id}:{page_index}"

    # 1. text_blocks not empty
    text_blocks = page_data.get("text_blocks", [])
    if not text_blocks:
        warnings.append(
            {
                "page_key": page_key,
                "page_index": page_index,
                "type": "empty_page",
                "severity": "warning",
                "message": f"Page {page_index}: no text blocks extracted",
            }
        )

    # 2. encoding check
    for block in text_blocks:
        text = block.get("text", "")
        if "\ufffd" in text or "\x00" in text:
            warnings.append(
                {
                    "page_key": page_key,
                    "page_index": page_index,
                    "type": "encoding_issue",
                    "severity": "warning",
                    "message": f"Page {page_index}: encoding issues detected in text block",
                }
            )
            break

    # 3. duplicate detection
    texts = [b["text"].strip() for b in text_blocks if b.get("text")]
    if texts:
        unique = set(texts)
        dup_ratio = 1.0 - len(unique) / len(texts)
        if dup_ratio > 0.5 and len(texts) > 3:
            warnings.append(
                {
                    "page_key": page_key,
                    "page_index": page_index,
                    "type": "duplicate_text",
                    "severity": "warning",
                    "message": f"Page {page_index}: {dup_ratio:.0%} duplicate text blocks detected",
                }
            )

    # 4. tables validation
    tables = page_data.get("tables", [])
    for tbl in tables:
        if not tbl.get("rows") and not tbl.get("headers"):
            warnings.append(
                {
                    "page_key": page_key,
                    "page_index": page_index,
                    "type": "invalid_table",
                    "severity": "warning",
                    "message": f"Page {page_index}: table {tbl.get('table_id', '?')} has no rows or headers",
                }
            )

    # 5. images bbox validation
    images = page_data.get("images", [])
    invalid_bbox_count = sum(1 for img in images if not img.get("bbox_valid", True))
    if invalid_bbox_count > 0:
        warnings.append(
            {
                "page_key": page_key,
                "page_index": page_index,
                "type": "invalid_image_bbox",
                "severity": "warning",
                "message": f"Page {page_index}: {invalid_bbox_count} image(s) with invalid bbox",
            }
        )

    return warnings
