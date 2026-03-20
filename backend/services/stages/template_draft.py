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

# ---------------------------------------------------------------------------
# CSS generation
# ---------------------------------------------------------------------------

_BASE_CSS = """\
.page {
  width: 8.27in;
  height: 11.69in;
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
  height: 1.5in;
}
.flow {
  position: absolute;
  top: 1.5in;
  left: 0;
  right: 0;
  bottom: 1in;
  overflow: hidden;
}
.footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1in;
}
.field-group {
  display: flex;
  margin-bottom: 0.2em;
}
.label {
  font-family: Arial, sans-serif;
  font-size: 10pt;
  font-weight: bold;
  margin-right: 0.5em;
}
.field-value {
  font-family: Arial, sans-serif;
  font-size: 10pt;
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
.field-group.positioned {
  position: absolute;
  display: flex;
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


def _bbox_to_style(bbox: Optional[List]) -> Optional[str]:
    """Convert PDF bbox [x0, y0, x1, y1] in points to CSS absolute positioning string.

    Returns a CSS string like 'left: 56px; top: 112px;' or None if bbox is absent/invalid.
    """
    if not bbox or len(bbox) < 2:
        return None
    x_px = round(bbox[0] * SCALE_X)
    y_px = round(bbox[1] * SCALE_Y)
    return f"left: {x_px}px; top: {y_px}px;"


def _generate_field_element(mapping: Dict[str, Any], field_tree: Optional[Dict[str, Any]]) -> str:
    """Generate HTML for a single field mapping.

    When xsd_field_path is empty but label_text or pdf_text exists, renders a
    fallback field-group with the extracted text visible in the canvas.  This
    prevents a completely blank canvas when XSD matching did not produce paths
    (e.g. OPENROUTER_API_KEY absent and difflib returned no candidates, or
    flat_paths was empty because field_tree was None).
    """
    path = mapping.get("xsd_field_path", "")
    label = mapping.get("label_text", "")
    pdf_text = mapping.get("pdf_text", "")

    # Determine positioning from bbox
    bbox = mapping.get("bbox")
    style = _bbox_to_style(bbox)
    if style:
        div_open = f'<div class="field-group positioned" style="{style}">'
    else:
        div_open = '<div class="field-group">'

    if not path:
        # Fallback: render whatever text was extracted from the PDF so the
        # canvas is not blank.  Use label as the label span and pdf_text as
        # the visible value span (static, not data-bound).
        if not label and not pdf_text:
            return ""
        label_html = f'<span class="label">{label}:</span>\n    ' if label else ""
        value_html = f'<span class="field-value">{pdf_text}</span>' if pdf_text else ""
        if not label_html and not value_html:
            return ""
        return (
            f'{div_open}\n'
            f"    {label_html}"
            f"{value_html}\n"
            f"  </div>"
        )

    if _is_array_path(path, field_tree):
        # Foreach wrapper (arrays don't support absolute positioning)
        item_name = path.rstrip("[]").split(".")[-1]
        lines = [
            f"<!-- ko foreach: {path.replace('[]', '')} -->",
            f'  <div class="field-group">',
            f'    <span class="field-value" data-bind="text: {item_name}"></span>',
            f"  </div>",
            f"<!-- /ko -->",
        ]
        return "\n".join(lines)
    else:
        label_html = f'<span class="label">{label}:</span>\n    ' if label else ""
        return (
            f'{div_open}\n'
            f"    {label_html}"
            f'<span class="field-value" data-bind="text: {path}"></span>\n'
            f"  </div>"
        )


def _generate_page_html(
    layout_name: str,
    mappings: List[Dict[str, Any]],
    variants: List[Dict[str, Any]],
    field_tree: Optional[Dict[str, Any]],
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
    for mapping in mappings:
        if mapping.get("is_table_cell") or mapping.get("from_table"):
            continue
        elem = _generate_field_element(mapping, field_tree)
        if elem:
            for eline in elem.splitlines():
                lines.append(f"    {eline}")

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
        page_html = _generate_page_html(name, field_mappings, variants, field_tree)
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
