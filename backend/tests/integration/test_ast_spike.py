"""Integration tests for AST spike — C1 and C2 validation.

Spike: spike/ast-validation

C1: Stage 3 → ast_emitter → PlanetAstV0 valid for Boleto Individual + Posição Consolidada
C2: extract_field_pairs_multi produces pairs consumable by Stage 4 (ast_field_pairs in context)

Test strategy:
  - Build realistic DocumentTreeNode dicts that mirror tree_builder.py output
  - Run ast_emitter.emit() on them
  - Validate PlanetAstV0 structure and content
  - Run Stage 4 consume_ast path, verify ast_field_pairs produced

LLM NOT required — all LLM calls skipped (no OPENROUTER_API_KEY in test env).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_BACKEND = str(Path(__file__).resolve().parents[2])
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest

from models.ast.nodes import PageNode, PlanetAstV0
from services.stages.stage3_structural.ast_emitter import (
    emit,
    extract_field_pairs,
    extract_field_pairs_multi,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures — realistic Stage 3 tree dicts per layout type
# ---------------------------------------------------------------------------


def _make_boleto_tree() -> dict[str, Any]:
    """Realistic tree dict for Boleto Individual (mirrors tree_builder output)."""
    return {
        "id": "root-boleto",
        "type": "page",
        "page_index": 0,
        "width": 595.0,
        "height": 842.0,
        "children": [
            {
                "id": "zone-header",
                "type": "zone",
                "name": "Cabeçalho",
                "bbox": [0, 0, 595, 80],
                "children": [
                    {
                        "id": "lbl-banco",
                        "type": "label",
                        "text": "Banco:",
                        "bbox": [10, 10, 80, 20],
                        "block_id": "b001",
                    },
                    {
                        "id": "val-banco",
                        "type": "value",
                        "text": "341-7",
                        "bbox": [85, 10, 200, 20],
                        "block_id": "b002",
                        "suggested_binding": "boleto.codigoBanco",
                    },
                ],
            },
            {
                "id": "zone-datas",
                "type": "zone",
                "name": "Datas",
                "bbox": [0, 90, 595, 160],
                "children": [
                    {
                        "id": "lbl-vencimento",
                        "type": "label",
                        "text": "Vencimento:",
                        "bbox": [10, 95, 100, 110],
                        "block_id": "b003",
                    },
                    {
                        "id": "val-vencimento",
                        "type": "value",
                        "text": "15/03/2024",
                        "bbox": [105, 95, 200, 110],
                        "block_id": "b004",
                        "suggested_binding": "boleto.dataVencimento",
                    },
                    {
                        "id": "lbl-valor",
                        "type": "label",
                        "text": "Valor:",
                        "bbox": [250, 95, 300, 110],
                        "block_id": "b005",
                    },
                    {
                        "id": "val-valor",
                        "type": "value",
                        "text": "R$ 1.234,56",
                        "bbox": [305, 95, 420, 110],
                        "block_id": "b006",
                        "suggested_binding": "boleto.valorDocumento",
                    },
                ],
            },
            {
                "id": "img-barcode",
                "type": "barcode",
                "bbox": [10, 700, 585, 740],
                "name": "codigoBarras",
            },
        ],
    }


def _make_boleto_classifications() -> dict[str, dict[str, Any]]:
    """Block classifications for boleto — mirrors Stage 3.3 output."""
    return {
        "b001": {"semantic": "label", "stability": "stable"},
        "b002": {"semantic": "dynamic", "stability": "variable"},
        "b003": {"semantic": "label", "stability": "stable"},
        "b004": {"semantic": "dynamic", "stability": "variable"},
        "b005": {"semantic": "label", "stability": "stable"},
        "b006": {"semantic": "dynamic", "stability": "variable"},
    }


def _make_posicao_tree() -> dict[str, Any]:
    """Realistic tree dict for Posição Consolidada (multi-section relatorio)."""
    return {
        "id": "root-posicao",
        "type": "page",
        "page_index": 0,
        "width": 595.0,
        "height": 842.0,
        "children": [
            {
                "id": "zone-header",
                "type": "zone",
                "name": "Identificação",
                "bbox": [0, 0, 595, 100],
                "children": [
                    {
                        "id": "lbl-nome",
                        "type": "label",
                        "text": "Nome do Segurado:",
                        "bbox": [10, 10, 150, 25],
                        "block_id": "p001",
                    },
                    {
                        "id": "val-nome",
                        "type": "value",
                        "text": "João da Silva",
                        "bbox": [155, 10, 400, 25],
                        "block_id": "p002",
                        "suggested_binding": "segurado.nome",
                    },
                    {
                        "id": "lbl-data",
                        "type": "label",
                        "text": "Data de Referência:",
                        "bbox": [10, 30, 160, 45],
                        "block_id": "p003",
                    },
                    {
                        "id": "val-data",
                        "type": "value",
                        "text": "31/12/2023",
                        "bbox": [165, 30, 280, 45],
                        "block_id": "p004",
                        "suggested_binding": "relatorio.dataReferencia",
                    },
                ],
            },
            {
                "id": "zone-posicao",
                "type": "section",
                "name": "Posição de Investimentos",
                "bbox": [0, 110, 595, 400],
                "children": [
                    {
                        "id": "lbl-saldo",
                        "type": "label",
                        "text": "Saldo Total:",
                        "bbox": [10, 120, 100, 135],
                        "block_id": "p005",
                    },
                    {
                        "id": "val-saldo",
                        "type": "value",
                        "text": "R$ 50.000,00",
                        "bbox": [105, 120, 250, 135],
                        "block_id": "p006",
                        "suggested_binding": "posicao.saldoTotal",
                    },
                    {
                        "id": "lbl-rentab",
                        "type": "label",
                        "text": "Rentabilidade:",
                        "bbox": [300, 120, 420, 135],
                        "block_id": "p007",
                    },
                    {
                        "id": "val-rentab",
                        "type": "value",
                        "text": "12,50%",
                        "bbox": [425, 120, 520, 135],
                        "block_id": "p008",
                        "suggested_binding": "posicao.rentabilidade",
                    },
                ],
            },
            {
                "id": "rs-fundos",
                "type": "repeated_section",
                "name": "list_3_items",
                "bbox": [0, 420, 595, 600],
                "children": [
                    {"type": "list_item", "text": "Fundo A — R$ 10.000,00", "bbox": [0, 430, 595, 445]},
                    {"type": "list_item", "text": "Fundo B — R$ 20.000,00", "bbox": [0, 450, 595, 465]},
                    {"type": "list_item", "text": "Fundo C — R$ 20.000,00", "bbox": [0, 470, 595, 485]},
                ],
            },
        ],
    }


def _make_posicao_classifications() -> dict[str, dict[str, Any]]:
    return {
        "p001": {"semantic": "label", "stability": "stable"},
        "p002": {"semantic": "dynamic", "stability": "variable"},
        "p003": {"semantic": "label", "stability": "stable"},
        "p004": {"semantic": "dynamic", "stability": "variable"},
        "p005": {"semantic": "label", "stability": "stable"},
        "p006": {"semantic": "dynamic", "stability": "variable"},
        "p007": {"semantic": "label", "stability": "stable"},
        "p008": {"semantic": "dynamic", "stability": "variable"},
    }


# ---------------------------------------------------------------------------
# C1: Stage 3 → AST v0 emission
# ---------------------------------------------------------------------------


class TestC1AstEmission:
    """C1: validates that ast_emitter.emit() produces valid PlanetAstV0 for both types."""

    def test_boleto_emits_valid_ast(self):
        tree = _make_boleto_tree()
        bc = _make_boleto_classifications()
        ast = emit(tree, bc, layout_type_id="boleto-individual", cluster_id="cluster-boleto")

        assert isinstance(ast, PlanetAstV0)
        assert ast.schema_version == "planet-ast-v0"
        assert ast.layout_type_id == "boleto-individual"

    def test_boleto_root_is_page_node(self):
        ast = emit(_make_boleto_tree(), _make_boleto_classifications())
        assert isinstance(ast.root, PageNode)
        assert ast.root.page_num == 0

    def test_boleto_has_field_nodes(self):
        ast = emit(_make_boleto_tree(), _make_boleto_classifications())
        pairs = extract_field_pairs(ast)
        assert len(pairs) > 0, "Expected FieldNode pairs from boleto AST"

    def test_boleto_date_field_has_correct_formatter(self):
        ast = emit(_make_boleto_tree(), _make_boleto_classifications())
        pairs = extract_field_pairs(ast)
        date_pairs = [p for p in pairs if "vencimento" in p["bind_path"].lower() or "data" in p["bind_path"].lower()]
        if date_pairs:
            assert date_pairs[0]["formatter"]["kind"] == "date"

    def test_boleto_currency_field_has_correct_formatter(self):
        ast = emit(_make_boleto_tree(), _make_boleto_classifications())
        pairs = extract_field_pairs(ast)
        currency_pairs = [p for p in pairs if "valor" in p["bind_path"].lower()]
        if currency_pairs:
            assert currency_pairs[0]["formatter"]["kind"] == "currency"

    def test_posicao_emits_valid_ast(self):
        tree = _make_posicao_tree()
        bc = _make_posicao_classifications()
        ast = emit(tree, bc, layout_type_id="posicao-consolidada", cluster_id="cluster-posicao")

        assert isinstance(ast, PlanetAstV0)
        assert ast.layout_type_id == "posicao-consolidada"

    def test_posicao_has_field_nodes(self):
        ast = emit(_make_posicao_tree(), _make_posicao_classifications())
        pairs = extract_field_pairs(ast)
        assert len(pairs) > 0, "Expected FieldNode pairs from posicao AST"

    def test_posicao_has_repeating_section(self):
        from models.ast.nodes import RepeatingNode

        ast = emit(_make_posicao_tree(), _make_posicao_classifications())
        page = ast.root
        assert isinstance(page, PageNode)
        repeating_nodes = [c for c in page.children if isinstance(c, RepeatingNode)]
        assert len(repeating_nodes) >= 1, "Expected RepeatingNode from repeated_section"

    def test_posicao_percent_formatter(self):
        ast = emit(_make_posicao_tree(), _make_posicao_classifications())
        pairs = extract_field_pairs(ast)
        percent_pairs = [p for p in pairs if "rentab" in p["bind_path"].lower()]
        if percent_pairs:
            assert percent_pairs[0]["formatter"]["kind"] == "percent"

    def test_ast_round_trip_serialization(self):
        ast = emit(_make_boleto_tree(), _make_boleto_classifications())
        dumped = ast.model_dump()
        restored = PlanetAstV0.model_validate(dumped)
        assert restored.schema_version == ast.schema_version
        assert isinstance(restored.root, PageNode)

    def test_both_types_gate(self):
        """C1 gate: 2/2 types must produce valid AST."""
        boleto_ast = emit(_make_boleto_tree(), _make_boleto_classifications(), "boleto-individual")
        posicao_ast = emit(_make_posicao_tree(), _make_posicao_classifications(), "posicao-consolidada")

        assert isinstance(boleto_ast, PlanetAstV0), "Boleto AST failed"
        assert isinstance(posicao_ast, PlanetAstV0), "Posicao AST failed"
        # Both must have at least one FieldNode
        assert len(extract_field_pairs(boleto_ast)) > 0, "Boleto has no FieldNodes"
        assert len(extract_field_pairs(posicao_ast)) > 0, "Posicao has no FieldNodes"


# ---------------------------------------------------------------------------
# C2: Stage 4 consume_ast path
# ---------------------------------------------------------------------------


class TestC2Stage4ConsumeAst:
    """C2: validates that Stage 4 ast patch produces ast_field_pairs in context."""

    def _make_ast_trees(self) -> dict[str, PlanetAstV0]:
        return {
            "boleto-individual": emit(_make_boleto_tree(), _make_boleto_classifications(), "boleto-individual"),
            "posicao-consolidada": emit(_make_posicao_tree(), _make_posicao_classifications(), "posicao-consolidada"),
        }

    def test_extract_field_pairs_multi_non_empty(self):
        ast_trees = self._make_ast_trees()
        pairs = extract_field_pairs_multi(ast_trees)
        assert len(pairs) > 0

    def test_pairs_have_required_keys(self):
        ast_trees = self._make_ast_trees()
        pairs = extract_field_pairs_multi(ast_trees)
        for p in pairs:
            assert "bind_path" in p, f"Missing bind_path: {p}"
            assert "formatter" in p, f"Missing formatter: {p}"
            assert "bbox" in p, f"Missing bbox: {p}"
            assert "layout_type_id" in p, f"Missing layout_type_id: {p}"

    def test_pairs_bbox_is_list_of_4(self):
        ast_trees = self._make_ast_trees()
        pairs = extract_field_pairs_multi(ast_trees)
        for p in pairs:
            assert isinstance(p["bbox"], list)
            assert len(p["bbox"]) == 4

    @pytest.mark.asyncio
    async def test_stage4_context_gets_ast_pairs(self):
        """C2 gate: run_stage4 with consume_ast=True sets context['ast_field_pairs']."""
        import os

        os.environ.setdefault("AUTH_DISABLED", "true")

        from services.stages.stage4_field_mapping import run_stage4

        ast_trees = self._make_ast_trees()
        context: dict[str, Any] = {
            "consume_ast": True,
            "ast_trees": ast_trees,
            "document_trees": {},
            "intelligence": {},
            "clusters": [],
            "visual_analysis": {},
            "label_value_pairs": {},
            "xsd_path": "",
        }

        async def _noop_emit(event: dict[str, Any]) -> None:
            pass

        await run_stage4(context, _noop_emit)

        assert "ast_field_pairs" in context, "Stage 4 did not set ast_field_pairs in context"
        assert len(context["ast_field_pairs"]) > 0, "ast_field_pairs is empty"
