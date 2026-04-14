"""Unit tests for Story 48.4 — Stage 3: detecção de seções repetidas.

Covers:
- AC1: detect_repeated_sections() identifica lista simples (N≥2 blocos similares)
- AC3: list_item_count, item_template, instances corretos
- AC4: sem falsa detecção em blocos diferentes
- AC6: collect_repeated_block_ids não double-counts blocos
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from models.pipeline_context import RepeatedSection
from services.stages.stage3_structural.repeated_sections import (
    collect_repeated_block_ids,
    detect_repeated_sections,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_block(bid: str, x0: float, y0: float, x1: float, y1: float, text: str) -> dict[str, Any]:
    return {
        "id": bid,
        "bbox": [x0, y0, x1, y1],
        "text": text,
    }


def _similar_blocks_column(
    n: int,
    x0: float = 50.0,
    width: float = 200.0,
    y_start: float = 100.0,
    y_step: float = 30.0,
    text_prefix: str = "Item",
) -> list[dict[str, Any]]:
    """Cria N blocos com posição/largura similar em y progressivos."""
    blocks = []
    for i in range(n):
        y0 = y_start + i * y_step
        y1 = y0 + 20.0
        text = f"{text_prefix} {i + 1}"
        bid = f"block_{uuid.uuid4().hex[:6]}"
        blocks.append(_make_block(bid, x0, y0, x0 + width, y1, text))
    return blocks


# ---------------------------------------------------------------------------
# AC1 — Detecção de lista simples
# ---------------------------------------------------------------------------


def test_detect_simple_list():
    """3 blocos com mesma posição/largura em y progressivos → 1 RepeatedSection."""
    blocks = _similar_blocks_column(n=3, y_step=40.0)
    result = detect_repeated_sections(blocks, page_index=0)

    assert len(result) == 1
    rs = result[0]
    assert isinstance(rs, RepeatedSection)
    assert rs.list_item_count == 3
    assert len(rs.instances) == 3
    assert rs.page_index == 0


def test_detect_minimum_two_occurrences():
    """2 blocos similares → RepeatedSection (valor mínimo)."""
    blocks = _similar_blocks_column(n=2, y_step=50.0)
    result = detect_repeated_sections(blocks, min_occurrences=2)
    assert len(result) == 1
    assert result[0].list_item_count == 2


def test_no_detection_single_block():
    """1 único bloco → nenhuma seção repetida."""
    blocks = _similar_blocks_column(n=1)
    result = detect_repeated_sections(blocks)
    assert result == []


# ---------------------------------------------------------------------------
# AC3 — Instâncias com bbox e textos corretos
# ---------------------------------------------------------------------------


def test_instances_have_correct_data():
    """instances devem conter bbox e texts de cada bloco."""
    blocks = [
        _make_block("b1", 50.0, 100.0, 250.0, 120.0, "JOAO DA SILVA"),
        _make_block("b2", 50.0, 140.0, 250.0, 160.0, "MARIA SANTOS"),
        _make_block("b3", 50.0, 180.0, 250.0, 200.0, "PEDRO LIMA"),
    ]
    result = detect_repeated_sections(blocks, tolerance_x=5.0, tolerance_w=5.0)

    assert len(result) == 1
    rs = result[0]

    texts = [inst.texts[0] for inst in rs.instances]
    assert "JOAO DA SILVA" in texts
    assert "MARIA SANTOS" in texts
    assert "PEDRO LIMA" in texts

    for inst in rs.instances:
        assert len(inst.bbox) == 4


def test_instances_ordered_by_y():
    """Instâncias devem estar em ordem crescente de y."""
    blocks = [
        _make_block("b3", 50.0, 180.0, 250.0, 200.0, "Terceiro"),
        _make_block("b1", 50.0, 100.0, 250.0, 120.0, "Primeiro"),
        _make_block("b2", 50.0, 140.0, 250.0, 160.0, "Segundo"),
    ]
    result = detect_repeated_sections(blocks, tolerance_x=5.0, tolerance_w=5.0)
    assert len(result) == 1
    y_values = [inst.bbox[1] for inst in result[0].instances]
    assert y_values == sorted(y_values)


def test_bbox_envelope_covers_all_instances():
    """bbox_envelope deve englobar todas as instâncias."""
    # Blocos com posições/larguras que ficam no mesmo bucket (tol_x=10, tol_w=15)
    # x0=50→bucket 5; x0=52→bucket 5; x0=49→bucket 5 (todos iguais com tol=10)
    # width=200 para todos → mesmo bucket
    blocks = [
        _make_block("b1", 50.0, 100.0, 250.0, 120.0, "Aa Bb"),
        _make_block("b2", 52.0, 140.0, 252.0, 160.0, "Cc Dd"),
        _make_block("b3", 49.0, 180.0, 249.0, 200.0, "Ee Ff"),
    ]
    result = detect_repeated_sections(blocks, tolerance_x=10.0, tolerance_w=15.0)
    assert len(result) == 1
    env = result[0].bbox_envelope

    assert env[0] <= 49.0  # x0_min
    assert env[1] <= 100.0  # y0_min
    assert env[2] >= 252.0  # x1_max
    assert env[3] >= 200.0  # y1_max


# ---------------------------------------------------------------------------
# AC4 — Sem falsa detecção em blocos diferentes
# ---------------------------------------------------------------------------


def test_no_false_positive_different_widths():
    """Blocos com larguras muito diferentes não devem ser agrupados."""
    blocks = [
        _make_block("b1", 50.0, 100.0, 150.0, 120.0, "Curto"),  # largura 100
        _make_block("b2", 50.0, 140.0, 400.0, 160.0, "Muito longo texto aqui"),  # largura 350
        _make_block("b3", 50.0, 180.0, 150.0, 200.0, "Curto 2"),  # largura 100
    ]
    # tolerance_w pequeno → não agrupa larguras muito diferentes
    result = detect_repeated_sections(blocks, tolerance_x=5.0, tolerance_w=10.0)

    for rs in result:
        # Nenhum grupo deve ter blocos com larguras muito diferentes
        for inst in rs.instances:
            width = inst.bbox[2] - inst.bbox[0]
            assert abs(width - (rs.instances[0].bbox[2] - rs.instances[0].bbox[0])) < 50


def test_no_false_positive_overlapping_y():
    """Blocos na mesma posição y (sobrepostos) não formam lista válida."""
    blocks = [
        _make_block("b1", 50.0, 100.0, 250.0, 120.0, "Coluna 1"),
        _make_block("b2", 270.0, 100.0, 470.0, 120.0, "Coluna 2"),  # mesmo y, diferente x
        _make_block("b3", 490.0, 100.0, 595.0, 120.0, "Coluna 3"),  # mesmo y, diferente x
    ]
    # Todos no mesmo y → y_span muito pequeno → não é lista
    result = detect_repeated_sections(blocks, tolerance_x=5.0, tolerance_w=10.0)
    # Mesmo que sejam agrupados, y_span < min_span → filtrado
    for rs in result:
        y_positions = [inst.bbox[1] for inst in rs.instances]
        y_span = max(y_positions) - min(y_positions)
        # Seções com y_span zero não deveriam chegar aqui
        assert y_span > 0


def test_no_detection_empty_blocks():
    """Lista vazia de blocos → retorna lista vazia."""
    result = detect_repeated_sections([])
    assert result == []


# ---------------------------------------------------------------------------
# AC6 — collect_repeated_block_ids sem double-counting
# ---------------------------------------------------------------------------


def test_collect_block_ids_no_duplicates():
    """collect_repeated_block_ids deve retornar conjunto sem duplicatas."""
    blocks = _similar_blocks_column(n=4, y_step=35.0)
    result = detect_repeated_sections(blocks, page_index=0)
    assert len(result) >= 1

    ids = collect_repeated_block_ids(result)
    assert len(ids) == len(set(ids))  # conjunto — sem duplicatas por definição
    assert all(isinstance(i, str) for i in ids)


def test_collect_block_ids_covers_all_instances():
    """Todos os block_ids das instâncias devem aparecer no resultado."""
    blocks = [
        _make_block("blk-001", 50.0, 100.0, 250.0, 120.0, "Alpha"),
        _make_block("blk-002", 50.0, 140.0, 250.0, 160.0, "Beta"),
        _make_block("blk-003", 50.0, 180.0, 250.0, 200.0, "Gamma"),
    ]
    result = detect_repeated_sections(blocks, tolerance_x=5.0, tolerance_w=5.0)
    assert len(result) >= 1

    ids = collect_repeated_block_ids(result)
    assert "blk-001" in ids
    assert "blk-002" in ids
    assert "blk-003" in ids


def test_collect_block_ids_empty():
    """Sem seções repetidas → conjunto vazio."""
    ids = collect_repeated_block_ids([])
    assert ids == set()


# ---------------------------------------------------------------------------
# item_template: dynamic vs static detection
# ---------------------------------------------------------------------------


def test_dynamic_field_detected():
    """Textos diferentes entre instâncias → field_type='dynamic'."""
    blocks = [
        _make_block("b1", 50.0, 100.0, 250.0, 120.0, "11246695424051"),
        _make_block("b2", 50.0, 140.0, 250.0, 160.0, "11476252815481"),
        _make_block("b3", 50.0, 180.0, 250.0, 200.0, "98765432109876"),
    ]
    result = detect_repeated_sections(blocks, tolerance_x=5.0, tolerance_w=5.0)
    assert len(result) == 1
    field = result[0].item_template.fields[0]
    assert field.field_type == "dynamic"
    assert field.value is None


def test_static_field_detected():
    """Textos idênticos entre instâncias → field_type='static'."""
    blocks = [
        _make_block("b1", 50.0, 100.0, 250.0, 120.0, "Previdência VG"),
        _make_block("b2", 50.0, 140.0, 250.0, 160.0, "Previdência VG"),
        _make_block("b3", 50.0, 180.0, 250.0, 200.0, "Previdência VG"),
    ]
    result = detect_repeated_sections(blocks, tolerance_x=5.0, tolerance_w=5.0)
    assert len(result) == 1
    field = result[0].item_template.fields[0]
    assert field.field_type == "static"
    assert field.value == "Previdência VG"
