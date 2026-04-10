"""Stage 5 � HTML Tree Walker sub-module.

Responsibilities:
  - _tree_to_html: recursively walks document tree nodes to produce HTML

Story 41.3 � extracted from stage5_template_generation.py
"""

from __future__ import annotations

import logging
from typing import Any

from services.stages.stage5_template.html_helpers import (
    _A4_HEIGHT_PTS,
    _A4_WIDTH_PTS,
    _SCALE_X,
    _SCALE_Y,
    _barcode_to_svg_content,
    _bbox_to_absolute_style,
    _color_int_to_hex,
    _font_class_with_style,
    _generate_field_html,
    _generate_table_html,
    _sanitize_name,
)

logger = logging.getLogger(__name__)


def _tree_to_html(
    node: dict[str, Any],
    mapping_by_block: dict[str, dict[str, Any]],
    field_tree: dict[str, Any] | None,
    layout: dict[str, Any],
    indent: int = 0,
    border_class_map: dict[tuple, str] | None = None,
    bg_class_map: dict[int, str] | None = None,
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
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1, border_class_map, bg_class_map)
            for c in children
        )
        return f'{pad}<div class="page page-{name}" data-layout-type="{layout_name}">\n{children_html}\n{pad}</div>'

    elif node_type == "page":
        # Render order matters for z-order (position:absolute, no explicit z-index →
        # later in DOM = on top). PDF paint order: fills → text → lines.
        # We replicate that: rects (backgrounds) first, zones (content) next,
        # lines (grid borders) last so borders sit on top of filled backgrounds.
        rects_c = [c for c in children if isinstance(c, dict) and c.get("type") == "rect"]
        zones_c = [c for c in children if isinstance(c, dict) and c.get("type") not in ("rect", "line")]
        lines_c = [c for c in children if isinstance(c, dict) and c.get("type") == "line"]
        ordered = rects_c + zones_c + lines_c
        children_html = "\n".join(
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1, border_class_map, bg_class_map)
            for c in ordered
        )
        return f'{pad}<div class="page-content">\n{children_html}\n{pad}</div>'

    elif node_type in ("header", "footer", "flow"):
        children_html = "\n".join(
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1, border_class_map, bg_class_map)
            for c in children
        )
        return f'{pad}<div class="{node_type}">\n{children_html}\n{pad}</div>'

    elif node_type == "section":
        variant = node.get("variant", "required")
        section_name = node.get("name", "")
        # Z-order within sections: images (backgrounds) first, then text/fields on top.
        # PDF boletos embed rasterized table images that must sit behind text spans.
        images_c = [c for c in children if isinstance(c, dict) and c.get("type") == "image"]
        rest_c = [c for c in children if not (isinstance(c, dict) and c.get("type") == "image")]
        ordered_children = images_c + rest_c
        children_html = "\n".join(
            _tree_to_html(c, mapping_by_block, field_tree, layout, indent + 1, border_class_map, bg_class_map)
            for c in ordered_children
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
                    '<table class="data-table"',
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
        # z-index:0 → background layer (fills sit behind text and borders).
        full_style = f"{fill_css}{border_css}z-index:0;{pos_style}"
        # Story 29.4: data-node-id added so patchNodeGeometry works for rect nodes
        node_id = node.get("id") or node.get("block_id") or f"rect-{id(node)}"
        # Story 32.1: apply bg-N CSS class from step 5.2 lookup
        bg_cls = ""
        if bg_class_map and fill_color is not None:
            bg_cls = bg_class_map.get(fill_color, "")
        class_attr = f' class="{bg_cls}"' if bg_cls else ""
        return f'{pad}<div data-node-id="{node_id}" data-type="rect"{class_attr} style="{full_style}"></div>'

    elif node_type == "field":
        return _generate_field_html(node, mapping_by_block, field_tree, layout, indent)

    elif node_type == "image":
        bbox = node.get("bbox")
        bbox_valid = node.get("bbox_valid", True)
        img_path = node.get("image_path", "")
        if not bbox_valid or not img_path:
            return ""
        pos_style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        # z-index:0 → background layer. Images (logos, table backgrounds) must always
        # sit behind text regardless of DOM position (cross-section z-order fix).
        # object-fit:contain — guarantees the full image is visible without cropping,
        # even when the PDF bbox aspect ratio differs from the extracted image's natural
        # aspect ratio (e.g. clamped y0 makes the CSS box shorter than the source image).
        # object-position:top left — aligns the image to the anchor point of the bbox.
        style = (
            f"z-index:0;object-fit:contain;object-position:top left;{pos_style}"
            if pos_style
            else "z-index:0;object-fit:contain;object-position:top left;"
        )
        # Story 29.4: data-node-id added so patchNodeGeometry works for image nodes
        node_id = node.get("id") or node.get("block_id") or f"image-{id(node)}"
        return f'{pad}<img src="{img_path}" data-node-id="{node_id}" data-type="image" style="{style}" />'

    elif node_type == "chart":
        chart_type = node.get("chart_type", "unknown")
        bbox = node.get("bbox")
        pos_style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        # z-index:1 → foreground layer (charts sit above image backgrounds).
        style = f"z-index:1;{pos_style}" if pos_style else "z-index:1;"
        # Story 29.4: data-node-id added so patchNodeGeometry works for chart nodes
        node_id = node.get("id") or node.get("block_id") or f"chart-{id(node)}"
        return f'{pad}<div data-node-id="{node_id}" data-type="chart" data-chart-type="{chart_type}" style="{style}"><!-- chart --></div>'

    elif node_type == "svg":
        svg_content = node.get("svg_content", "")
        bbox = node.get("bbox")
        pos_style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        # z-index:1 → foreground layer (SVG vector graphics above backgrounds).
        # overflow:hidden so SVG paths never bleed outside the positioned container.
        style = f"z-index:1;overflow:hidden;{pos_style}" if pos_style else "z-index:1;overflow:hidden;"
        node_id = node.get("id") or node.get("block_id") or f"svg-{id(node)}"
        if svg_content:
            return f'{pad}<div data-node-id="{node_id}" data-type="svg" style="{style}">{svg_content}</div>'
        # Fallback: placeholder when svg_content is empty
        return f'{pad}<div data-node-id="{node_id}" data-type="svg" style="{style}"><!-- svg: no content --></div>'

    elif node_type == "barcode":
        barcode_fmt = node.get("barcode_format", "CODE128")
        barcode_value = node.get("value", "")
        bbox = node.get("bbox")
        style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        # z-index:1 → foreground layer (barcode sits above image backgrounds).
        # overflow:hidden so the SVG never bleeds outside the positioned div.
        if style:
            style = style.rstrip(";") + ";z-index:1;overflow:hidden;"
        else:
            style = "z-index:1;overflow:hidden;"
        style_attr = f' style="{style}"'
        # Story 29.4: data-node-id added so patchNodeGeometry works for barcode nodes
        node_id = node.get("id") or node.get("block_id") or f"barcode-{id(node)}"
        if barcode_value:
            svg_content = _barcode_to_svg_content(barcode_value, barcode_fmt)
            if svg_content:
                return (
                    f'{pad}<div data-node-id="{node_id}" data-type="barcode" data-format="{barcode_fmt}"'
                    f' data-value="{barcode_value}"{style_attr}>{svg_content}</div>'
                )
        # Placeholder for unsupported formats or missing values.
        # Shows format name honestly instead of a misleading barcode.
        # JsBarcode will render the real barcode at runtime in the exported template.
        placeholder_svg = (
            f'<svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">'
            f'<rect width="200" height="80" fill="#f5f5f5" stroke="#ccc" rx="4"/>'
            f'<text x="100" y="35" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#888">'
            f"&#x2581;&#x2582;&#x2583;&#x2584;&#x2583;&#x2582;&#x2581; {barcode_fmt}</text>"
            f'<text x="100" y="55" text-anchor="middle" font-family="sans-serif" font-size="9" fill="#aaa">'
            f"{barcode_value or 'sem valor'}</text>"
            f"</svg>"
        )
        return (
            f'{pad}<div data-node-id="{node_id}" data-type="barcode" data-format="{barcode_fmt}"'
            f' data-value="{barcode_value}"{style_attr}>{placeholder_svg}</div>'
        )

    elif node_type == "line":
        bbox = node.get("bbox")
        stroke_color = node.get("stroke_color")
        width = node.get("width", 1.0)
        orientation = node.get("orientation", "horizontal")
        pos_style = _bbox_to_absolute_style(
            bbox,
            float(layout.get("page_height_pts", _A4_HEIGHT_PTS)),
            float(layout.get("page_width_pts", _A4_WIDTH_PTS)),
        )
        color_css = f"#{_color_int_to_hex(stroke_color)}" if stroke_color is not None else "#000000"
        if orientation == "vertical":
            # Vertical lines (e.g. barcode stripes): render as left border
            border_px = max(1, round(width * _SCALE_X))
            line_style = f"border-left:{border_px}px solid {color_css};"
        else:
            # Horizontal lines (separators): render as top border
            border_px = max(1, round(width * _SCALE_Y))
            line_style = f"border-top:{border_px}px solid {color_css};"
        # z-index:2 → border layer (grid lines sit on top of fills and text).
        z_style = "z-index:2;"
        full_style = f"{line_style}{z_style}{pos_style}" if pos_style else f"{line_style}{z_style}"
        # Story 29.4: data-node-id added so patchNodeGeometry works for line nodes
        node_id = node.get("id") or node.get("block_id") or f"line-{id(node)}"
        # Story 32.1: apply border-N CSS class from step 5.2 lookup
        border_cls = ""
        if border_class_map and stroke_color is not None:
            border_cls = border_class_map.get((stroke_color, orientation), "")
        class_attr = f' class="{border_cls}"' if border_cls else ""
        return f'{pad}<div data-node-id="{node_id}" data-type="line" data-orientation="{orientation}"{class_attr} style="{full_style}"></div>'

    else:
        # Generic node — recurse children or render standalone text block
        if children:
            children_html = "\n".join(
                _tree_to_html(c, mapping_by_block, field_tree, layout, indent, border_class_map, bg_class_map)
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
            # z-index:1 → foreground layer (text always above image/rect backgrounds).
            # white-space:nowrap — each span = one PDF line; prevent CSS font-metric drift
            # from wrapping text that occupies a single visual line in the source PDF.
            z_style = "z-index:1;"
            nowrap_style = "white-space:nowrap;"
            style_parts = [s for s in (z_style, nowrap_style, bold_style, size_style, color_style, pos_style) if s]
            style_attr = f' style="{"".join(style_parts)}"' if style_parts else ""
            font_name = node.get("font_name")
            is_italic = node.get("is_italic", False)
            css_classes = []
            if font_name:
                css_classes.append(_font_class_with_style(font_name, is_bold, is_italic))
            if color_int is not None:
                css_classes.append(f"c-{_color_int_to_hex(color_int)}")
            css_classes = [c for c in css_classes if c]
            class_attr = f' class="{" ".join(css_classes)}"' if css_classes else ""
            return f'{pad}<span data-node-id="{node_id}" data-type="{node_type}"{class_attr}{style_attr}>{text}</span>'
        return ""


def _step_5_1_tree_driven_html(
    document_trees: dict[str, dict[str, Any]],
    field_mappings: list[dict[str, Any]],
    field_tree: dict[str, Any] | None,
    layout_types: list[dict[str, Any]],
    border_class_map: dict[tuple, str] | None = None,
    bg_class_map: dict[int, str] | None = None,
) -> dict[str, str]:
    """5.1 — Generate hierarchical HTML per layout by walking document_trees.

    Returns: {layout_id: html_string}
    """
    html_by_layout: dict[str, str] = {}

    for layout in layout_types:
        layout_id = layout.get("id", "")
        tree = document_trees.get(layout_id)
        if not tree:
            continue

        layout_mappings = [m for m in field_mappings if m.get("layout_type_id") == layout_id]
        mapping_by_block: dict[str, dict[str, Any]] = {}
        for m in layout_mappings:
            bid = m.get("block_id")
            if bid:
                mapping_by_block[bid] = m

        html = _tree_to_html(tree, mapping_by_block, field_tree, layout, 0, border_class_map, bg_class_map)
        html_by_layout[layout_id] = html

    return html_by_layout
