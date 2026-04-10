"""Stage 5 -- CSS Generation sub-module (Step 5.2).

Responsibilities:
  - _step_5_2_css_from_extraction: generate CSS from extracted fonts, colors, drawn elements

Color/font utilities (_color_int_to_hex, _sanitize_font_class, _font_class_with_style)
live in html_helpers.py.

Story 41.3 -- extracted from stage5_template_generation.py
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from models.pipeline_context import LayoutTypeInfo
from services.stages.stage5_template.html_helpers import (
    _A4_HEIGHT_PTS,
    _A4_WIDTH_PTS,
    _BASE_CSS_RESET,
    _SCALE_X,
    _SCALE_Y,
    _color_int_to_hex,
    _sanitize_font_class,
)

logger = logging.getLogger(__name__)


def _step_5_2_css_from_extraction(
    enriched_documents: list[dict[str, Any]],
    visual_analysis: dict[str, dict[str, Any]] | None,
    layout_types: list[LayoutTypeInfo],
) -> tuple[str, dict[tuple, str], dict[int, str]]:
    """5.2 -- Generate CSS from extracted data (NOT hardcoded).

    Sources:
    - text_blocks[].font_name -> font-family classes
    - text_blocks[].color -> color classes
    - drawn_elements[type=line] -> border rules
    - drawn_elements[type=rect, fill_color] -> background-color
    - visual_regions -> header/footer heights
    - pages[].width/height -> page dimensions
    - text alignment from positional analysis

    Note: @font-face declarations are intentionally NOT generated because
    Planet Express PDFs use standard system fonts (Helvetica, Arial, Times,
    Courier, etc.) which do not require custom font loading.

    Returns:
        Tuple of (css_string, border_class_map, bg_class_map).
        - border_class_map: {(stroke_color_int, orientation) -> "border-N"}
        - bg_class_map: {fill_color_int -> "bg-N"}
        These maps allow step 5.1 to apply the corresponding CSS classes
        to line and rect HTML elements.
    """
    css_parts: list[str] = [_BASE_CSS_RESET]

    # Collect data from all representative pages
    # font_style_counter tracks (font_name, is_bold, is_italic) tuples
    font_style_counter: Counter = Counter()
    color_set: set[int] = set()
    font_sizes: dict[str, float] = {}
    page_widths: list[float] = []
    page_heights: list[float] = []
    drawn_lines: list[dict[str, Any]] = []
    drawn_rects: list[dict[str, Any]] = []
    right_aligned_blocks: int = 0
    center_aligned_blocks: int = 0
    total_blocks: int = 0

    for doc in enriched_documents:
        for page in doc.get("pages", []):
            if not page.get("is_representative", True):
                continue

            page_w = float(page.get("width", _A4_WIDTH_PTS) or _A4_WIDTH_PTS)
            page_h = float(page.get("height", _A4_HEIGHT_PTS) or _A4_HEIGHT_PTS)
            page_widths.append(page_w)
            page_heights.append(page_h)

            for block in page.get("text_blocks", []):
                font_name = block.get("font_name", "")
                if font_name:
                    is_bold = bool(block.get("is_bold", False))
                    is_italic = bool(block.get("is_italic", False))
                    font_key = (font_name, is_bold, is_italic)
                    font_style_counter[font_key] += 1
                    fs = block.get("font_size")
                    if fs and font_name not in font_sizes:
                        font_sizes[font_name] = float(fs)

                color = block.get("color")
                if color is not None and isinstance(color, int):
                    color_set.add(color)

                # Positional analysis for alignment
                bbox = block.get("bbox")
                if bbox and len(bbox) >= 4:
                    total_blocks += 1
                    x0, _, x1, _ = bbox[:4]
                    x_center = (float(x0) + float(x1)) / 2.0
                    if x_center > page_w * 0.70:
                        right_aligned_blocks += 1
                    elif abs(x_center - page_w * 0.5) < page_w * 0.05:
                        center_aligned_blocks += 1

            # Collect drawn elements
            for elem in page.get("drawn_elements", []) or []:
                if not isinstance(elem, dict):
                    continue
                elem_type = elem.get("type", "")
                if elem_type == "line":
                    drawn_lines.append(elem)
                elif elem_type == "rect" and elem.get("fill_color") is not None:
                    drawn_rects.append(elem)

    # 1. Page dimensions from actual pages
    if page_widths and page_heights:
        avg_w = round(sum(page_widths) / len(page_widths))
        avg_h = round(sum(page_heights) / len(page_heights))
        px_w = round(avg_w * _SCALE_X)
        px_h = round(avg_h * _SCALE_Y)
        css_parts.append(f".page {{ width: {px_w}px; height: {px_h}px; }}")

    # 2. Zone heights from visual_analysis
    header_height_px = None
    footer_height_px = None
    if visual_analysis:
        for page_key, va in visual_analysis.items():
            for region in va.get("regions", []):
                region_type = region.get("type", "")
                bbox = region.get("bbox")
                if bbox and len(bbox) >= 4:
                    # bbox in pixel coords relative to image
                    _, y0, _, y1 = bbox[:4]
                    h = abs(float(y1) - float(y0))
                    if region_type == "header" and header_height_px is None:
                        header_height_px = round(h)
                    elif region_type == "footer" and footer_height_px is None:
                        footer_height_px = round(h)

    if header_height_px is None:
        # Fallback: 15% of page
        header_height_px = round(1123 * 0.15)
    if footer_height_px is None:
        footer_height_px = round(1123 * 0.10)

    css_parts.append(f".header {{ height: {header_height_px}px; }}")
    # .flow keeps top:0 from _BASE_CSS_RESET -- children use full-page coords (fitz y=0 at top)
    css_parts.append(f".footer {{ height: {footer_height_px}px; }}")

    # 3. Font classes from extracted fonts (NOT hardcoded Arial)
    # Grouped by (font_name, is_bold, is_italic) -- generates suffixed classes
    for (font_name, is_bold, is_italic), count in font_style_counter.most_common(40):
        safe_class = _sanitize_font_class(font_name)
        if not safe_class:
            continue
        # Suffix: -b for bold, -i for italic, -bi for both
        suffix = ""
        if is_bold and is_italic:
            suffix = "-bi"
        elif is_bold:
            suffix = "-b"
        elif is_italic:
            suffix = "-i"
        clean_name = re.sub(r"^[A-Z]{6}\+", "", font_name)
        fs = font_sizes.get(font_name)
        size_rule = f" font-size: {fs}pt;" if fs else ""
        weight_rule = " font-weight: bold;" if is_bold else ""
        style_rule = " font-style: italic;" if is_italic else ""
        css_parts.append(
            f".f-{safe_class}{suffix} {{ font-family: '{clean_name}', sans-serif;{size_rule}{weight_rule}{style_rule} }}"
        )

    # 4. Color classes from extracted colors (NOT hardcoded #000)
    for color_int in sorted(color_set):
        hex_str = _color_int_to_hex(color_int)
        css_parts.append(f".c-{hex_str} {{ color: #{hex_str}; }}")

    # 5. Border rules from drawn_elements[type=line]
    border_index = 0
    border_class_map: dict[tuple, str] = {}
    for line in drawn_lines[:20]:  # limit to avoid bloat
        orientation = line.get("orientation", "horizontal")
        stroke_color = line.get("stroke_color")
        width = line.get("width", 1.0)
        if stroke_color is not None:
            key = (stroke_color, orientation)
            if key not in border_class_map:
                hex_str = _color_int_to_hex(stroke_color)
                side = "bottom" if orientation == "horizontal" else "right"
                css_parts.append(f".border-{border_index} {{ border-{side}: {width}pt solid #{hex_str}; }}")
                border_class_map[key] = f"border-{border_index}"
                border_index += 1

    # 6. Background rules from drawn_elements[type=rect, fill_color]
    bg_index = 0
    bg_class_map: dict[int, str] = {}
    for rect in drawn_rects[:10]:
        fill = rect.get("fill_color")
        if fill is not None:
            if fill not in bg_class_map:
                hex_str = _color_int_to_hex(fill)
                css_parts.append(f".bg-{bg_index} {{ background-color: #{hex_str}; }}")
                bg_class_map[fill] = f"bg-{bg_index}"
                bg_index += 1

    # 7. Text alignment hints
    if total_blocks > 0:
        if right_aligned_blocks / total_blocks > 0.3:
            css_parts.append(".text-right { text-align: right; }")
        if center_aligned_blocks / total_blocks > 0.3:
            css_parts.append(".text-center { text-align: center; }")

    return "\n".join(css_parts), border_class_map, bg_class_map
