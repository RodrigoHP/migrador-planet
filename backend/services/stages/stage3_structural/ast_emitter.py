"""AST Emitter — converts Stage 3 DocumentTreeNode dict to TemplateAstV0.

Spike: spike/ast-validation — C1 (Stage 3 → AST v0 consumível por Stage 4).

Design:
  - Input:  tree_dict (DocumentTreeNode.model_dump() from tree_builder.py)
            block_classifications (dict[block_id, BlockClassification.model_dump()])
  - Output: TemplateAstV0

100% additive — does NOT modify tree_builder.py or existing pipeline_context models.
Parallel output path: Stage 3 can emit both the existing dict AND the AST.

Node mapping from DocumentTreeNode.type → AstNode:
  zone / section          → SectionNode
  value / dynamic         → FieldNode (if dynamic classification) else TextNode
  label / text / static   → TextNode
  image                   → ImageNode (static or dynamic based on context)
  barcode                 → ImageNode (dynamic)
  table                   → TableNode
  chart / svg             → RawHtmlNode
  repeated_section        → RepeatingNode
  list_item               → (consumed inside RepeatingNode)
  line / rect             → skipped (decorative)
  (root / page node)      → PageNode
"""

from __future__ import annotations

import logging
from typing import Any

from models.ast.nodes import (
    AstNode,
    BBox,
    FieldNode,
    FormatterSpec,
    ImageNode,
    PageNode,
    RawHtmlNode,
    RepeatingNode,
    SectionNode,
    TableNode,
    TemplateAstV0,
    TextNode,
)
from services.stages.stage3_structural.formatter_inference import infer_formatter

logger = logging.getLogger(__name__)

# Node types that signal a dynamic field (should become FieldNode)
_DYNAMIC_TYPES = {"value", "dynamic", "field"}
_STATIC_TYPES = {"label", "text", "static", "header", "footer_text"}
_SECTION_TYPES = {"zone", "section"}
_SKIP_TYPES = {"line", "rect", "list_item"}

# Semantic classifications from BlockClassification that confirm dynamic
_DYNAMIC_SEMANTICS = {"dynamic", "semi_dynamic", "likely_dynamic"}


def emit(
    tree_dict: dict[str, Any],
    block_classifications: dict[str, dict[str, Any]] | None = None,
    layout_type_id: str = "",
    cluster_id: str = "",
) -> TemplateAstV0:
    """Convert a Stage 3 DocumentTreeNode dict into TemplateAstV0.

    Args:
        tree_dict: Output of DocumentTreeNode.model_dump() from tree_builder.py.
        block_classifications: Dict[block_id → BlockClassification.model_dump()].
            Used to confirm dynamic/static classification of value nodes.
        layout_type_id: Identifier for the layout type (cluster-level).
        cluster_id: Source cluster identifier.

    Returns:
        TemplateAstV0 with root node converted from the tree.
    """
    bc = block_classifications or {}
    ctx = _EmitContext(block_classifications=bc)

    root_node = _convert_node(tree_dict, ctx, page=0)
    if root_node is None:
        # Fallback: emit an empty page
        root_node = PageNode(type="page", page_num=0)

    return TemplateAstV0(
        root=root_node,
        layout_type_id=layout_type_id,
        source_cluster_id=cluster_id,
        metadata={"node_count": ctx.node_count, "skipped": ctx.skipped},
    )


def extract_field_pairs(ast: TemplateAstV0) -> list[dict[str, Any]]:
    """Extract FieldNode instances from a TemplateAstV0 for Stage 4 consumption.

    Returns a list of dicts with keys: bind_path, formatter, bbox, label.
    Stage 4's ≤100 LOC patch consumes this instead of walking the raw tree.
    """
    pairs: list[dict[str, Any]] = []
    _collect_fields(ast.root, pairs, layout_type_id=ast.layout_type_id)
    return pairs


def extract_field_pairs_multi(
    ast_trees: dict[str, TemplateAstV0],
) -> list[dict[str, Any]]:
    """Extract field pairs from multiple AST trees (one per cluster/layout)."""
    all_pairs: list[dict[str, Any]] = []
    for layout_id, ast in ast_trees.items():
        pairs = extract_field_pairs(ast)
        for p in pairs:
            p["layout_type_id"] = layout_id
        all_pairs.extend(pairs)
    return all_pairs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _EmitContext:
    """Mutable state threaded through the recursive conversion."""

    def __init__(self, block_classifications: dict[str, dict[str, Any]]) -> None:
        self.bc = block_classifications
        self.node_count = 0
        self.skipped = 0
        self._field_counter = 0

    def next_field_id(self) -> str:
        self._field_counter += 1
        return f"field_{self._field_counter}"

    def is_dynamic(self, node: dict[str, Any]) -> bool:
        """Return True if node should be emitted as FieldNode."""
        node_type = node.get("type", "")
        block_id = node.get("block_id", "")

        # Check block classification first (more reliable)
        if block_id and block_id in self.bc:
            semantic = self.bc[block_id].get("semantic", "")
            if semantic in _DYNAMIC_SEMANTICS:
                return True
            if semantic in ("static", "header", "footer_text", "label"):
                return False

        # Fall back to node type heuristic
        return node_type in _DYNAMIC_TYPES


def _make_bbox(node: dict[str, Any], page: int) -> BBox:
    """Build BBox from node dict, defaulting to zero bbox on missing data."""
    raw = node.get("bbox") or []
    return BBox.from_list(raw if isinstance(raw, list) else [], page=page)


def _make_field_node(node: dict[str, Any], ctx: _EmitContext, page: int) -> FieldNode:
    """Build a FieldNode from a dynamic value node."""
    text = node.get("text") or node.get("value") or ""
    # Infer formatter from observed text value
    formatter = infer_formatter([text]) if text else FormatterSpec(kind="raw")

    # Build bind_path from suggested_binding or block_id fallback
    bind_path = node.get("suggested_binding") or node.get("name") or ctx.next_field_id()

    return FieldNode(
        type="field",
        bind_path=bind_path,
        formatter=formatter,
        bbox=_make_bbox(node, page),
        label=node.get("label"),
    )


def _convert_node(
    node: dict[str, Any],
    ctx: _EmitContext,
    page: int,
) -> AstNode | None:
    """Recursively convert a DocumentTreeNode dict to an AstNode."""
    node_type = node.get("type", "")
    ctx.node_count += 1

    if node_type in _SKIP_TYPES:
        ctx.skipped += 1
        return None

    # --- Page node (top-level) ---
    if node_type == "page" or (not node_type and node.get("children")):
        page_num = node.get("page_index", page)
        children = _convert_children(node.get("children", []), ctx, page=page_num)
        return PageNode(
            type="page",
            page_num=page_num,
            children=children,
            width=node.get("width"),
            height=node.get("height"),
        )

    # --- Repeated section → RepeatingNode ---
    if node_type == "repeated_section":
        return _convert_repeated_section(node, ctx, page)

    # --- Zone / Section → SectionNode ---
    if node_type in _SECTION_TYPES:
        children = _convert_children(node.get("children", []), ctx, page)
        return SectionNode(
            type="section",
            name=node.get("name"),
            children=children,
            bbox=_make_bbox(node, page),
        )

    # --- Dynamic field → FieldNode ---
    if ctx.is_dynamic(node):
        return _make_field_node(node, ctx, page)

    # --- Static text → TextNode ---
    if node_type in _STATIC_TYPES or node.get("text"):
        text = node.get("text") or node.get("value") or ""
        return TextNode(
            type="text",
            content=text,
            bbox=_make_bbox(node, page),
            font_family=node.get("font_name"),
            font_size=node.get("font_size"),
            font_weight="bold" if node.get("is_bold") else None,
        )

    # --- Image → ImageNode ---
    if node_type == "image":
        return ImageNode(
            type="image",
            source="static",
            bind_path=None,
            bbox=_make_bbox(node, page),
        )

    # --- Barcode → dynamic ImageNode ---
    if node_type == "barcode":
        return ImageNode(
            type="image",
            source="dynamic",
            bind_path=node.get("name") or "barcode",
            bbox=_make_bbox(node, page),
            alt="barcode",
        )

    # --- Table → TableNode ---
    if node_type == "table":
        return _convert_table(node, ctx, page)

    # --- Chart / SVG / unknown → RawHtmlNode ---
    if node_type in ("chart", "svg"):
        return RawHtmlNode(
            type="raw_html",
            html=node.get("svg_content") or f'<div class="{node_type}"></div>',
            bbox=_make_bbox(node, page),
            reason=f"node_type={node_type}",
        )

    # --- Fallback: if has children, treat as section ---
    children_raw = node.get("children", [])
    if children_raw:
        children = _convert_children(children_raw, ctx, page)
        bbox = _make_bbox(node, page)
        return SectionNode(
            type="section",
            name=node.get("name"),
            children=children,
            bbox=bbox,
        )

    # --- Truly unknown leaf node → RawHtmlNode escape hatch ---
    ctx.skipped += 1
    return RawHtmlNode(
        type="raw_html",
        html=f"<!-- unknown node type: {node_type} -->",
        bbox=_make_bbox(node, page),
        reason=f"unknown_type={node_type}",
    )


def _convert_children(
    children_raw: list[dict[str, Any]],
    ctx: _EmitContext,
    page: int,
) -> list[AstNode]:
    """Convert a list of child node dicts, dropping None results."""
    result: list[AstNode] = []
    for child in children_raw:
        if not isinstance(child, dict):
            continue
        converted = _convert_node(child, ctx, page)
        if converted is not None:
            result.append(converted)
    return result


def _convert_repeated_section(
    node: dict[str, Any],
    ctx: _EmitContext,
    page: int,
) -> RepeatingNode:
    """Convert a repeated_section node to RepeatingNode."""
    name = node.get("name", "")
    # Extract iterator name from "list_N_items" pattern or fall back to node name
    iterator = name.replace("list_", "").replace("_items", "") if name else "items"
    iterator = f"{iterator}[]"

    # Build item template from first list_item child
    item_template: AstNode | None = None
    children_raw = node.get("children", [])
    if children_raw:
        first_item = children_raw[0] if isinstance(children_raw[0], dict) else {}
        # list_item nodes contain the text of one instance
        text = first_item.get("text", "")
        bbox = _make_bbox(first_item, page)
        item_template = TextNode(type="text", content=text, bbox=bbox)

    if item_template is None:
        item_template = RawHtmlNode(
            type="raw_html",
            html="<!-- empty repeating item -->",
            bbox=_make_bbox(node, page),
            reason="empty_repeating_section",
        )

    return RepeatingNode(
        type="repeating",
        iterator=iterator,
        item_template=item_template,
        bbox=_make_bbox(node, page),
        item_count_hint=len(children_raw),
    )


def _convert_table(
    node: dict[str, Any],
    ctx: _EmitContext,
    page: int,
) -> TableNode:
    """Convert a table node to TableNode."""
    # DocumentTreeNode.table_id exists; children are cells or rows
    rows_raw = node.get("rows") or []  # may not exist in tree format
    children_raw = node.get("children", [])

    if rows_raw:
        # If table has explicit rows structure
        rows: list[list[AstNode]] = []
        for row in rows_raw:
            if isinstance(row, list):
                row_nodes = []
                for cell_text in row:
                    cell_bbox = _make_bbox(node, page)
                    row_nodes.append(TextNode(type="text", content=str(cell_text), bbox=cell_bbox))
                rows.append(row_nodes)
        return TableNode(type="table", rows=rows, bbox=_make_bbox(node, page))

    # Children-based table (flatten to single row for now)
    if children_raw:
        row_cells = _convert_children(children_raw, ctx, page)
        return TableNode(type="table", rows=[row_cells] if row_cells else [], bbox=_make_bbox(node, page))

    return TableNode(type="table", rows=[], bbox=_make_bbox(node, page))


def _collect_fields(
    node: AstNode,
    result: list[dict[str, Any]],
    layout_type_id: str,
) -> None:
    """Walk AST recursively, collecting FieldNode dicts for Stage 4."""
    if isinstance(node, FieldNode):
        result.append(
            {
                "bind_path": node.bind_path,
                "formatter": node.formatter.model_dump(),
                "bbox": [node.bbox.x0, node.bbox.y0, node.bbox.x1, node.bbox.y1],
                "page": node.bbox.page,
                "label": node.label,
                "layout_type_id": layout_type_id,
            }
        )
        return

    # Recurse into container nodes
    if isinstance(node, PageNode):
        for child in node.children:
            _collect_fields(child, result, layout_type_id)
    elif isinstance(node, SectionNode):
        for child in node.children:
            _collect_fields(child, result, layout_type_id)
    elif isinstance(node, TableNode):
        for row in node.rows:
            for cell in row:
                _collect_fields(cell, result, layout_type_id)
    elif isinstance(node, RepeatingNode):
        _collect_fields(node.item_template, result, layout_type_id)
