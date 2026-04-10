"""Stage 3 — Tree Builder sub-module (Step 3.4).

Responsibilities:
  - Document hierarchy tree construction (_run_3_4, _build_tree)

Zone/section splitting and semantic utilities live in section_utils.py.

Story 41.3 — extracted from stage3_structural_analysis.py
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from models.pipeline_context import BlockClassification, DocumentTreeNode
from services.stages.stage3_structural.section_utils import (
    _assign_images_to_sections,
    _assign_tables_to_sections,
    _assign_visual_elements_to_sections,
    _barcode_bboxes_from_tree,
    _bbox_contains,
    _extract_barcode_value,
    _get_horizontal_separators,
    _line_inside_any_barcode,
    _split_by_drawn_lines,
    _split_by_gap,
    _zones_from_thresholds,
    _zones_from_visual_regions,
)
from services.stages.stage3_structural.semantic_utils import (
    _apply_suggested_bindings,  # noqa: F401 (re-exported for backward compat)
    _extract_semantic_name,
    _get_conditional_pdfs,
    _infer_section_name,
    _levenshtein_similarity,  # noqa: F401 (re-exported)
    _normalize_text,  # noqa: F401 (re-exported)
    _section_variant,
    _suggest_xsd_binding,  # noqa: F401 (re-exported)
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-step 3.4 — Hierarchy Builder
# ---------------------------------------------------------------------------


def _run_3_4(
    enriched_documents: list[dict[str, Any]],
    block_classifications: dict[str, BlockClassification],
    visual_analysis: dict[str, dict[str, Any]],
    clusters: list[dict[str, Any]],
    position_classifications_by_cluster: dict[str, Any],
) -> list[dict[str, Any]]:
    """Sub-step 3.4 — Hierarchy Builder.

    4 signals cascade: visual_regions -> drawn_elements -> grid_info -> proportional gap.
    Returns list of document_trees.
    """
    document_trees: list[dict[str, Any]] = []

    # Build page lookup
    page_lookup: dict[str, dict[str, Any]] = {}
    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            pk = f"{pdf_id}:{page['page_index']}"
            page_lookup[pk] = page

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        if cluster_id.startswith("_"):
            continue

        rep = cluster["representative_page"]
        page_key = f"{rep['pdf_id']}:{rep['page_index']}"
        page_data = page_lookup.get(page_key)

        if page_data is None:
            continue

        page_height = page_data.get("height", 842.0)
        _page_width = page_data.get("width", 595.0)  # noqa: F841

        # Step 1: Determine zones
        va = visual_analysis.get(page_key)
        if va and va.get("regions") and va.get("consistency_score", 0) > 0:
            zones = _zones_from_visual_regions(va["regions"], page_data)
        else:
            zones = _zones_from_thresholds(page_data)

        # Step 2: Split zones into sections
        for zone in zones:
            blocks_in_zone = zone["blocks"]
            drawn = page_data.get("drawn_elements")

            h_lines = _get_horizontal_separators(drawn, zone["bbox"])

            if h_lines:
                sections = _split_by_drawn_lines(blocks_in_zone, h_lines)
            else:
                gap_threshold = page_height * 0.025
                sections = _split_by_gap(blocks_in_zone, gap_threshold)

            grid_info = page_data.get("grid_info")
            if grid_info and isinstance(grid_info, dict) and grid_info.get("columns", 1) > 1:
                for section in sections:
                    section["multi_column"] = True
                    section["column_positions"] = grid_info.get("column_positions", [])

            zone["sections"] = sections

        # Step 3: Assign images, charts, barcodes, tables
        _assign_images_to_sections(zones, page_data.get("images", []))
        _assign_visual_elements_to_sections(zones, visual_analysis, page_key)
        _assign_tables_to_sections(zones, page_data.get("tables", []))

        # Step 4: Build tree
        tree = _build_tree(cluster_id, zones, block_classifications, page_data)

        document_trees.append(
            {
                "cluster_id": cluster_id,
                "representative_page": {"pdf_id": rep["pdf_id"], "page_index": rep["page_index"]},
                "tree": tree,
            }
        )

    return document_trees


def _build_tree(
    cluster_id: str,
    zones: list[dict[str, Any]],
    block_classifications: dict[str, BlockClassification],
    page_data: dict[str, Any],
) -> dict[str, Any]:
    """Build hierarchical tree: document > page > zones > sections > fields.

    Story 42.5 — internally builds DocumentTreeNode objects for type safety.
    Returns model_dump() so downstream stages receive plain dicts (backward compat).
    """
    page_node = DocumentTreeNode(type="page")
    root = DocumentTreeNode(id=f"root-{cluster_id}", type="document", children=[page_node])

    block_lookup: dict[str, dict[str, Any]] = {}
    for block in page_data.get("text_blocks", []):
        bid = block.get("id", "")
        if bid:
            block_lookup[bid] = block

    _empty_bc = BlockClassification()

    for zone in zones:
        zone_node = DocumentTreeNode(
            type=zone["type"],
            source=zone.get("source", "threshold"),
        )

        for section in zone.get("sections", []):
            section_blocks = section.get("blocks", [])
            variant = _section_variant(section_blocks, block_classifications)

            section_name = _infer_section_name(section_blocks, block_classifications)
            section_node = DocumentTreeNode(type="section", variant=variant)
            if section_name:
                section_node.name = section_name  # type: ignore[attr-defined]

            if variant == "conditional":
                section_node.present_in_pdfs = _get_conditional_pdfs(section_blocks, block_classifications)  # type: ignore[attr-defined]

            processed_ids: set[str] = set()

            table_bboxes = [t.get("bbox", [0, 0, 0, 0]) for t in section.get("tables", [])]
            for block in section_blocks:
                bb = block.get("bbox")
                if bb and any(_bbox_contains(tb, bb) for tb in table_bboxes):
                    processed_ids.add(block.get("id", ""))

            for block in section_blocks:
                bid = block.get("id", "")
                if bid in processed_ids:
                    continue

                bc = block_classifications.get(bid, _empty_bc)

                if bc.field_pair and bc.semantic == "label":
                    pair_id = bc.field_pair
                    pair_block = block_lookup.get(pair_id)

                    label_name = _extract_semantic_name(block)
                    label_child = DocumentTreeNode(
                        type="label",
                        block_id=bid,
                        text=block.get("text", ""),
                        bbox=block.get("bbox"),
                        is_bold=block.get("is_bold", False),
                        font_weight=block.get("font_weight", "normal"),
                        font_size=block.get("font_size"),
                        font_name=block.get("font_name"),
                        color=block.get("color"),
                    )
                    if label_name:
                        label_child.name = label_name  # type: ignore[attr-defined]
                    field_children: list[DocumentTreeNode] = [label_child]
                    if pair_block:
                        field_children.append(
                            DocumentTreeNode(
                                type="value",
                                block_id=pair_id,
                                text=pair_block.get("text", ""),
                                bbox=pair_block.get("bbox"),
                                is_bold=pair_block.get("is_bold", False),
                                font_weight=pair_block.get("font_weight", "normal"),
                                font_size=pair_block.get("font_size"),
                                font_name=pair_block.get("font_name"),
                                color=pair_block.get("color"),
                            )
                        )
                        processed_ids.add(pair_id)

                    field_node = DocumentTreeNode(
                        type="field",
                        variant=bc.variant,
                        children=field_children,
                    )
                    if label_name:
                        field_node.name = label_name  # type: ignore[attr-defined]
                    section_node.children.append(field_node)
                    processed_ids.add(bid)

                elif bc.field_pair and bc.semantic != "label":
                    if bid not in processed_ids:
                        processed_ids.add(bid)
                    continue

                else:
                    standalone_name = _extract_semantic_name(block)
                    standalone_node = DocumentTreeNode(
                        type=bc.semantic or "unknown",
                        block_id=bid,
                        text=block.get("text", ""),
                        bbox=block.get("bbox"),
                        is_bold=block.get("is_bold", False),
                        font_weight=block.get("font_weight", "normal"),
                        font_size=block.get("font_size"),
                        font_name=block.get("font_name"),
                        color=block.get("color"),
                        variant=bc.variant,
                    )
                    if standalone_name:
                        standalone_node.name = standalone_name  # type: ignore[attr-defined]
                    section_node.children.append(standalone_node)
                    processed_ids.add(bid)

            # Tables
            for table in section.get("tables", []):
                table_node = DocumentTreeNode(
                    type="table",
                    table_id=table.get("table_id", str(uuid.uuid4())),
                    bbox=table.get("bbox"),
                )
                for header_row in table.get("headers", []):
                    row_children: list[DocumentTreeNode] = []
                    for cell in header_row:
                        cell_text = cell.get("text", "") if isinstance(cell, dict) else str(cell)
                        cell_bbox = cell.get("bbox") if isinstance(cell, dict) else None
                        row_children.append(DocumentTreeNode(type="cell", text=cell_text, bbox=cell_bbox))
                    table_node.children.append(DocumentTreeNode(type="header_row", children=row_children))
                for row in table.get("rows", []):
                    row_children = []
                    for cell in row:
                        cell_text = cell.get("text", "") if isinstance(cell, dict) else str(cell)
                        cell_bbox = cell.get("bbox") if isinstance(cell, dict) else None
                        row_children.append(DocumentTreeNode(type="cell", text=cell_text, bbox=cell_bbox))
                    table_node.children.append(DocumentTreeNode(type="data_row", children=row_children))
                section_node.children.append(table_node)

            # Images
            for img in section.get("images", []):
                section_node.children.append(
                    DocumentTreeNode(
                        id=f"image-{str(uuid.uuid4())[:8]}",
                        type="image",
                        image_path=img.get("path", ""),
                        bbox=img.get("bbox", [0, 0, 0, 0]),
                        bbox_valid=img.get("bbox_valid", True),
                        format=img.get("format", "unknown"),
                    )
                )

            # Charts
            _screenshot_scale_c = 150.0 / 72.0
            _page_w_pts_c = float(page_data.get("width", 595.0))
            _page_h_pts_c = float(page_data.get("height", 842.0))
            for chart in section.get("charts", []):
                raw_bbox_c = chart.get("bbox", [0, 0, 0, 0])
                norm_bbox_c = [
                    max(0.0, min(raw_bbox_c[0] / _screenshot_scale_c, _page_w_pts_c)),
                    max(0.0, min(raw_bbox_c[1] / _screenshot_scale_c, _page_h_pts_c)),
                    max(0.0, min(raw_bbox_c[2] / _screenshot_scale_c, _page_w_pts_c)),
                    max(0.0, min(raw_bbox_c[3] / _screenshot_scale_c, _page_h_pts_c)),
                ]
                section_node.children.append(
                    DocumentTreeNode(
                        id=f"chart-{str(uuid.uuid4())[:8]}",
                        type="chart",
                        bbox=norm_bbox_c,
                        description=chart.get("description", ""),
                        chart_type=chart.get("chart_type", "bar"),
                        confidence=chart.get("confidence", 50),
                        source="visual_analysis",
                    )
                )

            # Barcodes
            _screenshot_scale = 150.0 / 72.0
            _page_w_pts = float(page_data.get("width", 595.0))
            _page_h_pts = float(page_data.get("height", 842.0))
            for barcode in section.get("barcodes", []):
                raw_bbox = barcode.get("bbox", [0, 0, 0, 0])
                norm_bbox = [
                    max(0.0, min(raw_bbox[0] / _screenshot_scale, _page_w_pts)),
                    max(0.0, min(raw_bbox[1] / _screenshot_scale, _page_h_pts)),
                    max(0.0, min(raw_bbox[2] / _screenshot_scale, _page_w_pts)),
                    max(0.0, min(raw_bbox[3] / _screenshot_scale, _page_h_pts)),
                ]
                barcode_value = _extract_barcode_value(page_data, norm_bbox)
                barcode_node = DocumentTreeNode(
                    id=f"barcode-{str(uuid.uuid4())[:8]}",
                    type="barcode",
                    bbox=norm_bbox,
                    description=barcode.get("description", ""),
                    barcode_format=barcode.get("barcode_format", "CODE128"),
                    confidence=barcode.get("confidence", 50),
                    source="visual_analysis",
                )
                if barcode_value:
                    barcode_node.value = barcode_value  # type: ignore[attr-defined]
                section_node.children.append(barcode_node)

            # SVGs
            for svg_item in section.get("svgs", []):
                raw_bbox = svg_item.get("bbox", [0, 0, 0, 0])
                norm_bbox = [
                    max(0.0, min(raw_bbox[0] / _screenshot_scale, _page_w_pts)),
                    max(0.0, min(raw_bbox[1] / _screenshot_scale, _page_h_pts)),
                    max(0.0, min(raw_bbox[2] / _screenshot_scale, _page_w_pts)),
                    max(0.0, min(raw_bbox[3] / _screenshot_scale, _page_h_pts)),
                ]
                section_node.children.append(
                    DocumentTreeNode(
                        id=f"svg-{str(uuid.uuid4())[:8]}",
                        type="svg",
                        bbox=norm_bbox,
                        svg_content="",
                        description=svg_item.get("description", ""),
                        confidence=svg_item.get("confidence", 50),
                        source="visual_analysis",
                    )
                )

            zone_node.children.append(section_node)

        page_node.children.append(zone_node)

    # Drawn elements at page level
    drawn = page_data.get("drawn_elements")
    barcode_bboxes = _barcode_bboxes_from_tree(root)
    if drawn and isinstance(drawn, list):
        for elem in drawn:
            if not isinstance(elem, dict):
                continue
            elem_type = elem.get("type")
            orientation = elem.get("orientation")
            if elem_type == "line" and orientation in ("horizontal", "vertical"):
                line_bbox = elem.get("bbox", [0, 0, 0, 0])
                if orientation == "vertical" and _line_inside_any_barcode(line_bbox, barcode_bboxes):
                    continue
                page_node.children.append(
                    DocumentTreeNode(
                        id=f"line-{str(uuid.uuid4())[:8]}",
                        type="line",
                        bbox=line_bbox,
                        orientation=orientation,
                        stroke_color=elem.get("stroke_color"),
                        width=elem.get("width", 1.0),
                    )
                )
            elif elem_type == "rect" and elem.get("fill_color") is not None:
                page_node.children.append(
                    DocumentTreeNode(
                        id=f"rect-{str(uuid.uuid4())[:8]}",
                        type="rect",
                        bbox=elem.get("bbox", [0, 0, 0, 0]),
                        fill_color=elem.get("fill_color"),
                        stroke_color=elem.get("stroke_color"),
                    )
                )

    # Serialize to plain dict at context boundary — stage 4 consumes plain dicts
    return root.model_dump()
