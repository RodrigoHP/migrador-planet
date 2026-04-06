"""Stage 5 — Template Generation (Tree-Driven HTML + CSS-from-Extraction).

Story 13.10 — Generates hierarchical HTML from document_trees (Stage 3),
CSS from extracted visual data (fonts, colors, drawn_elements, visual_regions),
multidimensional coverage, per-layout overlays, VariationMatrix, and assembles
the complete PipelineResult for the frontend editor.

7 sub-steps:
  5.1 Tree-Driven HTML (walk document_trees -> hierarchical HTML)
  5.2 CSS-from-Extraction (fonts, colors, borders, backgrounds, zones)
  5.3 Coverage Calculation (fields 60% + tables 25% + images 15%)
  5.4 Overlay Items (per-layout, filtered by layout_type_id)
  5.5 VariationMatrix Assembly (variant + present_in_pdfs)
  5.6 PipelineResult Assembly (G18-G22, full contract)
  5.7 Persistence (StorageGateway with handle_service_failure)

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 8
Output contract: Section 3.5
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import Counter
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_A4_WIDTH_PTS: float = 595.0
_A4_HEIGHT_PTS: float = 842.0
_SCALE_X: float = 794 / _A4_WIDTH_PTS
_SCALE_Y: float = 1123 / _A4_HEIGHT_PTS

# Base CSS reset — minimal, NOT hardcoded layout values
_BASE_CSS_RESET = """\
.page {
  position: relative;
  box-sizing: border-box;
  background: #ffffff;
  margin: 0 auto 1em auto;
  overflow: hidden;
  width: 794px;
  height: 1123px;
}
.header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}
.flow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1123px;
  overflow: hidden;
}
.footer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1123px;
}
.section {
  position: relative;
}
table.data-table {
  border-collapse: collapse;
}
table.data-table th,
table.data-table td {
  padding: 4px 6px;
}
"""


# ---------------------------------------------------------------------------
# 5.1 Tree-Driven HTML
# ---------------------------------------------------------------------------


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use in CSS classes and data attributes."""
    return re.sub(r"[^a-z0-9_-]", "_", name.lower().replace(" ", "_"))


def _bbox_to_absolute_style(
    bbox: Optional[List],
    page_height_pts: float = _A4_HEIGHT_PTS,
    page_width_pts: float = _A4_WIDTH_PTS,
) -> Optional[str]:
    """Convert PyMuPDF bbox [x0, y0, x1, y1] to CSS position:absolute style.

    PyMuPDF (fitz) uses screen coordinates: y=0 at top-left, y increases downward.
    bbox[1] (y0) is the TOP edge of the element — maps directly to CSS `top`.
    No axis inversion needed.
    """
    if not bbox or len(bbox) < 4:
        return None
    try:
        x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    except (TypeError, ValueError):
        return None
    scale_x = 794.0 / page_width_pts
    scale_y = 1123.0 / page_height_pts
    x_px = round(x0 * scale_x)
    y_px = round(y0 * scale_y)
    w_px = round((x1 - x0) * scale_x)
    h_px = round((y1 - y0) * scale_y)
    return f"position:absolute;left:{x_px}px;top:{y_px}px;width:{w_px}px;height:{h_px}px"


def _tree_to_html(
    node: Dict[str, Any],
    mapping_by_block: Dict[str, Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
    layout: Dict[str, Any],
    indent: int = 0,
) -> str:
    """Recursively walk a document tree node to produce HTML.

    Node types: document, page, header, footer, flow, section, field,
    table, image, chart, barcode, label, value, header_row, data_row.
    """
    if not isinstance(node, dict):
        return ""
    pad = "  " * indent
    node_type = node.get("type", "")
    children = node.get("children", [])

    if node_type == "document":
        name = _sanitize_name(layout.get("name", "default"))
        layout_name = layout.get("name", "default")
        children_html = "\n".join(
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1)
            for c in children
        )
        return f'{pad}<div class="page page-{name}" data-layout-type="{layout_name}">\n{children_html}\n{pad}</div>'

    elif node_type == "page":
        children_html = "\n".join(
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1)
            for c in children
        )
        return f'{pad}<div class="page-content">\n{children_html}\n{pad}</div>'

    elif node_type in ("header", "footer", "flow"):
        children_html = "\n".join(
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1)
            for c in children
        )
        return f'{pad}<div class="{node_type}">\n{children_html}\n{pad}</div>'

    elif node_type == "section":
        variant = node.get("variant", "required")
        section_name = node.get("name", "")
        children_html = "\n".join(
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1)
            for c in children
        )
        section_div = f'{pad}<div class="section" data-section="{section_name}">\n{children_html}\n{pad}</div>'

        if variant == "conditional":
            binding = _sanitize_name(section_name) if section_name else "condition"
            return f"{pad}<!-- ko if: {binding} -->\n{section_div}\n{pad}<!-- /ko -->"
        return section_div

    elif node_type == "table":
        table_html = _generate_table_html(node, mapping_by_block, field_tree, indent)
        bbox = node.get("bbox")
        if bbox:
            pos_style = _bbox_to_absolute_style(
                bbox,
                float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
                float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
            )
            if pos_style:
                table_html = table_html.replace(
                    f'<table class="data-table"',
                    f'<table class="data-table" style="{pos_style}"',
                    1,
                )
        return table_html

    elif node_type == "rect":
        bbox = node.get("bbox")
        fill_color = node.get("fill_color")
        stroke_color = node.get("stroke_color")
        pos_style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        if not pos_style:
            return ""
        fill_css = f"background-color:#{_color_int_to_hex(fill_color)};" if fill_color is not None else ""
        border_css = f"border:1px solid #{_color_int_to_hex(stroke_color)};" if stroke_color is not None else ""
        full_style = f"{fill_css}{border_css}{pos_style}"
        return f'{pad}<div data-type="rect" style="{full_style}"></div>'

    elif node_type == "field":
        return _generate_field_html(node, mapping_by_block, field_tree, layout, indent)

    elif node_type == "image":
        bbox = node.get("bbox")
        bbox_valid = node.get("bbox_valid", True)
        img_path = node.get("image_path", "")
        if not bbox_valid or not img_path:
            return ""
        style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        style_attr = f' style="{style}"' if style else ""
        return f'{pad}<img src="{img_path}" data-type="image"{style_attr} />'

    elif node_type == "chart":
        chart_type = node.get("chart_type", "unknown")
        bbox = node.get("bbox")
        style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        style_attr = f' style="{style}"' if style else ""
        return f'{pad}<div data-type="chart" data-chart-type="{chart_type}"{style_attr}><!-- chart --></div>'

    elif node_type == "barcode":
        barcode_fmt = node.get("barcode_format", "")
        bbox = node.get("bbox")
        style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        style_attr = f' style="{style}"' if style else ""
        return f'{pad}<div data-type="barcode" data-format="{barcode_fmt}"{style_attr}><!-- barcode --></div>'

    elif node_type == "line":
        bbox = node.get("bbox")
        stroke_color = node.get("stroke_color")
        width = node.get("width", 1.0)
        pos_style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        color_css = f"#{_color_int_to_hex(stroke_color)}" if stroke_color is not None else "#000000"
        border_px = max(1, round(width * _SCALE_Y))
        line_style = f"border-top:{border_px}px solid {color_css};"
        full_style = f"{line_style}{pos_style}" if pos_style else line_style
        return f'{pad}<div data-type="line" style="{full_style}"></div>'

    else:
        # Generic node — recurse children or render standalone text block
        if children:
            children_html = "\n".join(
                _tree_to_html(c, mapping_by_block, field_tree, layout, indent)
                for c in children
            )
            return children_html
        text = node.get("text", "")
        block_id = node.get("block_id", "")
        if text or block_id:
            node_id = block_id or f"{node_type}-{id(node)}"
            page_h = float(layout.get("page_height_pts", _A4_HEIGHT_PTS))
            page_w = float(layout.get("page_width_pts", _A4_WIDTH_PTS))
            pos_style = _bbox_to_absolute_style(node.get("bbox"), page_h, page_w)
            is_bold = node.get("is_bold", False) or node.get("font_weight", "normal") == "bold"
            bold_style = "font-weight:bold;" if is_bold else ""
            font_size = node.get("font_size")
            size_style = f"font-size:{round(font_size * _SCALE_Y, 1)}px;" if font_size else ""
            color_int = node.get("color")
            color_style = f"color:#{_color_int_to_hex(color_int)};" if color_int is not None else ""
            style_parts = [s for s in (bold_style, size_style, color_style, pos_style) if s]
            style_attr = f' style="{"".join(style_parts)}"' if style_parts else ""
            font_name = node.get("font_name")
            font_class = f' class="{_sanitize_font_class(font_name)}"' if font_name else ""
            return f'{pad}<span data-node-id="{node_id}" data-type="{node_type}"{font_class}{style_attr}>{text}</span>'
        return ""


def _generate_field_html(
    node: Dict[str, Any],
    mapping_by_block: Dict[str, Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
    layout: Dict[str, Any],
    indent: int,
) -> str:
    """Generate HTML for a field node (label + value children)."""
    pad = "  " * indent
    children = node.get("children", [])
    page_h = float(layout.get("page_height_pts", _A4_HEIGHT_PTS))
    page_w = float(layout.get("page_width_pts", _A4_WIDTH_PTS))

    parts = []
    for child in children:
        if not isinstance(child, dict):
            continue
        child_type = child.get("type", "")
        block_id = child.get("block_id", "")
        text = child.get("text", "")
        bbox = child.get("bbox")
        pos_style = _bbox_to_absolute_style(bbox, page_h, page_w)
        is_bold = child.get("is_bold", False) or child.get("font_weight", "normal") == "bold"
        bold_style = "font-weight:bold;" if is_bold else ""
        font_size = child.get("font_size")
        size_style = f"font-size:{round(font_size * _SCALE_Y, 1)}px;" if font_size else ""
        color_int = child.get("color")
        color_style = f"color:#{_color_int_to_hex(color_int)};" if color_int is not None else ""
        font_name = child.get("font_name")
        font_class = f' class="{_sanitize_font_class(font_name)}"' if font_name else ""
        style_parts = [s for s in (bold_style, size_style, color_style, pos_style) if s]
        style = "".join(style_parts)

        if child_type == "label":
            style_attr = f' style="{style}"' if style else ""
            node_id = block_id or f"label-{id(child)}"
            parts.append(
                f'{pad}<span data-node-id="{node_id}" data-type="label"'
                f'{font_class}{style_attr}>{text}</span>'
            )
        elif child_type == "value":
            mapping = mapping_by_block.get(block_id, {})
            xsd_path = mapping.get("xsd_field_path", "")
            status = mapping.get("status", "unmapped") if mapping else "unmapped"
            node_id = block_id or f"value-{id(child)}"

            if xsd_path:
                # Check if array
                if "[]" in xsd_path or _is_array_field(xsd_path, field_tree):
                    array_path = xsd_path.replace("[]", "")
                    item_name = array_path.split(".")[-1]
                    parts.append(f"{pad}<!-- ko foreach: {array_path} -->")
                    parts.append(
                        f'{pad}  <span data-node-id="{node_id}" data-xsd-path="{xsd_path}"'
                        f' data-status="{status}" data-bind="text: {item_name}"></span>'
                    )
                    parts.append(f"{pad}<!-- /ko -->")
                else:
                    style_attr = f' style="{style}"' if style else ""
                    parts.append(
                        f'{pad}<span data-node-id="{node_id}" data-xsd-path="{xsd_path}"'
                        f' data-status="{status}"{font_class}{style_attr}'
                        f' data-bind="text: {xsd_path}">{text}</span>'
                    )
            else:
                style_attr = f' style="{style}"' if style else ""
                parts.append(
                    f'{pad}<span data-node-id="{node_id}" data-status="{status}"'
                    f'{font_class}{style_attr}>{text}</span>'
                )
        elif child_type == "image":
            img_path = child.get("image_path", "")
            style = _bbox_to_absolute_style(child.get("bbox"), page_h, page_w)
            style_attr = f' style="{style}"' if style else ""
            parts.append(f'{pad}<img src="{img_path}" data-type="image"{style_attr} />')

    # Wrap field children
    variant = node.get("variant", "required")
    if variant == "conditional":
        block_id = node.get("id", "").replace("block-", "")
        binding = block_id or "condition"
        inner = "\n".join(parts)
        return f"{pad}<!-- ko if: {binding} -->\n{inner}\n{pad}<!-- /ko -->"

    return "\n".join(parts)


def _is_array_field(path: str, field_tree: Optional[Dict[str, Any]]) -> bool:
    """Check if a field path is an array in the XSD field tree."""
    if not field_tree:
        return False
    for node in field_tree.get("root_nodes", []):
        if _node_is_array(node, path):
            return True
    return False


def _node_is_array(node: Dict[str, Any], target_path: str) -> bool:
    """Recursively check if a node matches target_path and is_array."""
    if node.get("path", "") == target_path and node.get("is_array"):
        return True
    for child in node.get("children", []):
        if _node_is_array(child, target_path):
            return True
    return False


def _generate_table_html(
    table_node: Dict[str, Any],
    mapping_by_block: Dict[str, Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
    indent: int,
) -> str:
    """Generate real <table> HTML with ko foreach for data rows."""
    pad = "  " * indent
    table_id = table_node.get("table_id", "")

    # Collect header rows and data rows from children
    header_rows = []
    data_row_children = []

    for child in table_node.get("children", []):
        if not isinstance(child, dict):
            continue
        child_type = child.get("type", "")
        if child_type == "header_row":
            cells = []
            for cell_node in child.get("children", []):
                if not isinstance(cell_node, dict):
                    continue
                cells.append(cell_node.get("text", ""))
            header_rows.append(cells)
        elif child_type == "data_row":
            data_row_children = child.get("children", [])

    # Also check if headers are stored directly
    if not header_rows:
        direct_headers = table_node.get("headers", [])
        if direct_headers:
            if isinstance(direct_headers[0], list):
                for row in direct_headers:
                    cells = [h.get("text", h) if isinstance(h, dict) else str(h) for h in row]
                    header_rows.append(cells)
            else:
                cells = [h.get("text", h) if isinstance(h, dict) else str(h) for h in direct_headers]
                header_rows.append(cells)

    # Determine xsd_array_path for ko foreach
    xsd_array_path = table_node.get("xsd_array_path", "items")

    # Build body cells from data_row or table children
    body_cells = []
    for child in data_row_children or table_node.get("children", []):
        if not isinstance(child, dict):
            continue
        block_id = child.get("block_id", child.get("id", "").replace("block-", ""))
        mapping = mapping_by_block.get(block_id, {})
        path = mapping.get("xsd_field_path", "")
        field_name = path.split(".")[-1] if path else ""
        if field_name:
            body_cells.append(f'<td data-bind="text: {field_name}"></td>')
        else:
            body_cells.append("<td></td>")

    # Build header HTML
    header_html = ""
    if header_rows:
        thead_rows = []
        for row_cells in header_rows:
            cells_html = "".join(f"<th>{c}</th>" for c in row_cells)
            thead_rows.append(f"{pad}    <tr>{cells_html}</tr>")
        header_html = f"{pad}  <thead>\n" + "\n".join(thead_rows) + f"\n{pad}  </thead>"

    body_cells_html = "".join(body_cells)

    return (
        f'{pad}<table class="data-table" data-table-id="{table_id}">\n'
        f"{header_html}\n"
        f"{pad}  <tbody>\n"
        f"{pad}    <!-- ko foreach: {xsd_array_path} -->\n"
        f"{pad}    <tr>{body_cells_html}</tr>\n"
        f"{pad}    <!-- /ko -->\n"
        f"{pad}  </tbody>\n"
        f"{pad}</table>"
    )


def _step_5_1_tree_driven_html(
    document_trees: Dict[str, Dict[str, Any]],
    field_mappings: List[Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
    layout_types: List[Dict[str, Any]],
) -> Dict[str, str]:
    """5.1 — Generate hierarchical HTML per layout by walking document_trees.

    Returns: {layout_id: html_string}
    """
    html_by_layout: Dict[str, str] = {}

    for layout in layout_types:
        layout_id = layout.get("id", "")
        tree = document_trees.get(layout_id)
        if not tree:
            continue

        # Filter mappings for this layout
        layout_mappings = [
            m for m in field_mappings
            if m.get("layout_type_id") == layout_id
        ]
        mapping_by_block: Dict[str, Dict[str, Any]] = {}
        for m in layout_mappings:
            bid = m.get("block_id")
            if bid:
                mapping_by_block[bid] = m

        html = _tree_to_html(tree, mapping_by_block, field_tree, layout)
        html_by_layout[layout_id] = html

    return html_by_layout


# ---------------------------------------------------------------------------
# 5.2 CSS-from-Extraction
# ---------------------------------------------------------------------------


def _color_int_to_hex(color_int: int) -> str:
    """Convert an RGB integer to a 6-digit hex string."""
    return f"{color_int & 0xFFFFFF:06x}"


def _sanitize_font_class(font_name: str) -> str:
    """Create a safe CSS class name from a font name."""
    # Strip common PDF font subset prefixes like "ABCDEF+"
    clean = re.sub(r"^[A-Z]{6}\+", "", font_name)
    return re.sub(r"[^a-z0-9-]", "-", clean.lower()).strip("-")


def _step_5_2_css_from_extraction(
    enriched_documents: List[Dict[str, Any]],
    visual_analysis: Optional[Dict[str, Dict[str, Any]]],
    layout_types: List[Dict[str, Any]],
) -> str:
    """5.2 — Generate CSS from extracted data (NOT hardcoded).

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
    """
    css_parts: List[str] = [_BASE_CSS_RESET]

    # Collect data from all representative pages
    font_counter: Counter = Counter()
    color_set: Set[int] = set()
    font_sizes: Dict[str, float] = {}
    page_widths: List[float] = []
    page_heights: List[float] = []
    drawn_lines: List[Dict[str, Any]] = []
    drawn_rects: List[Dict[str, Any]] = []
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
                    font_counter[font_name] += 1
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

    flow_top = header_height_px
    css_parts.append(f".header {{ height: {header_height_px}px; }}")
    css_parts.append(f".flow {{ top: {flow_top}px; bottom: {footer_height_px}px; }}")
    css_parts.append(f".footer {{ height: {footer_height_px}px; }}")

    # 3. Font classes from extracted fonts (NOT hardcoded Arial)
    for font_name, count in font_counter.most_common(20):
        safe_class = _sanitize_font_class(font_name)
        if not safe_class:
            continue
        clean_name = re.sub(r"^[A-Z]{6}\+", "", font_name)
        fs = font_sizes.get(font_name)
        size_rule = f" font-size: {fs}pt;" if fs else ""
        css_parts.append(
            f".f-{safe_class} {{ font-family: '{clean_name}', sans-serif;{size_rule} }}"
        )

    # 4. Color classes from extracted colors (NOT hardcoded #000)
    for color_int in sorted(color_set):
        hex_str = _color_int_to_hex(color_int)
        css_parts.append(f".c-{hex_str} {{ color: #{hex_str}; }}")

    # 5. Border rules from drawn_elements[type=line]
    border_index = 0
    for line in drawn_lines[:20]:  # limit to avoid bloat
        orientation = line.get("orientation", "horizontal")
        stroke_color = line.get("stroke_color")
        width = line.get("width", 1.0)
        if stroke_color is not None:
            hex_str = _color_int_to_hex(stroke_color)
            side = "bottom" if orientation == "horizontal" else "right"
            css_parts.append(
                f".border-{border_index} {{ border-{side}: {width}pt solid #{hex_str}; }}"
            )
            border_index += 1

    # 6. Background rules from drawn_elements[type=rect, fill_color]
    bg_index = 0
    for rect in drawn_rects[:10]:
        fill = rect.get("fill_color")
        if fill is not None:
            hex_str = _color_int_to_hex(fill)
            css_parts.append(f".bg-{bg_index} {{ background-color: #{hex_str}; }}")
            bg_index += 1

    # 7. Text alignment hints
    if total_blocks > 0:
        if right_aligned_blocks / total_blocks > 0.3:
            css_parts.append(".text-right { text-align: right; }")
        if center_aligned_blocks / total_blocks > 0.3:
            css_parts.append(".text-center { text-align: center; }")

    return "\n".join(css_parts)


# ---------------------------------------------------------------------------
# 5.3 Coverage Calculation
# ---------------------------------------------------------------------------


def _count_nodes_by_type(tree: Optional[Dict[str, Any]], target_type: str) -> int:
    """Count nodes of a given type in the tree recursively."""
    if not tree:
        return 0
    count = 1 if tree.get("type") == target_type else 0
    for child in tree.get("children", []):
        count += _count_nodes_by_type(child, target_type)
    return count


def _count_mapped_tables(
    tree: Optional[Dict[str, Any]],
    layout_mappings: List[Dict[str, Any]],
) -> int:
    """Count tables that have at least one mapped cell."""
    if not tree:
        return 0
    table_ids_with_mapping: Set[str] = set()

    # Collect all table_cell block_ids
    mapped_block_ids = {m.get("block_id") for m in layout_mappings if m.get("xsd_field_path")}

    def _walk(node: Dict[str, Any], current_table_id: Optional[str] = None):
        ntype = node.get("type", "")
        tid = current_table_id
        if ntype == "table":
            tid = node.get("table_id", str(id(node)))
        block_id = node.get("block_id", "")
        if tid and block_id in mapped_block_ids:
            table_ids_with_mapping.add(tid)
        for child in node.get("children", []):
            _walk(child, tid)

    _walk(tree)
    return len(table_ids_with_mapping)


def _step_5_3_coverage(
    field_mappings: List[Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
    document_trees: Dict[str, Dict[str, Any]],
    layout_types: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """5.3 — Multidimensional coverage per layout.

    Weights: fields 60% + tables 25% + images 15%.
    """
    coverage_by_layout: Dict[str, Dict[str, Any]] = {}

    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    total_xsd_fields = len(flat_paths) if flat_paths else 0

    for layout in layout_types:
        layout_id = layout.get("id", "")
        tree = document_trees.get(layout_id)

        # Fields
        layout_mappings = [
            m for m in field_mappings
            if m.get("layout_type_id") == layout_id
        ]
        mapped_fields = len({
            m["xsd_field_path"]
            for m in layout_mappings
            if m.get("xsd_field_path")
        })

        # Tables — count in document_tree
        total_tables = _count_nodes_by_type(tree, "table")
        mapped_tables = _count_mapped_tables(tree, layout_mappings)

        # Images — count in document_tree
        total_images = _count_nodes_by_type(tree, "image")
        # Images are "mapped" if they exist in the tree (extracted = usable)
        mapped_images = total_images

        # Charts
        total_charts = _count_nodes_by_type(tree, "chart")

        # Weighted percentage
        f_pct = (mapped_fields / total_xsd_fields * 100) if total_xsd_fields else 0
        t_pct = (mapped_tables / total_tables * 100) if total_tables else 100
        i_pct = (mapped_images / total_images * 100) if total_images else 100
        percentage = round(f_pct * 0.6 + t_pct * 0.25 + i_pct * 0.15)

        coverage_by_layout[layout_id] = {
            "fields": {"mapped": mapped_fields, "total": total_xsd_fields},
            "tables": {"mapped": mapped_tables, "total": total_tables},
            "images": {"mapped": mapped_images, "total": total_images},
            "charts": {"mapped": 0, "total": total_charts},
            "percentage": percentage,
        }

    return coverage_by_layout


# ---------------------------------------------------------------------------
# 5.4 Overlay Items
# ---------------------------------------------------------------------------


def _get_page_dimensions(
    enriched_documents: List[Dict[str, Any]],
) -> Dict[int, Tuple[float, float]]:
    """Return page_number -> (width_pts, height_pts) from enriched_documents."""
    dims: Dict[int, Tuple[float, float]] = {}
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            page_num = int(page.get("page_index", page.get("page_number", 0)))
            w = float(page.get("width", _A4_WIDTH_PTS) or _A4_WIDTH_PTS)
            h = float(page.get("height", _A4_HEIGHT_PTS) or _A4_HEIGHT_PTS)
            dims[page_num] = (w, h)
    return dims


def _step_5_4_overlay_items(
    field_mappings: List[Dict[str, Any]],
    layout_types: List[Dict[str, Any]],
    enriched_documents: List[Dict[str, Any]],
    document_trees: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """5.4 — Build overlay items filtered by layout_type_id.

    Includes table overlays (container + cell hover).
    """
    page_dims = _get_page_dimensions(enriched_documents)
    overlay_by_layout: Dict[str, List[Dict[str, Any]]] = {}

    for layout in layout_types:
        layout_id = layout.get("id", "")
        layout_mappings = [
            m for m in field_mappings
            if m.get("layout_type_id") == layout_id
        ]

        items: List[Dict[str, Any]] = []
        for mapping in layout_mappings:
            bbox = mapping.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            try:
                x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            except (TypeError, ValueError):
                continue

            page_num = int(mapping.get("page_number", 0))
            page_w, page_h = page_dims.get(page_num, (_A4_WIDTH_PTS, _A4_HEIGHT_PTS))
            scale_x = 794.0 / page_w
            scale_y = 1123.0 / page_h

            overlay_type = "field"
            if mapping.get("is_table_cell") or mapping.get("from_table"):
                overlay_type = "table_cell"

            items.append({
                "node_id": mapping.get("block_id"),
                "xsd_path": mapping.get("xsd_field_path"),
                "label": mapping.get("label_text", ""),
                "value": mapping.get("pdf_text", ""),
                "status": mapping.get("status", "unmapped"),
                "page_number": page_num,
                "layout_type_id": layout_id,
                "overlay_type": overlay_type,
                "bbox_canvas": {
                    "left": round(x0 * scale_x, 1),
                    "top": round((page_h - y1) * scale_y, 1),
                    "width": round((x1 - x0) * scale_x, 1),
                    "height": round((y1 - y0) * scale_y, 1),
                },
                "bbox_pdf": {
                    "left": round(x0, 1),
                    "top": round(y0, 1),
                    "width": round(x1 - x0, 1),
                    "height": round(y1 - y0, 1),
                },
            })

        # Add table container overlays from document_trees (G22)
        tree = document_trees.get(layout_id)
        if tree:
            _add_table_container_overlays(tree, items, page_dims, layout_id)

        overlay_by_layout[layout_id] = items

    return overlay_by_layout


def _add_table_container_overlays(
    node: Dict[str, Any],
    items: List[Dict[str, Any]],
    page_dims: Dict[int, Tuple[float, float]],
    layout_id: str,
) -> None:
    """Recursively find table nodes and add container overlays."""
    if not isinstance(node, dict):
        return
    if node.get("type") == "table":
        bbox = node.get("bbox")
        if bbox and len(bbox) >= 4:
            try:
                x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                page_num = int(node.get("page_number", 0))
                page_w, page_h = page_dims.get(page_num, (_A4_WIDTH_PTS, _A4_HEIGHT_PTS))
                scale_x = 794.0 / page_w
                scale_y = 1123.0 / page_h

                items.append({
                    "node_id": node.get("table_id", f"table-{id(node)}"),
                    "xsd_path": node.get("xsd_array_path", ""),
                    "label": "",
                    "value": "",
                    "status": "table",
                    "page_number": 0,
                    "layout_type_id": layout_id,
                    "overlay_type": "table_container",
                    "bbox_canvas": {
                        "left": round(x0 * scale_x, 1),
                        "top": round((page_h - y1) * scale_y, 1),
                        "width": round((x1 - x0) * scale_x, 1),
                        "height": round((y1 - y0) * scale_y, 1),
                    },
                    "bbox_pdf": {
                        "left": round(x0, 1),
                        "top": round(y0, 1),
                        "width": round(x1 - x0, 1),
                        "height": round(y1 - y0, 1),
                    },
                })
            except (TypeError, ValueError):
                pass

    for child in node.get("children", []):
        _add_table_container_overlays(child, items, page_dims, layout_id)


# ---------------------------------------------------------------------------
# 5.5 VariationMatrix Assembly
# ---------------------------------------------------------------------------


def _step_5_5_variation_matrix(
    intelligence: Dict[str, Any],
    clusters: List[Dict[str, Any]],
    layout_types: List[Dict[str, Any]],
    pdf_documents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """5.5 — Build VariationMatrix + Detections from block_classifications.

    Iterates nodes with variant != 'required' to build the matrix and
    detection list.
    """
    # 1. Build pdf list from clusters
    all_pdf_ids: Set[str] = set()
    layout_pdf_map: Dict[str, Set[str]] = {}

    for cluster in clusters:
        layout_id = cluster.get("cluster_id", "")
        pdf_ids = {
            p.get("pdf_id")
            for p in cluster.get("pages", [])
            if p.get("pdf_id")
        }
        all_pdf_ids |= pdf_ids
        layout_pdf_map[layout_id] = pdf_ids

    if not all_pdf_ids:
        return {"pdfs": [], "matrix": {"layoutIds": [], "variationIds": [], "cells": {}}, "detections": []}

    # Determine base PDF (most cluster coverage)
    pdf_cluster_coverage: Dict[str, int] = {}
    for cluster in clusters:
        contributing = {
            p.get("pdf_id") for p in cluster.get("pages", []) if p.get("pdf_id")
        }
        for pid in contributing:
            pdf_cluster_coverage[pid] = pdf_cluster_coverage.get(pid, 0) + 1

    base_pdf_id = max(
        sorted(all_pdf_ids),
        key=lambda pid: pdf_cluster_coverage.get(pid, 0),
    )

    # Build pdf metadata
    pdf_doc_map = {str(d.get("id", "")): d for d in (pdf_documents or [])}
    pdfs = []
    for pid in sorted(all_pdf_ids):
        doc_info = pdf_doc_map.get(pid, {})
        pdfs.append({
            "id": pid,
            "name": doc_info.get("name", f"document-{pid}"),
            "role": "base" if pid == base_pdf_id else "variation",
            "sizeKB": 0,
            "pages": 0,
            "uploadedAt": "",
        })

    # 2. Build cells: layoutId x pdfId -> present
    layout_ids = [lt.get("id", "") for lt in layout_types]
    variation_ids = sorted(all_pdf_ids)

    cells: Dict[str, Dict[str, bool]] = {}
    for layout_id in layout_ids:
        cells[layout_id] = {}
        for pdf_id in variation_ids:
            cells[layout_id][pdf_id] = pdf_id in layout_pdf_map.get(layout_id, set())

    matrix = {
        "layoutIds": layout_ids,
        "variationIds": variation_ids,
        "cells": cells,
    }

    # 3. Generate Detections from block_classifications
    detections: List[Dict[str, Any]] = []
    for layout_id, intel_data in intelligence.items():
        block_classifications = intel_data.get("block_classifications", {})
        for block_id, classification in block_classifications.items():
            variant = classification.get("variant", "required")
            if variant == "required":
                continue

            present_in = classification.get("present_in_pdfs", [])
            det_type = "conditional_section" if variant == "conditional" else "optional_field"

            detections.append({
                "id": f"det-{block_id}",
                "pdfId": present_in[0] if present_in else "",
                "type": det_type,
                "description": f"Bloco presente em {len(present_in)}/{len(all_pdf_ids)} PDFs",
                "confidence": len(present_in) / len(all_pdf_ids) if all_pdf_ids else 0,
                "nodeBinding": block_id,
            })

    return {"pdfs": pdfs, "matrix": matrix, "detections": detections}


# ---------------------------------------------------------------------------
# 5.6 PipelineResult Assembly
# ---------------------------------------------------------------------------


def _normalize_confidence(
    confidence_scores: Dict[str, Any],
    layout_types: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Normalize ALL confidence factors to 0-100 scale (G18).

    Stage 4 outputs factors as 0.0-1.0 floats. Frontend expects 0-100 integers.
    """
    normalized: Dict[str, Dict[str, Any]] = {}

    for layout in layout_types:
        layout_id = layout.get("id", "")
        raw = confidence_scores.get(layout_id, {})

        if not raw:
            # Fallback
            normalized[layout_id] = {
                "layout_stability": 50,
                "anchor_detection": 50,
                "grid_quality": 50,
                "field_variability": 50,
                "vision_agreement": 50,
                "overall": 50,
                "status": "review_recommended",
            }
            continue

        entry: Dict[str, Any] = {}
        for key in ("layout_stability", "anchor_detection", "grid_quality",
                     "field_variability", "vision_agreement"):
            val = raw.get(key, 0.5)
            # If already 0-100, keep; if 0-1, multiply by 100
            if isinstance(val, (int, float)):
                entry[key] = round(val * 100) if val <= 1.0 else round(val)
            else:
                entry[key] = 50

        overall = raw.get("overall", 0)
        if isinstance(overall, (int, float)):
            entry["overall"] = round(overall) if overall > 1.0 else round(overall * 100)
        else:
            entry["overall"] = 50

        entry["status"] = raw.get("status", "review_recommended")
        normalized[layout_id] = entry

    return normalized


def _serialise_parsed_documents(
    parsed_documents: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return a simplified serialisation of parsed_documents."""
    simplified = []
    for doc in parsed_documents:
        pages = []
        for page in doc.get("pages", []):
            pages.append({
                "page_number": page.get("page_number", page.get("page_index", 0)),
                "block_count": len(page.get("text_blocks", [])),
                "image_count": len(page.get("images", [])),
            })
        simplified.append({
            "pdf_name": doc.get("pdf_name", ""),
            "pdf_index": doc.get("pdf_index", 0),
            "page_count": len(pages),
            "pages": pages,
        })
    return simplified


def _get_document_type(context: Dict[str, Any]) -> str:
    """Detect document type from context or heuristic keyword matching."""
    doc_type = context.get("document_type", "")
    if doc_type:
        return doc_type

    # Keyword matching fallback
    parts: List[str] = []
    for doc in context.get("enriched_documents", []):
        for page in doc.get("pages", []):
            for block in page.get("text_blocks", []):
                text = block.get("text", "")
                if text:
                    parts.append(text)
    all_text = " ".join(parts).lower()

    if any(kw in all_text for kw in ["boleto", "cobranca", "vencimento", "beneficiario", "cedente"]):
        return "boleto-bancario"
    elif any(kw in all_text for kw in ["nota fiscal", "nfe", "cnpj do emitente", "danfe"]):
        return "nota-fiscal"
    elif any(kw in all_text for kw in ["recibo", "comprovante de pagamento"]):
        return "recibo"
    return "documento-geral"


def _build_page_config(
    enriched_documents: List[Dict[str, Any]],
    visual_analysis: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build page_config for usePagination (G17-S5)."""
    # Detect page size from first representative
    page_w = _A4_WIDTH_PTS
    page_h = _A4_HEIGHT_PTS
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            if page.get("is_representative", True):
                page_w = float(page.get("width", _A4_WIDTH_PTS) or _A4_WIDTH_PTS)
                page_h = float(page.get("height", _A4_HEIGHT_PTS) or _A4_HEIGHT_PTS)
                break
        break

    # Determine size and orientation
    if abs(page_w - 595) < 5 and abs(page_h - 842) < 5:
        size = "A4"
    elif abs(page_w - 612) < 5 and abs(page_h - 792) < 5:
        size = "letter"
    else:
        size = "custom"

    orientation = "landscape" if page_w > page_h else "portrait"

    # Header/footer from visual analysis
    header_h_px = round(1123 * 0.15)
    footer_h_px = round(1123 * 0.10)
    if visual_analysis:
        for page_key, va in visual_analysis.items():
            for region in va.get("regions", []):
                bbox = region.get("bbox")
                if bbox and len(bbox) >= 4:
                    h = abs(float(bbox[3]) - float(bbox[1]))
                    if region.get("type") == "header":
                        header_h_px = round(h)
                    elif region.get("type") == "footer":
                        footer_h_px = round(h)
            break  # use first page

    return {
        "size": size,
        "orientation": orientation,
        "header_height_px": header_h_px,
        "footer_height_px": footer_h_px,
        "margins": {"top": 0, "bottom": 0, "left": 0, "right": 0},
    }


def _convert_tree_to_css_coords(
    tree: Dict[str, Any],
    layout: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert tree node bbox coords to CSS pixels (recursive)."""
    page_h = float(layout.get("page_height_pts", _A4_HEIGHT_PTS))
    page_w = float(layout.get("page_width_pts", _A4_WIDTH_PTS))
    scale_x = 794.0 / page_w
    scale_y = 1123.0 / page_h

    result = dict(tree)
    # Ensure every node has an 'id' (required by frontend TreeNode.id).
    # Prefer block_id when available — preserves the field_mappings ↔ node link
    # used by session.ts reconcileFieldBindings() to set node.binding + navItem.nodeId.
    # Without this, buildFlatMap() collapses all id-less nodes to key=undefined.
    if not result.get("id"):
        result["id"] = result.get("block_id") or str(uuid.uuid4())
    if "properties" not in result:
        result["properties"] = {}
    bbox = tree.get("bbox")
    if bbox and len(bbox) >= 4:
        try:
            x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            result["properties"] = dict(tree.get("properties", {}))
            result["properties"].update({
                "x": round(x0 * scale_x, 1),
                "y": round(y0 * scale_y, 1),
                "width": round((x1 - x0) * scale_x, 1),
                "height": round((y1 - y0) * scale_y, 1),
            })
        except (TypeError, ValueError):
            pass

    children = tree.get("children", [])
    if children:
        result["children"] = [
            _convert_tree_to_css_coords(child, layout) for child in children
        ]
    elif "children" not in result:
        result["children"] = []

    return result


def _step_5_6_pipeline_result(
    context: Dict[str, Any],
    html_by_layout: Dict[str, str],
    css_global: str,
    coverage_by_layout: Dict[str, Dict[str, Any]],
    overlay_by_layout: Dict[str, List[Dict[str, Any]]],
    multi_doc: Dict[str, Any],
) -> Dict[str, Any]:
    """5.6 — Assemble the complete PipelineResult for the frontend.

    Handles G18 (normalized confidence), G19 (enriched layout_types),
    G20 (8 new fields), G21 (monolithic template_draft), G22 (table overlays).
    """
    document_trees = context.get("document_trees", {})
    layout_types = context.get("layout_types", [])
    confidence_scores = context.get("confidence_scores", {})
    enriched_documents = context.get("enriched_documents", [])
    visual_analysis = context.get("visual_analysis")

    # trees_by_layout: hierarchical trees from Stage 3.4 (CSS coords)
    trees_by_layout: Dict[str, Dict[str, Any]] = {}
    for lt in layout_types:
        layout_id = lt.get("id", "")
        tree = document_trees.get(layout_id)
        if tree:
            trees_by_layout[layout_id] = _convert_tree_to_css_coords(tree, lt)

    # root: backward compat — first layout's tree
    first_layout = layout_types[0] if layout_types else None
    first_layout_id = first_layout.get("id") if isinstance(first_layout, dict) else None
    root = trees_by_layout.get(first_layout_id) if first_layout_id else None

    # G18: Normalize ALL confidence factors to 0-100
    normalized_confidence = _normalize_confidence(confidence_scores, layout_types)

    # G19: Enrich layout_types with documentTree, confidence, coverage
    enriched_layout_types = []
    for lt in layout_types:
        layout_id = lt.get("id", "")
        enriched = dict(lt)
        if layout_id in trees_by_layout:
            enriched["documentTree"] = {"root": trees_by_layout[layout_id]}
        if layout_id in coverage_by_layout:
            enriched["coverage"] = coverage_by_layout[layout_id]
        if layout_id in normalized_confidence:
            enriched["confidence"] = normalized_confidence[layout_id]
        # page_count from clusters
        for cluster in context.get("clusters", []):
            if cluster.get("cluster_id") == layout_id:
                enriched["page_count"] = cluster.get("page_count", len(cluster.get("pages", [])))
                break
        enriched_layout_types.append(enriched)

    # G21: monolithic template_draft (active layout / first)
    active_html = html_by_layout.get(first_layout_id, "") if first_layout_id else ""
    if not active_html and html_by_layout:
        active_html = next(iter(html_by_layout.values()))

    result_json: Dict[str, Any] = {
        "document_structure": {
            "pages": _serialise_parsed_documents(context.get("parsed_documents", enriched_documents)),
            "layout_types": enriched_layout_types,
            "root": root,
            "trees_by_layout": trees_by_layout,
        },
        "field_mappings": context.get("field_mappings", []),
        "confidence_scores": normalized_confidence,
        "coverage": coverage_by_layout,
        "layout_types": enriched_layout_types,
        "template_draft": {
            "html": active_html,
            "css": css_global,
        },
        "ambiguous_fields": [
            m for m in context.get("field_mappings", []) if m.get("is_ambiguous")
        ],
        "format_functions": context.get("format_functions", {}),
        "overlay_items": overlay_by_layout,
        "document_type": _get_document_type(context),
        "document_type_confidence": context.get("document_type_confidence", 0.0),
        "visual_analysis": visual_analysis,
        "intelligence": context.get("intelligence"),
        "validation_result": context.get("validation_result"),
        "block_classifications_confirmed": context.get("block_classifications_confirmed"),
        "multi_doc": multi_doc,
        "page_config": _build_page_config(enriched_documents, visual_analysis),
    }

    return result_json


# ---------------------------------------------------------------------------
# 5.7 Persistence
# ---------------------------------------------------------------------------


def _extract_visual_data(context: Dict[str, Any]) -> dict:
    """Extract drawn_elements and text_blocks from enriched_documents for persistence."""
    pages: list[dict] = []
    for doc in context.get("enriched_documents", []):
        for page in doc.get("pages", []):
            pages.append({
                "page_index": page.get("page_index"),
                "cluster_id": page.get("cluster_id"),
                "drawn_elements": page.get("drawn_elements"),
                "text_blocks": page.get("text_blocks"),
            })
    return {"pages": pages}


async def _step_5_7_persist(
    context: Dict[str, Any],
    result_json: Dict[str, Any],
    emit_progress: EmitProgressFn,
    *,
    _retry_count: int = 0,
    max_retries: int = 3,
) -> None:
    """5.7 — Persist result_json via StorageGateway with handle_service_failure."""
    storage = context.get("_storage")
    job_id = context.get("job_id", "")

    if not storage or not job_id:
        logger.info("[Stage 5] No storage or job_id — skipping persistence (dev/local)")
        return

    try:
        await storage.save_result(job_id, result_json)
        logger.info("[Stage 5] Result persisted for job %s", job_id)

        # Save visual data (auxiliary — non-blocking)
        try:
            visual_data = _extract_visual_data(context)
            if visual_data["pages"]:
                await storage.save_visual_data(job_id, visual_data)
                logger.info("[Stage 5] Visual data persisted for job %s", job_id)
        except Exception as vd_exc:
            logger.warning(
                "[Stage 5] Visual data persistence failed (non-blocking): %s", vd_exc
            )
    except Exception as exc:
        logger.error("[Stage 5] Persistence failed: %s", exc)
        # Use handle_service_failure if job context available
        job = context.get("_job")
        if job and emit_progress:
            from services.pipeline_orchestrator_v2 import handle_service_failure

            decision = await handle_service_failure(
                context=context,
                service_name="Storage",
                stage_name="Template Generation",
                error=exc,
                fallback_description="Continuar sem salvar — resultado ficara apenas em memoria",
                impact_description="Se a sessao for encerrada, o resultado sera perdido",
                job=job,
                emit_progress=emit_progress,
                timeout=300,
            )
            if decision == "retry":
                if _retry_count >= max_retries:
                    logger.error(
                        "[Stage 5] Persistence max retries (%d) reached — giving up",
                        max_retries,
                    )
                else:
                    await _step_5_7_persist(
                        context, result_json, emit_progress,
                        _retry_count=_retry_count + 1,
                        max_retries=max_retries,
                    )
            # else: operator accepted fallback — continue without persistence
        else:
            # No job context for checkpoint — log warning and continue
            logger.warning(
                "[Stage 5] Persistence failed and no checkpoint available — "
                "result remains in memory only: %s", exc,
            )


# ---------------------------------------------------------------------------
# Main orchestrator: run_stage5
# ---------------------------------------------------------------------------


async def run_stage5(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 5: Template Generation — 7 sub-steps.

    Reads:
        context["document_trees"], context["intelligence"],
        context["visual_analysis"], context["enriched_documents"],
        context["field_mappings"], context["field_tree"],
        context["layout_types"], context["clusters"],
        context["confidence_scores"], context["validation_result"],
        context["block_classifications_confirmed"],
        context["format_functions"], context["pdf_documents"],
        context["_storage"], context["job_id"]

    Writes:
        context["result_json"], context["stage_5_result"]
    """
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    stage = 5
    name = "Template Generation"
    context["_current_stage"] = stage
    context["_current_stage_name"] = name

    # Read inputs
    document_trees: Dict[str, Dict[str, Any]] = context.get("document_trees", {})

    intelligence = context.get("intelligence", {})
    enriched_documents = context.get("enriched_documents", [])
    visual_analysis = context.get("visual_analysis")
    field_mappings = context.get("field_mappings", [])
    field_tree = context.get("field_tree")
    layout_types = context.get("layout_types", [])
    clusters = context.get("clusters", [])
    pdf_documents = context.get("pdf_documents", [])

    # --- 5.1 Tree-Driven HTML ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.10),
        sub_step="5.1 Tree-Driven HTML", sub_progress_pct=0.10,
    ))

    html_by_layout = _step_5_1_tree_driven_html(
        document_trees, field_mappings, field_tree, layout_types,
    )
    logger.info(
        "[Stage 5] 5.1 HTML generated for %d layouts, sizes: %s",
        len(html_by_layout),
        {k: len(v) for k, v in html_by_layout.items()},
    )

    # --- 5.2 CSS-from-Extraction ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.30),
        sub_step="5.2 CSS-from-Extraction", sub_progress_pct=0.30,
    ))

    css_global = _step_5_2_css_from_extraction(
        enriched_documents, visual_analysis, layout_types,
    )
    logger.info("[Stage 5] 5.2 CSS generated: %d chars", len(css_global))

    # --- 5.3 Coverage ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.50),
        sub_step="5.3 Coverage Calculation", sub_progress_pct=0.50,
    ))

    coverage_by_layout = _step_5_3_coverage(
        field_mappings, field_tree, document_trees, layout_types,
    )
    logger.info("[Stage 5] 5.3 Coverage: %s", coverage_by_layout)

    # --- 5.4 Overlay Items ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.60),
        sub_step="5.4 Overlay Items", sub_progress_pct=0.60,
    ))

    overlay_by_layout = _step_5_4_overlay_items(
        field_mappings, layout_types, enriched_documents, document_trees,
    )
    logger.info(
        "[Stage 5] 5.4 Overlays: %s",
        {k: len(v) for k, v in overlay_by_layout.items()},
    )

    # --- 5.5 VariationMatrix ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.70),
        sub_step="5.5 VariationMatrix", sub_progress_pct=0.70,
    ))

    multi_doc = _step_5_5_variation_matrix(
        intelligence, clusters, layout_types, pdf_documents,
    )
    logger.info(
        "[Stage 5] 5.5 VariationMatrix: %d pdfs, %d detections",
        len(multi_doc.get("pdfs", [])),
        len(multi_doc.get("detections", [])),
    )

    # --- 5.6 PipelineResult Assembly ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.85),
        sub_step="5.6 PipelineResult Assembly", sub_progress_pct=0.85,
    ))

    result_json = _step_5_6_pipeline_result(
        context, html_by_layout, css_global,
        coverage_by_layout, overlay_by_layout, multi_doc,
    )
    context["result_json"] = result_json

    # --- 5.7 Persistence ---
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 0.95),
        sub_step="5.7 Persistence", sub_progress_pct=0.95,
    ))

    await _step_5_7_persist(context, result_json, emit_progress)

    # --- Done ---
    context["stage_5_result"] = {
        "template_draft": result_json.get("template_draft", {}),
        "coverage": coverage_by_layout,
        "overlay_count": sum(len(v) for v in overlay_by_layout.values()),
        "multi_doc_pdfs": len(multi_doc.get("pdfs", [])),
    }

    logger.info(
        "[Stage 5] Complete: html=%d chars, css=%d chars, layouts=%d",
        len(result_json.get("template_draft", {}).get("html", "")),
        len(result_json.get("template_draft", {}).get("css", "")),
        len(layout_types),
    )

    # Emit final summary for the accordion
    real_layout_types = [lt for lt in layout_types if not str(lt.get("cluster_id", "")).startswith("_")]
    overlay_count = sum(len(v) for v in overlay_by_layout.values())
    html_size = len(result_json.get("template_draft", {}).get("html", ""))
    await emit_progress(make_sub_progress_event(
        stage=stage, stage_name=name, status="running",
        progress_pct=compute_overall_progress(stage, 1.0), sub_step="5.7 Persistence",
        sub_progress_pct=1.0,
        summary={
            "layouts_detected": len(real_layout_types),
            "fields_mapped": overlay_count,
            "html_size_bytes": html_size,
        },
    ))

    return context
