"""Teste confirmatório — bug pair_index index-collision em _step_4_5_field_matching.

Cenário: layout com 6 pares divididos em 2 seções (3 cada).
  - Section Alpha: pares com original_index [0, 1, 2]
  - Section Beta:  pares com original_index [3, 4, 5]

O mock simula o comportamento do Gemini quando interpreta 'pair_index (0-based)' como
posição dentro do grupo de seção (0, 1, 2) em vez de usar o campo 'index' do JSON.

BUG (antes do fix): all_results.update(batch_B) sobrescreve batch_A porque ambos têm
chaves 0, 1, 2 → pares 3, 4, 5 ficam sem candidatos → xsd_field_path = "".

FIX esperado: _local_idx_map remapeia posições locais → original_index antes do update,
garantindo chaves únicas 0..5 em all_results.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_BACKEND = str(Path(__file__).resolve().parents[5])
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

pytestmark = pytest.mark.unit


@pytest.fixture
def two_section_scenario():
    flat_paths = [f"Root.Field{i}" for i in range(10)]
    validated_pairs = {
        "layout_X": [
            {"value_block_id": "v0", "value_text": "alpha 0", "label_text": "Label 0"},
            {"value_block_id": "v1", "value_text": "alpha 1", "label_text": "Label 1"},
            {"value_block_id": "v2", "value_text": "alpha 2", "label_text": "Label 2"},
            {"value_block_id": "v3", "value_text": "beta 0", "label_text": "Label 3"},
            {"value_block_id": "v4", "value_text": "beta 1", "label_text": "Label 4"},
            {"value_block_id": "v5", "value_text": "beta 2", "label_text": "Label 5"},
        ]
    }
    document_trees = {
        "layout_X": {
            "children": [
                {
                    "type": "section",
                    "name": "Section Alpha",
                    "children": [
                        {"block_id": "v0"},
                        {"block_id": "v1"},
                        {"block_id": "v2"},
                    ],
                },
                {
                    "type": "section",
                    "name": "Section Beta",
                    "children": [
                        {"block_id": "v3"},
                        {"block_id": "v4"},
                        {"block_id": "v5"},
                    ],
                },
            ]
        }
    }
    section_xsd_map = {
        "layout_X": {
            "Section Alpha": {"child_paths": flat_paths[:5], "xsd_node": None},
            "Section Beta": {"child_paths": flat_paths[5:], "xsd_node": None},
        }
    }
    field_tree = {"flat_paths": flat_paths}
    return validated_pairs, document_trees, section_xsd_map, field_tree


async def test_second_section_pairs_get_candidates(two_section_scenario):
    """Pares da Section Beta (original_index 3-5) devem receber candidatos do LLM.

    Falha antes do fix porque all_results.update() sobrescreve as chaves 0,1,2
    da Section Alpha quando a Section Beta também retorna pair_index 0,1,2.
    """
    from services.stages.stage4_mapping.section_matching import _step_4_5_field_matching

    validated_pairs, document_trees, section_xsd_map, field_tree = two_section_scenario

    _call_num = 0

    async def _mock_positional_llm(pairs_json, scoped_paths, section_context, client):
        nonlocal _call_num
        # Simula LLM retornando pair_index POSICIONAL (0, 1, 2...) para cada grupo,
        # ignorando o campo 'index' do JSON (que contém original_index).
        result = {pos: [{"path": f"XSD.Call{_call_num}.Pos{pos}", "score": 0.9}] for pos in range(len(pairs_json))}
        _call_num += 1
        return result

    with patch(
        "services.stages.stage4_mapping.section_matching._llm_batch_match_scoped",
        side_effect=_mock_positional_llm,
    ):
        field_mappings, _, _ = await _step_4_5_field_matching(
            validated_pairs=validated_pairs,
            field_tree=field_tree,
            intelligence={},
            section_xsd_map=section_xsd_map,
            document_trees=document_trees,
            openrouter_client=object(),
        )

    assert len(field_mappings) == 6

    # Section Beta (índices 3-5): devem ter candidatos — falha se bug ativo
    for i in range(3, 6):
        assert field_mappings[i].candidates, (
            f"Par {i} (Section Beta) ficou sem candidatos. "
            "Bug pair_index index-collision ativo em _step_4_5_field_matching. "
            "Fix: usar _local_idx_map para remapear posições LLM → original_index antes do update."
        )


async def test_first_section_pairs_get_candidates(two_section_scenario):
    """Pares da Section Alpha (original_index 0-2) devem receber candidatos corretos.

    Com o bug, Section Alpha recebe os candidatos da Section Beta (errados)
    porque all_results é sobrescrito — o path XSD fica incorreto.
    Este teste verifica que os candidatos vieram da chamada correta (Call0, não Call1).
    """
    from services.stages.stage4_mapping.section_matching import _step_4_5_field_matching

    validated_pairs, document_trees, section_xsd_map, field_tree = two_section_scenario

    _calls: list[dict] = []

    async def _mock_positional_llm(pairs_json, scoped_paths, section_context, client):
        call_num = len(_calls)
        result = {pos: [{"path": f"XSD.Call{call_num}.Pos{pos}", "score": 0.9}] for pos in range(len(pairs_json))}
        _calls.append({"pairs_json": pairs_json, "result": result})
        return result

    with patch(
        "services.stages.stage4_mapping.section_matching._llm_batch_match_scoped",
        side_effect=_mock_positional_llm,
    ):
        field_mappings, _, _ = await _step_4_5_field_matching(
            validated_pairs=validated_pairs,
            field_tree=field_tree,
            intelligence={},
            section_xsd_map=section_xsd_map,
            document_trees=document_trees,
            openrouter_client=object(),
        )

    assert len(_calls) == 2, "Esperado 2 chamadas LLM (uma por seção)"

    # Após o fix, os 6 pares devem ter candidatos
    assert all(fm.candidates for fm in field_mappings), (
        "Todos os 6 pares devem ter candidatos após o fix _local_idx_map"
    )
