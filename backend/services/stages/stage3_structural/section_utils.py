"""Stage 3 — Section Utilities sub-module.

Responsibilities:
  - Zone building from visual regions or thresholds
  - Section detection via drawn lines or gap analysis
  - Barcode utilities
  - Image, table, chart, barcode, SVG assignment to sections

Semantic name/XSD binding utilities live in semantic_utils.py.

Story 41.3 — extracted from stage3_structural_analysis.py
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.stages.stage3_structural.semantic_utils import (  # noqa: F401 (re-exports for backward compat)
    _apply_suggested_bindings,
    _extract_semantic_name,
    _get_conditional_pdfs,
    _infer_section_name,
    _levenshtein_similarity,
    _normalize_text,
    _section_variant,
    _suggest_xsd_binding,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Zone building
# ---------------------------------------------------------------------------


def _zones_from_visual_regions(
    regions: list[dict[str, Any]],
    page_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build zones from visual analysis regions."""
    page_height = page_data.get("height", 842.0)
    page_width = page_data.get("width", 595.0)
    text_blocks = page_data.get("text_blocks", [])

    zone_map: dict[str, dict[str, Any]] = {}

    for region in regions:
        rtype = region["type"]
        if rtype == "header":
            ztype = "header"
        elif rtype == "footer":
            ztype = "footer"
        elif rtype in ("body", "table_area", "image_area", "form_area"):
            ztype = "flow"
        elif rtype == "sidebar":
            ztype = "flow"
        else:
            ztype = "flow"

        if ztype not in zone_map:
            zone_map[ztype] = {
                "type": ztype,
                "source": "visual",
                "bbox": list(region["bbox"]),
                "blocks": [],
            }
        else:
            existing = zone_map[ztype]["bbox"]
            existing[0] = min(existing[0], region["bbox"][0])
            existing[1] = min(existing[1], region["bbox"][1])
            existing[2] = max(existing[2], region["bbox"][2])
            existing[3] = max(existing[3], region["bbox"][3])

    if "flow" not in zone_map:
        header_end = (
            zone_map.get("header", {}).get("bbox", [0, 0, 0, 0])[3] if "header" in zone_map else int(page_height * 0.10)
        )
        footer_start = (
            zone_map.get("footer", {}).get("bbox", [0, 0, 0, 0])[1] if "footer" in zone_map else int(page_height * 0.90)
        )
        zone_map["flow"] = {
            "type": "flow",
            "source": "visual",
            "bbox": [0, header_end, int(page_width), footer_start],
            "blocks": [],
        }

    zones = list(zone_map.values())
    for block in text_blocks:
        block_cy = (block["bbox"][1] + block["bbox"][3]) / 2
        assigned = False
        for zone in zones:
            zy0, zy1 = zone["bbox"][1], zone["bbox"][3]
            if zy0 <= block_cy <= zy1:
                zone["blocks"].append(block)
                assigned = True
                break
        if not assigned:
            for zone in zones:
                if zone["type"] == "flow":
                    zone["blocks"].append(block)
                    break

    zone_order = {"header": 0, "flow": 1, "footer": 2}
    zones.sort(key=lambda z: zone_order.get(z["type"], 1))

    return zones


def _zones_from_thresholds(
    page_data: dict[str, Any],
    header_pct: float = 0.10,
    footer_pct: float = 0.90,
) -> list[dict[str, Any]]:
    """Fallback: build zones from adaptive thresholds."""
    page_height = page_data.get("height", 842.0)
    page_width = page_data.get("width", 595.0)
    text_blocks = page_data.get("text_blocks", [])

    header_end = page_height * header_pct
    footer_start = page_height * footer_pct

    zones = [
        {"type": "header", "source": "threshold", "bbox": [0, 0, page_width, header_end], "blocks": []},
        {"type": "flow", "source": "threshold", "bbox": [0, header_end, page_width, footer_start], "blocks": []},
        {"type": "footer", "source": "threshold", "bbox": [0, footer_start, page_width, page_height], "blocks": []},
    ]

    for block in text_blocks:
        block_cy = (block["bbox"][1] + block["bbox"][3]) / 2
        if block_cy <= header_end:
            zones[0]["blocks"].append(block)
        elif block_cy >= footer_start:
            zones[2]["blocks"].append(block)
        else:
            zones[1]["blocks"].append(block)

    return zones


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------


def _split_by_drawn_lines(
    blocks: list[dict[str, Any]],
    h_lines: list[float],
) -> list[dict[str, Any]]:
    """Split blocks into sections using horizontal separator lines."""
    if not blocks:
        return []

    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])
    sorted_lines = sorted(h_lines)

    sections = []
    current_blocks: list[dict[str, Any]] = []

    line_idx = 0
    for block in sorted_blocks:
        block_cy = (block["bbox"][1] + block["bbox"][3]) / 2
        while line_idx < len(sorted_lines) and block_cy > sorted_lines[line_idx]:
            if current_blocks:
                sections.append({"blocks": current_blocks})
                current_blocks = []
            line_idx += 1
        current_blocks.append(block)

    if current_blocks:
        sections.append({"blocks": current_blocks})

    return sections


def _split_by_gap(
    blocks: list[dict[str, Any]],
    gap_threshold: float,
) -> list[dict[str, Any]]:
    """Split blocks into sections by proportional gap."""
    if not blocks:
        return []

    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])
    sections = []
    current_blocks = [sorted_blocks[0]]

    for i in range(1, len(sorted_blocks)):
        prev_bottom = sorted_blocks[i - 1]["bbox"][3]
        curr_top = sorted_blocks[i]["bbox"][1]
        gap = curr_top - prev_bottom

        if gap > gap_threshold:
            sections.append({"blocks": current_blocks})
            current_blocks = [sorted_blocks[i]]
        else:
            current_blocks.append(sorted_blocks[i])

    if current_blocks:
        sections.append({"blocks": current_blocks})

    return sections


def _get_horizontal_separators(
    drawn_elements: Any | None,
    zone_bbox: list[float],
) -> list[float]:
    """Extract horizontal line Y positions from drawn_elements within zone bbox."""
    if not drawn_elements:
        return []

    if isinstance(drawn_elements, dict):
        h_lines = drawn_elements.get("horizontal_lines", [])
    elif isinstance(drawn_elements, list):
        h_lines = [el for el in drawn_elements if isinstance(el, dict) and el.get("orientation") == "horizontal"]
    else:
        return []

    if not h_lines:
        return []

    zy0, zy1 = zone_bbox[1], zone_bbox[3]
    result = []

    for line in h_lines:
        y = line.get("y") or line.get("bbox", [0, 0, 0, 0])[1]
        if zy0 < y < zy1:
            result.append(y)

    return result


# ---------------------------------------------------------------------------
# Barcode utilities
# ---------------------------------------------------------------------------


def _extract_barcode_value(
    page_data: dict[str, Any],
    barcode_bbox: list[float],
) -> str | None:
    """Find the numeric barcode value from text blocks near the barcode bbox."""
    bx0, by0, bx1, by1 = barcode_bbox
    margin = (by1 - by0) * 0.5

    best: tuple[float, str] | None = None
    for block in page_data.get("text_blocks", []):
        tbbox = block.get("bbox", [0, 0, 0, 0])
        if tbbox[2] <= bx0 or tbbox[0] >= bx1:
            continue
        if tbbox[3] < by0 - margin or tbbox[1] > by1 + margin:
            continue

        text = block.get("text", "").strip()
        if not text:
            continue

        digit_count = sum(1 for c in text if c.isdigit())
        if digit_count < 8:
            continue

        numeric_ratio = digit_count / len(text)
        if numeric_ratio < 0.6:
            continue

        score = numeric_ratio * digit_count
        if best is None or score > best[0]:
            best = (score, re.sub(r"[^0-9]", "", text))

    return best[1] if best else None


def _barcode_bboxes_from_tree(node: dict[str, Any]) -> list[list[float]]:
    """Recursively collect all barcode node bboxes from a tree node."""
    bboxes: list[list[float]] = []
    if node.get("type") == "barcode":
        bb = node.get("bbox")
        if bb and len(bb) == 4:
            bboxes.append(list(bb))
    for child in node.get("children", []):
        if isinstance(child, dict):
            bboxes.extend(_barcode_bboxes_from_tree(child))
    return bboxes


def _line_inside_any_barcode(
    line_bbox: list[float],
    barcode_bboxes: list[list[float]],
) -> bool:
    """Return True if the line's centre falls within any barcode bbox."""
    cx = (line_bbox[0] + line_bbox[2]) / 2
    cy = (line_bbox[1] + line_bbox[3]) / 2
    for bx0, by0, bx1, by1 in barcode_bboxes:
        if bx0 <= cx <= bx1 and by0 <= cy <= by1:
            return True
    return False


# ---------------------------------------------------------------------------
# Section assignment utilities
# ---------------------------------------------------------------------------


def _bbox_contains(outer: list[float], inner: list[float], tolerance: float = 2.0) -> bool:
    """Return True if outer bbox fully contains inner bbox (within tolerance)."""
    return (
        inner[0] >= outer[0] - tolerance
        and inner[1] >= outer[1] - tolerance
        and inner[2] <= outer[2] + tolerance
        and inner[3] <= outer[3] + tolerance
    )


def _assign_images_to_sections(
    zones: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> None:
    """Distribute images from Stage 2 into sections by position."""
    for img in images:
        bbox = img.get("bbox", [0, 0, 0, 0])
        img_cy = (bbox[1] + bbox[3]) / 2
        best_section = None
        best_overlap = 0

        for zone in zones:
            for section in zone.get("sections", []):
                if not section.get("blocks"):
                    continue
                sy0 = min(b["bbox"][1] for b in section["blocks"])
                sy1 = max(b["bbox"][3] for b in section["blocks"])
                overlap = max(0, min(bbox[3], sy1) - max(bbox[1], sy0))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_section = section

        if best_section is None:
            for zone in zones:
                zy0, zy1 = zone["bbox"][1], zone["bbox"][3]
                if zy0 <= img_cy <= zy1 and zone.get("sections"):
                    best_section = zone["sections"][0]
                    break

        if best_section:
            best_section.setdefault("images", []).append(img)


def _assign_tables_to_sections(
    zones: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> None:
    """Distribute tables from Stage 2 into sections by Y-position overlap."""
    for table in tables:
        bbox = table.get("bbox", [0, 0, 0, 0])
        best_section = None
        best_overlap = 0

        for zone in zones:
            for section in zone.get("sections", []):
                if not section.get("blocks"):
                    continue
                sy0 = min(b["bbox"][1] for b in section["blocks"])
                sy1 = max(b["bbox"][3] for b in section["blocks"])
                overlap = max(0, min(bbox[3], sy1) - max(bbox[1], sy0))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_section = section

        if best_section is None:
            table_cy = (bbox[1] + bbox[3]) / 2
            for zone in zones:
                zy0, zy1 = zone["bbox"][1], zone["bbox"][3]
                if zy0 <= table_cy <= zy1 and zone.get("sections"):
                    best_section = zone["sections"][0]
                    break

        if best_section is not None:
            best_section.setdefault("tables", []).append(table)


def _assign_visual_elements_to_sections(
    zones: list[dict[str, Any]],
    visual_analysis: dict[str, dict[str, Any]],
    page_key: str,
) -> None:
    """Convert GPT-4o visual elements (charts, barcodes, svgs) into section entries."""
    va = visual_analysis.get(page_key)
    if not va or not va.get("regions"):
        return

    for region in va["regions"]:
        rtype = region.get("type", "")
        if rtype not in ("chart_area", "barcode_area", "svg_area"):
            continue

        ry0, ry1 = region["bbox"][1], region["bbox"][3]
        region_cy = (ry0 + ry1) / 2

        for zone in zones:
            zy0, zy1 = zone["bbox"][1], zone["bbox"][3]
            if zy0 <= region_cy <= zy1:
                for section in zone.get("sections", []):
                    if rtype == "chart_area":
                        section.setdefault("charts", []).append(
                            {
                                "bbox": region["bbox"],
                                "description": region.get("description", ""),
                                "chart_type": region.get("chart_type", "bar"),
                                "confidence": region.get("confidence", 50),
                            }
                        )
                    elif rtype == "barcode_area":
                        section.setdefault("barcodes", []).append(
                            {
                                "bbox": region["bbox"],
                                "description": region.get("description", ""),
                                "barcode_format": region.get("barcode_format", "CODE128"),
                                "confidence": region.get("confidence", 50),
                            }
                        )
                    elif rtype == "svg_area":
                        section.setdefault("svgs", []).append(
                            {
                                "bbox": region["bbox"],
                                "description": region.get("description", ""),
                                "confidence": region.get("confidence", 50),
                            }
                        )
                    break
                break
