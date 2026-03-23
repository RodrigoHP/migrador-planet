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
    _count_mapped_tables,
    _count_nodes_by_type,
    _normalize_confidence,
    _step_5_1_tree_driven_html,
    _step_5_2_css_from_extraction,
    _step_5_3_coverage,
    _step_5_4_overlay_items,
    _step_5_5_variation_matrix,
    _step_5_6_pipeline_result,
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
