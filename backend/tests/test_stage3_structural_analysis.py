"""Tests for Stage 3 — Structural Analysis (Story 13.7).

Covers:
- 3.1 Multi-Example Analysis: statistical, regex (CPF), spaCy NER
- 3.2 Visual Analysis: GPT-4o mock + fallback path
- 3.3 Semantic Classification + Label-Value Pairing
- 3.4 Hierarchy Builder: valid tree structure
- Contract 3.3 JSON Schema validation
- Parallelism (3.1 + 3.2 in parallel)
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jsonschema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_stage3():
    import services.stages.stage3_structural_analysis as mod
    return mod


async def _noop_emit(event: Dict[str, Any]) -> None:
    """No-op progress emitter for tests."""
    pass


def _make_block(
    block_id: str,
    text: str,
    bbox: List[float],
    font_size: float = 10.0,
    is_bold: bool = False,
    color: str = "#000000",
) -> Dict[str, Any]:
    return {
        "id": block_id,
        "text": text,
        "bbox": bbox,
        "font_name": "Helvetica-Bold" if is_bold else "Helvetica",
        "font_size": font_size,
        "is_bold": is_bold,
        "is_italic": False,
        "is_mono": False,
        "color": color,
        "sub_spans": None,
    }


def _make_cluster(
    cluster_id: str,
    pages: List[Dict[str, Any]],
    rep_pdf_id: str = "pdf-1",
    rep_page_index: int = 0,
) -> Dict[str, Any]:
    return {
        "cluster_id": cluster_id,
        "pages": pages,
        "representative_page": {"pdf_id": rep_pdf_id, "page_index": rep_page_index},
        "page_count": len(pages),
    }


def _make_enriched_doc(
    pdf_id: str,
    pages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "pdf_id": pdf_id,
        "pdf_name": f"{pdf_id}.pdf",
        "pages": pages,
    }


def _make_page(
    page_index: int,
    cluster_id: str,
    is_representative: bool,
    text_blocks: List[Dict[str, Any]],
    width: float = 595.0,
    height: float = 842.0,
    images: List[Dict[str, Any]] | None = None,
    tables: List[Dict[str, Any]] | None = None,
    drawn_elements: Dict[str, Any] | None = None,
    grid_info: Dict[str, Any] | None = None,
    screenshot_path: str | None = None,
) -> Dict[str, Any]:
    return {
        "page_index": page_index,
        "cluster_id": cluster_id,
        "is_representative": is_representative,
        "width": width,
        "height": height,
        "text_blocks": text_blocks,
        "images": images or [],
        "fonts": [],
        "grid_info": grid_info,
        "screenshot_path": screenshot_path,
        "tables": tables or [],
        "drawn_elements": drawn_elements,
    }


def _make_raw_text_blocks(
    pdf_id: str,
    page_index: int,
    blocks: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    page_key = f"{pdf_id}:{page_index}"
    return {page_key: blocks}


def _raw_block(text: str, x_center: float, y_center: float) -> Dict[str, Any]:
    return {
        "text": text,
        "bbox_norm": [x_center - 0.05, y_center - 0.01, x_center + 0.05, y_center + 0.01],
        "x_center": x_center,
        "y_center": y_center,
        "type": 0,
    }


def _load_contract_schema() -> Dict[str, Any]:
    schema_path = Path(__file__).parent / "schemas" / "contract_3_3.json"
    with open(schema_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test: 3.1 — CPF classified as dynamic via regex
# ---------------------------------------------------------------------------


class TestMultiExampleAnalysis:
    """Tests for sub-step 3.1."""

    def test_cpf_classified_dynamic_regex(self):
        """Block with CPF pattern is classified as dynamic via regex override."""
        mod = _get_stage3()

        clusters = [_make_cluster("A", [
            {"pdf_id": "pdf-1", "page_index": 0},
        ])]
        raw_text_blocks = {
            "pdf-1:0": [
                _raw_block("123.456.789-00", 0.5, 0.3),
                _raw_block("Nome:", 0.2, 0.2),
            ],
        }

        result = mod._run_3_1(clusters, raw_text_blocks)

        assert "A" in result
        classifications = result["A"]["classifications"]
        cpf_block = next(
            (c for c in classifications if "123.456.789-00" in c.get("sample_texts", [])),
            None,
        )
        assert cpf_block is not None
        # Single PDF: statistical says label, but regex override -> likely_dynamic
        assert cpf_block["classification"] in ("likely_dynamic", "dynamic")

    def test_ner_detects_person_name(self):
        """spaCy NER detects 'Joao Silva' as PER -> dynamic."""
        mod = _get_stage3()

        # Mock spaCy NER
        mock_ent = MagicMock()
        mock_ent.label_ = "PER"
        mock_ent.text = "João Silva"

        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent]

        mock_nlp = MagicMock(return_value=mock_doc)

        # Patch the global _nlp
        original_nlp = mod._nlp
        mod._nlp = mock_nlp

        try:
            clusters = [_make_cluster("A", [
                {"pdf_id": "pdf-1", "page_index": 0},
            ])]
            raw_text_blocks = {
                "pdf-1:0": [
                    _raw_block("João Silva", 0.5, 0.3),
                ],
            }

            result = mod._run_3_1(clusters, raw_text_blocks)
            classifications = result["A"]["classifications"]
            name_block = next(
                (c for c in classifications if "João Silva" in c.get("sample_texts", [])),
                None,
            )
            assert name_block is not None
            assert name_block["classification"] in ("likely_dynamic", "dynamic")
        finally:
            mod._nlp = original_nlp

    def test_multi_pdf_statistical_variation(self):
        """Text that varies between PDFs is classified as dynamic statistically."""
        mod = _get_stage3()

        # Disable smart override for this test by mocking _nlp to return no entities
        original_nlp = mod._nlp
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_nlp.return_value = mock_doc
        mod._nlp = mock_nlp

        try:
            clusters = [_make_cluster("A", [
                {"pdf_id": "pdf-1", "page_index": 0},
                {"pdf_id": "pdf-2", "page_index": 0},
            ])]
            raw_text_blocks = {
                "pdf-1:0": [
                    _raw_block("Company ABC", 0.5, 0.1),
                    _raw_block("Header Text", 0.5, 0.05),
                ],
                "pdf-2:0": [
                    _raw_block("Company XYZ", 0.5, 0.1),
                    _raw_block("Header Text", 0.5, 0.05),
                ],
            }

            result = mod._run_3_1(clusters, raw_text_blocks)
            classifications = result["A"]["classifications"]

            # "Header Text" is same in both PDFs -> label
            header = next(
                (c for c in classifications if "Header Text" in c.get("sample_texts", [])),
                None,
            )
            assert header is not None
            assert header["classification"] == "label"

            # "Company ABC"/"Company XYZ" varies -> dynamic
            company = next(
                (c for c in classifications
                 if "Company ABC" in c.get("sample_texts", [])
                 or "Company XYZ" in c.get("sample_texts", [])),
                None,
            )
            assert company is not None
            assert company["classification"] == "dynamic"
        finally:
            mod._nlp = original_nlp

    def test_classification_quality(self):
        """classification_quality is produced correctly."""
        mod = _get_stage3()

        # Mock NLP
        original_nlp = mod._nlp
        mod._nlp = MagicMock(return_value=MagicMock(ents=[]))

        try:
            clusters = [_make_cluster("A", [
                {"pdf_id": "pdf-1", "page_index": 0},
            ])]
            raw_text_blocks = {
                "pdf-1:0": [_raw_block("Test", 0.5, 0.5)],
            }

            result = mod._run_3_1(clusters, raw_text_blocks)
            quality = result["A"]["classification_quality"]

            assert quality["total_pdfs"] == 1
            assert quality["statistical_strength"] == "none"  # single PDF
            assert "smart_override_count" in quality
            assert "uncertain_count" in quality
        finally:
            mod._nlp = original_nlp

    def test_skips_blank_scanned_clusters(self):
        """Clusters with _blank or _scanned IDs are skipped."""
        mod = _get_stage3()

        clusters = [
            _make_cluster("_blank", [{"pdf_id": "pdf-1", "page_index": 0}]),
            _make_cluster("_scanned", [{"pdf_id": "pdf-1", "page_index": 1}]),
        ]
        result = mod._run_3_1(clusters, {})
        assert "_blank" not in result
        assert "_scanned" not in result


# ---------------------------------------------------------------------------
# Test: 3.2 — Visual Analysis
# ---------------------------------------------------------------------------


class TestVisualAnalysis:
    """Tests for sub-step 3.2."""

    @pytest.mark.asyncio
    async def test_fallback_without_vision(self):
        """Without Vision AI, fallback produces threshold-based regions."""
        mod = _get_stage3()

        clusters = [_make_cluster("A", [{"pdf_id": "pdf-1", "page_index": 0}])]
        enriched_docs = [_make_enriched_doc("pdf-1", [
            _make_page(0, "A", True, [
                _make_block("b1", "Header", [50, 30, 200, 50]),
                _make_block("b2", "Content", [50, 300, 200, 320]),
            ]),
        ])]

        # No vision client, VISION_AI_ENABLED=false
        with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
            context: Dict[str, Any] = {}
            result = await mod._run_3_2(clusters, enriched_docs, context, _noop_emit)

        assert "pdf-1:0" in result
        va = result["pdf-1:0"]
        assert len(va["regions"]) >= 3  # header, body, footer
        assert va["consistency_score"] == 50  # fallback score

        # Check region types
        region_types = {r["type"] for r in va["regions"]}
        assert "header" in region_types
        assert "body" in region_types
        assert "footer" in region_types

    @pytest.mark.asyncio
    async def test_vision_call_mocked(self):
        """GPT-4o Vision call is mocked and parsed correctly."""
        mod = _get_stage3()

        mock_response = json.dumps({
            "regions": [
                {
                    "type": "header",
                    "bbox": [0, 0, 800, 100],
                    "description": "Company header",
                    "html_suggestion": "<header>Company</header>",
                },
                {
                    "type": "body",
                    "bbox": [0, 100, 800, 700],
                    "description": "Main content",
                    "html_suggestion": "<main>Content</main>",
                },
                {
                    "type": "footer",
                    "bbox": [0, 700, 800, 842],
                    "description": "Page number",
                    "html_suggestion": "<footer>1/1</footer>",
                },
            ],
            "consistency_score": 90,
            "consistency_notes": "Good alignment",
        })

        mock_client = AsyncMock()

        clusters = [_make_cluster("A", [{"pdf_id": "pdf-1", "page_index": 0}])]
        enriched_docs = [_make_enriched_doc("pdf-1", [
            _make_page(0, "A", True, [
                _make_block("b1", "Header", [50, 30, 200, 50]),
            ], screenshot_path="/tmp/test_screenshot.png"),
        ])]

        context: Dict[str, Any] = {"vision_client": mock_client}

        with patch("services.openrouter_client.load_image_as_base64", return_value="base64data"), \
             patch("services.openrouter_client.chat_with_vision", new_callable=AsyncMock, return_value=mock_response):
            result = await mod._run_3_2(clusters, enriched_docs, context, _noop_emit)

        va = result["pdf-1:0"]
        assert va["consistency_score"] == 90
        assert len(va["regions"]) == 3
        assert va["regions"][0]["type"] == "header"
        assert va["regions"][0]["html_suggestion"] == "<header>Company</header>"

    def test_parse_visual_response_invalid_json(self):
        """Invalid JSON returns empty fallback."""
        mod = _get_stage3()
        result = mod._parse_visual_response("not json")
        assert result["regions"] == []
        assert result["consistency_score"] == 0

    def test_parse_visual_response_with_fences(self):
        """JSON wrapped in markdown fences is handled."""
        mod = _get_stage3()
        raw = '```json\n{"regions": [{"type": "body", "bbox": [0,0,100,100]}], "consistency_score": 75}\n```'
        result = mod._parse_visual_response(raw)
        assert len(result["regions"]) == 1
        assert result["consistency_score"] == 75

    def test_parse_visual_response_handles_list_response(self):
        """_parse_visual_response deve tratar lista JSON como array de regiões."""
        mod = _get_stage3()
        raw = '[{"type": "header", "bbox": [0, 0, 595, 80], "description": "header", "html_suggestion": ""}]'
        result = mod._parse_visual_response(raw)
        assert len(result["regions"]) == 1
        assert result["regions"][0]["type"] == "header"
        assert result["regions"][0]["bbox"] == [0, 0, 595, 80]
        assert result["consistency_score"] == 0
        assert result["consistency_notes"] == "auto_wrapped"

    def test_fallback_visual_analysis(self):
        """Fallback produces header/body/footer with adaptive thresholds."""
        mod = _get_stage3()
        page_data = {"height": 842.0, "width": 595.0}
        result = mod._fallback_visual_analysis(page_data)

        assert len(result["regions"]) == 3
        types = [r["type"] for r in result["regions"]]
        assert types == ["header", "body", "footer"]

        # Header is top 10%
        header = result["regions"][0]
        assert header["bbox"][3] == int(842.0 * 0.10)


# ---------------------------------------------------------------------------
# Test: 3.3 — Label-Value Pairing
# ---------------------------------------------------------------------------


class TestSemanticClassification:
    """Tests for sub-step 3.3."""

    def test_label_value_pairing(self):
        """'Nome:' above 'Joao Silva' pairs as field."""
        mod = _get_stage3()

        # Mock NLP
        original_nlp = mod._nlp
        mod._nlp = MagicMock(return_value=MagicMock(ents=[]))

        try:
            clusters = [_make_cluster("A", [{"pdf_id": "pdf-1", "page_index": 0}])]

            # Create blocks: "Nome:" as label, "João Silva" to the right
            blocks = [
                _make_block("lbl-1", "Nome:", [50, 200, 120, 215]),
                _make_block("val-1", "João Silva", [130, 200, 300, 215]),
                _make_block("lbl-2", "Data:", [50, 250, 120, 265]),
                _make_block("val-2", "15/03/2026", [130, 250, 300, 265]),
            ]

            enriched_docs = [_make_enriched_doc("pdf-1", [
                _make_page(0, "A", True, blocks),
            ])]

            # Position classifications from 3.1
            pos_class = {
                "A": {
                    "classifications": [
                        {
                            "position": [0.14, 0.25],
                            "classification": "label",
                            "confidence": 1.0,
                            "stability": "stable",
                            "variant": "required",
                            "presence_ratio": 1.0,
                            "pdf_coverage": 1.0,
                        },
                        {
                            "position": [0.36, 0.25],
                            "classification": "dynamic",
                            "confidence": 0.95,
                            "stability": "variable",
                            "variant": "required",
                            "presence_ratio": 1.0,
                            "pdf_coverage": 1.0,
                        },
                        {
                            "position": [0.14, 0.31],
                            "classification": "label",
                            "confidence": 1.0,
                            "stability": "stable",
                            "variant": "required",
                            "presence_ratio": 1.0,
                            "pdf_coverage": 1.0,
                        },
                        {
                            "position": [0.36, 0.31],
                            "classification": "dynamic",
                            "confidence": 0.95,
                            "stability": "variable",
                            "variant": "required",
                            "presence_ratio": 1.0,
                            "pdf_coverage": 1.0,
                        },
                    ],
                    "classification_quality": {
                        "total_pdfs": 1,
                        "total_pages_in_cluster": 1,
                        "statistical_strength": "none",
                        "smart_override_count": 0,
                        "uncertain_count": 0,
                    },
                },
            }

            visual_analysis: Dict[str, Dict[str, Any]] = {}

            block_cls, lv_pairs = mod._run_3_3(
                enriched_docs, pos_class, visual_analysis, clusters
            )

            # Check that pairs were created
            assert len(lv_pairs) >= 1

            # Check field_pair links
            has_nome_pair = any(
                p["label_block_id"] == "lbl-1" and p["value_block_id"] == "val-1"
                for p in lv_pairs
            )
            assert has_nome_pair
        finally:
            mod._nlp = original_nlp


# ---------------------------------------------------------------------------
# Test: 3.4 — Hierarchy Builder
# ---------------------------------------------------------------------------


class TestHierarchyBuilder:
    """Tests for sub-step 3.4."""

    def test_produces_valid_tree(self):
        """Hierarchy builder produces valid document > page > zone > section tree."""
        mod = _get_stage3()

        clusters = [_make_cluster("A", [{"pdf_id": "pdf-1", "page_index": 0}])]

        blocks = [
            _make_block("b1", "Header Text", [50, 30, 200, 50]),
            _make_block("b2", "Nome:", [50, 200, 120, 215]),
            _make_block("b3", "João Silva", [130, 200, 300, 215]),
            _make_block("b4", "Page 1", [250, 800, 350, 815]),
        ]

        enriched_docs = [_make_enriched_doc("pdf-1", [
            _make_page(0, "A", True, blocks),
        ])]

        block_classifications = {
            "b1": {"semantic": "label", "stability": "stable", "variant": "required",
                   "confidence": 1.0, "presence_ratio": 1.0, "pdf_coverage": 1.0,
                   "field_pair": None, "smart_signals": None},
            "b2": {"semantic": "label", "stability": "stable", "variant": "required",
                   "confidence": 1.0, "presence_ratio": 1.0, "pdf_coverage": 1.0,
                   "field_pair": "b3", "smart_signals": None},
            "b3": {"semantic": "dynamic", "stability": "variable", "variant": "required",
                   "confidence": 0.95, "presence_ratio": 1.0, "pdf_coverage": 1.0,
                   "field_pair": "b2", "smart_signals": None},
            "b4": {"semantic": "label", "stability": "stable", "variant": "required",
                   "confidence": 1.0, "presence_ratio": 1.0, "pdf_coverage": 1.0,
                   "field_pair": None, "smart_signals": None},
        }

        visual_analysis = {
            "pdf-1:0": {
                "regions": [
                    {"type": "header", "bbox": [0, 0, 595, 84], "description": "Header",
                     "html_suggestion": "<header></header>", "chart_type": None,
                     "barcode_format": None, "confidence": None},
                    {"type": "body", "bbox": [0, 84, 595, 758], "description": "Body",
                     "html_suggestion": "<main></main>", "chart_type": None,
                     "barcode_format": None, "confidence": None},
                    {"type": "footer", "bbox": [0, 758, 595, 842], "description": "Footer",
                     "html_suggestion": "<footer></footer>", "chart_type": None,
                     "barcode_format": None, "confidence": None},
                ],
                "consistency_score": 85,
                "consistency_notes": "",
            }
        }

        pos_class = {"A": {"classifications": [], "classification_quality": {
            "total_pdfs": 1, "total_pages_in_cluster": 1,
            "statistical_strength": "none", "smart_override_count": 0, "uncertain_count": 0,
        }}}

        trees = mod._run_3_4(
            enriched_docs, block_classifications, visual_analysis, clusters, pos_class
        )

        assert len(trees) == 1
        tree_entry = trees[0]
        assert tree_entry["cluster_id"] == "A"
        assert tree_entry["representative_page"]["pdf_id"] == "pdf-1"

        tree = tree_entry["tree"]
        assert tree["type"] == "document"
        assert len(tree["children"]) == 1  # 1 page

        page_node = tree["children"][0]
        assert page_node["type"] == "page"
        assert len(page_node["children"]) >= 1  # at least 1 zone

        # Check zone types
        zone_types = [z["type"] for z in page_node["children"]]
        assert "header" in zone_types or "flow" in zone_types

        # Check field node with label+value pair
        found_field = False
        for zone in page_node["children"]:
            for section in zone.get("children", []):
                for child in section.get("children", []):
                    if child.get("type") == "field":
                        found_field = True
                        assert len(child["children"]) == 2
                        assert child["children"][0]["type"] == "label"
                        assert child["children"][1]["type"] == "value"
        assert found_field

    def test_fallback_zones_without_vision(self):
        """Without visual analysis, threshold-based zones are used."""
        mod = _get_stage3()

        clusters = [_make_cluster("A", [{"pdf_id": "pdf-1", "page_index": 0}])]
        blocks = [
            _make_block("b1", "Content", [50, 400, 200, 420]),
        ]
        enriched_docs = [_make_enriched_doc("pdf-1", [
            _make_page(0, "A", True, blocks),
        ])]
        block_cls = {
            "b1": {"semantic": "label", "stability": "stable", "variant": "required",
                   "confidence": 1.0, "presence_ratio": 1.0, "pdf_coverage": 1.0,
                   "field_pair": None, "smart_signals": None},
        }

        # Empty visual analysis
        trees = mod._run_3_4(enriched_docs, block_cls, {}, clusters, {})

        assert len(trees) == 1
        tree = trees[0]["tree"]
        page_node = tree["children"][0]

        # Check source is "threshold"
        for zone in page_node["children"]:
            assert zone.get("source") in ("threshold", "visual")


# ---------------------------------------------------------------------------
# Test: Contract 3.3 JSON Schema Validation
# ---------------------------------------------------------------------------


class TestContract33:
    """Validate output against contract 3.3 JSON Schema."""

    def test_contract_3_3_schema(self):
        """Output matches the contract 3.3 JSON Schema."""
        schema = _load_contract_schema()

        output = {
            "document_trees": {
                "A": {
                    "id": "root-A",
                    "type": "document",
                    "children": [{
                        "type": "page",
                        "children": [{
                            "type": "flow",
                            "source": "threshold",
                            "children": [{
                                "type": "section",
                                "variant": "required",
                                "children": [{
                                    "type": "field",
                                    "variant": "required",
                                    "children": [
                                        {"type": "label", "block_id": "b1", "text": "Nome:"},
                                        {"type": "value", "block_id": "b2", "text": "João"},
                                    ],
                                }],
                            }],
                        }],
                    }],
                },
            },
            "intelligence": {
                "A": {
                    "block_classifications": {
                        "b1": {
                            "semantic": "label",
                            "stability": "stable",
                            "variant": "required",
                            "presence_ratio": 1.0,
                            "pdf_coverage": 1.0,
                            "confidence": 1.0,
                            "field_pair": "b2",
                            "smart_signals": None,
                        },
                        "b2": {
                            "semantic": "dynamic",
                            "stability": "variable",
                            "variant": "required",
                            "presence_ratio": 1.0,
                            "pdf_coverage": 1.0,
                            "confidence": 0.95,
                            "field_pair": "b1",
                            "smart_signals": None,
                        },
                    },
                    "labels": ["b1"],
                    "dynamic_fields": ["b2"],
                    "optional_fields": [],
                    "conditional_fields": [],
                    "classification_quality": {
                        "total_pdfs": 1,
                        "total_pages_in_cluster": 1,
                        "statistical_strength": "none",
                        "smart_override_count": 0,
                        "uncertain_count": 0,
                    },
                },
            },
        }

        # Should not raise
        jsonschema.validate(instance=output, schema=schema)


# ---------------------------------------------------------------------------
# Test: Full Stage 3 integration (run_stage3)
# ---------------------------------------------------------------------------


class TestRunStage3:
    """Integration tests for the full run_stage3 entry point."""

    @pytest.mark.asyncio
    async def test_full_stage3_produces_context(self):
        """run_stage3 produces document_trees and intelligence in context."""
        mod = _get_stage3()

        # Mock NLP to avoid spaCy dependency
        original_nlp = mod._nlp
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_nlp.return_value = mock_doc
        mod._nlp = mock_nlp

        try:
            blocks = [
                _make_block("b1", "Nome:", [50, 200, 120, 215]),
                _make_block("b2", "João Silva", [130, 200, 300, 215]),
                _make_block("b3", "CPF:", [50, 250, 120, 265]),
                _make_block("b4", "123.456.789-00", [130, 250, 300, 265]),
            ]

            context: Dict[str, Any] = {
                "clusters": [
                    _make_cluster("A", [
                        {"pdf_id": "pdf-1", "page_index": 0},
                    ]),
                ],
                "_raw_text_blocks": {
                    "pdf-1:0": [
                        _raw_block("Nome:", 0.14, 0.25),
                        _raw_block("João Silva", 0.36, 0.25),
                        _raw_block("CPF:", 0.14, 0.31),
                        _raw_block("123.456.789-00", 0.36, 0.31),
                    ],
                },
                "enriched_documents": [_make_enriched_doc("pdf-1", [
                    _make_page(0, "A", True, blocks),
                ])],
            }

            with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
                result = await mod.run_stage3(context, _noop_emit)

            assert "document_trees" in result
            assert "intelligence" in result
            assert "visual_analysis" in result

            # Validate against schema
            schema = _load_contract_schema()
            contract_output = {
                "document_trees": result["document_trees"],
                "intelligence": result["intelligence"],
            }
            jsonschema.validate(instance=contract_output, schema=schema)

            # Check that trees were built (document_trees is now Dict[cluster_id, tree])
            assert len(result["document_trees"]) == 1
            assert "A" in result["document_trees"]

            # Check intelligence
            assert "A" in result["intelligence"]
            intel = result["intelligence"]["A"]
            assert "block_classifications" in intel
            assert "classification_quality" in intel

        finally:
            mod._nlp = original_nlp

    @pytest.mark.asyncio
    async def test_empty_clusters(self):
        """run_stage3 handles empty clusters gracefully."""
        mod = _get_stage3()

        context: Dict[str, Any] = {
            "clusters": [],
            "_raw_text_blocks": {},
            "enriched_documents": [],
        }

        with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
            result = await mod.run_stage3(context, _noop_emit)

        assert result["document_trees"] == {}
        assert result["intelligence"] == {}


# ---------------------------------------------------------------------------
# Test: Smart classify
# ---------------------------------------------------------------------------


class TestSmartClassify:
    """Tests for _smart_classify helper."""

    def test_label_with_colon(self):
        """Text ending with ':' is classified as label."""
        mod = _get_stage3()
        original_nlp = mod._nlp
        mod._nlp = MagicMock(return_value=MagicMock(ents=[]))
        try:
            is_dyn, score, signals = mod._smart_classify("Nome:")
            assert is_dyn is False
            assert score <= 0.3
        finally:
            mod._nlp = original_nlp

    def test_cpf_detected_as_dynamic(self):
        """CPF pattern is detected as dynamic."""
        mod = _get_stage3()
        original_nlp = mod._nlp
        mod._nlp = MagicMock(return_value=MagicMock(ents=[]))
        try:
            is_dyn, score, signals = mod._smart_classify("123.456.789-00")
            assert is_dyn is True
            signal_names = [s[0] for s in signals]
            assert "regex_cpf" in signal_names
        finally:
            mod._nlp = original_nlp

    def test_currency_detected_as_dynamic(self):
        """Currency pattern is detected as dynamic."""
        mod = _get_stage3()
        original_nlp = mod._nlp
        mod._nlp = MagicMock(return_value=MagicMock(ents=[]))
        try:
            is_dyn, score, signals = mod._smart_classify("R$ 1.234,56")
            assert is_dyn is True
            signal_names = [s[0] for s in signals]
            assert "regex_currency" in signal_names
        finally:
            mod._nlp = original_nlp


# ---------------------------------------------------------------------------
# Test: Story 15.14 — context["layout_types"] populated after run_stage3
# ---------------------------------------------------------------------------


class TestLayoutTypesPopulated:
    """Story 15.14: run_stage3 must write context['layout_types'] for Stage 5."""

    @pytest.mark.asyncio
    async def test_layout_types_populated_from_clusters(self):
        """run_stage3 derives layout_types from clusters and writes to context."""
        mod = _get_stage3()

        original_nlp = mod._nlp
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_nlp.return_value = mock_doc
        mod._nlp = mock_nlp

        try:
            blocks = [
                _make_block("b1", "Nome:", [50, 200, 120, 215]),
                _make_block("b2", "João Silva", [130, 200, 300, 215]),
            ]

            context: Dict[str, Any] = {
                "clusters": [
                    _make_cluster("layout-A", [{"pdf_id": "pdf-1", "page_index": 0}]),
                    _make_cluster("layout-B", [{"pdf_id": "pdf-1", "page_index": 1}]),
                    # Special clusters must be excluded
                    _make_cluster("_blank", [{"pdf_id": "pdf-1", "page_index": 2}]),
                ],
                "_raw_text_blocks": {},
                "enriched_documents": [
                    _make_enriched_doc("pdf-1", [
                        _make_page(0, "layout-A", True, blocks, width=595.0, height=842.0),
                        _make_page(1, "layout-B", True, blocks, width=612.0, height=792.0),
                    ])
                ],
            }

            with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
                result = await mod.run_stage3(context, _noop_emit)

            # AC1: layout_types must be written (not empty)
            assert "layout_types" in result, "context['layout_types'] must be set by run_stage3"
            layout_types = result["layout_types"]
            assert len(layout_types) == 2, (
                f"Expected 2 layout_types (excluding _blank), got {len(layout_types)}"
            )

            # AC2: each item has required fields for Stage 5
            ids = {lt["id"] for lt in layout_types}
            assert "layout-A" in ids
            assert "layout-B" in ids

            lt_a = next(lt for lt in layout_types if lt["id"] == "layout-A")
            assert lt_a["page_width_pts"] == 595.0
            assert lt_a["page_height_pts"] == 842.0

            lt_b = next(lt for lt in layout_types if lt["id"] == "layout-B")
            assert lt_b["page_width_pts"] == 612.0
            assert lt_b["page_height_pts"] == 792.0

        finally:
            mod._nlp = original_nlp

    @pytest.mark.asyncio
    async def test_layout_types_excludes_special_clusters(self):
        """layout_types must not include _blank or _scanned clusters."""
        mod = _get_stage3()

        original_nlp = mod._nlp
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_nlp.return_value = mock_doc
        mod._nlp = mock_nlp

        try:
            context: Dict[str, Any] = {
                "clusters": [
                    _make_cluster("_blank", [{"pdf_id": "pdf-1", "page_index": 0}]),
                    _make_cluster("_scanned", [{"pdf_id": "pdf-1", "page_index": 1}]),
                ],
                "_raw_text_blocks": {},
                "enriched_documents": [],
            }

            with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
                result = await mod.run_stage3(context, _noop_emit)

            assert result.get("layout_types", []) == [], (
                "layout_types must be empty when only special clusters exist"
            )

        finally:
            mod._nlp = original_nlp
