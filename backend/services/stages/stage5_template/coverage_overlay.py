"""Stage 5 -- Coverage & Overlay sub-module (Steps 5.3, 5.4).

Responsibilities:
  - Coverage calculation (fields 60%% + tables 25%% + images 15%%) (5.3)
  - Per-layout overlay items (5.4)
  - Anchor generation and table container overlays

Story 41.3 -- extracted from stage5_template_generation.py
"""

from __future__ import annotations

import logging
from typing import Any

from models.pipeline_context import FieldMappingEntry, LayoutTypeInfo
from services.stages.stage5_template.html_helpers import (
    _A4_HEIGHT_PTS,
    _A4_WIDTH_PTS,
)

logger = logging.getLogger(__name__)


def _count_nodes_by_type(tree: dict[str, Any] | None, target_type: str) -> int:
    """Count nodes of a given type in the tree recursively."""
    if not tree:
        return 0
    count = 1 if tree.get("type") == target_type else 0
    for child in tree.get("children", []):
        count += _count_nodes_by_type(child, target_type)
    return count


def _count_mapped_tables(
    tree: dict[str, Any] | None,
    layout_mappings: list[FieldMappingEntry],
) -> int:
    """Count tables that have at least one mapped cell."""
    if not tree:
        return 0
    table_ids_with_mapping: set[str] = set()

    # Collect all table_cell block_ids
    mapped_block_ids = {m.block_id for m in layout_mappings if m.xsd_field_path}

    def _walk(node: dict[str, Any], current_table_id: str | None = None):
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


def _count_mapped_charts(
    tree: dict[str, Any] | None,
    layout_mappings: list[FieldMappingEntry],
) -> int:
    """Story 34.2 -- Count charts that have data binding configured.

    A chart is considered mapped if it has a block_id that appears in
    the field_mappings with an xsd_field_path, OR if its node has a
    non-empty 'binding' or 'data_source' property.
    """
    if not tree:
        return 0

    mapped_block_ids = {m.block_id for m in layout_mappings if m.xsd_field_path}
    count = 0

    def _walk(node: dict[str, Any]):
        nonlocal count
        if node.get("type") == "chart":
            block_id = node.get("block_id", "")
            binding = node.get("binding", "") or node.get("properties", {}).get("data_source", "")
            if (block_id and block_id in mapped_block_ids) or binding:
                count += 1
        for child in node.get("children", []):
            _walk(child)

    _walk(tree)
    return count


def _step_5_3_coverage(
    field_mappings: list[FieldMappingEntry],
    field_tree: dict[str, Any] | None,
    document_trees: dict[str, dict[str, Any]],
    layout_types: list[LayoutTypeInfo],
) -> dict[str, dict[str, Any]]:
    """5.3 â€" Multidimensional coverage per layout.

    Story 34.2: Weights updated to include charts:
    fields 55% + tables 25% + images 10% + charts 10%.
    """
    coverage_by_layout: dict[str, dict[str, Any]] = {}

    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    total_xsd_fields = len(flat_paths) if flat_paths else 0

    for layout in layout_types:
        layout_id = layout.id
        tree = document_trees.get(layout_id)

        # Fields
        layout_mappings = [m for m in field_mappings if m.layout_type_id == layout_id]
        mapped_fields = len({m.xsd_field_path for m in layout_mappings if m.xsd_field_path})

        # Tables â€" count in document_tree
        total_tables = _count_nodes_by_type(tree, "table")
        mapped_tables = _count_mapped_tables(tree, layout_mappings)

        # Images â€" count in document_tree
        total_images = _count_nodes_by_type(tree, "image")
        # Images are "mapped" if they exist in the tree (extracted = usable)
        mapped_images = total_images

        # Charts â€" Story 34.2: count charts with data binding
        total_charts = _count_nodes_by_type(tree, "chart")
        mapped_charts = _count_mapped_charts(tree, layout_mappings)

        # Weighted percentage â€" Story 34.2: fields 55% + tables 25% + images 10% + charts 10%
        f_pct = (mapped_fields / total_xsd_fields * 100) if total_xsd_fields else 0
        t_pct = (mapped_tables / total_tables * 100) if total_tables else 100
        i_pct = (mapped_images / total_images * 100) if total_images else 100
        c_pct = (mapped_charts / total_charts * 100) if total_charts else 100
        percentage = round(f_pct * 0.55 + t_pct * 0.25 + i_pct * 0.10 + c_pct * 0.10)

        coverage_by_layout[layout_id] = {
            "fields": {"mapped": mapped_fields, "total": total_xsd_fields},
            "tables": {"mapped": mapped_tables, "total": total_tables},
            "images": {"mapped": mapped_images, "total": total_images},
            "charts": {"mapped": mapped_charts, "total": total_charts},
            "percentage": percentage,
        }

    return coverage_by_layout


# ---------------------------------------------------------------------------
# 5.4 Overlay Items
# ---------------------------------------------------------------------------


def _get_page_dimensions(
    enriched_documents: list[dict[str, Any]],
) -> dict[int, tuple[float, float]]:
    """Return page_number -> (width_pts, height_pts) from enriched_documents."""
    dims: dict[int, tuple[float, float]] = {}
    for doc in enriched_documents:
        for page in doc.get("pages", []):
            page_num = int(page.get("page_index", page.get("page_number", 0)))
            w = float(page.get("width", _A4_WIDTH_PTS) or _A4_WIDTH_PTS)
            h = float(page.get("height", _A4_HEIGHT_PTS) or _A4_HEIGHT_PTS)
            dims[page_num] = (w, h)
    return dims


def _step_5_4_overlay_items(
    field_mappings: list[FieldMappingEntry],
    layout_types: list[LayoutTypeInfo],
    enriched_documents: list[dict[str, Any]],
    document_trees: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """5.4 â€" Build overlay items filtered by layout_type_id.

    Includes table overlays (container + cell hover).
    """
    page_dims = _get_page_dimensions(enriched_documents)
    overlay_by_layout: dict[str, list[dict[str, Any]]] = {}

    for layout in layout_types:
        layout_id = layout.id
        layout_mappings = [m for m in field_mappings if m.layout_type_id == layout_id]

        items: list[dict[str, Any]] = []
        for mapping in layout_mappings:
            bbox = mapping.bbox
            if not bbox or len(bbox) < 4:
                continue
            try:
                x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            except (TypeError, ValueError):
                continue

            page_num = mapping.page_number
            page_w, page_h = page_dims.get(page_num, (_A4_WIDTH_PTS, _A4_HEIGHT_PTS))
            scale_x = 794.0 / page_w
            scale_y = 1123.0 / page_h

            overlay_type = "field"
            if mapping.is_table_cell or mapping.from_table:
                overlay_type = "table_cell"

            items.append(
                {
                    "node_id": mapping.block_id,
                    "xsd_path": mapping.xsd_field_path,
                    "label": mapping.label_text,
                    "value": mapping.pdf_text,
                    "status": "unmapped",
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
                }
            )

        # Add table container overlays from document_trees (G22)
        tree = document_trees.get(layout_id)
        if tree:
            _add_table_container_overlays(tree, items, page_dims, layout_id)

        overlay_by_layout[layout_id] = items

    return overlay_by_layout


def _generate_anchors(
    overlay_by_layout: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Generate layout anchors from overlay items for SyncView.

    Selects mapped fields that have both bbox_canvas and bbox_pdf,
    producing anchor points that connect both panels.
    """
    anchors_by_layout: dict[str, list[dict[str, Any]]] = {}

    for layout_id, items in overlay_by_layout.items():
        anchors: list[dict[str, Any]] = []
        for item in items:
            if item.get("overlay_type") == "table_container":
                continue
            bbox_canvas = item.get("bbox_canvas")
            bbox_pdf = item.get("bbox_pdf")
            if not bbox_canvas or not bbox_pdf:
                continue

            label = item.get("label") or item.get("xsd_path") or item.get("node_id") or ""
            anchors.append(
                {
                    "id": item.get("node_id") or f"anchor-{len(anchors)}",
                    "label": label,
                    "bbox_canvas": bbox_canvas,
                    "bbox_pdf": bbox_pdf,
                }
            )

        anchors_by_layout[layout_id] = anchors

    return anchors_by_layout


def _add_table_container_overlays(
    node: dict[str, Any],
    items: list[dict[str, Any]],
    page_dims: dict[int, tuple[float, float]],
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

                items.append(
                    {
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
                    }
                )
            except (TypeError, ValueError):
                pass

    for child in node.get("children", []):
        _add_table_container_overlays(child, items, page_dims, layout_id)


# ---------------------------------------------------------------------------
# 5.5 VariationMatrix Assembly
# ---------------------------------------------------------------------------
