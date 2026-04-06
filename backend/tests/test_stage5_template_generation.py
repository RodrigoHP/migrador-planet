"""Tests for Stage 5 — Template Generation (Story 13.10).

Covers:
- tree_to_html produces valid HTML with real <table>
- CSS contains real font classes (not hardcoded Arial)
- CSS contains real color classes (not hardcoded #000)
- Coverage calculates correctly (fields + tables + images)
- Overlay items filtered by layout
- Confidence normalized 0-100 for ALL factors
- layout_types[] pre-populated with documentTree/confidence/coverage
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.stages.stage5_template_generation import (
    _BASE_CSS_RESET,
    _bbox_to_absolute_style,
    _convert_tree_to_css_coords,
    _count_mapped_tables,
    _count_nodes_by_type,
    _extract_visual_data,
    _normalize_confidence,
    _step_5_1_tree_driven_html,
    _step_5_2_css_from_extraction,
    _step_5_3_coverage,
    _step_5_4_overlay_items,
    _step_5_5_variation_matrix,
    _step_5_6_pipeline_result,
    _step_5_7_persist,
    _tree_to_html,
    run_stage5,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_document_tree() -> Dict[str, Any]:
    """Build a realistic document tree for layout-A."""
    return {
        "id": "root-A",
        "type": "document",
        "children": [
            {
                "type": "header",
                "source": "visual",
                "children": [
                    {
                        "type": "field",
                        "variant": "required",
                        "children": [
                            {"type": "label", "block_id": "blk-1", "text": "Empresa"},
                        ],
                    },
                ],
            },
            {
                "type": "flow",
                "children": [
                    {
                        "type": "section",
                        "name": "Dados do Cliente",
                        "variant": "required",
                        "children": [
                            {
                                "type": "field",
                                "variant": "required",
                                "children": [
                                    {"type": "label", "block_id": "blk-2", "text": "Nome:"},
                                    {
                                        "type": "value",
                                        "block_id": "blk-3",
                                        "text": "Joao Silva",
                                        "bbox": [50, 200, 300, 220],
                                    },
                                ],
                            },
                            {
                                "type": "field",
                                "variant": "optional",
                                "children": [
                                    {"type": "label", "block_id": "blk-4", "text": "Conjuge:"},
                                    {
                                        "type": "value",
                                        "block_id": "blk-5",
                                        "text": "Maria",
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "name": "Pagamento",
                        "variant": "conditional",
                        "present_in_pdfs": ["0"],
                        "children": [
                            {
                                "type": "field",
                                "variant": "conditional",
                                "children": [
                                    {"type": "label", "block_id": "blk-6", "text": "Valor:"},
                                    {
                                        "type": "value",
                                        "block_id": "blk-7",
                                        "text": "R$ 100,00",
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "type": "table",
                        "table_id": "tbl-1",
                        "bbox": [50, 300, 500, 600],
                        "xsd_array_path": "itens",
                        "children": [
                            {
                                "type": "header_row",
                                "children": [
                                    {"text": "Descricao"},
                                    {"text": "Valor"},
                                ],
                            },
                            {
                                "type": "data_row",
                                "children": [
                                    {"block_id": "blk-8", "text": "Item 1"},
                                    {"block_id": "blk-9", "text": "R$ 50"},
                                ],
                            },
                        ],
                    },
                    {
                        "type": "image",
                        "image_path": "img-001.png",
                        "bbox": [10, 10, 100, 80],
                        "bbox_valid": True,
                    },
                    {
                        "type": "chart",
                        "chart_type": "bar",
                        "bbox": [50, 650, 400, 800],
                    },
                ],
            },
            {
                "type": "footer",
                "source": "visual",
                "children": [],
            },
        ],
    }


def _make_field_mappings() -> List[Dict[str, Any]]:
    return [
        {
            "block_id": "blk-3",
            "layout_type_id": "layout-A",
            "xsd_field_path": "cliente.nome",
            "pdf_text": "Joao Silva",
            "label_text": "Nome:",
            "bbox": [50, 200, 300, 220],
            "status": "mapped",
            "confidence": 0.95,
            "page_number": 0,
            "is_table_cell": False,
            "from_table": False,
            "is_ambiguous": False,
        },
        {
            "block_id": "blk-5",
            "layout_type_id": "layout-A",
            "xsd_field_path": "cliente.conjuge",
            "pdf_text": "Maria",
            "label_text": "Conjuge:",
            "bbox": [50, 240, 300, 260],
            "status": "mapped",
            "confidence": 0.80,
            "page_number": 0,
            "is_table_cell": False,
            "from_table": False,
            "is_ambiguous": False,
        },
        {
            "block_id": "blk-7",
            "layout_type_id": "layout-A",
            "xsd_field_path": "pagamento.valor",
            "pdf_text": "R$ 100,00",
            "label_text": "Valor:",
            "bbox": [50, 280, 300, 300],
            "status": "mapped",
            "confidence": 0.70,
            "page_number": 0,
            "is_table_cell": False,
            "from_table": False,
            "is_ambiguous": False,
        },
        {
            "block_id": "blk-8",
            "layout_type_id": "layout-A",
            "xsd_field_path": "itens.descricao",
            "pdf_text": "Item 1",
            "label_text": "",
            "bbox": [60, 350, 250, 370],
            "status": "mapped",
            "confidence": 0.85,
            "page_number": 0,
            "is_table_cell": True,
            "from_table": True,
            "is_ambiguous": False,
        },
        {
            "block_id": "blk-9",
            "layout_type_id": "layout-A",
            "xsd_field_path": "itens.valor",
            "pdf_text": "R$ 50",
            "label_text": "",
            "bbox": [260, 350, 450, 370],
            "status": "mapped",
            "confidence": 0.85,
            "page_number": 0,
            "is_table_cell": True,
            "from_table": True,
            "is_ambiguous": False,
        },
    ]


def _make_layout_types() -> List[Dict[str, Any]]:
    return [
        {
            "id": "layout-A",
            "name": "Padrao",
            "page_height_pts": 842.0,
            "page_width_pts": 595.0,
            "pages": [{"pdf_id": "0", "page_index": 0}],
        },
    ]


def _make_enriched_documents() -> List[Dict[str, Any]]:
    return [
        {
            "pdf_id": "0",
            "pdf_name": "test.pdf",
            "pages": [
                {
                    "page_index": 0,
                    "cluster_id": "layout-A",
                    "is_representative": True,
                    "width": 595.0,
                    "height": 842.0,
                    "text_blocks": [
                        {
                            "id": "blk-2",
                            "text": "Nome:",
                            "bbox": [50, 180, 120, 200],
                            "font_name": "Helvetica",
                            "font_size": 10.0,
                            "color": 0,
                        },
                        {
                            "id": "blk-3",
                            "text": "Joao Silva",
                            "bbox": [50, 200, 300, 220],
                            "font_name": "Helvetica-Bold",
                            "font_size": 12.0,
                            "color": 255,  # blue
                        },
                        {
                            "id": "blk-4",
                            "text": "Conjuge:",
                            "bbox": [50, 220, 130, 240],
                            "font_name": "TimesNewRoman",
                            "font_size": 10.0,
                            "color": 16711680,  # red
                        },
                    ],
                    "drawn_elements": [
                        {
                            "type": "line",
                            "bbox": [50, 150, 500, 150],
                            "orientation": "horizontal",
                            "stroke_color": 8421504,
                            "width": 1.0,
                        },
                        {
                            "type": "rect",
                            "bbox": [0, 0, 595, 120],
                            "fill_color": 15790320,
                        },
                    ],
                    "images": [],
                    "fonts": [],
                },
            ],
        },
    ]


def _make_field_tree() -> Dict[str, Any]:
    return {
        "flat_paths": [
            "cliente.nome",
            "cliente.conjuge",
            "cliente.cpf",
            "pagamento.valor",
            "pagamento.data",
            "itens.descricao",
            "itens.valor",
        ],
        "root_nodes": [],
    }


def _make_intelligence() -> Dict[str, Any]:
    return {
        "layout-A": {
            "block_classifications": {
                "blk-2": {
                    "semantic": "label",
                    "stability": "stable",
                    "variant": "required",
                    "presence_ratio": 1.0,
                    "confidence": 1.0,
                },
                "blk-3": {
                    "semantic": "dynamic",
                    "stability": "variable",
                    "variant": "required",
                    "presence_ratio": 1.0,
                    "confidence": 0.95,
                },
                "blk-6": {
                    "semantic": "label",
                    "stability": "stable",
                    "variant": "conditional",
                    "presence_ratio": 0.5,
                    "present_in_pdfs": ["0"],
                    "confidence": 0.8,
                },
            },
            "labels": ["blk-2"],
            "dynamic_fields": ["blk-3"],
        },
    }


def _make_clusters() -> List[Dict[str, Any]]:
    return [
        {
            "cluster_id": "layout-A",
            "pages": [
                {"pdf_id": "0", "page_index": 0},
                {"pdf_id": "1", "page_index": 0},
            ],
            "representative_page": {"pdf_id": "0", "page_index": 0},
            "page_count": 2,
        },
    ]


def _make_visual_analysis() -> Dict[str, Any]:
    return {
        "0:0": {
            "regions": [
                {
                    "type": "header",
                    "bbox": [0, 0, 794, 130],
                    "description": "Logo + empresa",
                },
                {
                    "type": "footer",
                    "bbox": [0, 1020, 794, 1123],
                    "description": "Rodape",
                },
            ],
            "consistency_score": 85,
        },
    }


# ---------------------------------------------------------------------------
# Tests: 5.1 Tree-Driven HTML
# ---------------------------------------------------------------------------


class TestTreeDrivenHTML:
    def test_produces_valid_html_with_table(self):
        """tree_to_html produces HTML with real <table> elements."""
        tree = _make_document_tree()
        mappings = _make_field_mappings()
        layout = _make_layout_types()[0]
        mapping_by_block = {m["block_id"]: m for m in mappings if m.get("block_id")}

        html = _tree_to_html(tree, mapping_by_block, None, layout)

        assert "<table" in html
        assert "data-table" in html
        assert "<!-- ko foreach: itens -->" in html
        assert "</table>" in html
        # Should have real table structure
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "<th>" in html
        assert "<td" in html

    def test_html_is_hierarchical(self):
        """HTML preserves document tree hierarchy (sections, not flat)."""
        tree = _make_document_tree()
        mappings = _make_field_mappings()
        layout = _make_layout_types()[0]
        mapping_by_block = {m["block_id"]: m for m in mappings if m.get("block_id")}

        html = _tree_to_html(tree, mapping_by_block, None, layout)

        assert 'class="header"' in html
        assert 'class="flow"' in html
        assert 'class="footer"' in html
        assert 'class="section"' in html
        assert 'data-section="Dados do Cliente"' in html

    def test_conditional_section_has_ko_if(self):
        """Conditional sections wrap with ko if AND have content inside."""
        tree = _make_document_tree()
        mappings = _make_field_mappings()
        layout = _make_layout_types()[0]
        mapping_by_block = {m["block_id"]: m for m in mappings if m.get("block_id")}

        html = _tree_to_html(tree, mapping_by_block, None, layout)

        assert "<!-- ko if:" in html
        assert "<!-- /ko -->" in html
        # Content should be INSIDE the ko if block
        ko_if_idx = html.index("<!-- ko if:")
        ko_end_idx = html.index("<!-- /ko -->", ko_if_idx)
        inside = html[ko_if_idx:ko_end_idx]
        assert 'data-section="Pagamento"' in inside

    def test_field_with_xsd_path_has_data_bind(self):
        """Mapped fields include data-bind="text: xsd_path"."""
        tree = _make_document_tree()
        mappings = _make_field_mappings()
        layout = _make_layout_types()[0]
        mapping_by_block = {m["block_id"]: m for m in mappings if m.get("block_id")}

        html = _tree_to_html(tree, mapping_by_block, None, layout)

        assert 'data-bind="text: cliente.nome"' in html
        assert 'data-xsd-path="cliente.nome"' in html

    def test_page_div_has_layout_type(self):
        """Top-level page div has data-layout-type attribute."""
        tree = _make_document_tree()
        layout = _make_layout_types()[0]

        html = _tree_to_html(tree, {}, None, layout)

        assert 'data-layout-type="Padrao"' in html
        assert 'class="page page-padrao"' in html

    def test_image_node_generates_img_tag(self):
        """Image nodes produce <img> tags."""
        tree = _make_document_tree()
        layout = _make_layout_types()[0]

        html = _tree_to_html(tree, {}, None, layout)

        assert '<img src="img-001.png"' in html

    def test_chart_node_generates_div(self):
        """Chart nodes produce div with data-chart-type."""
        tree = _make_document_tree()
        layout = _make_layout_types()[0]

        html = _tree_to_html(tree, {}, None, layout)

        assert 'data-type="chart"' in html
        assert 'data-chart-type="bar"' in html

    def test_step_5_1_filters_by_layout(self):
        """Step 5.1 only processes mappings for matching layout_type_id."""
        trees = {"layout-A": _make_document_tree()}
        mappings = _make_field_mappings()
        # Add a mapping for different layout
        mappings.append({
            "block_id": "blk-99",
            "layout_type_id": "layout-B",
            "xsd_field_path": "other.field",
            "pdf_text": "Test",
            "status": "mapped",
        })

        result = _step_5_1_tree_driven_html(trees, mappings, None, _make_layout_types())

        assert "layout-A" in result
        assert "layout-B" not in result

    def test_position_absolute_style(self):
        """Fields with bbox get position:absolute style."""
        tree = _make_document_tree()
        mappings = _make_field_mappings()
        layout = _make_layout_types()[0]
        mapping_by_block = {m["block_id"]: m for m in mappings if m.get("block_id")}

        html = _tree_to_html(tree, mapping_by_block, None, layout)

        assert "position:absolute" in html

    def test_bold_label_renders_font_weight_bold(self):
        """label node with is_bold=True must produce font-weight:bold in span style."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [
                {
                    "type": "header",
                    "children": [
                        {
                            "type": "field",
                            "variant": "required",
                            "children": [
                                {
                                    "type": "label",
                                    "block_id": "blk-bold",
                                    "text": "Beneficiário",
                                    "bbox": [50, 100, 200, 115],
                                    "is_bold": True,
                                    "font_weight": "bold",
                                    "children": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "font-weight:bold" in html, (
            "label com is_bold=True deve gerar font-weight:bold no style do span"
        )

    def test_positioned_label_renders_position_absolute(self):
        """label node with bbox must produce position:absolute in span style."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [
                {
                    "type": "flow",
                    "children": [
                        {
                            "type": "field",
                            "variant": "required",
                            "children": [
                                {
                                    "type": "label",
                                    "block_id": "blk-pos",
                                    "text": "Vencimento",
                                    "bbox": [50, 200, 150, 215],
                                    "is_bold": False,
                                    "font_weight": "normal",
                                    "children": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "position:absolute" in html, (
            "label node com bbox deve gerar position:absolute no style do span"
        )

    def test_color_label_renders_color_style(self):
        """label node with color must produce color:# in span style."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "flow",
                "children": [{
                    "type": "field",
                    "variant": "required",
                    "children": [{
                        "type": "label",
                        "block_id": "blk-color",
                        "text": "Nome",
                        "bbox": None,
                        "color": 16711680,  # RGB red = 0xFF0000
                        "is_bold": False,
                        "font_weight": "normal",
                        "children": [],
                    }],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "color:#ff0000" in html, "label com color deve gerar color:# no style"

    def test_font_size_label_renders_font_size_style(self):
        """label node with font_size must produce font-size: in span style."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "flow",
                "children": [{
                    "type": "field",
                    "variant": "required",
                    "children": [{
                        "type": "label",
                        "block_id": "blk-size",
                        "text": "CPF",
                        "bbox": None,
                        "font_size": 12.0,
                        "is_bold": False,
                        "font_weight": "normal",
                        "children": [],
                    }],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "font-size:" in html, "label com font_size deve gerar font-size: no style"

    def test_value_span_has_font_class(self):
        """value node with font_name must have font CSS class applied."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "flow",
                "children": [{
                    "type": "field",
                    "variant": "required",
                    "children": [{
                        "type": "value",
                        "block_id": "blk-val",
                        "text": "R$ 100",
                        "bbox": None,
                        "font_name": "Helvetica",
                        "is_bold": False,
                        "font_weight": "normal",
                        "children": [],
                    }],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "helvetica" in html, "value span deve ter classe de fonte aplicada"

    def test_standalone_node_gets_styles(self):
        """Standalone node (else-branch) must receive bbox and bold styles."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "flow",
                "children": [{
                    "type": "label",
                    "block_id": "standalone-1",
                    "text": "Título",
                    "bbox": [10, 10, 200, 25],
                    "is_bold": True,
                    "font_weight": "bold",
                    "children": [],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "font-weight:bold" in html, "standalone node bold deve ter font-weight:bold"
        assert "position:absolute" in html, "standalone node com bbox deve ter position:absolute"

    def test_image_with_invalid_bbox_not_rendered(self):
        """image node with bbox_valid=False must not render any <img> tag."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "flow",
                "children": [{
                    "type": "image",
                    "image_path": "http://example.com/logo.png",
                    "bbox": [0, 0, 0, 0],
                    "bbox_valid": False,
                    "children": [],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "<img" not in html, "imagem com bbox_valid=False não deve gerar <img>"

    def test_image_with_valid_bbox_is_rendered(self):
        """image node with bbox_valid=True must render <img> with position:absolute."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "flow",
                "children": [{
                    "type": "image",
                    "image_path": "http://example.com/logo.png",
                    "bbox": [10, 10, 200, 80],
                    "bbox_valid": True,
                    "children": [],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "<img" in html, "imagem com bbox_valid=True deve gerar <img>"
        assert "position:absolute" in html, "imagem deve estar posicionada"

    def test_table_with_bbox_gets_position_absolute(self):
        """table node with bbox must have position:absolute in style attribute."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "flow",
                "children": [{
                    "type": "table",
                    "table_id": "tbl-1",
                    "bbox": [50, 100, 500, 300],
                    "children": [{
                        "type": "header_row",
                        "children": [{"type": "cell", "text": "Col A", "children": []}],
                    }],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert "<table" in html
        assert "position:absolute" in html, "tabela com bbox deve ter position:absolute"

    def test_rect_node_renders_div_with_background(self):
        """rect node with fill_color must produce positioned <div> with background-color."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "page",
                "children": [{
                    "type": "rect",
                    "bbox": [0, 0, 595, 30],
                    "fill_color": 3355443,  # some grey
                    "stroke_color": None,
                    "children": [],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert 'data-type="rect"' in html, "rect node deve gerar <div data-type='rect'>"
        assert "background-color:" in html, "rect com fill_color deve ter background-color"
        assert "position:absolute" in html, "rect deve estar posicionado"

    def test_line_node_renders_div_with_border(self):
        """line node must produce a positioned <div> with border-top style."""
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "page",
                "children": [{
                    "type": "line",
                    "bbox": [0, 400, 595, 401],
                    "stroke_color": 0,
                    "width": 1.0,
                    "orientation": "horizontal",
                    "children": [],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert 'data-type="line"' in html, "line node deve gerar <div data-type='line'>"
        assert "border-top:" in html, "line node deve ter border-top no style"

    def test_vertical_line_node_renders_border_left(self):
        """Vertical line nodes (barcode stripes) must render with border-left, not border-top.

        Fix for rca-2026-04-06-canvas-missing-images-barcode: before this fix, all lines
        used border-top which made vertical barcode stripes invisible (zero height div).
        """
        layout = _make_layout_types()[0]
        tree = {
            "type": "document",
            "children": [{
                "type": "page",
                "children": [{
                    "type": "line",
                    "bbox": [100, 700, 101, 740],
                    "stroke_color": 0,
                    "width": 1.0,
                    "orientation": "vertical",
                    "children": [],
                }],
            }],
        }
        html = _tree_to_html(tree, {}, None, layout)
        assert 'data-type="line"' in html, "vertical line deve gerar <div data-type='line'>"
        assert "border-left:" in html, "vertical line deve ter border-left no style"
        assert "border-top:" not in html, "vertical line NAO deve ter border-top"
        assert 'data-orientation="vertical"' in html, "deve ter data-orientation='vertical'"


# ---------------------------------------------------------------------------
# Tests: 5.2 CSS-from-Extraction
# ---------------------------------------------------------------------------


class TestCSSFromExtraction:
    def test_css_contains_real_font_classes(self):
        """CSS has font classes from extracted fonts, NOT hardcoded Arial."""
        docs = _make_enriched_documents()
        css = _step_5_2_css_from_extraction(docs, None, _make_layout_types())

        # Must contain extracted font names
        assert ".f-helvetica" in css
        assert ".f-helvetica-bold" in css
        assert ".f-timesnewroman" in css
        # Should contain font-family declarations
        assert "font-family:" in css
        # Should NOT be only hardcoded Arial
        assert "Helvetica" in css

    def test_css_contains_real_color_classes(self):
        """CSS has color classes from extracted colors, NOT hardcoded #000."""
        docs = _make_enriched_documents()
        css = _step_5_2_css_from_extraction(docs, None, _make_layout_types())

        # Color 0 = black
        assert ".c-000000" in css
        # Color 255 = blue
        assert ".c-0000ff" in css
        # Color 16711680 = red
        assert ".c-ff0000" in css
        assert "color: #" in css

    def test_css_contains_page_dimensions(self):
        """CSS has page dimensions from extracted page sizes."""
        docs = _make_enriched_documents()
        css = _step_5_2_css_from_extraction(docs, None, _make_layout_types())

        assert ".page {" in css or ".page{" in css
        assert "width:" in css
        assert "height:" in css

    def test_css_zone_heights_from_visual_analysis(self):
        """CSS zone heights come from visual_analysis, not hardcoded."""
        docs = _make_enriched_documents()
        va = _make_visual_analysis()
        css = _step_5_2_css_from_extraction(docs, va, _make_layout_types())

        # Header from visual analysis: bbox height = 130 - 0 = 130px
        assert ".header { height: 130px; }" in css
        # Footer from visual analysis: bbox height = 1123 - 1020 = 103px
        assert ".footer { height: 103px; }" in css

    def test_css_contains_border_from_drawn_elements(self):
        """CSS has border rules from drawn_elements[type=line]."""
        docs = _make_enriched_documents()
        css = _step_5_2_css_from_extraction(docs, None, _make_layout_types())

        assert ".border-0" in css
        assert "border-bottom" in css

    def test_css_contains_background_from_drawn_rects(self):
        """CSS has background rules from drawn_elements[type=rect]."""
        docs = _make_enriched_documents()
        css = _step_5_2_css_from_extraction(docs, None, _make_layout_types())

        assert ".bg-0" in css
        assert "background-color" in css

    def test_css_fallback_without_visual_analysis(self):
        """CSS uses fallback zone heights when visual_analysis is None."""
        docs = _make_enriched_documents()
        css = _step_5_2_css_from_extraction(docs, None, _make_layout_types())

        # Should still have header/footer with fallback sizes
        assert ".header { height:" in css
        assert ".footer { height:" in css

    def test_base_css_reset_has_page_dimensions(self):
        """_BASE_CSS_RESET must include width/height so .page never collapses.

        Regression: canvas em branco quando enriched_documents não gera CSS
        dinâmico. Sem width/height no BASE, .page colapsa para 0×0 com
        overflow:hidden, cortando todo conteúdo position:absolute.
        """
        from services.stages.stage5_template_generation import _BASE_CSS_RESET

        assert "width: 794px" in _BASE_CSS_RESET, (
            "_BASE_CSS_RESET deve ter 'width: 794px' como fallback para .page"
        )
        assert "height: 1123px" in _BASE_CSS_RESET, (
            "_BASE_CSS_RESET deve ter 'height: 1123px' como fallback para .page"
        )

    def test_css_without_enriched_documents_still_has_page_size(self):
        """When enriched_documents is empty, BASE CSS fallback provides page dimensions.

        Regression: canvas em branco quando pipeline não tem enriched_documents
        com páginas is_representative=True (ex: pipeline parcial, draft).
        """
        css = _step_5_2_css_from_extraction([], None, _make_layout_types())

        # Dynamic .page override will NOT be generated (no page_widths)
        # but _BASE_CSS_RESET provides width/height as fallback
        assert "width: 794px" in css, (
            "Sem enriched_documents, _BASE_CSS_RESET deve prover width: 794px"
        )
        assert "height: 1123px" in css, (
            "Sem enriched_documents, _BASE_CSS_RESET deve prover height: 1123px"
        )


# ---------------------------------------------------------------------------
# Tests: 5.3 Coverage
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_coverage_calculates_correctly(self):
        """Coverage uses multidimensional formula: fields*0.6 + tables*0.25 + images*0.15."""
        field_tree = _make_field_tree()
        mappings = _make_field_mappings()
        trees = {"layout-A": _make_document_tree()}
        layouts = _make_layout_types()

        coverage = _step_5_3_coverage(mappings, field_tree, trees, layouts)

        assert "layout-A" in coverage
        cov = coverage["layout-A"]

        # Fields: 5 mapped (cliente.nome, cliente.conjuge, pagamento.valor, itens.descricao, itens.valor) out of 7 XSD paths
        assert cov["fields"]["mapped"] == 5
        assert cov["fields"]["total"] == 7

        # Tables: 1 in tree
        assert cov["tables"]["total"] == 1

        # Images: 1 in tree
        assert cov["images"]["total"] == 1

        # Percentage should be weighted
        assert isinstance(cov["percentage"], int)
        assert 0 <= cov["percentage"] <= 100

    def test_coverage_per_layout(self):
        """Coverage is calculated per layout, not global."""
        field_tree = _make_field_tree()
        mappings = _make_field_mappings()
        trees = {"layout-A": _make_document_tree()}
        layouts = _make_layout_types()

        coverage = _step_5_3_coverage(mappings, field_tree, trees, layouts)

        # Should have exactly one entry per layout
        assert len(coverage) == 1
        assert "layout-A" in coverage

    def test_coverage_empty_tree(self):
        """Coverage handles empty document tree gracefully."""
        coverage = _step_5_3_coverage([], None, {}, _make_layout_types())

        assert "layout-A" in coverage
        cov = coverage["layout-A"]
        assert cov["fields"]["total"] == 0
        assert cov["fields"]["mapped"] == 0


# ---------------------------------------------------------------------------
# Tests: 5.4 Overlay Items
# ---------------------------------------------------------------------------


class TestOverlayItems:
    def test_overlay_filtered_by_layout(self):
        """Overlay items are filtered by layout_type_id."""
        mappings = _make_field_mappings()
        # Add mapping for a different layout
        mappings.append({
            "block_id": "blk-99",
            "layout_type_id": "layout-B",
            "xsd_field_path": "other.field",
            "pdf_text": "Test",
            "bbox": [10, 10, 100, 30],
            "status": "mapped",
            "page_number": 0,
            "is_table_cell": False,
            "from_table": False,
        })
        layouts = _make_layout_types()
        docs = _make_enriched_documents()
        trees = {"layout-A": _make_document_tree()}

        overlay = _step_5_4_overlay_items(mappings, layouts, docs, trees)

        assert "layout-A" in overlay
        # All items in layout-A should have layout_type_id == "layout-A"
        for item in overlay["layout-A"]:
            assert item["layout_type_id"] == "layout-A"

    def test_overlay_has_bbox_canvas_and_pdf(self):
        """Each overlay item has both bbox_canvas and bbox_pdf."""
        mappings = _make_field_mappings()
        layouts = _make_layout_types()
        docs = _make_enriched_documents()
        trees = {"layout-A": _make_document_tree()}

        overlay = _step_5_4_overlay_items(mappings, layouts, docs, trees)

        items = overlay.get("layout-A", [])
        # Should have items (at least the ones with bbox)
        field_items = [i for i in items if i.get("overlay_type") != "table_container"]
        assert len(field_items) > 0
        for item in field_items:
            assert "bbox_canvas" in item
            assert "bbox_pdf" in item
            assert "left" in item["bbox_canvas"]
            assert "top" in item["bbox_canvas"]

    def test_overlay_table_cells_typed(self):
        """Table cell overlays have overlay_type = 'table_cell'."""
        mappings = _make_field_mappings()
        layouts = _make_layout_types()
        docs = _make_enriched_documents()
        trees = {"layout-A": _make_document_tree()}

        overlay = _step_5_4_overlay_items(mappings, layouts, docs, trees)

        items = overlay.get("layout-A", [])
        table_cells = [i for i in items if i.get("overlay_type") == "table_cell"]
        assert len(table_cells) >= 2  # blk-8 and blk-9 are table cells

    def test_overlay_includes_table_container(self):
        """Table containers from document_trees produce overlay_type='table_container' (G22)."""
        mappings = _make_field_mappings()
        layouts = _make_layout_types()
        docs = _make_enriched_documents()
        trees = {"layout-A": _make_document_tree()}

        overlay = _step_5_4_overlay_items(mappings, layouts, docs, trees)

        items = overlay.get("layout-A", [])
        containers = [i for i in items if i.get("overlay_type") == "table_container"]
        assert len(containers) >= 1


# ---------------------------------------------------------------------------
# Tests: 5.5 VariationMatrix
# ---------------------------------------------------------------------------


class TestVariationMatrix:
    def test_variation_matrix_structure(self):
        """VariationMatrix has pdfs, matrix, and detections."""
        intel = _make_intelligence()
        clusters = _make_clusters()
        layouts = _make_layout_types()

        result = _step_5_5_variation_matrix(intel, clusters, layouts, [])

        assert "pdfs" in result
        assert "matrix" in result
        assert "detections" in result
        assert "layoutIds" in result["matrix"]
        assert "variationIds" in result["matrix"]
        assert "cells" in result["matrix"]

    def test_variation_detections_for_non_required(self):
        """Detections are generated for optional/conditional blocks only."""
        intel = _make_intelligence()
        clusters = _make_clusters()
        layouts = _make_layout_types()

        result = _step_5_5_variation_matrix(intel, clusters, layouts, [])

        # blk-6 is conditional, should generate a detection
        detections = result["detections"]
        assert len(detections) >= 1
        det_bindings = [d["nodeBinding"] for d in detections]
        assert "blk-6" in det_bindings

        # blk-2 is required, should NOT generate a detection
        assert "blk-2" not in det_bindings

    def test_base_pdf_determined_by_coverage(self):
        """Base PDF is the one present in most clusters."""
        intel = _make_intelligence()
        clusters = _make_clusters()
        layouts = _make_layout_types()

        result = _step_5_5_variation_matrix(intel, clusters, layouts, [])

        pdfs = result["pdfs"]
        base_pdfs = [p for p in pdfs if p["role"] == "base"]
        assert len(base_pdfs) == 1


# ---------------------------------------------------------------------------
# Tests: 5.6 PipelineResult Assembly — Confidence Normalization
# ---------------------------------------------------------------------------


class TestConfidenceNormalization:
    def test_all_factors_normalized_0_100(self):
        """ALL confidence factors are normalized to 0-100, not just overall (G18)."""
        scores = {
            "layout-A": {
                "layout_stability": 0.85,
                "anchor_detection": 0.70,
                "grid_quality": 0.90,
                "field_variability": 0.65,
                "vision_agreement": 0.80,
                "overall": 78,
                "status": "review_recommended",
            },
        }
        layouts = _make_layout_types()

        normalized = _normalize_confidence(scores, layouts)

        entry = normalized["layout-A"]
        # All factors should be integers 0-100
        for key in ("layout_stability", "anchor_detection", "grid_quality",
                     "field_variability", "vision_agreement", "overall"):
            val = entry[key]
            assert isinstance(val, int), f"{key} should be int, got {type(val)}"
            assert 0 <= val <= 100, f"{key}={val} out of range"

        # Specific checks for 0-1 -> 0-100 conversion
        assert entry["layout_stability"] == 85
        assert entry["anchor_detection"] == 70
        assert entry["grid_quality"] == 90

    def test_already_0_100_values_not_multiplied(self):
        """Values already in 0-100 scale are not double-multiplied."""
        scores = {
            "layout-A": {
                "layout_stability": 85,
                "anchor_detection": 70,
                "grid_quality": 90,
                "field_variability": 65,
                "vision_agreement": 80,
                "overall": 78,
                "status": "approved",
            },
        }
        layouts = _make_layout_types()

        normalized = _normalize_confidence(scores, layouts)

        entry = normalized["layout-A"]
        assert entry["layout_stability"] == 85
        assert entry["overall"] == 78

    def test_fallback_when_no_scores(self):
        """Missing confidence scores get fallback values."""
        normalized = _normalize_confidence({}, _make_layout_types())

        entry = normalized["layout-A"]
        assert entry["overall"] == 50
        assert entry["status"] == "review_recommended"


# ---------------------------------------------------------------------------
# Tests: 5.6 PipelineResult — layout_types enrichment
# ---------------------------------------------------------------------------


class TestLayoutTypesEnrichment:
    def test_layout_types_pre_populated(self):
        """layout_types[] includes documentTree, confidence, coverage (G19)."""
        context = {
            "document_trees": {"layout-A": _make_document_tree()},
            "layout_types": _make_layout_types(),
            "confidence_scores": {
                "layout-A": {
                    "layout_stability": 0.85,
                    "anchor_detection": 0.70,
                    "grid_quality": 0.90,
                    "field_variability": 0.65,
                    "vision_agreement": 0.80,
                    "overall": 78,
                    "status": "review_recommended",
                },
            },
            "enriched_documents": _make_enriched_documents(),
            "visual_analysis": _make_visual_analysis(),
            "field_mappings": _make_field_mappings(),
            "field_tree": _make_field_tree(),
            "clusters": _make_clusters(),
            "format_functions": {},
            "validation_result": {"warnings": [], "errors": []},
            "block_classifications_confirmed": {},
            "pdf_documents": [],
        }

        coverage = _step_5_3_coverage(
            context["field_mappings"],
            context["field_tree"],
            context["document_trees"],
            context["layout_types"],
        )

        result = _step_5_6_pipeline_result(
            context,
            {"layout-A": "<div>test</div>"},
            ".page { width: 794px; }",
            coverage,
            {"layout-A": []},
            {"pdfs": [], "matrix": {}, "detections": []},
        )

        enriched = result["layout_types"]
        assert len(enriched) == 1
        lt = enriched[0]

        # G19: documentTree present
        assert "documentTree" in lt
        assert "root" in lt["documentTree"]

        # G19: confidence present and normalized
        assert "confidence" in lt
        assert lt["confidence"]["layout_stability"] == 85

        # G19: coverage present
        assert "coverage" in lt
        assert "fields" in lt["coverage"]

        # page_count from clusters
        assert "page_count" in lt
        assert lt["page_count"] == 2

    def test_result_has_trees_by_layout(self):
        """PipelineResult includes trees_by_layout in document_structure."""
        context = {
            "document_trees": {"layout-A": _make_document_tree()},
            "layout_types": _make_layout_types(),
            "confidence_scores": {},
            "enriched_documents": _make_enriched_documents(),
            "visual_analysis": None,
            "field_mappings": [],
            "clusters": _make_clusters(),
            "format_functions": {},
            "validation_result": {},
            "block_classifications_confirmed": {},
            "pdf_documents": [],
        }

        result = _step_5_6_pipeline_result(
            context, {}, "", {}, {}, {"pdfs": [], "matrix": {}, "detections": []},
        )

        assert "trees_by_layout" in result["document_structure"]
        assert "layout-A" in result["document_structure"]["trees_by_layout"]

    def test_result_has_all_required_fields(self):
        """PipelineResult contains all required fields (G20 — 8 new fields)."""
        context = {
            "document_trees": {"layout-A": _make_document_tree()},
            "layout_types": _make_layout_types(),
            "confidence_scores": {},
            "enriched_documents": _make_enriched_documents(),
            "visual_analysis": _make_visual_analysis(),
            "field_mappings": _make_field_mappings(),
            "field_tree": _make_field_tree(),
            "clusters": _make_clusters(),
            "format_functions": {},
            "validation_result": {"warnings": [], "errors": []},
            "block_classifications_confirmed": {"blk-3": {"confirmed": "dynamic"}},
            "pdf_documents": [],
        }

        result = _step_5_6_pipeline_result(
            context, {"layout-A": "<div>html</div>"}, ".page {}",
            {"layout-A": {"fields": {"mapped": 3, "total": 5}, "percentage": 60}},
            {"layout-A": []},
            {"pdfs": [], "matrix": {}, "detections": []},
        )

        # Check all required top-level keys
        required_keys = [
            "document_structure", "field_mappings", "confidence_scores",
            "coverage", "layout_types", "template_draft", "ambiguous_fields",
            "format_functions", "overlay_items", "document_type",
            "visual_analysis", "intelligence", "validation_result",
            "block_classifications_confirmed", "multi_doc", "page_config",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

        # template_draft is monolithic (html + css)
        assert "html" in result["template_draft"]
        assert "css" in result["template_draft"]


# ---------------------------------------------------------------------------
# Tests: run_stage5 integration
# ---------------------------------------------------------------------------


class TestRunStage5:
    @pytest.mark.asyncio
    async def test_run_stage5_produces_context(self):
        """run_stage5 writes result_json and stage_5_result to context."""
        emit = AsyncMock()
        context = {
            "_storage": None,
            "job_id": "test-job",
            "_current_stage": 0,
            "_current_stage_name": "",
            "document_trees": {"layout-A": _make_document_tree()},
            "intelligence": _make_intelligence(),
            "enriched_documents": _make_enriched_documents(),
            "visual_analysis": _make_visual_analysis(),
            "field_mappings": _make_field_mappings(),
            "field_tree": _make_field_tree(),
            "layout_types": _make_layout_types(),
            "clusters": _make_clusters(),
            "confidence_scores": {
                "layout-A": {
                    "layout_stability": 0.85,
                    "anchor_detection": 0.70,
                    "grid_quality": 0.90,
                    "field_variability": 0.65,
                    "vision_agreement": 0.80,
                    "overall": 78,
                    "status": "review_recommended",
                },
            },
            "validation_result": {"warnings": [], "errors": []},
            "block_classifications_confirmed": {},
            "format_functions": {},
            "pdf_documents": [{"id": "0", "path": "test.pdf", "name": "test.pdf"}],
        }

        result_ctx = await run_stage5(context, emit)

        assert "result_json" in result_ctx
        assert "stage_5_result" in result_ctx

        rj = result_ctx["result_json"]
        assert rj["template_draft"]["html"]  # non-empty
        assert rj["template_draft"]["css"]  # non-empty
        assert "layout-A" in rj["coverage"]
        assert "<table" in rj["template_draft"]["html"]

        # Emit progress was called multiple times
        assert emit.call_count >= 7  # 7 sub-steps

    @pytest.mark.asyncio
    async def test_run_stage5_with_persistence(self):
        """run_stage5 calls storage.save_result when storage is available."""
        storage = AsyncMock()
        storage.save_result = AsyncMock()
        emit = AsyncMock()

        context = {
            "_storage": storage,
            "job_id": "test-job-persist",
            "_current_stage": 0,
            "_current_stage_name": "",
            "document_trees": {"layout-A": _make_document_tree()},
            "intelligence": _make_intelligence(),
            "enriched_documents": _make_enriched_documents(),
            "visual_analysis": None,
            "field_mappings": _make_field_mappings(),
            "field_tree": _make_field_tree(),
            "layout_types": _make_layout_types(),
            "clusters": _make_clusters(),
            "confidence_scores": {},
            "validation_result": {},
            "block_classifications_confirmed": {},
            "format_functions": {},
            "pdf_documents": [],
        }

        await run_stage5(context, emit)

        storage.save_result.assert_awaited_once()
        call_args = storage.save_result.call_args
        assert call_args[0][0] == "test-job-persist"


# ---------------------------------------------------------------------------
# Tests: Helper functions
# ---------------------------------------------------------------------------


class TestExtractVisualData:
    """Tests for _extract_visual_data helper (Story 14.0)."""

    def test_extract_visual_data_from_context(self):
        context = {
            "enriched_documents": [
                {
                    "pdf_id": "doc_0",
                    "pages": [
                        {
                            "page_index": 0,
                            "cluster_id": "layout_A",
                            "drawn_elements": [{"type": "line", "x0": 10}],
                            "text_blocks": [{"text": "hello", "font_size": 12}],
                        },
                        {
                            "page_index": 1,
                            "cluster_id": "layout_A",
                            "drawn_elements": [],
                            "text_blocks": [{"text": "world"}],
                        },
                    ],
                }
            ]
        }
        result = _extract_visual_data(context)
        assert "pages" in result
        assert len(result["pages"]) == 2
        assert result["pages"][0]["page_index"] == 0
        assert result["pages"][0]["cluster_id"] == "layout_A"
        assert len(result["pages"][0]["drawn_elements"]) == 1
        assert len(result["pages"][0]["text_blocks"]) == 1

    def test_extract_visual_data_empty_context(self):
        result = _extract_visual_data({})
        assert result == {"pages": []}

    def test_extract_visual_data_no_pages(self):
        context = {"enriched_documents": [{"pdf_id": "doc_0", "pages": []}]}
        result = _extract_visual_data(context)
        assert result == {"pages": []}


class TestStep57VisualDataPersistence:
    """Tests for visual data persistence in _step_5_7_persist (Story 14.0)."""

    @pytest.mark.asyncio
    async def test_persist_visual_data(self):
        """Visual data is persisted after result_json."""
        mock_storage = AsyncMock()
        context = {
            "_storage": mock_storage,
            "job_id": "job-vd-001",
            "enriched_documents": [
                {
                    "pdf_id": "doc_0",
                    "pages": [
                        {
                            "page_index": 0,
                            "cluster_id": "A",
                            "drawn_elements": [{"type": "rect"}],
                            "text_blocks": [{"text": "test"}],
                        }
                    ],
                }
            ],
        }
        result_json = {"field_mappings": []}
        emit = AsyncMock()

        await _step_5_7_persist(context, result_json, emit)

        mock_storage.save_result.assert_awaited_once_with("job-vd-001", result_json)
        mock_storage.save_visual_data.assert_awaited_once()
        vd_arg = mock_storage.save_visual_data.call_args[0][1]
        assert len(vd_arg["pages"]) == 1

    @pytest.mark.asyncio
    async def test_persist_visual_data_failure_non_blocking(self):
        """Visual data failure does not block the pipeline."""
        mock_storage = AsyncMock()
        mock_storage.save_visual_data.side_effect = Exception("Bucket error")
        context = {
            "_storage": mock_storage,
            "job_id": "job-vd-002",
            "enriched_documents": [
                {
                    "pdf_id": "doc_0",
                    "pages": [
                        {
                            "page_index": 0,
                            "cluster_id": "A",
                            "drawn_elements": [{"type": "line"}],
                            "text_blocks": [],
                        }
                    ],
                }
            ],
        }
        result_json = {"field_mappings": []}
        emit = AsyncMock()

        # Should NOT raise
        await _step_5_7_persist(context, result_json, emit)

        mock_storage.save_result.assert_awaited_once()
        mock_storage.save_visual_data.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persist_skips_empty_visual_data(self):
        """Visual data is not saved when no pages have visual data."""
        mock_storage = AsyncMock()
        context = {
            "_storage": mock_storage,
            "job_id": "job-vd-003",
            "enriched_documents": [],
        }
        result_json = {"field_mappings": []}
        emit = AsyncMock()

        await _step_5_7_persist(context, result_json, emit)

        mock_storage.save_result.assert_awaited_once()
        mock_storage.save_visual_data.assert_not_awaited()


class TestConvertTreeToCssCoords:
    """_convert_tree_to_css_coords always emits children: [] for leaf nodes.

    RCA: rca-2026-03-31-editor-redirect-to-home — leaf nodes without 'children'
    caused buildFlatMap() in the frontend to throw TypeError, preventing
    session.analysisCompleted from being set and redirecting the user to home.
    """

    _LAYOUT = {"page_height_pts": 841.89, "page_width_pts": 595.28}

    def test_leaf_node_without_children_key_gets_empty_children(self):
        """Leaf nodes with no 'children' key must get children: [] after conversion."""
        cell = {"type": "cell", "text": "Header A"}
        result = _convert_tree_to_css_coords(cell, self._LAYOUT)
        assert "children" in result, "converted node must always have 'children' key"
        assert result["children"] == []

    def test_leaf_node_with_empty_children_keeps_empty_children(self):
        """Nodes with children: [] must still have children: [] after conversion."""
        node = {"id": "n1", "type": "field", "children": []}
        result = _convert_tree_to_css_coords(node, self._LAYOUT)
        assert result["children"] == []

    def test_image_node_without_children_gets_empty_children(self):
        """image nodes (no children key) must get children: []."""
        image = {"type": "image", "bbox": [10, 10, 100, 200], "format": "png"}
        result = _convert_tree_to_css_coords(image, self._LAYOUT)
        assert "children" in result
        assert result["children"] == []

    def test_parent_node_children_are_converted_recursively(self):
        """Parent nodes must have children converted; all descendants get children key."""
        row = {
            "id": "row1",
            "type": "data_row",
            "children": [
                {"type": "cell", "text": "A"},
                {"type": "cell", "text": "B"},
            ],
        }
        result = _convert_tree_to_css_coords(row, self._LAYOUT)
        assert len(result["children"]) == 2
        for child in result["children"]:
            assert "children" in child, "each converted child must have 'children' key"
            assert child["children"] == []

    def test_bbox_coords_converted_to_css_pixels(self):
        """Nodes with bbox must have CSS pixel properties injected."""
        node = {"id": "n", "type": "field", "bbox": [0, 0, 595.28, 841.89], "children": []}
        result = _convert_tree_to_css_coords(node, self._LAYOUT)
        assert "x" in result["properties"]
        assert "y" in result["properties"]
        assert "width" in result["properties"]
        assert "height" in result["properties"]

    def test_node_without_id_gets_block_id_as_id(self):
        """Nodes with block_id but no id must get id = block_id.

        RCA: rca-2026-04-01-fieldnav-click-silent-failure (v2) —
        stage3 emits value/label nodes with block_id but no id.
        buildFlatMap() does map.set(node.id, node); without id all nodes
        collapse to key=undefined and reconcileFieldBindings() cannot find them.
        """
        node = {"type": "value", "block_id": "blk-abc123", "text": "42.00"}
        result = _convert_tree_to_css_coords(node, self._LAYOUT)
        assert result["id"] == "blk-abc123", (
            "node without id must get id = block_id so flatNodes is indexed correctly"
        )

    def test_node_without_id_or_block_id_gets_synthetic_id(self):
        """Nodes without both id and block_id must still get a non-empty id."""
        node = {"type": "section", "children": []}
        result = _convert_tree_to_css_coords(node, self._LAYOUT)
        assert result.get("id"), "every node must have a non-empty id after conversion"

    def test_existing_id_is_not_overwritten(self):
        """Nodes that already have id must keep their id."""
        node = {"id": "existing-id", "type": "field", "block_id": "blk-999", "children": []}
        result = _convert_tree_to_css_coords(node, self._LAYOUT)
        assert result["id"] == "existing-id", "pre-existing id must not be overwritten by block_id"

    def test_id_propagated_to_all_children(self):
        """All nested children must receive id after conversion."""
        tree = {
            "id": "root",
            "type": "section",
            "children": [
                {"type": "field", "children": [
                    {"type": "label", "block_id": "lbl-1", "text": "Data"},
                    {"type": "value", "block_id": "val-1", "text": "01/01/2026"},
                ]},
            ],
        }
        result = _convert_tree_to_css_coords(tree, self._LAYOUT)
        field = result["children"][0]
        assert field.get("id"), "field node (no block_id) must get synthetic id"
        label = field["children"][0]
        value = field["children"][1]
        assert label["id"] == "lbl-1"
        assert value["id"] == "val-1"


class TestBboxToAbsoluteStyle:
    """Regression tests for _bbox_to_absolute_style — fitz screen coords (y=0 at top)."""

    def test_top_of_page_element_has_small_top(self):
        """Element near page top (small y0 in fitz coords) must produce small CSS top value.

        PyMuPDF uses screen coordinates: y=0 at top-left, y increases downward.
        An element at the top of the page has y0≈10, y1≈30 (small values near 0).
        CSS top = y0 * scale → 10 * 1.33 ≈ 13px (near top).
        """
        style = _bbox_to_absolute_style([0.0, 10.0, 100.0, 30.0], 842.0, 595.0)
        assert style is not None
        parts = dict(p.split(":") for p in style.rstrip(";").split(";"))
        top_px = int(parts["top"].replace("px", ""))
        assert top_px < 50, f"Element at y0=10 (near page top) must be near CSS top, got top={top_px}px"

    def test_bottom_of_page_element_has_large_top(self):
        """Element near page bottom (large y0 in fitz coords) must produce large CSS top value.

        PyMuPDF screen coords: y=0 at top, increases downward.
        An element at the bottom has y0≈812 (close to page_height=842).
        CSS top = y0 * scale → 812 * 1.33 ≈ 1080px (near bottom of 1123px canvas).
        """
        style = _bbox_to_absolute_style([0.0, 812.0, 100.0, 832.0], 842.0, 595.0)
        assert style is not None
        parts = dict(p.split(":") for p in style.rstrip(";").split(";"))
        top_px = int(parts["top"].replace("px", ""))
        assert top_px > 900, f"Element at y0=812 (near page bottom) must be near CSS bottom, got top={top_px}px"

    def test_y_axis_not_inverted(self):
        """Elements with smaller fitz y0 (closer to top) must have smaller CSS top values."""
        # top_elem: small fitz y → near page top → small CSS top
        top_elem = _bbox_to_absolute_style([0.0, 50.0, 200.0, 80.0], 842.0, 595.0)
        # bot_elem: large fitz y → near page bottom → large CSS top
        bot_elem = _bbox_to_absolute_style([0.0, 760.0, 200.0, 792.0], 842.0, 595.0)
        assert top_elem and bot_elem
        def get_top(s):
            return int(dict(p.split(":") for p in s.rstrip(";").split(";"))["top"].replace("px", ""))
        assert get_top(top_elem) < get_top(bot_elem), "Smaller fitz y (page top) must map to smaller CSS top"

    def test_returns_none_for_invalid_bbox(self):
        assert _bbox_to_absolute_style(None) is None
        assert _bbox_to_absolute_style([]) is None
        assert _bbox_to_absolute_style([0, 0]) is None


class TestFlowCssHeight:
    """Regression: .flow must have explicit height so position:absolute children are not clipped."""

    def test_flow_has_height_in_base_css_reset(self):
        """_BASE_CSS_RESET must declare height on .flow — without it, overflow:hidden collapses to 0."""
        import re
        flow_block = re.search(r"\.flow\s*\{([^}]+)\}", _BASE_CSS_RESET)
        assert flow_block, ".flow rule not found in _BASE_CSS_RESET"
        flow_props = flow_block.group(1)
        assert "height" in flow_props, (
            ".flow must declare 'height' — without it, all position:absolute children "
            "are clipped by overflow:hidden (height collapses to 0)"
        )

    def test_flow_has_top_in_base_css_reset(self):
        """_BASE_CSS_RESET must declare top on .flow — without it placement is undefined."""
        import re
        flow_block = re.search(r"\.flow\s*\{([^}]+)\}", _BASE_CSS_RESET)
        assert flow_block, ".flow rule not found in _BASE_CSS_RESET"
        flow_props = flow_block.group(1)
        assert "top" in flow_props, ".flow must declare 'top' to anchor it to the page origin"


class TestHelpers:
    def test_count_nodes_by_type(self):
        """_count_nodes_by_type counts correctly."""
        tree = _make_document_tree()
        assert _count_nodes_by_type(tree, "table") == 1
        assert _count_nodes_by_type(tree, "image") == 1
        assert _count_nodes_by_type(tree, "chart") == 1
        assert _count_nodes_by_type(tree, "section") == 2
        assert _count_nodes_by_type(tree, "nonexistent") == 0
        assert _count_nodes_by_type(None, "table") == 0


class TestPageRenderOrder:
    """page node renders: rects first (backgrounds), zones next (content), lines last (grid)."""

    def _make_page_tree(self) -> dict:
        layout = {"id": "test", "name": "test", "page_height_pts": 842.0, "page_width_pts": 595.0}
        tree = {
            "type": "document",
            "children": [{
                "type": "page",
                "children": [
                    # Zones added first in stage3
                    {
                        "type": "flow",
                        "children": [{
                            "type": "section",
                            "children": [
                                {"type": "label", "block_id": "b1", "text": "CellText",
                                 "bbox": [36, 350, 200, 365], "children": []}
                            ]
                        }]
                    },
                    # Drawn elements added last in stage3
                    {"type": "rect", "bbox": [36, 350, 559, 395], "fill_color": 14540253, "stroke_color": None},
                    {"type": "line", "bbox": [36, 365, 559, 365], "stroke_color": 0, "width": 0.5},
                ]
            }]
        }
        return tree, layout

    def test_rect_before_flow_before_line_in_html(self):
        """Drawn rects must appear before .flow (text) and .flow before drawn lines."""
        tree, layout = self._make_page_tree()
        html = _tree_to_html(tree, {}, None, layout)
        rect_pos = html.find('data-type="rect"')
        flow_pos = html.find('class="flow"')
        line_pos = html.find('data-type="line"')
        assert rect_pos != -1, "rect element must be present"
        assert flow_pos != -1, ".flow must be present"
        assert line_pos != -1, "line element must be present"
        assert rect_pos < flow_pos, "rect (background) must come before .flow (text) in DOM"
        assert flow_pos < line_pos, ".flow (text) must come before line (grid) in DOM"

    def test_text_content_visible_over_rect_background(self):
        """Text span inside .flow must appear after rect-div in DOM so it paints on top."""
        tree, layout = self._make_page_tree()
        html = _tree_to_html(tree, {}, None, layout)
        rect_pos = html.find('data-type="rect"')
        text_pos = html.find("CellText")
        assert rect_pos < text_pos, "text content must come after rect background in DOM"


class TestSectionImageZOrder:
    """Images inside sections must render BEFORE text spans (z-order)."""

    def test_image_before_text_in_section(self):
        """Rasterized table image must appear before text spans in section DOM."""
        layout = {"id": "t", "name": "t", "page_height_pts": 842.0, "page_width_pts": 595.0}
        tree = {
            "type": "section",
            "variant": "required",
            "name": "boleto_data",
            "children": [
                # Text blocks added first by stage3
                {"type": "label", "block_id": "b1", "text": "Cedente",
                 "bbox": [25, 561, 80, 575], "color": 0, "children": []},
                {"type": "value", "block_id": "b2", "text": "MAG SEGUROS",
                 "bbox": [200, 561, 400, 575], "color": 0, "children": []},
                # Image added AFTER blocks by stage3
                {"type": "image", "image_path": "table_bg.jpg",
                 "bbox": [36, 535, 756, 1019], "bbox_valid": True, "format": "jpeg",
                 "children": []},
            ],
        }
        html = _tree_to_html(tree, {}, None, layout)
        img_pos = html.find('<img ')
        text_pos = html.find("Cedente")
        assert img_pos != -1, "image must be present"
        assert text_pos != -1, "text must be present"
        assert img_pos < text_pos, (
            "image (background) must come before text in DOM for correct z-order"
        )

    def test_section_with_only_text_unchanged(self):
        """Sections without images should render children in original order."""
        layout = {"id": "t", "name": "t", "page_height_pts": 842.0, "page_width_pts": 595.0}
        tree = {
            "type": "section",
            "variant": "required",
            "name": "header",
            "children": [
                {"type": "label", "block_id": "b1", "text": "First",
                 "bbox": [25, 30, 80, 45], "color": 0, "children": []},
                {"type": "value", "block_id": "b2", "text": "Second",
                 "bbox": [25, 50, 80, 65], "color": 0, "children": []},
            ],
        }
        html = _tree_to_html(tree, {}, None, layout)
        first_pos = html.find("First")
        second_pos = html.find("Second")
        assert first_pos < second_pos, "without images, original children order preserved"


# ---------------------------------------------------------------------------
# Barcode SVG rendering
# ---------------------------------------------------------------------------


class TestBarcodeNodeRendering:
    """Validates that a barcode node with `value` renders an inline SVG.

    AC: stage5 must emit <svg> content (not <!-- barcode -->) when the node
        carries a `value` field; must fall back to placeholder when value is absent.
    """

    _LAYOUT = {"id": "t", "name": "t", "page_height_pts": 842.0, "page_width_pts": 595.0}

    def _barcode_node(self, value=None, fmt="CODE128"):
        node = {
            "type": "barcode",
            "barcode_format": fmt,
            "bbox": [28.0, 540.0, 583.0, 610.0],
            "children": [],
        }
        if value is not None:
            node["value"] = value
        return node

    def test_barcode_with_value_renders_svg(self):
        """Barcode node with value must produce inline <svg> content."""
        node = self._barcode_node(value="23793369085202072907")
        html = _tree_to_html(node, {}, None, self._LAYOUT)
        assert "<svg" in html, "Barcode com value deve renderizar <svg>"
        assert "<!-- barcode: no value -->" not in html

    def test_barcode_without_value_renders_placeholder(self):
        """Barcode node without value must render placeholder comment."""
        node = self._barcode_node(value=None)
        html = _tree_to_html(node, {}, None, self._LAYOUT)
        assert "<!-- barcode: no value -->" in html, (
            "Barcode sem value deve renderizar placeholder"
        )
        assert "<svg" not in html

    def test_barcode_svg_has_no_fixed_width(self):
        """Generated SVG must not have a fixed pixel width (must scale to container)."""
        node = self._barcode_node(value="12345678901234")
        html = _tree_to_html(node, {}, None, self._LAYOUT)
        if "<svg" not in html:
            pytest.skip("python-barcode not available in this environment")
        # Root <svg> tag must use width="100%", not a fixed dimension.
        import re
        svg_open_tag = re.search(r"<svg[^>]*>", html)
        assert svg_open_tag is not None, "SVG tag not found"
        svg_tag = svg_open_tag.group()
        fixed_width = re.search(r'width="[\d.]+(?:px|mm|pt|cm)"', svg_tag)
        assert fixed_width is None, (
            f"<svg> raiz não deve ter width fixo; encontrado em: {svg_tag}"
        )
        assert 'width="100%"' in svg_tag, f"<svg> deve ter width=100%; obtido: {svg_tag}"

    def test_barcode_div_has_overflow_hidden(self):
        """Container div must have overflow:hidden to prevent SVG bleed."""
        node = self._barcode_node(value="23793369085202072907")
        html = _tree_to_html(node, {}, None, self._LAYOUT)
        assert "overflow:hidden" in html, "Container barcode deve ter overflow:hidden"
