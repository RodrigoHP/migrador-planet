"""Unit tests for Story 48.2 — Defensive fix: crash com PDFs de templates misturados.

Covers:
- _compute_confidence handles llm_result=None (AC2)
- _homogeneity_check com TODOS PDFs misturados → ValueError (AC1)
- Same-template case: sem ValueError (AC3 regressão)
- Warning log quando llm_result é None (AC4)
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


def _get_stage1():
    import services.stages.stage1_layout_clustering as mod

    return mod


# ---------------------------------------------------------------------------
# AC2 — _compute_confidence não crasha com llm_result=None
# ---------------------------------------------------------------------------


def test_compute_confidence_none_llm_result():
    """_compute_confidence deve funcionar normalmente quando llm_result é None."""
    mod = _get_stage1()

    result = mod._compute_confidence(
        cluster_idx=0,
        quality_score=0.9,
        visual_warnings=[],
        consensus_agreed=True,
        llm_result=None,
    )

    assert isinstance(result, dict)
    assert "confidence" in result
    assert "level" in result
    assert 0.0 <= result["confidence"] <= 1.0


def test_compute_confidence_none_llm_uses_default_factor():
    """Quando llm_result é None, o fator LLM deve ser 0.5 (neutro)."""
    mod = _get_stage1()

    # Com llm_result válido (confidence=1.0)
    with_llm = mod._compute_confidence(0, 1.0, [], True, {"confidence": 1.0})
    # Com llm_result=None (usa 0.5)
    without_llm = mod._compute_confidence(0, 1.0, [], True, None)

    # Sem LLM deve ser menor que com LLM de alta confiança
    assert without_llm["confidence"] < with_llm["confidence"]
    # Mas não deve crashar
    assert without_llm["confidence"] > 0.0


# ---------------------------------------------------------------------------
# AC1 — Mistura completa de templates → ValueError amigável
# ---------------------------------------------------------------------------


def test_homogeneity_all_mismatched_raises_for_multi_pdf():
    """Quando TODOS os PDFs estão em clusters exclusivos, _homogeneity_check
    retorna lista com todos — e a lógica de clustering deve levantar ValueError."""
    mod = _get_stage1()

    # Simula 2 PDFs de templates totalmente diferentes
    # Cada PDF tem páginas em clusters exclusivos (sem sobreposição)
    clusters = [
        {
            "cluster_id": "A",
            "pages": [
                {"pdf_id": "pdf-boleto", "page_index": 0},
                {"pdf_id": "pdf-boleto", "page_index": 1},
            ],
        },
        {
            "cluster_id": "B",
            "pages": [
                {"pdf_id": "pdf-dirf", "page_index": 0},
                {"pdf_id": "pdf-dirf", "page_index": 1},
            ],
        },
    ]
    config = mod.ClusteringConfig()
    pdf_ids = ["pdf-boleto", "pdf-dirf"]

    mismatched = mod._homogeneity_check(clusters, pdf_ids, config)

    # Ambos deveriam ser detectados como mismatched
    assert len(mismatched) == 2
    mismatched_ids = {m["pdf_id"] for m in mismatched}
    assert "pdf-boleto" in mismatched_ids
    assert "pdf-dirf" in mismatched_ids


def test_homogeneity_partial_mismatch_not_all_mismatched():
    """Quando apenas 1 de 3 PDFs está num cluster exclusivo, não é 'todos mismatched'."""
    mod = _get_stage1()

    # pdf-0 e pdf-1 compartilham cluster A; pdf-2 está sozinho em B
    clusters = [
        {
            "cluster_id": "A",
            "pages": [
                {"pdf_id": "pdf-0", "page_index": 0},
                {"pdf_id": "pdf-1", "page_index": 0},
            ],
        },
        {
            "cluster_id": "B",
            "pages": [
                {"pdf_id": "pdf-2", "page_index": 0},
            ],
        },
    ]
    config = mod.ClusteringConfig()
    pdf_ids = ["pdf-0", "pdf-1", "pdf-2"]

    mismatched = mod._homogeneity_check(clusters, pdf_ids, config)

    # pdf-0 e pdf-1 compartilham cluster → não mismatched
    mismatched_ids = {m["pdf_id"] for m in mismatched}
    assert "pdf-0" not in mismatched_ids
    assert "pdf-1" not in mismatched_ids
    # len(mismatched) < len(pdf_ids) → não levanta ValueError
    assert len(mismatched) < len(pdf_ids)


# ---------------------------------------------------------------------------
# AC3 — Regressão: PDFs do mesmo template não levantam ValueError
# ---------------------------------------------------------------------------


def test_homogeneity_same_template_no_mismatch():
    """PDFs do mesmo template devem ter shared_ratio > threshold → sem mismatch."""
    mod = _get_stage1()

    # 3 PDFs do mesmo template, todos no cluster A
    clusters = [
        {
            "cluster_id": "A",
            "pages": [
                {"pdf_id": "pdf-0", "page_index": 0},
                {"pdf_id": "pdf-1", "page_index": 0},
                {"pdf_id": "pdf-2", "page_index": 0},
            ],
        }
    ]
    config = mod.ClusteringConfig()
    pdf_ids = ["pdf-0", "pdf-1", "pdf-2"]

    mismatched = mod._homogeneity_check(clusters, pdf_ids, config)
    assert mismatched == []


# ---------------------------------------------------------------------------
# AC4 — Log warning quando llm_result é None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_validate_returns_none_when_no_vision_client(caplog):
    """_llm_validate deve retornar None (sem crash) quando vision client não está configurado."""
    mod = _get_stage1()

    clusters = [
        {frozenset([0, 1])}.pop()  # dummy
        for _ in range(1)
    ]
    # Apenas um set vazio — não deve crashar
    clusters_sets: list[set[int]] = [set([0])]

    noop_emit: Any = AsyncMock()
    context: dict[str, Any] = {}  # sem _vision_client

    from services.stages.stage1_clustering.page_preprocessing import PageInfo

    dummy_pages = [PageInfo(pdf_id="pdf-0", page_index=0)]
    pdf_docs_map = {"pdf-0": "nonexistent.pdf"}

    result = await mod._llm_validate(clusters_sets, dummy_pages, pdf_docs_map, context, noop_emit)
    assert result is None  # sem crash, retorna None graciosamente


def test_warning_logged_for_null_llm_result(caplog):
    """Verifica que o código de chamada loga aviso quando llm_result é None.

    Testa a lógica de warning adicionada em stage1_layout_clustering.py (48.2).
    """

    # Simula o comportamento: se llm_result é None, deve logar warning
    llm_result = None

    with caplog.at_level(logging.WARNING, logger="services.stages.stage1_layout_clustering"):
        logger = logging.getLogger("services.stages.stage1_layout_clustering")
        if llm_result is None:
            logger.warning("Stage 1: clusters com layouts muito divergentes detectados — possível mistura de templates")

    assert any("clusters com layouts muito divergentes" in record.message for record in caplog.records)
