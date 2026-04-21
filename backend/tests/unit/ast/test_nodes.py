"""Unit tests for Planet AST v0 schema — Spike C1 (schema validation).

Validates:
  - All 8 node types construct correctly
  - Discriminated union resolves correctly via type discriminator
  - TemplateAstV0 root model validates
  - BBox rejects invalid coordinates
  - FormatterSpec covers all 5 kinds
  - ImageNode validation (dynamic requires bind_path)
  - model_dump / model_validate round-trip
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = str(Path(__file__).resolve().parents[3])
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest
from pydantic import ValidationError

from models.ast.nodes import (
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

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# BBox
# ---------------------------------------------------------------------------


class TestBBox:
    def test_basic(self):
        b = BBox(page=0, x0=10, y0=20, x1=100, y1=200)
        assert b.page == 0
        assert b.x0 == 10

    def test_from_list(self):
        b = BBox.from_list([10.0, 20.0, 100.0, 200.0], page=1)
        assert b.x0 == 10.0 and b.y1 == 200.0 and b.page == 1

    def test_from_list_empty(self):
        b = BBox.from_list([], page=0)
        assert b.x0 == 0 and b.x1 == 0

    def test_invalid_coords_raises(self):
        with pytest.raises(ValidationError):
            BBox(page=0, x0=100, y0=0, x1=10, y1=200)  # x1 < x0

    def test_equal_coords_ok(self):
        # zero-size bbox is valid (point)
        b = BBox(page=0, x0=50, y0=50, x1=50, y1=50)
        assert b.x0 == b.x1


# ---------------------------------------------------------------------------
# FormatterSpec
# ---------------------------------------------------------------------------


class TestFormatterSpec:
    def test_date(self):
        f = FormatterSpec(kind="date", pattern="dd/MM/yyyy")
        assert f.kind == "date"
        assert f.locale == "pt-BR"

    def test_currency_no_pattern(self):
        f = FormatterSpec(kind="currency")
        assert f.pattern is None

    def test_all_kinds(self):
        for kind in ("date", "currency", "number", "percent", "raw"):
            f = FormatterSpec(kind=kind)
            assert f.kind == kind

    def test_invalid_kind_raises(self):
        with pytest.raises(ValidationError):
            FormatterSpec(kind="unknown")


# ---------------------------------------------------------------------------
# Individual node types
# ---------------------------------------------------------------------------


_BBOX = BBox(page=0, x0=0, y0=0, x1=100, y1=20)


class TestTextNode:
    def test_basic(self):
        n = TextNode(type="text", content="Vencimento:", bbox=_BBOX)
        assert n.type == "text"
        assert n.content == "Vencimento:"

    def test_optional_style(self):
        n = TextNode(type="text", content="X", bbox=_BBOX, font_size=10.0, font_weight="bold")
        assert n.font_size == 10.0


class TestFieldNode:
    def test_basic(self):
        n = FieldNode(
            type="field",
            bind_path="boleto.vencimento",
            formatter=FormatterSpec(kind="date", pattern="dd/MM/yyyy"),
            bbox=_BBOX,
        )
        assert n.bind_path == "boleto.vencimento"
        assert n.formatter.kind == "date"

    def test_label_optional(self):
        n = FieldNode(
            type="field",
            bind_path="x",
            formatter=FormatterSpec(kind="raw"),
            bbox=_BBOX,
            label="Data:",
        )
        assert n.label == "Data:"


class TestSectionNode:
    def test_empty_children(self):
        n = SectionNode(type="section", bbox=_BBOX)
        assert n.children == []

    def test_with_child(self):
        child = TextNode(type="text", content="test", bbox=_BBOX)
        n = SectionNode(type="section", bbox=_BBOX, children=[child])
        assert len(n.children) == 1
        assert isinstance(n.children[0], TextNode)


class TestRepeatingNode:
    def test_basic(self):
        template = TextNode(type="text", content="{{item}}", bbox=_BBOX)
        n = RepeatingNode(type="repeating", iterator="itens[]", item_template=template, bbox=_BBOX)
        assert n.iterator == "itens[]"
        assert isinstance(n.item_template, TextNode)


class TestImageNode:
    def test_static(self):
        n = ImageNode(type="image", source="static", bbox=_BBOX)
        assert n.source == "static"

    def test_dynamic_with_path(self):
        n = ImageNode(type="image", source="dynamic", bind_path="boleto.barcode", bbox=_BBOX)
        assert n.bind_path == "boleto.barcode"

    def test_dynamic_without_path_raises(self):
        with pytest.raises(ValidationError):
            ImageNode(type="image", source="dynamic", bbox=_BBOX)


class TestTableNode:
    def test_empty(self):
        n = TableNode(type="table", bbox=_BBOX)
        assert n.rows == []

    def test_with_rows(self):
        cell = TextNode(type="text", content="R$", bbox=_BBOX)
        n = TableNode(type="table", rows=[[cell]], bbox=_BBOX)
        assert len(n.rows) == 1


class TestPageNode:
    def test_basic(self):
        n = PageNode(type="page", page_num=0)
        assert n.page_num == 0
        assert n.children == []


class TestRawHtmlNode:
    def test_basic(self):
        n = RawHtmlNode(type="raw_html", html="<div>x</div>", bbox=_BBOX)
        assert n.html == "<div>x</div>"
        assert n.reason is None


# ---------------------------------------------------------------------------
# Discriminated union resolution
# ---------------------------------------------------------------------------


class TestDiscriminatedUnion:
    def test_text_resolves(self):
        data = {"type": "text", "content": "hello", "bbox": {"page": 0, "x0": 0, "y0": 0, "x1": 1, "y1": 1}}
        node = SectionNode(type="section", bbox=_BBOX, children=[data])
        assert isinstance(node.children[0], TextNode)

    def test_field_resolves(self):
        data = {
            "type": "field",
            "bind_path": "x.y",
            "formatter": {"kind": "raw"},
            "bbox": {"page": 0, "x0": 0, "y0": 0, "x1": 1, "y1": 1},
        }
        node = SectionNode(type="section", bbox=_BBOX, children=[data])
        assert isinstance(node.children[0], FieldNode)

    def test_unknown_type_raises(self):
        with pytest.raises(ValidationError):
            SectionNode(
                type="section",
                bbox=_BBOX,
                children=[{"type": "unknown_xyz", "bbox": {"page": 0, "x0": 0, "y0": 0, "x1": 1, "y1": 1}}],
            )


# ---------------------------------------------------------------------------
# TemplateAstV0 root model
# ---------------------------------------------------------------------------


class TestTemplateAstV0:
    def test_schema_version_default(self):
        root = PageNode(type="page", page_num=0)
        ast = TemplateAstV0(root=root)
        assert ast.schema_version == "template-ast-v0"

    def test_schema_version_literal_only(self):
        root = PageNode(type="page", page_num=0)
        with pytest.raises(ValidationError):
            TemplateAstV0(root=root, schema_version="planet-ast-v1")

    def test_round_trip(self):
        field = FieldNode(
            type="field",
            bind_path="boleto.valor",
            formatter=FormatterSpec(kind="currency", pattern="R$ #.##0,00"),
            bbox=_BBOX,
        )
        page = PageNode(type="page", page_num=0, children=[field])
        ast = TemplateAstV0(root=page, layout_type_id="boleto-individual")

        dumped = ast.model_dump()
        restored = TemplateAstV0.model_validate(dumped)

        assert restored.schema_version == "template-ast-v0"
        assert restored.layout_type_id == "boleto-individual"
        assert isinstance(restored.root, PageNode)
        assert isinstance(restored.root.children[0], FieldNode)

    def test_nested_section_with_field(self):
        field = FieldNode(
            type="field",
            bind_path="segurado.nome",
            formatter=FormatterSpec(kind="raw"),
            bbox=_BBOX,
        )
        section = SectionNode(type="section", name="Segurado", bbox=_BBOX, children=[field])
        page = PageNode(type="page", page_num=0, children=[section])
        ast = TemplateAstV0(root=page)

        # Verify deep nesting survives round-trip
        dumped = ast.model_dump()
        restored = TemplateAstV0.model_validate(dumped)
        restored_section = restored.root.children[0]
        assert isinstance(restored_section, SectionNode)
        assert isinstance(restored_section.children[0], FieldNode)
