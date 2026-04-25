"""Unit tests for Stage 3 inline label+value extraction via sub_spans.

Story 48.15 — AC4: unit tests for _extract_inline_label_value helper.
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _make_sub_span(text: str, is_bold: bool) -> dict[str, Any]:
    return {
        "text": text,
        "offset": 0,
        "length": len(text),
        "font_name": "Helvetica-Bold" if is_bold else "Helvetica",
        "font_size": 10.0,
        "is_bold": is_bold,
        "is_italic": False,
        "color": 0,
    }


def _make_block(text: str, sub_spans: list[dict[str, Any]] | None) -> dict[str, Any]:
    return {
        "id": "block-1",
        "text": text,
        "bbox": [50.0, 100.0, 300.0, 115.0],
        "font_name": "Helvetica",
        "font_size": 10.0,
        "is_bold": False,
        "is_italic": False,
        "is_mono": False,
        "color": 0,
        "sub_spans": sub_spans,
    }


class TestExtractInlineLabelValue:
    """Tests for _extract_inline_label_value in semantic_utils."""

    def _fn(self, block: dict[str, Any]):
        from services.stages.stage3_structural.semantic_utils import _extract_inline_label_value

        return _extract_inline_label_value(block)

    def test_bold_label_regular_value_returns_tuple(self):
        """AC1: sub_spans[0] bold + sub_spans[-1] regular → (label, value)."""
        block = _make_block(
            "TELEFONE: (19) 98189-4732",
            [
                _make_sub_span("TELEFONE:", is_bold=True),
                _make_sub_span(" (19) 98189-4732", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is not None
        label, value = result
        assert label == "TELEFONE"
        assert value == "(19) 98189-4732"

    def test_email_colon_at_start_of_value(self):
        """AC2: E-MAIL edge case — ':' at start of span[-1], not at end of span[0]."""
        block = _make_block(
            "E-MAIL: TELMATSANCHES@GMAIL.COM",
            [
                _make_sub_span("E-MAIL", is_bold=True),
                _make_sub_span(": TELMATSANCHES@GMAIL.COM", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is not None
        label, value = result
        assert label == "E-MAIL"
        assert value == "TELMATSANCHES@GMAIL.COM"

    def test_inscricao_field(self):
        """AC2: INSCRIÇÃO: 1124669542800."""
        block = _make_block(
            "INSCRIÇÃO: 1124669542800",
            [
                _make_sub_span("INSCRIÇÃO:", is_bold=True),
                _make_sub_span(" 1124669542800", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is not None
        label, value = result
        assert label == "INSCRIÇÃO"
        assert value == "1124669542800"

    def test_plano_field(self):
        """AC2: PLANO: 2800 - WHOLE LIFE DECRESCENTE."""
        block = _make_block(
            "PLANO: 2800 - WHOLE LIFE DECRESCENTE",
            [
                _make_sub_span("PLANO:", is_bold=True),
                _make_sub_span(" 2800 - WHOLE LIFE DECRESCENTE", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is not None
        label, value = result
        assert label == "PLANO"
        assert value == "2800 - WHOLE LIFE DECRESCENTE"

    def test_forma_pagamento_field(self):
        """AC2: FORMA DE PAGAMENTO: CARTÃO DE CRÉDITO."""
        block = _make_block(
            "FORMA DE PAGAMENTO: CARTÃO DE CRÉDITO",
            [
                _make_sub_span("FORMA DE PAGAMENTO:", is_bold=True),
                _make_sub_span(" CARTÃO DE CRÉDITO", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is not None
        label, value = result
        assert label == "FORMA DE PAGAMENTO"
        assert value == "CARTÃO DE CRÉDITO"

    def test_sub_spans_none_returns_none(self):
        """AC3: sub_spans=None → fallback (returns None from helper)."""
        block = _make_block("VALOR TOTAL: R$ 1.234,56", sub_spans=None)
        result = self._fn(block)
        assert result is None

    def test_uniform_bold_all_returns_none(self):
        """Fallback: all sub_spans bold → not an inline label+value → None."""
        block = _make_block(
            "BOLD TEXT ONLY",
            [
                _make_sub_span("BOLD", is_bold=True),
                _make_sub_span(" TEXT ONLY", is_bold=True),
            ],
        )
        result = self._fn(block)
        assert result is None

    def test_uniform_regular_all_returns_none(self):
        """Fallback: all sub_spans not bold → None."""
        block = _make_block(
            "regular text here",
            [
                _make_sub_span("regular", is_bold=False),
                _make_sub_span(" text here", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is None

    def test_single_sub_span_returns_none(self):
        """Only one sub_span → not inline label+value → None."""
        block = _make_block(
            "ONLY ONE SPAN",
            [_make_sub_span("ONLY ONE SPAN", is_bold=True)],
        )
        result = self._fn(block)
        assert result is None

    def test_empty_label_after_strip_returns_none(self):
        """If label text is empty after stripping → None (guard against ':' only spans)."""
        block = _make_block(
            ": some value",
            [
                _make_sub_span(":", is_bold=True),
                _make_sub_span(" some value", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is None

    def test_empty_value_after_strip_returns_none(self):
        """If value text is empty after stripping → None."""
        block = _make_block(
            "LABEL: :",
            [
                _make_sub_span("LABEL:", is_bold=True),
                _make_sub_span(" :", is_bold=False),
            ],
        )
        result = self._fn(block)
        assert result is None


class TestTreeBuilderInlineSubSpans:
    """Integration-style unit tests for tree_builder handling of sub_spans."""

    def _run_build_tree_minimal(
        self,
        block: dict[str, Any],
        semantic: str = "likely_dynamic",
    ) -> dict[str, Any]:
        """Build a minimal tree with a single block and return the tree dict."""
        from models.pipeline_context import BlockClassification
        from services.stages.stage3_structural.tree_builder import _build_tree

        bid = block["id"]
        bc = BlockClassification(
            semantic=semantic,
            stability="stable",
            variant="required",
            confidence=0.9,
            presence_ratio=1.0,
            pdf_coverage=1.0,
            field_pair=None,
        )
        block_classifications = {bid: bc}

        # Minimal zone/section structure expected by _build_tree
        zones = [
            {
                "type": "body",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": [block],
                        "tables": [],
                        "images": [],
                        "charts": [],
                        "barcodes": [],
                        "svgs": [],
                    }
                ],
            }
        ]

        page_data = {
            "page_index": 0,
            "width": 595.0,
            "height": 842.0,
            "text_blocks": [block],
            "images": [],
            "tables": [],
            "drawn_elements": [],
        }

        tree = _build_tree("cluster-A", zones, block_classifications, page_data)
        return tree

    def _find_nodes(self, node: dict, node_type: str) -> list[dict]:
        """Recursively collect nodes of a given type."""
        results = []
        if node.get("type") == node_type:
            results.append(node)
        for child in node.get("children", []):
            results.extend(self._find_nodes(child, node_type))
        return results

    def test_inline_block_becomes_field_node(self):
        """A block with mixed sub_spans is emitted as a 'field' node."""
        block = {
            "id": "blk-1",
            "text": "TELEFONE: (19) 98189-4732",
            "bbox": [50.0, 100.0, 300.0, 115.0],
            "font_name": "Helvetica",
            "font_size": 10.0,
            "is_bold": False,
            "is_italic": False,
            "is_mono": False,
            "color": 0,
            "sub_spans": [
                {
                    "text": "TELEFONE:",
                    "offset": 0,
                    "length": 9,
                    "font_name": "Helvetica-Bold",
                    "font_size": 10.0,
                    "is_bold": True,
                    "is_italic": False,
                    "color": 0,
                },
                {
                    "text": " (19) 98189-4732",
                    "offset": 9,
                    "length": 16,
                    "font_name": "Helvetica",
                    "font_size": 10.0,
                    "is_bold": False,
                    "is_italic": False,
                    "color": 0,
                },
            ],
        }
        tree = self._run_build_tree_minimal(block)
        field_nodes = self._find_nodes(tree, "field")
        assert len(field_nodes) == 1
        fn = field_nodes[0]
        assert fn.get("name") == "TELEFONE"
        children = fn.get("children", [])
        assert len(children) == 2
        label_child = next((c for c in children if c.get("type") == "label"), None)
        value_child = next((c for c in children if c.get("type") == "value"), None)
        assert label_child is not None
        assert value_child is not None
        assert label_child.get("text") == "TELEFONE"
        assert value_child.get("text") == "(19) 98189-4732"

    def test_uniform_block_becomes_standalone_node(self):
        """AC3: A block with sub_spans=None is emitted as standalone (not field)."""
        block = {
            "id": "blk-2",
            "text": "Header title text",
            "bbox": [50.0, 50.0, 300.0, 65.0],
            "font_name": "Helvetica",
            "font_size": 14.0,
            "is_bold": True,
            "is_italic": False,
            "is_mono": False,
            "color": 0,
            "sub_spans": None,
        }
        tree = self._run_build_tree_minimal(block, semantic="label")
        # No field nodes for a uniform block
        field_nodes = self._find_nodes(tree, "field")
        assert len(field_nodes) == 0
        # Should appear as label node
        label_nodes = self._find_nodes(tree, "label")
        assert len(label_nodes) >= 1
