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

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jsonschema
import pytest

from models.pipeline_context import BlockClassification

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bc(**kwargs) -> BlockClassification:
    """Create a BlockClassification for tests. Defaults: semantic='label', variant='required'."""
    defaults: dict[str, Any] = {
        "semantic": "label",
        "stability": "stable",
        "variant": "required",
        "confidence": 1.0,
        "presence_ratio": 1.0,
        "pdf_coverage": 1.0,
        "field_pair": None,
        "smart_signals": None,
    }
    defaults.update(kwargs)
    return BlockClassification(**defaults)


def _get_stage3():
    import services.stages.stage3_structural_analysis as mod

    return mod


async def _noop_emit(event: dict[str, Any]) -> None:
    """No-op progress emitter for tests."""
    pass


def _make_block(
    block_id: str,
    text: str,
    bbox: list[float],
    font_size: float = 10.0,
    is_bold: bool = False,
    color: str = "#000000",
) -> dict[str, Any]:
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
    pages: list[dict[str, Any]],
    rep_pdf_id: str = "pdf-1",
    rep_page_index: int = 0,
) -> dict[str, Any]:
    return {
        "cluster_id": cluster_id,
        "pages": pages,
        "representative_page": {"pdf_id": rep_pdf_id, "page_index": rep_page_index},
        "page_count": len(pages),
    }


def _make_enriched_doc(
    pdf_id: str,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "pdf_id": pdf_id,
        "pdf_name": f"{pdf_id}.pdf",
        "pages": pages,
    }


def _make_page(
    page_index: int,
    cluster_id: str,
    is_representative: bool,
    text_blocks: list[dict[str, Any]],
    width: float = 595.0,
    height: float = 842.0,
    images: list[dict[str, Any]] | None = None,
    tables: list[dict[str, Any]] | None = None,
    drawn_elements: dict[str, Any] | None = None,
    grid_info: dict[str, Any] | None = None,
    screenshot_path: str | None = None,
) -> dict[str, Any]:
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
    blocks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    page_key = f"{pdf_id}:{page_index}"
    return {page_key: blocks}


def _raw_block(text: str, x_center: float, y_center: float) -> dict[str, Any]:
    return {
        "text": text,
        "bbox_norm": [x_center - 0.05, y_center - 0.01, x_center + 0.05, y_center + 0.01],
        "x_center": x_center,
        "y_center": y_center,
        "type": 0,
    }


def _load_contract_schema() -> dict[str, Any]:
    schema_path = Path(__file__).parent / "schemas" / "contract_3_3.json"
    with open(schema_path) as f:
        data: dict[str, Any] = json.load(f)
        return data


# ---------------------------------------------------------------------------
# Test: 3.1 — CPF classified as dynamic via regex
# ---------------------------------------------------------------------------


class TestMultiExampleAnalysis:
    """Tests for sub-step 3.1."""

    def test_cpf_classified_dynamic_regex(self):
        """Block with CPF pattern is classified as dynamic via regex override."""
        mod = _get_stage3()

        clusters = [
            _make_cluster(
                "A",
                [
                    {"pdf_id": "pdf-1", "page_index": 0},
                ],
            )
        ]
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
            clusters = [
                _make_cluster(
                    "A",
                    [
                        {"pdf_id": "pdf-1", "page_index": 0},
                    ],
                )
            ]
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
            clusters = [
                _make_cluster(
                    "A",
                    [
                        {"pdf_id": "pdf-1", "page_index": 0},
                        {"pdf_id": "pdf-2", "page_index": 0},
                    ],
                )
            ]
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
                (
                    c
                    for c in classifications
                    if "Company ABC" in c.get("sample_texts", []) or "Company XYZ" in c.get("sample_texts", [])
                ),
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
            clusters = [
                _make_cluster(
                    "A",
                    [
                        {"pdf_id": "pdf-1", "page_index": 0},
                    ],
                )
            ]
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
        enriched_docs = [
            _make_enriched_doc(
                "pdf-1",
                [
                    _make_page(
                        0,
                        "A",
                        True,
                        [
                            _make_block("b1", "Header", [50, 30, 200, 50]),
                            _make_block("b2", "Content", [50, 300, 200, 320]),
                        ],
                    ),
                ],
            )
        ]

        # No vision client, VISION_AI_ENABLED=false
        with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
            context: dict[str, Any] = {}
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

        mock_response = json.dumps(
            {
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
            }
        )

        mock_client = AsyncMock()

        clusters = [_make_cluster("A", [{"pdf_id": "pdf-1", "page_index": 0}])]
        enriched_docs = [
            _make_enriched_doc(
                "pdf-1",
                [
                    _make_page(
                        0,
                        "A",
                        True,
                        [
                            _make_block("b1", "Header", [50, 30, 200, 50]),
                        ],
                        screenshot_path="/tmp/test_screenshot.png",
                    ),
                ],
            )
        ]

        context: dict[str, Any] = {"vision_client": mock_client}

        with (
            patch("services.openrouter_client.load_image_as_base64", return_value="base64data"),
            patch(
                "services.openrouter_client.chat_with_vision",
                new_callable=AsyncMock,
                return_value=(mock_response, 0.025),
            ),
        ):
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

    def test_summarize_extraction_includes_vertical_lines(self):
        """_summarize_extraction must count vertical lines from list-format drawn_elements.

        Root cause fix: drawn_elements is list[dict], not dict. The old isinstance(drawn, dict)
        check always failed → GPT-4o never received line context → barcode/table misclassification.
        """
        mod = _get_stage3()

        drawn_elements = [
            {"type": "line", "orientation": "horizontal", "bbox": [0, 10, 100, 10]},
            {"type": "line", "orientation": "horizontal", "bbox": [0, 50, 100, 50]},
            {"type": "line", "orientation": "vertical", "bbox": [10, 0, 10, 200]},
            {"type": "line", "orientation": "vertical", "bbox": [20, 0, 20, 200]},
            {"type": "line", "orientation": "vertical", "bbox": [30, 0, 30, 200]},
            {"type": "rect", "bbox": [0, 0, 100, 100]},  # rect should not be counted
        ]

        page_data = {
            "text_blocks": [{"text": "A"}, {"text": "B"}],
            "tables": [],
            "images": [],
            "drawn_elements": drawn_elements,
        }

        summary = mod._summarize_extraction(page_data)

        assert "Horizontal lines: 2" in summary
        assert "Vertical lines: 3" in summary
        assert "barcode" in summary.lower()  # hint for GPT-4o

    def test_summarize_extraction_no_drawn_elements(self):
        """_summarize_extraction handles None drawn_elements gracefully."""
        mod = _get_stage3()

        page_data = {
            "text_blocks": [{"text": "A"}],
            "tables": [{"rows": 2}],
            "images": [],
            "drawn_elements": None,
        }

        summary = mod._summarize_extraction(page_data)

        assert "Text blocks: 1" in summary
        assert "Tables: 1" in summary
        assert "lines" not in summary.lower()

    def test_summarize_extraction_legacy_dict_ignored(self):
        """_summarize_extraction silently ignores if drawn_elements is a dict (legacy format)."""
        mod = _get_stage3()

        page_data = {
            "text_blocks": [],
            "tables": [],
            "images": [],
            "drawn_elements": {"horizontal_lines": [1, 2, 3]},  # legacy dict format
        }

        summary = mod._summarize_extraction(page_data)
        # dict format is not a list, so no line info — no crash
        assert "Text blocks: 0" in summary
        assert "lines" not in summary.lower()


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

            enriched_docs = [
                _make_enriched_doc(
                    "pdf-1",
                    [
                        _make_page(0, "A", True, blocks),
                    ],
                )
            ]

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

            visual_analysis: dict[str, dict[str, Any]] = {}

            block_cls, lv_pairs = mod._run_3_3(enriched_docs, pos_class, visual_analysis, clusters)

            # Check that pairs were created
            assert len(lv_pairs) >= 1

            # Check field_pair links
            has_nome_pair = any(p["label_block_id"] == "lbl-1" and p["value_block_id"] == "val-1" for p in lv_pairs)
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

        enriched_docs = [
            _make_enriched_doc(
                "pdf-1",
                [
                    _make_page(0, "A", True, blocks),
                ],
            )
        ]

        block_classifications = {
            "b1": _bc(),
            "b2": _bc(field_pair="b3"),
            "b3": _bc(semantic="dynamic", stability="variable", confidence=0.95, field_pair="b2"),
            "b4": _bc(),
        }

        visual_analysis = {
            "pdf-1:0": {
                "regions": [
                    {
                        "type": "header",
                        "bbox": [0, 0, 595, 84],
                        "description": "Header",
                        "html_suggestion": "<header></header>",
                        "chart_type": None,
                        "barcode_format": None,
                        "confidence": None,
                    },
                    {
                        "type": "body",
                        "bbox": [0, 84, 595, 758],
                        "description": "Body",
                        "html_suggestion": "<main></main>",
                        "chart_type": None,
                        "barcode_format": None,
                        "confidence": None,
                    },
                    {
                        "type": "footer",
                        "bbox": [0, 758, 595, 842],
                        "description": "Footer",
                        "html_suggestion": "<footer></footer>",
                        "chart_type": None,
                        "barcode_format": None,
                        "confidence": None,
                    },
                ],
                "consistency_score": 85,
                "consistency_notes": "",
            }
        }

        pos_class = {
            "A": {
                "classifications": [],
                "classification_quality": {
                    "total_pdfs": 1,
                    "total_pages_in_cluster": 1,
                    "statistical_strength": "none",
                    "smart_override_count": 0,
                    "uncertain_count": 0,
                },
            }
        }

        trees = mod._run_3_4(enriched_docs, block_classifications, visual_analysis, clusters, pos_class)

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
        enriched_docs = [
            _make_enriched_doc(
                "pdf-1",
                [
                    _make_page(0, "A", True, blocks),
                ],
            )
        ]
        block_cls = {
            "b1": _bc(),
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
                    "children": [
                        {
                            "type": "page",
                            "children": [
                                {
                                    "type": "flow",
                                    "source": "threshold",
                                    "children": [
                                        {
                                            "type": "section",
                                            "variant": "required",
                                            "children": [
                                                {
                                                    "type": "field",
                                                    "variant": "required",
                                                    "children": [
                                                        {"type": "label", "block_id": "b1", "text": "Nome:"},
                                                        {"type": "value", "block_id": "b2", "text": "João"},
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
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

            context: dict[str, Any] = {
                "clusters": [
                    _make_cluster(
                        "A",
                        [
                            {"pdf_id": "pdf-1", "page_index": 0},
                        ],
                    ),
                ],
                "_raw_text_blocks": {
                    "pdf-1:0": [
                        _raw_block("Nome:", 0.14, 0.25),
                        _raw_block("João Silva", 0.36, 0.25),
                        _raw_block("CPF:", 0.14, 0.31),
                        _raw_block("123.456.789-00", 0.36, 0.31),
                    ],
                },
                "enriched_documents": [
                    _make_enriched_doc(
                        "pdf-1",
                        [
                            _make_page(0, "A", True, blocks),
                        ],
                    )
                ],
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

        context: dict[str, Any] = {
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

            context: dict[str, Any] = {
                "clusters": [
                    _make_cluster("layout-A", [{"pdf_id": "pdf-1", "page_index": 0}]),
                    _make_cluster("layout-B", [{"pdf_id": "pdf-1", "page_index": 1}]),
                    # Special clusters must be excluded
                    _make_cluster("_blank", [{"pdf_id": "pdf-1", "page_index": 2}]),
                ],
                "_raw_text_blocks": {},
                "enriched_documents": [
                    _make_enriched_doc(
                        "pdf-1",
                        [
                            _make_page(0, "layout-A", True, blocks, width=595.0, height=842.0),
                            _make_page(1, "layout-B", True, blocks, width=612.0, height=792.0),
                        ],
                    )
                ],
            }

            with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
                result = await mod.run_stage3(context, _noop_emit)

            # AC1: layout_types must be written (not empty)
            assert "layout_types" in result, "context['layout_types'] must be set by run_stage3"
            layout_types = result["layout_types"]
            assert len(layout_types) == 2, f"Expected 2 layout_types (excluding _blank), got {len(layout_types)}"

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
            context: dict[str, Any] = {
                "clusters": [
                    _make_cluster("_blank", [{"pdf_id": "pdf-1", "page_index": 0}]),
                    _make_cluster("_scanned", [{"pdf_id": "pdf-1", "page_index": 1}]),
                ],
                "_raw_text_blocks": {},
                "enriched_documents": [],
            }

            with patch.dict(os.environ, {"VISION_AI_ENABLED": "false"}):
                result = await mod.run_stage3(context, _noop_emit)

            assert result.get("layout_types", []) == [], "layout_types must be empty when only special clusters exist"

        finally:
            mod._nlp = original_nlp


# ---------------------------------------------------------------------------
# Story 22.3 — TreeNode children contract
# ---------------------------------------------------------------------------


class TestTreeNodeChildrenContract:
    """Validates that every node produced by Stage 3 hierarchy builder
    includes the 'children' key — including leaf nodes (cell, image, chart, barcode).

    AC-2 and AC-3 from story 22.3.
    """

    def _assert_all_nodes_have_children(self, node: dict, path: str = "root") -> None:
        assert "children" in node, f"Nó sem 'children' em {path}: type={node.get('type')}, keys={list(node.keys())}"
        for i, child in enumerate(node["children"]):
            self._assert_all_nodes_have_children(child, f"{path}.children[{i}]")

    def test_cell_nodes_have_children(self):
        """cell nodes in header_row and data_row must have children: []."""
        mod = _get_stage3()

        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, 595, 842],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": [],
                        "tables": [
                            {
                                "table_id": "t1",
                                "headers": ["Col A", "Col B"],
                                "rows": [["val1", "val2"]],
                            }
                        ],
                        "images": [],
                        "charts": [],
                        "barcodes": [],
                    }
                ],
            }
        ]

        root = mod._build_tree("A", zones, {}, {"text_blocks": []})

        self._assert_all_nodes_have_children(root)

    def test_standalone_blocks_have_children(self):
        """Standalone semantic block nodes (label, value, unknown) must have children: [].

        AC-1 and AC-3 from story 14.16.
        """
        mod = _get_stage3()

        # Full block dicts (blocks list contains dicts with id/text/bbox)
        b1 = {"id": "b1", "text": "Some Label", "bbox": [50, 100, 200, 115]}
        b2 = {"id": "b2", "text": "Some Value", "bbox": [50, 130, 200, 145]}

        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, 595, 842],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": [b1, b2],  # full block dicts, no field_pair
                        "tables": [],
                        "images": [],
                        "charts": [],
                        "barcodes": [],
                    }
                ],
            }
        ]

        # block_classifications with no field_pair -> standalone blocks
        block_classifications = {
            "b1": _bc(semantic="label", variant="required"),
            "b2": _bc(semantic="value", variant="optional"),
        }

        text_blocks_page = {"text_blocks": [b1, b2]}

        root = mod._build_tree("A", zones, block_classifications, text_blocks_page)
        self._assert_all_nodes_have_children(root)

    def test_image_chart_barcode_nodes_have_children(self):
        """image, chart, barcode leaf nodes must have children: []."""
        mod = _get_stage3()

        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, 595, 842],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": [],
                        "tables": [],
                        "images": [
                            {"path": "img.png", "bbox": [10, 10, 100, 100], "bbox_valid": True, "format": "png"}
                        ],
                        "charts": [
                            {
                                "bbox": [10, 120, 200, 220],
                                "description": "Bar chart",
                                "chart_type": "bar",
                                "confidence": 80,
                            }
                        ],
                        "barcodes": [
                            {
                                "bbox": [10, 230, 100, 260],
                                "description": "Code128",
                                "barcode_format": "CODE128",
                                "confidence": 90,
                            }
                        ],
                    }
                ],
            }
        ]

        root = mod._build_tree("A", zones, {}, {"text_blocks": []})

        self._assert_all_nodes_have_children(root)


# ---------------------------------------------------------------------------
# Story 15.22 — Pipeline Warning Tests
# ---------------------------------------------------------------------------


class TestSpaCyWarning:
    """Validate that run_stage3 emits a spacy_unavailable warning when spaCy is not available."""

    @pytest.mark.asyncio
    async def test_spacy_unavailable_emits_warning(self):
        """When spaCy is unavailable, context should contain spacy_unavailable warning."""
        mod = _get_stage3()

        original_nlp = mod._nlp
        try:
            # Force sentinel: spaCy not available
            mod._nlp = False

            ctx: dict[str, Any] = {
                "clusters": [],
                "_raw_text_blocks": {},
                "enriched_documents": [],
            }

            await mod.run_stage3(ctx, _noop_emit)

            warnings = ctx.get("_pipeline_warnings", [])
            codes = [w["code"] for w in warnings if isinstance(w, dict)]
            assert "spacy_unavailable" in codes, f"Expected spacy_unavailable warning, got: {warnings}"

            # Verify structure
            spacy_warn = next(w for w in warnings if isinstance(w, dict) and w.get("code") == "spacy_unavailable")
            assert spacy_warn["severity"] == "info"
            assert spacy_warn["stage"] == 3
            assert "message" in spacy_warn

        finally:
            mod._nlp = original_nlp

    @pytest.mark.asyncio
    async def test_spacy_warning_not_duplicated_when_flag_set(self):
        """spacy_unavailable warning should not be added when _spacy_warning_emitted is True."""
        mod = _get_stage3()

        original_nlp = mod._nlp
        try:
            mod._nlp = False

            ctx: dict[str, Any] = {
                "clusters": [],
                "_raw_text_blocks": {},
                "enriched_documents": [],
                "_spacy_warning_emitted": True,  # Already emitted in this run
            }

            await mod.run_stage3(ctx, _noop_emit)

            warnings = ctx.get("_pipeline_warnings", [])
            spacy_warns = [w for w in warnings if isinstance(w, dict) and w.get("code") == "spacy_unavailable"]
            assert len(spacy_warns) == 0, "Should not emit spacy_unavailable when flag is already set"

        finally:
            mod._nlp = original_nlp


# ---------------------------------------------------------------------------
# Tests: Tree node visual property propagation (RCA fix)
# ---------------------------------------------------------------------------


class TestTreeNodeVisualProps:
    """Validates that bbox, is_bold and font_weight are preserved in tree nodes.

    Root cause fix: Stage 3 was dropping visual properties when building
    label/value/standalone nodes — Stage 5 had no data to apply positioning
    and bold formatting.
    """

    def _build_field_tree(self, block_id: str, text: str, bbox: list, is_bold: bool, font_weight: str):
        mod = _get_stage3()
        block = {
            "id": block_id,
            "text": text,
            "bbox": bbox,
            "is_bold": is_bold,
            "font_weight": font_weight,
        }
        value_id = block_id + "_val"
        value_block = {
            "id": value_id,
            "text": "valor",
            "bbox": [130, 200, 300, 215],
            "is_bold": False,
            "font_weight": "normal",
        }
        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, 595, 842],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": [block, value_block],
                        "tables": [],
                        "images": [],
                        "charts": [],
                        "barcodes": [],
                    }
                ],
            }
        ]
        block_classifications = {
            block_id: _bc(semantic="label", variant="required", field_pair=value_id),
            value_id: _bc(
                semantic="dynamic", stability="variable", confidence=0.95, variant="required", field_pair=block_id
            ),
        }
        text_blocks_page = {"text_blocks": [block, value_block]}
        return mod._build_tree("A", zones, block_classifications, text_blocks_page)

    def _find_nodes_by_type(self, node: dict, node_type: str) -> list:
        results = []
        if node.get("type") == node_type:
            results.append(node)
        for child in node.get("children", []):
            results.extend(self._find_nodes_by_type(child, node_type))
        return results

    def test_label_node_has_bbox(self):
        """label tree node must preserve bbox from original block."""
        tree = self._build_field_tree("b1", "Nome:", [50, 200, 120, 215], False, "normal")
        labels = self._find_nodes_by_type(tree, "label")
        assert labels, "Deve existir pelo menos um nó label na árvore"
        assert labels[0].get("bbox") == [50, 200, 120, 215], "label node deve preservar bbox do block original"

    def test_label_node_has_font_weight(self):
        """label tree node must preserve is_bold and font_weight from original block."""
        tree = self._build_field_tree("b2", "Empresa:", [50, 100, 200, 115], True, "bold")
        labels = self._find_nodes_by_type(tree, "label")
        assert labels, "Deve existir pelo menos um nó label na árvore"
        assert labels[0].get("is_bold") is True, "label node deve preservar is_bold=True"
        assert labels[0].get("font_weight") == "bold", "label node deve preservar font_weight='bold'"

    def test_standalone_node_has_bbox_and_font_weight(self):
        """Standalone (no field_pair) block node must preserve bbox and font_weight."""
        mod = _get_stage3()
        block = {
            "id": "b_stand",
            "text": "Texto standalone",
            "bbox": [10, 10, 200, 25],
            "is_bold": True,
            "font_weight": "bold",
        }
        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, 595, 842],
                "source": "threshold",
                "sections": [{"blocks": [block], "tables": [], "images": [], "charts": [], "barcodes": []}],
            }
        ]
        block_classifications = {
            "b_stand": _bc(semantic="label", variant="required"),
        }
        tree = mod._build_tree("A", zones, block_classifications, {"text_blocks": [block]})
        labels = self._find_nodes_by_type(tree, "label")
        assert labels, "Deve existir nó label standalone"
        node = labels[0]
        assert node.get("bbox") == [10, 10, 200, 25], "standalone node deve ter bbox"
        assert node.get("is_bold") is True, "standalone node deve ter is_bold=True"
        assert node.get("font_weight") == "bold", "standalone node deve ter font_weight='bold'"

    def test_label_node_has_color_font_size_font_name(self):
        """label tree node must preserve color, font_size and font_name from block."""
        tree = self._build_field_tree("b3", "Valor:", [50, 50, 150, 65], False, "normal")
        # Add color/font_size/font_name to the block via a direct build
        mod = _get_stage3()
        block = {
            "id": "b_color",
            "text": "Valor:",
            "bbox": [50, 50, 150, 65],
            "is_bold": False,
            "font_weight": "normal",
            "color": 255,
            "font_size": 10.0,
            "font_name": "Helvetica",
        }
        value_block = {
            "id": "b_color_val",
            "text": "R$ 100",
            "bbox": [160, 50, 300, 65],
            "is_bold": False,
            "font_weight": "normal",
            "color": 0,
            "font_size": 10.0,
            "font_name": "Helvetica",
        }
        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, 595, 842],
                "source": "threshold",
                "sections": [
                    {"blocks": [block, value_block], "tables": [], "images": [], "charts": [], "barcodes": []}
                ],
            }
        ]
        block_classifications = {
            "b_color": _bc(semantic="label", variant="required", field_pair="b_color_val"),
            "b_color_val": _bc(
                semantic="dynamic", stability="variable", confidence=0.95, variant="required", field_pair="b_color"
            ),
        }
        tree = mod._build_tree("A", zones, block_classifications, {"text_blocks": [block, value_block]})
        labels = self._find_nodes_by_type(tree, "label")
        assert labels, "Deve existir nó label"
        node = labels[0]
        assert node.get("color") == 255, "label node deve preservar color"
        assert node.get("font_size") == 10.0, "label node deve preservar font_size"
        assert node.get("font_name") == "Helvetica", "label node deve preservar font_name"

    def test_drawn_lines_both_orientations_added_to_tree(self):
        """Both horizontal AND vertical drawn_elements must appear as 'line' nodes.

        Fix for rca-2026-04-06-canvas-missing-images-barcode:
        Vertical lines (barcode stripes) were previously excluded from the tree by
        an orientation=='horizontal' filter, causing barcode visuals to disappear.
        """
        mod = _get_stage3()
        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, 595, 842],
                "source": "threshold",
                "sections": [{"blocks": [], "tables": [], "images": [], "charts": [], "barcodes": []}],
            }
        ]
        page_data = {
            "text_blocks": [],
            "drawn_elements": [
                {
                    "type": "line",
                    "orientation": "horizontal",
                    "bbox": [0, 400, 595, 401],
                    "stroke_color": 0,
                    "width": 1.0,
                },
                {
                    "type": "line",
                    "orientation": "vertical",
                    "bbox": [100, 0, 101, 842],
                    "stroke_color": 0,
                    "width": 1.0,
                },
            ],
        }
        tree = mod._build_tree("A", zones, {}, page_data)
        lines = self._find_nodes_by_type(tree, "line")
        assert len(lines) == 2, "Deve existir 2 nós line (horizontal + vertical)"
        orientations = {l.get("orientation") for l in lines}
        assert "horizontal" in orientations, "Linha horizontal deve estar na árvore"
        assert "vertical" in orientations, "Linha vertical (barcode stripe) deve estar na árvore"
        h_line = next(l for l in lines if l.get("orientation") == "horizontal")
        assert h_line.get("bbox") == [0, 400, 595, 401]
        assert h_line.get("stroke_color") == 0
        v_line = next(l for l in lines if l.get("orientation") == "vertical")
        assert v_line.get("bbox") == [100, 0, 101, 842]

    def test_barcode_bbox_normalized_from_screenshot_pixels_to_pdf_pts(self):
        """Barcode bboxes from GPT-4o vision (screenshot pixels) must be converted to PDF pts.

        Fix for rca-2026-04-06-canvas-missing-images-barcode:
        GPT-4o Vision returns bboxes in 150 DPI screenshot pixel coordinates.
        Without normalization, stage5 re-scales them as PDF pts, placing elements
        off-screen (e.g. left:908px on an 817px page).
        """
        mod = _get_stage3()
        # Screenshot at 150 DPI: scale = 150/72 = 2.0833 px/pt
        # For a page of 612x792pt, barcode at ~436pt from left = ~908 screenshot pixels
        screenshot_scale = 150.0 / 72.0
        page_w_pts = 612.0
        page_h_pts = 792.0
        raw_x0 = 908.0  # screenshot pixels (maps to ~436pt)
        raw_y0 = 1276.0  # screenshot pixels (maps to ~613pt)
        raw_x1 = 1288.0  # screenshot pixels (maps to ~618pt -> clamped to page_w_pts)
        raw_y1 = 1489.0  # screenshot pixels (maps to ~715pt)
        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, page_w_pts, page_h_pts],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": [],
                        "tables": [],
                        "images": [],
                        "charts": [],
                        "barcodes": [
                            {
                                "bbox": [raw_x0, raw_y0, raw_x1, raw_y1],
                                "description": "CODE128 barcode",
                                "barcode_format": "CODE128",
                                "confidence": 90,
                            }
                        ],
                    }
                ],
            }
        ]
        page_data = {"text_blocks": [], "width": page_w_pts, "height": page_h_pts}
        tree = mod._build_tree("A", zones, {}, page_data)
        barcodes = self._find_nodes_by_type(tree, "barcode")
        assert len(barcodes) == 1, "Deve existir 1 nó barcode"
        bbox = barcodes[0].get("bbox")
        assert bbox is not None
        # All normalized coords must be within page bounds
        assert 0 <= bbox[0] <= page_w_pts, f"x0 fora dos limites: {bbox[0]}"
        assert 0 <= bbox[1] <= page_h_pts, f"y0 fora dos limites: {bbox[1]}"
        assert 0 <= bbox[2] <= page_w_pts, f"x1 fora dos limites: {bbox[2]}"
        assert 0 <= bbox[3] <= page_h_pts, f"y1 fora dos limites: {bbox[3]}"
        # Verify normalization: raw_x0 / screenshot_scale ≈ bbox[0]
        import math

        assert math.isclose(bbox[0], raw_x0 / screenshot_scale, abs_tol=0.1), (
            f"bbox[0] incorreto: esperado {raw_x0 / screenshot_scale:.2f}, obtido {bbox[0]:.2f}"
        )


# ---------------------------------------------------------------------------
# Barcode value extraction + vertical line de-duplication
# ---------------------------------------------------------------------------


class TestBarcodeValueExtraction:
    """Validates _extract_barcode_value and the drawn-elements de-duplication logic.

    AC: barcode node carries `value` when a numeric text block is near the bbox;
        vertical lines within a barcode bbox are NOT added as individual line nodes.
    """

    def _get_mod(self):
        import importlib
        import sys

        sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
        return importlib.import_module("services.stages.stage3_structural_analysis")

    def test_extracts_numeric_value_from_adjacent_text_block(self):
        """When a text block with >60% digits sits near the barcode bbox, value is extracted."""
        mod = self._get_mod()
        barcode_bbox = [28.0, 540.0, 583.0, 610.0]
        page_data = {
            "text_blocks": [
                # Block above barcode — mostly digits, high score
                {
                    "id": "b1",
                    "bbox": [28.0, 510.0, 583.0, 530.0],
                    "text": "23793.36908 52020.72907 27000.00590 3 8 14010000497854",
                },
                # Block far away — should be ignored
                {"id": "b2", "bbox": [28.0, 50.0, 583.0, 70.0], "text": "Header text"},
            ],
            "width": 595.0,
            "height": 842.0,
        }
        value = mod._extract_barcode_value(page_data, barcode_bbox)
        assert value is not None, "Deve extrair valor do bloco numérico adjacente"
        # Must be digits only
        assert value.isdigit(), f"Valor deve conter apenas dígitos, obtido: {value!r}"
        assert len(value) >= 8, "Valor muito curto"

    def test_returns_none_when_no_numeric_block_nearby(self):
        """Returns None when all nearby text blocks are non-numeric."""
        mod = self._get_mod()
        barcode_bbox = [28.0, 540.0, 583.0, 610.0]
        page_data = {
            "text_blocks": [
                {"id": "b1", "bbox": [28.0, 510.0, 583.0, 530.0], "text": "Instruções ao beneficiário"},
            ],
            "width": 595.0,
            "height": 842.0,
        }
        value = mod._extract_barcode_value(page_data, barcode_bbox)
        assert value is None

    def test_vertical_lines_inside_barcode_bbox_excluded_from_page_nodes(self):
        """Vertical lines within a barcode bbox must NOT be added as individual line nodes."""
        mod = self._get_mod()
        page_w, page_h = 595.0, 842.0
        barcode_bbox = [28.0, 540.0, 583.0, 610.0]
        # A vertical line whose centre is inside the barcode bbox
        v_line_inside = {"type": "line", "orientation": "vertical", "bbox": [100.0, 545.0, 100.0, 605.0], "width": 1.0}
        # A vertical line outside the barcode bbox
        v_line_outside = {"type": "line", "orientation": "vertical", "bbox": [10.0, 100.0, 10.0, 200.0], "width": 1.0}
        # A horizontal line (separator) — always kept
        h_line = {"type": "line", "orientation": "horizontal", "bbox": [28.0, 400.0, 583.0, 400.0], "width": 0.5}
        zones = [
            {
                "type": "flow",
                "bbox": [0, 0, page_w, page_h],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": [],
                        "tables": [],
                        "images": [],
                        "charts": [],
                        "barcodes": [
                            {
                                "bbox": [
                                    barcode_bbox[0] * (150 / 72),
                                    barcode_bbox[1] * (150 / 72),
                                    barcode_bbox[2] * (150 / 72),
                                    barcode_bbox[3] * (150 / 72),
                                ],
                                "barcode_format": "CODE128",
                                "confidence": 90,
                                "description": "",
                            }
                        ],
                    }
                ],
            }
        ]
        page_data = {
            "text_blocks": [],
            "drawn_elements": [v_line_inside, v_line_outside, h_line],
            "width": page_w,
            "height": page_h,
        }
        tree = mod._build_tree("A", zones, {}, page_data)

        # Collect all line nodes at any depth
        def collect_lines(node):
            result = []
            if isinstance(node, dict):
                if node.get("type") == "line":
                    result.append(node)
                for child in node.get("children", []):
                    result.extend(collect_lines(child))
            return result

        lines = collect_lines(tree)
        orientations = [ln.get("orientation") for ln in lines]
        # The inside vertical line must NOT appear
        vertical_lines = [ln for ln in lines if ln.get("orientation") == "vertical"]
        for vl in vertical_lines:
            vl_cx = (vl["bbox"][0] + vl["bbox"][2]) / 2
            vl_cy = (vl["bbox"][1] + vl["bbox"][3]) / 2
            inside = barcode_bbox[0] <= vl_cx <= barcode_bbox[2] and barcode_bbox[1] <= vl_cy <= barcode_bbox[3]
            assert not inside, f"Linha vertical dentro do bbox do barcode não deveria estar na árvore: {vl}"
        # Horizontal separator must always be present
        assert "horizontal" in orientations, "Linha horizontal deve ser preservada"


# ---------------------------------------------------------------------------
# Tests: _assign_tables_to_sections + _bbox_contains (table rendering fix)
# RCA: rca-2026-04-06-canvas-tables-not-rendered
# ---------------------------------------------------------------------------

from services.stages.stage3_structural_analysis import (  # noqa: E402
    _assign_tables_to_sections,
    _bbox_contains,
)


class TestBboxContains:
    def test_inner_fully_inside(self):
        outer = [10.0, 10.0, 200.0, 300.0]
        inner = [20.0, 20.0, 150.0, 250.0]
        assert _bbox_contains(outer, inner) is True

    def test_inner_outside(self):
        outer = [10.0, 10.0, 100.0, 100.0]
        inner = [110.0, 110.0, 200.0, 200.0]
        assert _bbox_contains(outer, inner) is False

    def test_inner_partially_outside(self):
        outer = [10.0, 10.0, 100.0, 100.0]
        inner = [90.0, 10.0, 150.0, 100.0]  # right edge exceeds outer
        assert _bbox_contains(outer, inner) is False

    def test_tolerance_allows_2px_overflow(self):
        outer = [10.0, 10.0, 100.0, 100.0]
        inner = [10.0, 10.0, 101.5, 100.0]  # 1.5px beyond — within tolerance
        assert _bbox_contains(outer, inner) is True

    def test_tolerance_blocks_beyond_tolerance(self):
        outer = [10.0, 10.0, 100.0, 100.0]
        inner = [10.0, 10.0, 103.0, 100.0]  # 3px beyond — exceeds tolerance=2
        assert _bbox_contains(outer, inner) is False


class TestAssignTablesToSections:
    def _make_zones(self, section_blocks):
        """Build minimal zones structure with a single flow zone."""
        return [
            {
                "type": "flow",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "sections": [{"blocks": section_blocks}],
            }
        ]

    def test_table_assigned_to_section_by_overlap(self):
        """Table with Y range overlapping section blocks should be assigned."""
        blocks = [
            {"id": "b1", "bbox": [50.0, 100.0, 500.0, 120.0], "text": "Header"},
            {"id": "b2", "bbox": [50.0, 130.0, 200.0, 145.0], "text": "Cell 1"},
        ]
        zones = self._make_zones(blocks)
        tables = [
            {
                "table_id": "t1",
                "bbox": [50.0, 125.0, 500.0, 200.0],
                "headers": [],
                "rows": [],
            }
        ]
        _assign_tables_to_sections(zones, tables)
        section = zones[0]["sections"][0]
        assert "tables" in section
        assert len(section["tables"]) == 1
        assert section["tables"][0]["table_id"] == "t1"

    def test_no_tables_leaves_section_unchanged(self):
        """Empty tables list should not modify any section."""
        blocks = [{"id": "b1", "bbox": [50.0, 100.0, 200.0, 120.0], "text": "X"}]
        zones = self._make_zones(blocks)
        _assign_tables_to_sections(zones, [])
        section = zones[0]["sections"][0]
        assert "tables" not in section

    def test_blocks_inside_table_bbox_are_deduplicated_in_build_tree(self):
        """_build_tree must skip text blocks contained within a table bbox."""
        import uuid as _uuid

        from services.stages.stage3_structural_analysis import _build_tree

        bid_inside = str(_uuid.uuid4())
        bid_outside = str(_uuid.uuid4())
        table_bbox = [50.0, 100.0, 500.0, 300.0]

        blocks = [
            {"id": bid_inside, "bbox": [60.0, 110.0, 200.0, 130.0], "text": "CellText"},
            {"id": bid_outside, "bbox": [50.0, 50.0, 200.0, 90.0], "text": "Header"},
        ]
        zones = [
            {
                "type": "flow",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "source": "threshold",
                "sections": [
                    {
                        "blocks": blocks,
                        "tables": [
                            {
                                "table_id": "t1",
                                "bbox": table_bbox,
                                "headers": [[{"text": "CellText", "bbox": [60.0, 110.0, 200.0, 130.0]}]],
                                "rows": [],
                            }
                        ],
                    }
                ],
            }
        ]
        block_classifications = {
            bid_inside: _bc(semantic="value", variant="required"),
            bid_outside: _bc(semantic="label", variant="required"),
        }
        page_data = {
            "text_blocks": blocks,
            "tables": [{"table_id": "t1", "bbox": table_bbox}],
            "width": 595.0,
            "height": 842.0,
        }

        tree = _build_tree("cluster-1", zones, block_classifications, page_data)

        def collect_texts(node):
            texts = []
            if node.get("text"):
                texts.append(node["text"])
            for child in node.get("children", []):
                texts.extend(collect_texts(child))
            return texts

        all_texts = collect_texts(tree)
        # "CellText" should appear ONLY in the table node, not also as a standalone span
        assert all_texts.count("CellText") == 1, (
            f"'CellText' aparece {all_texts.count('CellText')}x — esperado 1 (somente na tabela)"
        )


# ---------------------------------------------------------------------------
# Story 29.4 — Semantic Names in Tree
# ---------------------------------------------------------------------------


class TestSemanticNames:
    """Story 29.4 — AC1/AC2/AC3: Nomes semânticos nos nós da árvore."""

    def _get_build_tree(self):
        from services.stages.stage3_structural_analysis import _build_tree

        return _build_tree

    def _get_helpers(self):
        from services.stages.stage3_structural_analysis import (
            _extract_semantic_name,
            _infer_section_name,
        )

        return _extract_semantic_name, _infer_section_name

    def test_extract_semantic_name_strips_trailing_colon(self):
        """AC1: label 'Cedente:' → name 'Cedente' (colon stripped)."""
        extract, _ = self._get_helpers()
        block = {"text": "Cedente:"}
        assert extract(block) == "Cedente"

    def test_extract_semantic_name_empty_text_returns_empty(self):
        """AC1: block with no text → empty name (frontend falls back to type)."""
        extract, _ = self._get_helpers()
        assert extract({}) == ""
        assert extract({"text": ""}) == ""

    def test_extract_semantic_name_truncates_long_text(self):
        """AC1: text longer than 50 chars is truncated."""
        extract, _ = self._get_helpers()
        long_text = "A" * 60
        result = extract({"text": long_text})
        assert len(result) <= 50

    def test_extract_semantic_name_preserves_short_text(self):
        """AC2: likely_dynamic with text 'R$ 1.500,00' → name 'R$ 1.500,00'."""
        extract, _ = self._get_helpers()
        block = {"text": "R$ 1.500,00"}
        assert extract(block) == "R$ 1.500,00"

    def test_label_node_gets_semantic_name(self):
        """AC1: label node in tree has name = text without colon."""
        _build_tree = self._get_build_tree()
        label_block = {
            "id": "b1",
            "text": "Cedente:",
            "bbox": [10.0, 10.0, 100.0, 25.0],
            "font_size": 10.0,
            "is_bold": False,
            "font_weight": "normal",
            "font_name": "Helvetica",
            "color": None,
        }
        zones = [
            {
                "type": "flow",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "source": "threshold",
                "sections": [{"blocks": [label_block]}],
            }
        ]
        block_classifications = {
            "b1": _bc(semantic="label", variant="required"),
        }
        page_data = {"text_blocks": [label_block], "width": 595.0, "height": 842.0}

        tree = _build_tree("c1", zones, block_classifications, page_data)

        # Find the label node
        def find_label(node):
            if node.get("type") == "label":
                return node
            for c in node.get("children", []):
                r = find_label(c)
                if r:
                    return r
            return None

        label_node = find_label(tree)
        assert label_node is not None, "label node not found in tree"
        assert label_node.get("name") == "Cedente", f"Expected name='Cedente', got '{label_node.get('name')}'"

    def test_likely_dynamic_node_gets_semantic_name(self):
        """AC2: likely_dynamic standalone node has name = detected text."""
        _build_tree = self._get_build_tree()
        dyn_block = {
            "id": "b2",
            "text": "R$ 1.500,00",
            "bbox": [200.0, 10.0, 350.0, 25.0],
            "font_size": 10.0,
            "is_bold": False,
            "font_weight": "normal",
            "font_name": "Helvetica",
            "color": None,
        }
        zones = [
            {
                "type": "flow",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "source": "threshold",
                "sections": [{"blocks": [dyn_block]}],
            }
        ]
        block_classifications = {
            "b2": _bc(semantic="likely_dynamic", variant="required"),
        }
        page_data = {"text_blocks": [dyn_block], "width": 595.0, "height": 842.0}

        tree = _build_tree("c1", zones, block_classifications, page_data)

        def find_dynamic(node):
            if node.get("type") == "likely_dynamic":
                return node
            for c in node.get("children", []):
                r = find_dynamic(c)
                if r:
                    return r
            return None

        dyn_node = find_dynamic(tree)
        assert dyn_node is not None, "likely_dynamic node not found"
        assert dyn_node.get("name") == "R$ 1.500,00", f"Expected name='R$ 1.500,00', got '{dyn_node.get('name')}'"

    def test_section_node_gets_inferred_name(self):
        """AC3: section containing label 'Cedente:' gets name 'Seção Cedente'."""
        _build_tree = self._get_build_tree()
        label_block = {
            "id": "b1",
            "text": "Cedente:",
            "bbox": [10.0, 10.0, 100.0, 25.0],
            "font_size": 10.0,
            "is_bold": False,
            "font_weight": "normal",
            "font_name": "Helvetica",
            "color": None,
        }
        zones = [
            {
                "type": "flow",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "source": "threshold",
                "sections": [{"blocks": [label_block]}],
            }
        ]
        block_classifications = {
            "b1": _bc(semantic="label", variant="required"),
        }
        page_data = {"text_blocks": [label_block], "width": 595.0, "height": 842.0}

        tree = _build_tree("c1", zones, block_classifications, page_data)

        def find_section(node):
            if node.get("type") == "section":
                return node
            for c in node.get("children", []):
                r = find_section(c)
                if r:
                    return r
            return None

        section_node = find_section(tree)
        assert section_node is not None, "section node not found"
        assert section_node.get("name") == "Seção Cedente", (
            f"Expected name='Seção Cedente', got '{section_node.get('name')}'"
        )


# ---------------------------------------------------------------------------
# Tests: Story 34.7 — Auto-bind semantic
# ---------------------------------------------------------------------------


class TestAutoBindSemantic:
    """Story 34.7 — Test Levenshtein similarity, normalization, and suggested bindings."""

    def test_normalize_text_removes_accents(self):
        mod = _get_stage3()
        assert mod._normalize_text("Cédula") == "cedula"
        assert mod._normalize_text("Beneficiário") == "beneficiario"

    def test_normalize_text_removes_punctuation(self):
        mod = _get_stage3()
        assert mod._normalize_text("Nome:") == "nome"
        assert mod._normalize_text("CNPJ/CPF") == "cnpjcpf"

    def test_normalize_text_lowercase(self):
        mod = _get_stage3()
        assert mod._normalize_text("VALOR") == "valor"

    def test_levenshtein_identical(self):
        mod = _get_stage3()
        assert mod._levenshtein_similarity("cedente", "cedente") == 1.0

    def test_levenshtein_empty(self):
        mod = _get_stage3()
        assert mod._levenshtein_similarity("", "") == 1.0
        assert mod._levenshtein_similarity("abc", "") == 0.0

    def test_levenshtein_similar(self):
        mod = _get_stage3()
        score = mod._levenshtein_similarity("cedente", "cedent")
        assert score > 0.8

    def test_levenshtein_different(self):
        mod = _get_stage3()
        score = mod._levenshtein_similarity("abc", "xyz")
        assert score < 0.3

    def test_suggest_xsd_binding_exact_match(self):
        mod = _get_stage3()
        paths = ["boleto.cedente", "boleto.valor", "boleto.sacado.nome"]
        result = mod._suggest_xsd_binding("Cedente", paths)
        assert result == "boleto.cedente"

    def test_suggest_xsd_binding_no_match(self):
        mod = _get_stage3()
        paths = ["boleto.cedente", "boleto.valor"]
        result = mod._suggest_xsd_binding("XYZABC", paths)
        assert result is None

    def test_suggest_xsd_binding_accent_match(self):
        mod = _get_stage3()
        paths = ["boleto.beneficiario"]
        result = mod._suggest_xsd_binding("Beneficiário", paths)
        assert result == "boleto.beneficiario"

    def test_suggest_xsd_binding_empty_inputs(self):
        mod = _get_stage3()
        assert mod._suggest_xsd_binding("", ["boleto.valor"]) is None
        assert mod._suggest_xsd_binding("Valor", []) is None

    def test_apply_suggested_bindings(self):
        mod = _get_stage3()
        tree: dict[str, Any] = {
            "type": "document",
            "children": [
                {
                    "type": "field",
                    "name": "Cedente",
                    "children": [],
                },
                {
                    "type": "value",
                    "name": "Valor",
                    "children": [],
                },
                {
                    "type": "label",
                    "name": "Título:",
                    "children": [],
                },
            ],
        }
        paths = ["boleto.cedente", "boleto.valor"]
        count = mod._apply_suggested_bindings(tree, paths)
        assert count == 2
        children: list[Any] = tree["children"]
        assert children[0]["suggested_binding"] == "boleto.cedente"
        assert children[1]["suggested_binding"] == "boleto.valor"
        # label type is not in the bindable types — no suggestion
        assert "suggested_binding" not in children[2]


# ---------------------------------------------------------------------------
# Test: _build_visual_table_from_blocks + table_area visual fallback
# ---------------------------------------------------------------------------


class TestBuildVisualTableFromBlocks:
    """Tests for _build_visual_table_from_blocks (visual fallback for table_area)."""

    def _get_section_utils(self):
        import services.stages.stage3_structural.section_utils as mod

        return mod

    def test_groups_blocks_into_rows_by_y(self):
        """Blocks with similar Y must be grouped into the same row."""
        mod = self._get_section_utils()
        blocks = [
            {"bbox": [10.0, 100.0, 80.0, 115.0], "text": "Local de Pagamento"},
            {"bbox": [90.0, 101.0, 400.0, 116.0], "text": "Qualquer banco"},
            {"bbox": [10.0, 130.0, 80.0, 145.0], "text": "Beneficiário"},
            {"bbox": [90.0, 132.0, 300.0, 147.0], "text": "Bradesco S.A."},
        ]
        region_bbox = [0, 90, 595, 160]
        result = mod._build_visual_table_from_blocks(blocks, region_bbox)

        assert result is not None
        assert result["row_count"] == 2
        assert result["raw_cells"][0] == ["Local de Pagamento", "Qualquer banco"]
        assert result["raw_cells"][1] == ["Beneficiário", "Bradesco S.A."]
        assert result["source"] == "visual_analysis_fallback"

    def test_sorts_columns_by_x(self):
        """Within a row, blocks must be sorted left-to-right by X position."""
        mod = self._get_section_utils()
        blocks = [
            {"bbox": [200.0, 50.0, 300.0, 65.0], "text": "Valor"},
            {"bbox": [10.0, 50.0, 150.0, 65.0], "text": "Beneficiário"},
        ]
        region_bbox = [0, 40, 400, 80]
        result = mod._build_visual_table_from_blocks(blocks, region_bbox)

        assert result is not None
        assert result["raw_cells"][0] == ["Beneficiário", "Valor"]

    def test_returns_none_for_empty_region(self):
        """Returns None when no blocks fall within the region bbox."""
        mod = self._get_section_utils()
        blocks = [{"bbox": [0.0, 0.0, 10.0, 10.0], "text": "Outside"}]
        region_bbox = [400, 400, 595, 500]
        result = mod._build_visual_table_from_blocks(blocks, region_bbox)
        assert result is None

    def test_table_area_creates_synthetic_table_in_section(self):
        """_assign_visual_elements_to_sections must process table_area and create synthetic table."""
        mod = self._get_section_utils()

        blocks = [
            {"bbox": [10.0, 100.0, 100.0, 115.0], "text": "Cedente"},
            {"bbox": [110.0, 101.0, 300.0, 115.0], "text": "Empresa S.A."},
            {"bbox": [10.0, 130.0, 100.0, 145.0], "text": "CNPJ"},
            {"bbox": [110.0, 131.0, 300.0, 145.0], "text": "12.345.678/0001-90"},
        ]
        zones = [
            {
                "type": "flow",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "sections": [{"blocks": blocks}],
            }
        ]
        visual_analysis = {
            "page_0": {
                "regions": [
                    {
                        "type": "table_area",
                        "bbox": [0, 90, 595, 160],
                        "description": "Payment fields table",
                        "confidence": 80,
                    }
                ]
            }
        }

        mod._assign_visual_elements_to_sections(zones, visual_analysis, "page_0")

        section = zones[0]["sections"][0]
        tables = section.get("tables", [])
        assert len(tables) == 1
        assert tables[0]["source"] == "visual_analysis_fallback"
        assert tables[0]["row_count"] == 2
        assert tables[0]["col_count"] == 2

    def test_table_area_skips_if_programmatic_table_exists(self):
        """If a programmatic table already covers the region, no synthetic table is added."""
        mod = self._get_section_utils()

        blocks = [{"bbox": [10.0, 100.0, 100.0, 115.0], "text": "Field"}]
        zones = [
            {
                "type": "flow",
                "bbox": [0.0, 0.0, 595.0, 842.0],
                "sections": [
                    {
                        "blocks": blocks,
                        "tables": [
                            {
                                "bbox": [0, 90, 595, 160],
                                "raw_cells": [["Field", "Value"]],
                                "source": "programmatic",  # no "visual_analysis_fallback"
                            }
                        ],
                    }
                ],
            }
        ]
        visual_analysis = {
            "page_0": {
                "regions": [
                    {
                        "type": "table_area",
                        "bbox": [0, 90, 595, 160],
                        "description": "Same table",
                        "confidence": 80,
                    }
                ]
            }
        }

        mod._assign_visual_elements_to_sections(zones, visual_analysis, "page_0")

        section = zones[0]["sections"][0]
        tables = section.get("tables", [])
        # Still only 1 table (no synthetic added)
        assert len(tables) == 1
        assert tables[0]["source"] == "programmatic"
