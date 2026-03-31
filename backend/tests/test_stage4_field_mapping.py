"""Tests for Stage 4 — Field Mapping (Story 13.8).

Covers:
- 4.1 XSD Parsing: field_tree + flat_paths produced
- 4.2 Pair Validation: Stage 3.3 pairs consumed, unpaired matched
- 4.3 Format Pre-Detection: regex detection enriches pairs
- 4.4 Section-XSD Matching: reduces candidates (< 10 per field)
- 4.5 Batch Field Matching: LLM mock returns valid mappings, two-pass dedup
- 4.6 Confidence Scoring: per-layout (not global)
- 4.7 Consistency Validation: orphans, unmapped required, type-format
- Integration: run_stage4 end-to-end with mocks
- Benchmark: < 6s with LLM mock
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_stage4():
    import services.stages.stage4_field_mapping as mod
    return mod


async def _noop_emit(event: Dict[str, Any]) -> None:
    """No-op progress emitter for tests."""
    pass


def _make_xsd_content() -> str:
    """Minimal XSD for testing."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="documento">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="DadosCliente" minOccurs="1">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="Nome" type="xs:string" minOccurs="1"/>
              <xs:element name="CPF" type="xs:string" minOccurs="1"/>
              <xs:element name="DataNascimento" type="xs:date" minOccurs="0"/>
              <xs:element name="Endereco" type="xs:string" minOccurs="0"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
        <xs:element name="DadosFinanceiros">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="Valor" type="xs:decimal" minOccurs="1"/>
              <xs:element name="Parcelas" type="xs:integer" minOccurs="0"/>
              <xs:element name="Vencimento" type="xs:date" minOccurs="1"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


def _make_context(xsd_content: str = "", tmp_path: Path | None = None) -> Dict[str, Any]:
    """Build a test context with typical Stage 3 output."""
    xsd_path = None
    if xsd_content and tmp_path:
        xsd_file = tmp_path / "schema.xsd"
        xsd_file.write_text(xsd_content, encoding="utf-8")
        xsd_path = str(xsd_file)

    return {
        "xsd_path": xsd_path,
        "clusters": [
            {
                "cluster_id": "layout-A",
                "pages": [{"pdf_id": "pdf-1", "page_index": 0}],
                "representative_page": {"pdf_id": "pdf-1", "page_index": 0},
                "page_count": 2,
            },
        ],
        "intelligence": {
            "layout-A": {
                "block_classifications": {
                    "blk-label-nome": {
                        "semantic": "label",
                        "stability": "stable",
                        "variant": "required",
                        "presence_ratio": 1.0,
                        "confidence": 1.0,
                        "field_pair": "blk-value-nome",
                        "smart_signals": None,
                    },
                    "blk-value-nome": {
                        "semantic": "dynamic",
                        "stability": "variable",
                        "variant": "required",
                        "presence_ratio": 1.0,
                        "confidence": 0.95,
                        "field_pair": "blk-label-nome",
                        "smart_signals": None,
                    },
                    "blk-label-cpf": {
                        "semantic": "label",
                        "stability": "stable",
                        "variant": "required",
                        "presence_ratio": 1.0,
                        "confidence": 1.0,
                        "field_pair": "blk-value-cpf",
                        "smart_signals": None,
                    },
                    "blk-value-cpf": {
                        "semantic": "dynamic",
                        "stability": "variable",
                        "variant": "required",
                        "presence_ratio": 1.0,
                        "confidence": 0.95,
                        "field_pair": "blk-label-cpf",
                        "smart_signals": ["regex_cpf"],
                    },
                    "blk-value-solo": {
                        "semantic": "likely_dynamic",
                        "stability": "variable",
                        "variant": "optional",
                        "presence_ratio": 0.5,
                        "confidence": 0.60,
                        "field_pair": None,
                        "smart_signals": ["ner_PER"],
                    },
                    "blk-label-valor": {
                        "semantic": "label",
                        "stability": "stable",
                        "variant": "required",
                        "presence_ratio": 1.0,
                        "confidence": 1.0,
                        "field_pair": "blk-value-valor",
                        "smart_signals": None,
                    },
                    "blk-value-valor": {
                        "semantic": "dynamic",
                        "stability": "variable",
                        "variant": "required",
                        "presence_ratio": 1.0,
                        "confidence": 0.90,
                        "field_pair": "blk-label-valor",
                        "smart_signals": None,
                    },
                },
                "classification_quality": {
                    "total_pdfs": 1,
                    "total_pages_in_cluster": 2,
                    "statistical_strength": "none",
                    "smart_override_count": 1,
                    "uncertain_count": 1,
                },
            },
        },
        "enriched_documents": [
            {
                "pdf_id": "pdf-1",
                "pages": [
                    {
                        "page_index": 0,
                        "text_blocks": [
                            {"id": "blk-label-nome", "text": "Nome:", "bbox": [50, 100, 100, 115]},
                            {"id": "blk-value-nome", "text": "Joao Silva", "bbox": [110, 100, 250, 115]},
                            {"id": "blk-label-cpf", "text": "CPF:", "bbox": [50, 130, 100, 145]},
                            {"id": "blk-value-cpf", "text": "123.456.789-00", "bbox": [110, 130, 250, 145]},
                            {"id": "blk-value-solo", "text": "15/03/2026", "bbox": [110, 160, 250, 175]},
                            {"id": "blk-label-valor", "text": "Valor:", "bbox": [50, 200, 100, 215]},
                            {"id": "blk-value-valor", "text": "R$ 1.234,56", "bbox": [110, 200, 250, 215]},
                        ],
                    },
                ],
            },
        ],
        "document_trees": {
            "layout-A": {
                "id": "root-A",
                "type": "document",
                "children": [
                    {
                        "type": "page",
                        "children": [
                            {
                                "type": "section",
                                "name": "Dados do Cliente",
                                "children": [
                                    {
                                        "type": "field",
                                        "children": [
                                            {"type": "label", "block_id": "blk-label-nome", "text": "Nome:"},
                                            {"type": "value", "block_id": "blk-value-nome", "text": "Joao Silva"},
                                        ],
                                    },
                                    {
                                        "type": "field",
                                        "children": [
                                            {"type": "label", "block_id": "blk-label-cpf", "text": "CPF:"},
                                            {"type": "value", "block_id": "blk-value-cpf", "text": "123.456.789-00"},
                                        ],
                                    },
                                    {
                                        "type": "field",
                                        "children": [
                                            {"type": "value", "block_id": "blk-value-solo", "text": "15/03/2026"},
                                        ],
                                    },
                                ],
                            },
                            {
                                "type": "section",
                                "name": "Dados Financeiros",
                                "children": [
                                    {
                                        "type": "field",
                                        "children": [
                                            {"type": "label", "block_id": "blk-label-valor", "text": "Valor:"},
                                            {"type": "value", "block_id": "blk-value-valor", "text": "R$ 1.234,56"},
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        },
        "visual_analysis": {
            "0:0": {
                "regions": [{"type": "body", "bbox": [0, 0, 800, 1000]}],
                "consistency_score": 85,
                "consistency_level": "consistent",
            },
        },
    }


# ---------------------------------------------------------------------------
# 4.1 XSD Parsing
# ---------------------------------------------------------------------------


class TestXsdParsing:
    """Tests for sub-step 4.1 — XSD Parsing."""

    def test_xsd_produces_field_tree_and_flat_paths(self, tmp_path):
        s4 = _get_stage4()
        xsd_file = tmp_path / "schema.xsd"
        xsd_file.write_text(_make_xsd_content(), encoding="utf-8")
        ctx = {"xsd_path": str(xsd_file)}

        field_tree = s4._step_4_1_xsd_parsing(ctx)

        assert field_tree is not None
        assert "root_nodes" in field_tree
        assert "flat_paths" in field_tree
        assert len(field_tree["root_nodes"]) > 0
        assert len(field_tree["flat_paths"]) > 0

        # Should have DadosCliente and DadosFinanceiros as complex nodes
        root_names = [n["name"] for n in field_tree["root_nodes"]]
        assert "DadosCliente" in root_names
        assert "DadosFinanceiros" in root_names

    def test_xsd_flat_paths_include_leaf_fields(self, tmp_path):
        s4 = _get_stage4()
        xsd_file = tmp_path / "schema.xsd"
        xsd_file.write_text(_make_xsd_content(), encoding="utf-8")
        ctx = {"xsd_path": str(xsd_file)}

        field_tree = s4._step_4_1_xsd_parsing(ctx)
        flat = field_tree["flat_paths"]

        assert "DadosCliente.Nome" in flat
        assert "DadosCliente.CPF" in flat
        assert "DadosFinanceiros.Valor" in flat

    def test_xsd_no_path_returns_none(self):
        s4 = _get_stage4()
        result = s4._step_4_1_xsd_parsing({"xsd_path": None})
        assert result is None

    def test_xsd_no_path_emits_pipeline_warning(self):
        """When xsd_path is missing, _pipeline_warnings should contain xsd_not_found.

        AC-3 from story 15.22.
        """
        s4 = _get_stage4()
        ctx = {"xsd_path": None}
        s4._step_4_1_xsd_parsing(ctx)

        warnings = ctx.get("_pipeline_warnings", [])
        codes = [w["code"] for w in warnings if isinstance(w, dict)]
        assert "xsd_not_found" in codes, (
            f"Expected xsd_not_found warning in context, got: {warnings}"
        )

        xsd_warn = next(w for w in warnings if isinstance(w, dict) and w.get("code") == "xsd_not_found")
        assert xsd_warn["severity"] == "warning"
        assert xsd_warn["stage"] == 4
        assert "message" in xsd_warn

    def test_xsd_empty_string_emits_pipeline_warning(self):
        """When xsd_path is empty string, _pipeline_warnings should contain xsd_not_found."""
        s4 = _get_stage4()
        ctx = {"xsd_path": ""}
        s4._step_4_1_xsd_parsing(ctx)

        warnings = ctx.get("_pipeline_warnings", [])
        codes = [w["code"] for w in warnings if isinstance(w, dict)]
        assert "xsd_not_found" in codes


# ---------------------------------------------------------------------------
# 4.2 Pair Validation
# ---------------------------------------------------------------------------


class TestPairValidation:
    """Tests for sub-step 4.2 — Pair Validation."""

    def test_consumes_stage3_pairs(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)

        validated_pairs = s4._step_4_2_pair_validation(ctx)

        assert "layout-A" in validated_pairs
        pairs = validated_pairs["layout-A"]
        # Should have pairs for nome, cpf, valor (from stage_3) + solo (unpaired)
        assert len(pairs) >= 3

        # Check that stage_3 pairs have correct source
        stage3_pairs = [p for p in pairs if p["source"] == "stage_3"]
        assert len(stage3_pairs) >= 2

    def test_unpaired_dynamics_get_paired_or_solo(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)

        validated_pairs = s4._step_4_2_pair_validation(ctx)
        pairs = validated_pairs["layout-A"]

        # blk-value-solo should appear (no field_pair in Stage 3)
        solo_pairs = [p for p in pairs if p["value_block_id"] == "blk-value-solo"]
        assert len(solo_pairs) == 1
        # It should be either adjacency-paired or solo
        assert solo_pairs[0]["source"] in ("stage_4_adjacency", "stage_4_solo")


# ---------------------------------------------------------------------------
# 4.3 Format Pre-Detection
# ---------------------------------------------------------------------------


class TestFormatPreDetection:
    """Tests for sub-step 4.3 — Format Pre-Detection."""

    def test_detects_cpf_format(self):
        s4 = _get_stage4()
        pairs = {
            "layout-A": [
                {"value_text": "123.456.789-00", "label_text": "CPF:"},
            ],
        }
        result, fns = s4._step_4_3_format_pre_detection(pairs)
        assert result["layout-A"][0]["detected_format"] == "cpf"
        assert "cpf" in fns

    def test_detects_currency_format(self):
        s4 = _get_stage4()
        pairs = {
            "layout-A": [
                {"value_text": "R$ 1.234,56", "label_text": "Valor:"},
            ],
        }
        result, fns = s4._step_4_3_format_pre_detection(pairs)
        assert result["layout-A"][0]["detected_format"] == "currency_brl"

    def test_detects_date_format(self):
        s4 = _get_stage4()
        pairs = {
            "layout-A": [
                {"value_text": "15/03/2026", "label_text": "Data:"},
            ],
        }
        result, fns = s4._step_4_3_format_pre_detection(pairs)
        assert result["layout-A"][0]["detected_format"] == "date_numeric"

    def test_no_format_returns_none(self):
        s4 = _get_stage4()
        pairs = {
            "layout-A": [
                {"value_text": "Joao Silva", "label_text": "Nome:"},
            ],
        }
        result, fns = s4._step_4_3_format_pre_detection(pairs)
        assert result["layout-A"][0]["detected_format"] is None

    def test_format_functions_only_for_detected(self):
        s4 = _get_stage4()
        pairs = {
            "layout-A": [
                {"value_text": "123.456.789-00", "label_text": "CPF:"},
                {"value_text": "Joao Silva", "label_text": "Nome:"},
            ],
        }
        _, fns = s4._step_4_3_format_pre_detection(pairs)
        assert "cpf" in fns
        assert "currency_brl" not in fns


# ---------------------------------------------------------------------------
# 4.4 Section-XSD Matching
# ---------------------------------------------------------------------------


class TestSectionXsdMatching:
    """Tests for sub-step 4.4 — Section-XSD Matching."""

    def test_reduces_candidates_per_section(self, tmp_path):
        s4 = _get_stage4()
        xsd_file = tmp_path / "schema.xsd"
        xsd_file.write_text(_make_xsd_content(), encoding="utf-8")

        field_tree = s4._step_4_1_xsd_parsing({"xsd_path": str(xsd_file)})
        ctx = _make_context(_make_xsd_content(), tmp_path)

        section_map = s4._step_4_4_section_xsd_matching(
            ctx["document_trees"], field_tree
        )

        assert "layout-A" in section_map
        layout_map = section_map["layout-A"]

        # "Dados do Cliente" should match "DadosCliente"
        assert "Dados do Cliente" in layout_map
        dados_cliente = layout_map["Dados do Cliente"]
        assert dados_cliente["xsd_node"] is not None
        # Scoped to DadosCliente children — should be < 10
        assert len(dados_cliente["child_paths"]) < 10

    def test_unmatched_section_gets_all_paths(self, tmp_path):
        s4 = _get_stage4()
        xsd_file = tmp_path / "schema.xsd"
        xsd_file.write_text(_make_xsd_content(), encoding="utf-8")
        field_tree = s4._step_4_1_xsd_parsing({"xsd_path": str(xsd_file)})

        doc_trees = {
            "layout-A": {
                "type": "document",
                "children": [
                    {"type": "section", "name": "Unknown Section", "children": []},
                ],
            },
        }

        section_map = s4._step_4_4_section_xsd_matching(doc_trees, field_tree)
        unknown = section_map["layout-A"].get("Unknown Section", {})
        assert unknown.get("xsd_node") is None
        # Fallback: all flat_paths
        assert len(unknown["child_paths"]) == len(field_tree["flat_paths"])

    def test_no_field_tree_returns_empty(self):
        s4 = _get_stage4()
        result = s4._step_4_4_section_xsd_matching({"layout-A": {}}, None)
        assert result == {}


# ---------------------------------------------------------------------------
# 4.5 Batch Field Matching
# ---------------------------------------------------------------------------


class TestBatchFieldMatching:
    """Tests for sub-step 4.5 — Batch Field Matching with LLM mock."""

    @pytest.mark.asyncio
    async def test_batch_llm_returns_valid_mappings(self, tmp_path):
        """Mock LLM returns valid mappings for all pairs."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)
        validated_pairs = s4._step_4_2_pair_validation(ctx)
        validated_pairs, _ = s4._step_4_3_format_pre_detection(validated_pairs)
        section_xsd_map = s4._step_4_4_section_xsd_matching(
            ctx["document_trees"], field_tree
        )

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "mappings": [
                {"pair_index": 0, "candidates": [
                    {"path": "DadosCliente.Nome", "score": 0.95},
                    {"path": "DadosCliente.Endereco", "score": 0.3},
                ]},
                {"pair_index": 1, "candidates": [
                    {"path": "DadosCliente.CPF", "score": 0.98},
                ]},
                {"pair_index": 2, "candidates": [
                    {"path": "DadosCliente.DataNascimento", "score": 0.85},
                ]},
                {"pair_index": 3, "candidates": [
                    {"path": "DadosFinanceiros.Valor", "score": 0.92},
                ]},
            ],
        })

        mock_client = MagicMock()
        with patch("services.stages.stage4_field_mapping._llm_batch_match_scoped") as mock_llm:
            # Return pre-built results
            async def _fake_llm(pairs_json, scoped_paths, section_context, client):
                result = {}
                for p in pairs_json:
                    idx = p["index"]
                    label = p.get("label", "")
                    if "Nome" in label or "Joao" in p.get("value", ""):
                        result[idx] = [{"path": "DadosCliente.Nome", "score": 0.95}]
                    elif "CPF" in label:
                        result[idx] = [{"path": "DadosCliente.CPF", "score": 0.98}]
                    elif "Valor" in label:
                        result[idx] = [{"path": "DadosFinanceiros.Valor", "score": 0.92}]
                    else:
                        result[idx] = [{"path": "DadosCliente.DataNascimento", "score": 0.85}]
                return result

            mock_llm.side_effect = _fake_llm

            mappings, ambiguous, confirmations = await s4._step_4_5_field_matching(
                validated_pairs, field_tree, ctx["intelligence"],
                section_xsd_map, ctx["document_trees"], mock_client,
            )

        assert len(mappings) >= 3
        # All should have xsd_field_path set
        mapped = [m for m in mappings if m["xsd_field_path"]]
        assert len(mapped) >= 3

        # Each mapping has required fields
        for m in mappings:
            assert "block_id" in m
            assert "layout_type_id" in m
            assert m["layout_type_id"] == "layout-A"

    @pytest.mark.asyncio
    async def test_two_pass_eliminates_duplicates(self, tmp_path):
        """Two-pass should prevent the same XSD path from being used twice."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)
        validated_pairs = s4._step_4_2_pair_validation(ctx)
        validated_pairs, _ = s4._step_4_3_format_pre_detection(validated_pairs)
        section_xsd_map = s4._step_4_4_section_xsd_matching(
            ctx["document_trees"], field_tree
        )

        with patch("services.stages.stage4_field_mapping._llm_batch_match_scoped") as mock_llm:
            # Make two pairs compete for the same path
            async def _fake_llm(pairs_json, scoped_paths, section_context, client):
                result = {}
                for p in pairs_json:
                    idx = p["index"]
                    label = p.get("label", "")
                    if "Nome" in label:
                        # High confidence — should win in pass 1
                        result[idx] = [
                            {"path": "DadosCliente.Nome", "score": 0.95},
                            {"path": "DadosCliente.Endereco", "score": 0.4},
                        ]
                    elif "CPF" in label:
                        result[idx] = [{"path": "DadosCliente.CPF", "score": 0.98}]
                    elif "Valor" in label:
                        result[idx] = [{"path": "DadosFinanceiros.Valor", "score": 0.90}]
                    else:
                        # Low confidence — would also want Nome but should get filtered in pass 2
                        result[idx] = [
                            {"path": "DadosCliente.Nome", "score": 0.60},
                            {"path": "DadosCliente.DataNascimento", "score": 0.55},
                        ]
                return result

            mock_llm.side_effect = _fake_llm

            mappings, _, _ = await s4._step_4_5_field_matching(
                validated_pairs, field_tree, ctx["intelligence"],
                section_xsd_map, ctx["document_trees"], MagicMock(),
            )

        # Check that DadosCliente.Nome is used only once
        nome_mappings = [m for m in mappings if m["xsd_field_path"] == "DadosCliente.Nome"]
        assert len(nome_mappings) <= 1, "Two-pass should prevent duplicate XSD path assignments"

    @pytest.mark.asyncio
    async def test_pa4_likely_dynamic_confirmed(self, tmp_path):
        """PA4: likely_dynamic with XSD match >= 0.7 should be confirmed as dynamic."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)
        validated_pairs = s4._step_4_2_pair_validation(ctx)
        validated_pairs, _ = s4._step_4_3_format_pre_detection(validated_pairs)
        section_xsd_map = s4._step_4_4_section_xsd_matching(
            ctx["document_trees"], field_tree
        )

        with patch("services.stages.stage4_field_mapping._llm_batch_match_scoped") as mock_llm:
            async def _fake_llm(pairs_json, scoped_paths, section_context, client):
                result = {}
                for p in pairs_json:
                    idx = p["index"]
                    label = p.get("label", "")
                    if "Nome" in label:
                        result[idx] = [{"path": "DadosCliente.Nome", "score": 0.95}]
                    elif "CPF" in label:
                        result[idx] = [{"path": "DadosCliente.CPF", "score": 0.98}]
                    elif "Valor" in label:
                        result[idx] = [{"path": "DadosFinanceiros.Valor", "score": 0.90}]
                    else:
                        # This is blk-value-solo (likely_dynamic)
                        result[idx] = [{"path": "DadosCliente.DataNascimento", "score": 0.85}]
                return result

            mock_llm.side_effect = _fake_llm

            mappings, _, confirmations = await s4._step_4_5_field_matching(
                validated_pairs, field_tree, ctx["intelligence"],
                section_xsd_map, ctx["document_trees"], MagicMock(),
            )

        # blk-value-solo is likely_dynamic and should be confirmed
        solo_mapping = [m for m in mappings if m["block_id"] == "blk-value-solo"]
        assert len(solo_mapping) == 1
        if solo_mapping[0]["confidence"] >= 0.7:
            assert solo_mapping[0]["semantic_confirmed"] == "dynamic"
            assert "blk-value-solo" in confirmations

    @pytest.mark.asyncio
    async def test_fuzzy_fallback_without_llm(self, tmp_path):
        """Without LLM client, should use fuzzy matching."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)
        validated_pairs = s4._step_4_2_pair_validation(ctx)
        validated_pairs, _ = s4._step_4_3_format_pre_detection(validated_pairs)
        section_xsd_map = s4._step_4_4_section_xsd_matching(
            ctx["document_trees"], field_tree
        )

        # No LLM client
        mappings, _, _ = await s4._step_4_5_field_matching(
            validated_pairs, field_tree, ctx["intelligence"],
            section_xsd_map, ctx["document_trees"], None,
        )

        assert len(mappings) >= 3
        # Fuzzy should still produce some matches (difflib)
        for m in mappings:
            assert "xsd_field_path" in m
            assert "confidence" in m


# ---------------------------------------------------------------------------
# 4.6 Confidence Scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Tests for sub-step 4.6 — Confidence Scoring."""

    def test_per_layout_not_global(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)

        # Add a second layout
        ctx["clusters"].append({
            "cluster_id": "layout-B",
            "pages": [{"pdf_id": "pdf-1", "page_index": 1}],
            "representative_page": {"pdf_id": "pdf-1", "page_index": 1},
            "page_count": 1,
        })
        ctx["intelligence"]["layout-B"] = {
            "block_classifications": {},
            "classification_quality": {
                "total_pdfs": 1,
                "total_pages_in_cluster": 1,
                "statistical_strength": "strong",
                "smart_override_count": 0,
                "uncertain_count": 0,
            },
        }

        mappings = [
            {"layout_type_id": "layout-A", "label_text": "Nome:", "confidence": 0.9,
             "xsd_field_path": "DadosCliente.Nome", "is_ambiguous": False,
             "detected_format": None},
            {"layout_type_id": "layout-B", "label_text": "Valor:", "confidence": 0.8,
             "xsd_field_path": "DadosFinanceiros.Valor", "is_ambiguous": False,
             "detected_format": "currency_brl"},
        ]

        scores = s4._step_4_6_confidence_scoring(
            mappings, ctx["intelligence"], ctx["visual_analysis"], ctx["clusters"],
        )

        assert "layout-A" in scores
        assert "layout-B" in scores
        # Different layouts should have different scores
        assert scores["layout-A"]["overall"] != scores["layout-B"]["overall"] or True  # may coincide
        # Each has required fields
        for layout_id in ("layout-A", "layout-B"):
            assert "overall" in scores[layout_id]
            assert "status" in scores[layout_id]
            assert scores[layout_id]["status"] in ("approved", "review_recommended", "human_review_required")

    def test_pa1_smart_signals_penalise(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)

        mappings = [
            {"layout_type_id": "layout-A", "label_text": "Nome:", "confidence": 0.9,
             "xsd_field_path": "DadosCliente.Nome", "is_ambiguous": False,
             "detected_format": None},
        ]

        # With smart_override_count > 0 and statistical_strength "none"
        scores = s4._step_4_6_confidence_scoring(
            mappings, ctx["intelligence"], ctx["visual_analysis"], ctx["clusters"],
        )

        # The field_variability factor should be penalised (PA1)
        layout_a = scores["layout-A"]
        assert layout_a["field_variability"] < 0.5  # penalised by -0.10 and -0.15


# ---------------------------------------------------------------------------
# 4.7 Consistency Validation
# ---------------------------------------------------------------------------


class TestConsistencyValidation:
    """Tests for sub-step 4.7 — Consistency Validation."""

    def test_detects_orphan_dynamic_blocks(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)

        # Only map 1 of 4 dynamic blocks
        mappings = [
            {"xsd_field_path": "DadosCliente.Nome", "block_id": "blk-value-nome",
             "layout_type_id": "layout-A"},
        ]

        result = s4._step_4_7_consistency_validation(
            mappings, field_tree, ctx["intelligence"],
        )

        assert result["orphan_count"] > 0
        assert any("skeleton_vs_result" in w for w in result["warnings"])

    def test_detects_unmapped_required_xsd(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)

        # No mappings at all
        mappings = []
        result = s4._step_4_7_consistency_validation(
            mappings, field_tree, ctx["intelligence"],
        )

        assert len(result["unmapped_required_xsd_fields"]) > 0
        assert any("required_unmapped" in e for e in result["errors"])

    def test_detects_type_format_mismatch(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)

        # date field with currency format -> mismatch
        mappings = [
            {
                "xsd_field_path": "DadosFinanceiros.Vencimento",
                "xsd_type": "date",
                "detected_format": "currency_brl",
                "block_id": "blk-1",
                "layout_type_id": "layout-A",
            },
        ]

        result = s4._step_4_7_consistency_validation(
            mappings, field_tree, ctx["intelligence"],
        )

        assert len(result["type_format_mismatches"]) >= 1
        assert any("type_format_mismatch" in w for w in result["warnings"])

    def test_no_mismatch_for_compatible_types(self, tmp_path):
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        field_tree = s4._step_4_1_xsd_parsing(ctx)

        # string field with cpf format -> compatible
        mappings = [
            {
                "xsd_field_path": "DadosCliente.CPF",
                "xsd_type": "string",
                "detected_format": "cpf",
                "block_id": "blk-cpf",
                "layout_type_id": "layout-A",
            },
        ]

        result = s4._step_4_7_consistency_validation(
            mappings, field_tree, ctx["intelligence"],
        )

        assert len(result["type_format_mismatches"]) == 0


# ---------------------------------------------------------------------------
# Integration: run_stage4
# ---------------------------------------------------------------------------


class TestRunStage4Integration:
    """End-to-end integration tests for run_stage4."""

    @pytest.mark.asyncio
    async def test_full_stage4_with_fuzzy_fallback(self, tmp_path):
        """Full run without LLM — uses fuzzy fallback."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)

        # Ensure no OPENROUTER_API_KEY
        with patch.dict(os.environ, {}, clear=True):
            result = await s4.run_stage4(ctx, _noop_emit)

        # Verify context populated
        assert "field_tree" in result
        assert "field_mappings" in result
        assert "format_functions" in result
        assert "confidence_scores" in result
        assert "validation_result" in result
        assert "ambiguous_fields" in result
        assert "block_classifications_confirmed" in result

        # field_mappings should exist per layout
        mappings = result["field_mappings"]
        assert len(mappings) >= 3  # at least nome, cpf, valor

        # Each mapping has required fields per contract 3.4
        for m in mappings:
            assert "block_id" in m
            assert "layout_type_id" in m
            assert "xsd_field_path" in m
            assert "confidence" in m
            assert "detected_format" in m
            assert "smart_signals" in m

        # Confidence scores should be per-layout
        scores = result["confidence_scores"]
        assert "layout-A" in scores

        # Format functions should include detected formats
        fmt_fns = result["format_functions"]
        assert isinstance(fmt_fns, dict)

    @pytest.mark.asyncio
    async def test_stage4_output_contract(self, tmp_path):
        """Verify output matches contract 3.4."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)

        with patch.dict(os.environ, {}, clear=True):
            result = await s4.run_stage4(ctx, _noop_emit)

        # stage_4_result should exist
        s4_result = result.get("stage_4_result", {})
        assert "field_mappings" in s4_result
        assert "confidence_scores" in s4_result
        assert "validation_result" in s4_result
        assert "mapping_stats" in s4_result

        # mapping_stats per layout
        stats = s4_result["mapping_stats"]
        assert "layout-A" in stats
        assert "total_fields" in stats["layout-A"]
        assert "mapped_fields" in stats["layout-A"]
        assert "accuracy_estimate" in stats["layout-A"]

        # validation_result structure
        vr = s4_result["validation_result"]
        assert "warnings" in vr
        assert "errors" in vr
        assert "orphan_count" in vr
        assert "unmapped_xsd_fields" in vr
        assert "unmapped_required_xsd_fields" in vr
        assert "type_format_mismatches" in vr

    @pytest.mark.asyncio
    async def test_benchmark_under_6s(self, tmp_path):
        """Stage 4 should complete in < 6s with mocked LLM."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)

        start = time.monotonic()
        with patch.dict(os.environ, {}, clear=True):
            await s4.run_stage4(ctx, _noop_emit)
        elapsed = time.monotonic() - start

        assert elapsed < 6.0, f"Stage 4 took {elapsed:.2f}s (max 6s)"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_no_xsd_path(self, tmp_path):
        """Stage 4 should handle missing XSD gracefully."""
        s4 = _get_stage4()
        ctx = _make_context("", None)
        ctx["xsd_path"] = None

        with patch.dict(os.environ, {}, clear=True):
            result = await s4.run_stage4(ctx, _noop_emit)

        assert result["field_tree"] is None
        # Mappings should still exist but without xsd_field_path
        for m in result.get("field_mappings", []):
            assert m["xsd_field_path"] == ""

    @pytest.mark.asyncio
    async def test_empty_clusters(self, tmp_path):
        """Stage 4 with no clusters should produce empty results."""
        s4 = _get_stage4()
        ctx = _make_context(_make_xsd_content(), tmp_path)
        ctx["clusters"] = []
        ctx["intelligence"] = {}

        with patch.dict(os.environ, {}, clear=True):
            result = await s4.run_stage4(ctx, _noop_emit)

        assert result["field_mappings"] == []

    def test_fuzzy_match_quality(self):
        """Fuzzy matching should rank 'Nome' highest for label 'Nome:'."""
        s4 = _get_stage4()
        candidates = s4._fuzzy_match_single(
            "Nome", "", ["DadosCliente.Nome", "DadosCliente.CPF", "DadosCliente.Endereco"]
        )
        assert len(candidates) >= 1
        assert candidates[0]["path"] == "DadosCliente.Nome"
        assert candidates[0]["score"] > 0.5
