"""Unit tests for Stage 4 two-pass deduplication in _step_4_5_field_matching.

RCA 2026-04-13: Pass 1 did not check `best['path'] not in used_paths`, allowing
two high-confidence pairs claiming the same XSD path to both receive
needs_pass2=False → duplicate xsd_field_paths in output.

Fix: added `and best["path"] not in used_paths` to the Pass 1 condition in
services/stages/stage4_mapping/section_matching.py:441.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _get_section_matching():
    import services.stages.stage4_mapping.section_matching as mod

    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LAYOUT_ID = "layout-A"
_SACADO_PATH = "sacado.nome"
_CEDENTE_PATH = "cedente.nome"

HIGH_SCORE = 0.95  # Above any reasonable HIGH_CONFIDENCE_THRESHOLD


def _make_pair(idx: int, label: str, value: str) -> dict[str, Any]:
    return {
        "value_block_id": f"blk-{idx}",
        "label_text": label,
        "value_text": value,
        "value_bbox": [0, idx * 20, 100, idx * 20 + 15],
        "detected_format": None,
    }


def _make_field_tree(paths: list[str]) -> dict[str, Any]:
    return {"flat_paths": paths, "fields": {}}


# ---------------------------------------------------------------------------
# Core regression test — Pass 1 dedup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_pass_no_duplicate_paths_when_both_pairs_high_confidence():
    """Two pairs both high-confidence for sacado.nome → only one gets it; the other falls through to Pass 2.

    This is the regression test for RCA 2026-04-13 (Pass 1 dedup missing).
    """
    mod = _get_section_matching()

    pair_a = _make_pair(0, "Nome Sacado", "EMPRESA A")
    pair_b = _make_pair(1, "Beneficiário", "EMPRESA B")
    pairs = [pair_a, pair_b]

    # Both pairs ranked sacado.nome first with high confidence
    mock_candidates = {
        0: [{"path": _SACADO_PATH, "score": HIGH_SCORE}, {"path": _CEDENTE_PATH, "score": 0.5}],
        1: [{"path": _SACADO_PATH, "score": HIGH_SCORE}, {"path": _CEDENTE_PATH, "score": 0.4}],
    }

    validated_pairs = {_LAYOUT_ID: pairs}
    field_tree = _make_field_tree([_SACADO_PATH, _CEDENTE_PATH])

    with patch.object(mod, "_fuzzy_batch_match", return_value=mock_candidates):
        field_mappings, _, _ = await mod._step_4_5_field_matching(
            validated_pairs=validated_pairs,
            field_tree=field_tree,
            intelligence={},
            section_xsd_map={},
            document_trees={},
            openrouter_client=None,  # triggers fuzzy path (mocked above)
        )

    assigned_paths = [m.xsd_field_path for m in field_mappings if m.xsd_field_path]
    unique_paths = set(assigned_paths)

    assert len(assigned_paths) == len(unique_paths), (
        f"Duplicate XSD paths found: {[p for p in assigned_paths if assigned_paths.count(p) > 1]}"
    )


@pytest.mark.asyncio
async def test_two_pass_second_pair_gets_next_best_candidate():
    """When sacado.nome is claimed by Pair A, Pair B must receive its 2nd-best candidate (cedente.nome)."""
    mod = _get_section_matching()

    pair_a = _make_pair(0, "Nome Sacado", "EMPRESA A")
    pair_b = _make_pair(1, "Beneficiário", "EMPRESA B")
    pairs = [pair_a, pair_b]

    mock_candidates = {
        0: [{"path": _SACADO_PATH, "score": HIGH_SCORE}, {"path": _CEDENTE_PATH, "score": 0.5}],
        1: [{"path": _SACADO_PATH, "score": HIGH_SCORE}, {"path": _CEDENTE_PATH, "score": 0.72}],
    }

    validated_pairs = {_LAYOUT_ID: pairs}
    field_tree = _make_field_tree([_SACADO_PATH, _CEDENTE_PATH])

    with patch.object(mod, "_fuzzy_batch_match", return_value=mock_candidates):
        field_mappings, _, _ = await mod._step_4_5_field_matching(
            validated_pairs=validated_pairs,
            field_tree=field_tree,
            intelligence={},
            section_xsd_map={},
            document_trees={},
            openrouter_client=None,
        )

    paths_by_block = {m.block_id: m.xsd_field_path for m in field_mappings}
    # Pair A gets sacado.nome (first claimer)
    assert paths_by_block["blk-0"] == _SACADO_PATH
    # Pair B falls to Pass 2 → gets next available (cedente.nome)
    assert paths_by_block["blk-1"] == _CEDENTE_PATH


@pytest.mark.asyncio
async def test_single_high_confidence_pair_unaffected():
    """Single high-confidence pair is not changed by the dedup fix."""
    mod = _get_section_matching()

    pair_a = _make_pair(0, "Nome Sacado", "EMPRESA A")
    pairs = [pair_a]

    mock_candidates = {
        0: [{"path": _SACADO_PATH, "score": HIGH_SCORE}],
    }

    validated_pairs = {_LAYOUT_ID: pairs}
    field_tree = _make_field_tree([_SACADO_PATH, _CEDENTE_PATH])

    with patch.object(mod, "_fuzzy_batch_match", return_value=mock_candidates):
        field_mappings, _, _ = await mod._step_4_5_field_matching(
            validated_pairs=validated_pairs,
            field_tree=field_tree,
            intelligence={},
            section_xsd_map={},
            document_trees={},
            openrouter_client=None,
        )

    assert field_mappings[0].xsd_field_path == _SACADO_PATH
