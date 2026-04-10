"""Stage 5 -- HTML Generation Helpers sub-module.

Responsibilities:
  - Constants (_BASE_CSS_RESET, scale factors)
  - Barcode placeholder HTML (_barcode_placeholder_html) — Story 41.9
  - Backward-compat stub (_barcode_to_svg_content) — returns "" (python-barcode removed)
  - Color and font utilities (_color_int_to_hex, _sanitize_font_class, _font_class_with_style)
  - Bbox to CSS style conversion (_bbox_to_absolute_style, _sanitize_name)
  - Field HTML generation (_generate_field_html)
  - Array field detection (_is_array_field, _node_is_array)
  - Table HTML generation (_generate_table_html)
  - Step 5.1 entry point (_step_5_1_tree_driven_html -- imports html_tree._tree_to_html)

Story 41.3 -- extracted from stage5_template_generation.py
Story 41.9 -- replaced python-barcode SVG with JsBarcode placeholder div
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)


def _color_int_to_hex(color_int: int) -> str:
    """Convert an RGB integer to a 6-digit hex string."""
    return f"{color_int & 0xFFFFFF:06x}"


def _sanitize_font_class(font_name: str) -> str:
    """Create a safe CSS class name from a font name."""
    # Strip common PDF font subset prefixes like "ABCDEF+"
    clean = re.sub(r"^[A-Z]{6}\+", "", font_name)
    return re.sub(r"[^a-z0-9-]", "-", clean.lower()).strip("-")


def _font_class_with_style(font_name: str, is_bold: bool = False, is_italic: bool = False) -> str:
    """Create a CSS class name including bold/italic suffix.

    Returns e.g. 'f-arial', 'f-arial-b', 'f-arial-i', 'f-arial-bi'.
    """
    base = _sanitize_font_class(font_name)
    if not base:
        return ""
    suffix = ""
    if is_bold and is_italic:
        suffix = "-bi"
    elif is_bold:
        suffix = "-b"
    elif is_italic:
        suffix = "-i"
    return f"f-{base}{suffix}"


def _barcode_placeholder_html(node_id: str, barcode_format: str, value: str, bbox: dict) -> str:
    """Generate a JsBarcode-compatible placeholder div for a barcode node.

    Story 41.9: Replaces python-barcode SVG generation. JsBarcode renders the
    real barcode at runtime in the canvas iframe and exported template.
    Supports all formats including MSI and CODABAR (python-barcode did not).
    """
    x = bbox.get("x", 0)
    y = bbox.get("y", 0)
    w = bbox.get("width", 200)
    h = bbox.get("height", 60)
    return (
        f'<div id="{node_id}" data-node-id="{node_id}" data-type="barcode" '
        f'data-format="{barcode_format}" data-value="{value}" '
        f'style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
        f'z-index:1;overflow:hidden;"></div>'
    )


def _barcode_to_svg_content(value: str, barcode_format: str) -> str:  # noqa: ARG001
    """Backward-compatible stub — python-barcode removed in Story 41.9.

    Always returns "" so callers fall back to their placeholder SVG path.
    JsBarcode renders barcodes at runtime in canvas iframe and exported template.
    """
    return ""


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_A4_WIDTH_PTS: float = 595.0
_A4_HEIGHT_PTS: float = 842.0
_SCALE_X: float = 794 / _A4_WIDTH_PTS
_SCALE_Y: float = 1123 / _A4_HEIGHT_PTS

# Base CSS reset -- minimal, NOT hardcoded layout values
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
  z-index: 3;
}
.flow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1123px;
  z-index: 1;
  /* overflow:visible -- .page already clips at its boundary.
     overflow:hidden here cropped images whose top bbox was near 0 or
     whose containing section had accumulated layout offset. */
}
.footer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1123px;
  z-index: 2;
}
.section {
  position: relative;
}
table.data-table {
  border-collapse: collapse;
}
table.data-table th,
table.data-table td {
  border: 1px solid #ccc;
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
    bbox: list | None,
    page_height_pts: float = _A4_HEIGHT_PTS,
    page_width_pts: float = _A4_WIDTH_PTS,
) -> str | None:
    """Convert PyMuPDF bbox [x0, y0, x1, y1] to CSS position:absolute style.

    PyMuPDF (fitz) uses screen coordinates: y=0 at top-left, y increases downward.
    bbox[1] (y0) is the TOP edge of the element -- maps directly to CSS `top`.
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


def _generate_field_html(
    node: dict[str, Any],
    mapping_by_block: dict[str, dict[str, Any]],
    field_tree: dict[str, Any] | None,
    layout: dict[str, Any],
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
        is_italic = child.get("is_italic", False)
        css_classes: list[str] = []
        if font_name:
            fc = _font_class_with_style(font_name, is_bold, is_italic)
            if fc:
                css_classes.append(fc)
        if color_int is not None:
            css_classes.append(f"c-{_color_int_to_hex(color_int)}")
        class_attr = f' class="{" ".join(css_classes)}"' if css_classes else ""
        # z-index:1 → foreground layer (field text above image/rect backgrounds).
        # white-space:nowrap -- each child = one PDF line; prevent CSS font-metric wrapping.
        z_style = "z-index:1;"
        nowrap_style = "white-space:nowrap;"
        style_parts = [s for s in (z_style, nowrap_style, bold_style, size_style, color_style, pos_style) if s]
        style = "".join(style_parts)

        if child_type == "label":
            style_attr = f' style="{style}"' if style else ""
            node_id = block_id or f"label-{id(child)}"
            parts.append(f'{pad}<span data-node-id="{node_id}" data-type="label"{class_attr}{style_attr}>{text}</span>')
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
                        f' data-status="{status}"{class_attr}{style_attr}'
                        f' data-bind="text: {xsd_path}">{text}</span>'
                    )
            else:
                style_attr = f' style="{style}"' if style else ""
                parts.append(
                    f'{pad}<span data-node-id="{node_id}" data-status="{status}"{class_attr}{style_attr}>{text}</span>'
                )
        elif child_type == "image":
            img_path = child.get("image_path", "")
            pos_style = _bbox_to_absolute_style(child.get("bbox"), page_h, page_w)
            # object-fit:contain -- same rationale as top-level image nodes above.
            img_style = (
                f"z-index:0;object-fit:contain;object-position:top left;{pos_style}"
                if pos_style
                else "z-index:0;object-fit:contain;object-position:top left;"
            )
            parts.append(f'{pad}<img src="{img_path}" data-type="image" style="{img_style}" />')

    # Wrap field children
    variant = node.get("variant", "required")
    if variant == "conditional":
        block_id = node.get("id", "").replace("block-", "")
        binding = block_id or "condition"
        inner = "\n".join(parts)
        return f"{pad}<!-- ko if: {binding} -->\n{inner}\n{pad}<!-- /ko -->"

    return "\n".join(parts)


def _is_array_field(path: str, field_tree: dict[str, Any] | None) -> bool:
    """Check if a field path is an array in the XSD field tree."""
    if not field_tree:
        return False
    for node in field_tree.get("root_nodes", []):
        if _node_is_array(node, path):
            return True
    return False


def _node_is_array(node: dict[str, Any], target_path: str) -> bool:
    """Recursively check if a node matches target_path and is_array."""
    if node.get("path", "") == target_path and node.get("is_array"):
        return True
    for child in node.get("children", []):
        if _node_is_array(child, target_path):
            return True
    return False


def _generate_table_html(
    table_node: dict[str, Any],
    mapping_by_block: dict[str, dict[str, Any]],
    field_tree: dict[str, Any] | None,
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
        cell_text = child.get("text", "")
        if field_name:
            body_cells.append(f'<td data-bind="text: {field_name}">{cell_text}</td>')
        else:
            body_cells.append(f"<td>{cell_text}</td>")

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


# NOTE: _step_5_1_tree_driven_html lives in html_tree.py (it calls _tree_to_html)
# Re-exported here for backward compatibility via __init__.py
