"""Stage 27 — Template Draft Generation.

Generates a full HTML/CSS draft template from the pipeline's intermediate
results, suitable for loading into the Canvas editor.

Structure:
    - One <div class="page page-{name_lower}" data-layout-type="{name}">
      per layout type in context["layout_types"].
    - Each page contains three zones: header, flow, footer.
    - For each field_mapping that is NOT a table cell, a
      <span data-bind="text: {xsd_field_path}"></span> is emitted in .flow.
    - Arrays (xsd_field_path contains "[]", or field_tree shows is_array)
      emit <!-- ko foreach: items --> … <!-- /ko --> wrappers.
    - Conditional sections from context["variants"] (if present) emit
      <!-- ko if: condition --> … <!-- /ko -->.
    - CSS includes A4 dimensions and basic zone styling.

Reads:
    context["layout_types"]   — List[Dict] with "name", "pages" keys
    context["field_mappings"] — List[Dict] from Stage 23/24
    context["field_tree"]     — optional Dict with flat_paths, nodes
    context["variants"]       — optional List[Dict] with "condition" key

Writes:
    context["template_draft"] — Dict:
        {
          "html": str,
          "css": str,
          "coverage": {
              "fields": {"mapped": int, "total": int}
          }
        }

Registers itself as Stage 27 (Block 8).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# A4 scale constants: 595 pt wide × 842 pt tall → 794 px × 1123 px (96 DPI)
SCALE_X = 794 / 595  # ≈ 1.3345
SCALE_Y = 1123 / 842  # ≈ 1.3337

# A4 page dimensions in points (default for scale calculation)
_A4_HEIGHT_PTS: float = 842.0
_A4_WIDTH_PTS: float = 595.0

# ---------------------------------------------------------------------------
# CSS generation
# ---------------------------------------------------------------------------

_BASE_CSS = """\
.page {
  width: 794px;
  height: 1123px;
  position: relative;
  box-sizing: border-box;
  background: #ffffff;
  margin: 0 auto 1em auto;
  overflow: hidden;
}
.header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 144px;
}
.flow {
  position: absolute;
  top: 144px;
  left: 0;
  right: 0;
  bottom: 96px;
  overflow: hidden;
}
.footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 96px;
}
.unpositioned {
  display: block;
  position: relative;
  margin-bottom: 0.2em;
  font-family: Arial, sans-serif;
  font-size: 10pt;
  white-space: nowrap;
  overflow: hidden;
}
table.data-table {
  width: 100%;
  border-collapse: collapse;
}
table.data-table th,
table.data-table td {
  border: 1px solid #ccc;
  padding: 4px 6px;
  font-family: Arial, sans-serif;
  font-size: 9pt;
}
.flow.positioned-layout {
  overflow: visible;
}
"""


def _generate_css() -> str:
    return _BASE_CSS


# ---------------------------------------------------------------------------
# HTML generation helpers
# ---------------------------------------------------------------------------


def _is_array_path(path: str, field_tree: Optional[Dict[str, Any]]) -> bool:
    """Return True if path represents an array field."""
    if "[]" in path:
        return True
    # Check field_tree nodes for is_array flag
    if field_tree:
        for node in field_tree.get("root_nodes", []):
            if _node_is_array(node, path):
                return True
    return False


def _node_is_array(node: Dict[str, Any], target_path: str) -> bool:
    """Recursively check if a node or its children match target_path and is_array."""
    node_path = node.get("path", "")
    if node_path == target_path and node.get("is_array"):
        return True
    for child in node.get("children", []):
        if _node_is_array(child, target_path):
            return True
    return False


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def _bbox_to_style(
    bbox: Optional[List],
    page_height_pts: float = _A4_HEIGHT_PTS,
    font_name: Optional[str] = None,
    font_size: Optional[float] = None,
) -> Optional[str]:
    """Convert PDF bbox [x0, y0, x1, y1] in points to inline CSS for position:absolute.

    Y-axis is inverted: PDF origin is bottom-left; CSS origin is top-left.
    Uses bbox[3] (y1 = top edge in PDF coordinates) for the CSS top distance.

    Returns a compact CSS string like 'position:absolute;left:56px;top:995px;...'
    or None if bbox is absent or has fewer than 4 coordinates.
    """
    if not bbox or len(bbox) < 4:
        return None
    x_px = round(bbox[0] * SCALE_X)
    # Y-inversion: bbox[3] is the top edge in PDF coords (highest y value).
    # CSS top = distance from page top = (page_height - pdf_y1) * SCALE_Y
    y_px = round((page_height_pts - bbox[3]) * SCALE_Y)
    w_px = round((bbox[2] - bbox[0]) * SCALE_X)
    h_px = round((bbox[3] - bbox[1]) * SCALE_Y)
    parts = [
        "position:absolute",
        f"left:{x_px}px",
        f"top:{y_px}px",
        f"width:{w_px}px",
        f"height:{h_px}px",
    ]
    if font_name:
        parts.append(f"font-family:{font_name}")
    if font_size:
        parts.append(f"font-size:{font_size}pt")
    parts += ["white-space:nowrap", "overflow:hidden", "line-height:1.2"]
    return ";".join(parts)


def _generate_field_element(
    mapping: Dict[str, Any],
    field_tree: Optional[Dict[str, Any]],
    page_height_pts: float = _A4_HEIGHT_PTS,
    block_index: int = 0,
) -> str:
    """Generate HTML <span> for a single field mapping.

    Positioned fields (bbox present): position:absolute with Y-inverted coordinates,
    width/height, optional font, and data-node-id/data-xsd-path/data-status attributes.

    Unpositioned fields (no bbox): position:relative with class 'unpositioned'.

    When xsd_field_path is empty but label_text or pdf_text exists, renders a
    fallback span with the extracted text visible in the canvas so the canvas is
    not blank when XSD matching produced no paths.
    """
    path = mapping.get("xsd_field_path", "")
    label = mapping.get("label_text", "")
    pdf_text = mapping.get("pdf_text", "")
    status = mapping.get("status") or ("mapped" if path else "unmapped")

    # Stable node identifier for inspector / drag-and-drop interaction
    node_id = (
        mapping.get("block_id")
        or (f"field-{path.replace('.', '-').replace('[]', '-arr')}" if path else f"field-{block_index}")
    )

    # Optional font properties from PDF extraction
    font_name: Optional[str] = mapping.get("font_name") or mapping.get("font_family")
    font_size: Optional[float] = mapping.get("font_size")

    bbox = mapping.get("bbox")
    style = (
        _bbox_to_style(bbox, page_height_pts=page_height_pts, font_name=font_name, font_size=font_size)
        if bbox
        else None
    )

    if not path:
        # Fallback: render whatever text was extracted from the PDF so the
        # canvas is not blank (e.g. OPENROUTER_API_KEY absent, difflib had no
        # candidates, or flat_paths was empty because field_tree was None).
        display_text = label or pdf_text
        if not display_text:
            return ""
        if style:
            return (
                f'<span data-node-id="{node_id}" data-status="{status}"'
                f' style="{style}">{display_text}</span>'
            )
        return (
            f'<span class="unpositioned" data-node-id="{node_id}"'
            f' data-status="{status}" style="position:relative">{display_text}</span>'
        )

    if _is_array_path(path, field_tree):
        # Foreach wrapper — arrays cannot use absolute positioning
        item_name = path.rstrip("[]").split(".")[-1]
        return "\n".join([
            f"<!-- ko foreach: {path.replace('[]', '')} -->",
            f'  <span class="unpositioned" data-node-id="{node_id}"'
            f' data-xsd-path="{path}" data-status="{status}"'
            f' data-bind="text: {item_name}" style="position:relative"></span>',
            "<!-- /ko -->",
        ])

    if style:
        return (
            f'<span data-node-id="{node_id}" data-xsd-path="{path}"'
            f' data-status="{status}" style="{style}"'
            f' data-bind="text: {path}">{pdf_text}</span>'
        )
    return (
        f'<span class="unpositioned" data-node-id="{node_id}"'
        f' data-xsd-path="{path}" data-status="{status}"'
        f' data-bind="text: {path}" style="position:relative">{pdf_text}</span>'
    )


def _generate_page_html(
    layout_name: str,
    mappings: List[Dict[str, Any]],
    variants: List[Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
    page_height_pts: float = _A4_HEIGHT_PTS,
) -> str:
    name_lower = layout_name.lower().replace(" ", "_").replace("-", "_")

    # Determine if any non-table mapping has bbox coordinates
    has_positioned = any(
        m.get("bbox")
        for m in mappings
        if not m.get("is_table_cell") and not m.get("from_table")
    )
    flow_class = "flow positioned-layout" if has_positioned else "flow"

    lines = [
        f'<div class="page page-{name_lower}" data-layout-type="{layout_name}">',
        '  <div class="header">',
        "    <!-- Header content -->",
        "  </div>",
        f'  <div class="{flow_class}">',
    ]

    # Conditional sections from variants
    for variant in variants:
        condition = variant.get("condition", "")
        if condition:
            lines.append(f"    <!-- ko if: {condition} -->")
            lines.append(f"    <!-- /ko -->")

    # Regular field mappings
    block_index = 0
    for mapping in mappings:
        if mapping.get("is_table_cell") or mapping.get("from_table"):
            continue
        elem = _generate_field_element(
            mapping, field_tree,
            page_height_pts=page_height_pts,
            block_index=block_index,
        )
        if elem:
            for eline in elem.splitlines():
                lines.append(f"    {eline}")
        block_index += 1

    lines.append("  </div>")
    lines.append('  <div class="footer">')
    lines.append("    <!-- Footer content -->")
    lines.append("  </div>")
    lines.append("</div>")

    return "\n".join(lines)


def _generate_html(
    layout_types: List[Dict[str, Any]],
    field_mappings: List[Dict[str, Any]],
    variants: List[Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
) -> str:
    page_blocks = []
    for lt in layout_types:
        name = lt.get("name", "default")
        # Use actual page height from layout type if provided (AC6 — non-A4 scale)
        page_height_pts = float(lt.get("page_height_pts", _A4_HEIGHT_PTS))
        page_html = _generate_page_html(
            name, field_mappings, variants, field_tree,
            page_height_pts=page_height_pts,
        )
        page_blocks.append(page_html)

    if not page_blocks:
        # Fallback: generate a single default page
        page_html = _generate_page_html("default", field_mappings, variants, field_tree)
        page_blocks.append(page_html)

    return "\n\n".join(page_blocks)


# ---------------------------------------------------------------------------
# Coverage calculation
# ---------------------------------------------------------------------------


def _calculate_coverage(
    field_mappings: List[Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    flat_paths: List[str] = []
    if field_tree:
        flat_paths = [p for p in field_tree.get("flat_paths", []) if p]

    total = len(flat_paths)
    mapped_paths: Set[str] = {
        m.get("xsd_field_path", "")
        for m in field_mappings
        if m.get("xsd_field_path")
    }
    mapped = len(mapped_paths & set(flat_paths)) if flat_paths else len(mapped_paths)

    return {"fields": {"mapped": mapped, "total": total}}


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 27 executor — Template Draft Generation."""
    emit = context.get("emit_progress")

    if emit:
        try:
            emit(
                {
                    "stage": 27,
                    "stage_name": "Template Draft Generation",
                    "status": "running",
                    "summary": {},
                }
            )
        except Exception:  # noqa: BLE001
            pass

    layout_types: List[Dict[str, Any]] = context.get("layout_types") or []
    field_mappings: List[Dict[str, Any]] = context.get("field_mappings") or []
    field_tree: Optional[Dict[str, Any]] = context.get("field_tree")
    variants: List[Dict[str, Any]] = context.get("variants") or []

    # --- Diagnostic logging (Bug 2 investigation) ---------------------------
    mappings_with_path = sum(1 for m in field_mappings if m.get("xsd_field_path"))
    logger.info(
        "[Stage 27] field_mappings total=%d, with_xsd_field_path=%d",
        len(field_mappings),
        mappings_with_path,
    )
    logger.info("[Stage 27] layout_types count=%d", len(layout_types))
    if field_tree:
        flat_paths = field_tree.get("flat_paths", [])
        logger.info("[Stage 27] field_tree flat_paths count=%d", len(flat_paths))
    else:
        logger.info("[Stage 27] field_tree=None (XSD not parsed)")
    # ------------------------------------------------------------------------

    html = _generate_html(layout_types, field_mappings, variants, field_tree)
    css = _generate_css()
    coverage = _calculate_coverage(field_mappings, field_tree)

    # --- Diagnostic logging (html output) -----------------------------------
    logger.info("[Stage 27] html length=%d", len(html))
    logger.info("[Stage 27] html preview=%r", html[:200])
    # ------------------------------------------------------------------------

    template_draft: Dict[str, Any] = {
        "html": html,
        "css": css,
        "coverage": coverage,
    }

    context["template_draft"] = template_draft

    summary = {
        "html_length": len(html),
        "css_length": len(css),
        "coverage": coverage,
        "layout_types_count": len(layout_types),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 27,
                    "stage_name": "Template Draft Generation",
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
    """Replace stub Stage 27 with this implementation."""
    registry.remove_stage(27)
    registry.register_stage(
        stage_number=27,
        name="Template Draft",
        block_id=8,
        estimated_duration=2.0,
        execute_fn=execute,
    )
