"""Tests for Story 5.11 — Bloco 7: Matching Semântico.

Covers:
- Stage 23 — Field Matching: label adjacency, fuzzy fallback, LLM mock, ambiguous detection
- Stage 24 — Format Detection: all regex patterns, JS function generation
- Stage 25 — Confidence Scoring: 5-factor calculation, thresholds, LLM mock fallback
- register_bloco7 and register_bloco8_confidence wire stages into registry
- Story 10.15 — field_mappings vazio: blocks without semantic_label and non-structural labels
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_block(
    text: str,
    bbox: Tuple[float, float, float, float],
    semantic_label: str = "value",
    page_number: int = 0,
    pdf_index: int = 0,
) -> Dict[str, Any]:
    return {
        "text": text,
        "bbox": bbox,
        "page_number": page_number,
        "pdf_index": pdf_index,
        "font_name": "Arial",
        "font_size": 10.0,
        "semantic_label": semantic_label,
    }


def _make_page(
    blocks: List[Dict[str, Any]],
    page_number: int = 0,
    grid_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "page_number": page_number,
        "text_blocks": blocks,
        "images": [],
        "fonts": [],
        "grid_info": grid_info,
        "screenshot_path": None,
    }


def _make_doc(pages: List[Dict[str, Any]], pdf_index: int = 0) -> Dict[str, Any]:
    return {
        "job_id": "test-job",
        "pdf_index": pdf_index,
        "pdf_name": f"doc_{pdf_index}.pdf",
        "pages": pages,
    }


def _make_field_tree(paths: List[str]) -> Dict[str, Any]:
    return {
        "root_nodes": [],
        "flat_paths": paths,
    }


def _mock_completion(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ---------------------------------------------------------------------------
# Test 1 — Field Matching: label adjacente encontrado corretamente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_matching_finds_adjacent_label():
    """Value block to the right of a label block should detect label."""
    from services.stages.field_matching import execute

    label_blk = _make_block("Nome:", (50.0, 300.0, 150.0, 312.0), semantic_label="label")
    value_blk = _make_block("João Silva", (160.0, 300.0, 350.0, 312.0), semantic_label="value")

    page = _make_page([label_blk, value_blk])
    doc = _make_doc([page])

    field_tree = _make_field_tree(["cliente.nome", "cliente.cpf", "cliente.email"])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
        "field_tree": field_tree,
    }

    # No API key → fuzzy fallback
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        result = await execute(context)

    mappings = context["field_mappings"]
    assert len(mappings) == 1
    mapping = mappings[0]
    assert mapping["label_text"] == "Nome"  # stripped colon
    assert mapping["pdf_text"] == "João Silva"
    assert mapping["xsd_field_path"] != ""  # some match returned


# ---------------------------------------------------------------------------
# Test 2 — Field Matching: sem label adjacente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_matching_no_adjacent_label():
    """Value block with no nearby label should produce mapping with empty label_text."""
    from services.stages.field_matching import execute

    value_blk = _make_block("12345", (400.0, 200.0, 500.0, 212.0), semantic_label="value")
    page = _make_page([value_blk])
    doc = _make_doc([page])
    field_tree = _make_field_tree(["pedido.numero", "pedido.valor"])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
        "field_tree": field_tree,
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    mapping = context["field_mappings"][0]
    assert mapping["label_text"] == ""


# ---------------------------------------------------------------------------
# Test 3 — Field Matching: resultado ambíguo quando scores similares
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_matching_ambiguous_when_scores_similar():
    """If top-2 candidates differ < 0.1, mapping should be flagged as ambiguous."""
    from services.stages.field_matching import _fuzzy_match, AMBIGUITY_THRESHOLD

    # Two paths with identical similarity to "nome"
    paths = ["cliente.nome", "contato.nome", "endereco.complemento"]
    candidates = _fuzzy_match("nome", "João", paths)

    # Manually test the ambiguity logic
    assert len(candidates) >= 2
    if len(candidates) >= 2:
        diff = candidates[0]["score"] - candidates[1]["score"]
        is_ambiguous = diff < AMBIGUITY_THRESHOLD
        # Both "cliente.nome" and "contato.nome" end with ".nome" → should be ambiguous
        assert is_ambiguous


# ---------------------------------------------------------------------------
# Test 4 — Field Matching: LLM mock retorna candidatos corretos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_matching_llm_mock():
    """With mocked OpenRouter client, LLM result should be used."""
    from services.stages.field_matching import execute

    label_blk = _make_block("CPF:", (50.0, 400.0, 130.0, 412.0), semantic_label="label")
    value_blk = _make_block("123.456.789-01", (140.0, 400.0, 320.0, 412.0), semantic_label="value")

    page = _make_page([label_blk, value_blk])
    doc = _make_doc([page])
    field_tree = _make_field_tree(["cliente.cpf", "cliente.nome", "empresa.cnpj"])

    llm_response = json.dumps({
        "candidates": [
            {"path": "cliente.cpf", "score": 0.95},
            {"path": "empresa.cnpj", "score": 0.30},
        ]
    })
    mock_client = AsyncMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_completion(llm_response)
    )

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
        "field_tree": field_tree,
        "openrouter_client": mock_client,
    }

    result = await execute(context)

    mappings = context["field_mappings"]
    assert len(mappings) == 1
    assert mappings[0]["xsd_field_path"] == "cliente.cpf"
    assert mappings[0]["confidence"] == 0.95
    assert mappings[0]["is_ambiguous"] is False


# ---------------------------------------------------------------------------
# Test 5 — Field Matching: sem field_tree retorna mapeamento vazio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_matching_no_field_tree():
    """Without field_tree, mappings should have empty xsd_field_path."""
    from services.stages.field_matching import execute

    value_blk = _make_block("Test Value", (100.0, 200.0, 300.0, 212.0), semantic_label="value")
    page = _make_page([value_blk])
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    assert context["field_mappings"][0]["xsd_field_path"] == ""


# ---------------------------------------------------------------------------
# Test 6 — Field Matching: SSE emitido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_matching_emits_sse():
    """Stage 23 should emit an SSE event when emit_progress is present."""
    from services.stages.field_matching import execute

    events: List[Dict[str, Any]] = []
    value_blk = _make_block("value_text", (100.0, 200.0, 300.0, 212.0), semantic_label="value")
    page = _make_page([value_blk])
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
        "emit_progress": lambda e: events.append(e),
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    assert any(e.get("stage") == 23 for e in events)
    assert events[-1]["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 7 — Format Detection: moeda BRL
# ---------------------------------------------------------------------------


def test_format_detection_currency_brl():
    """'R$ 1.234,56' should be detected as currency_brl."""
    from services.stages.format_detection import detect_format

    assert detect_format("R$ 1.234,56") == "currency_brl"
    assert detect_format("R$100,00") == "currency_brl"


# ---------------------------------------------------------------------------
# Test 8 — Format Detection: data numérica
# ---------------------------------------------------------------------------


def test_format_detection_date_numeric():
    """'01/02/2025' should be detected as date_numeric."""
    from services.stages.format_detection import detect_format

    assert detect_format("01/02/2025") == "date_numeric"
    assert detect_format("31/12/1999") == "date_numeric"


# ---------------------------------------------------------------------------
# Test 9 — Format Detection: data por extenso
# ---------------------------------------------------------------------------


def test_format_detection_date_extenso():
    """'15 de Janeiro de 2025' should be detected as date_extenso."""
    from services.stages.format_detection import detect_format

    assert detect_format("15 de Janeiro de 2025") == "date_extenso"
    assert detect_format("1 de março de 2024") == "date_extenso"


# ---------------------------------------------------------------------------
# Test 10 — Format Detection: CPF
# ---------------------------------------------------------------------------


def test_format_detection_cpf():
    """'123.456.789-01' should be detected as cpf."""
    from services.stages.format_detection import detect_format

    assert detect_format("123.456.789-01") == "cpf"


# ---------------------------------------------------------------------------
# Test 11 — Format Detection: CNPJ
# ---------------------------------------------------------------------------


def test_format_detection_cnpj():
    """'12.345.678/0001-99' should be detected as cnpj."""
    from services.stages.format_detection import detect_format

    assert detect_format("12.345.678/0001-99") == "cnpj"


# ---------------------------------------------------------------------------
# Test 12 — Format Detection: telefone
# ---------------------------------------------------------------------------


def test_format_detection_phone():
    """'(11) 98765-4321' should be detected as phone."""
    from services.stages.format_detection import detect_format

    assert detect_format("(11) 98765-4321") == "phone"
    assert detect_format("(11) 3456-7890") == "phone"


# ---------------------------------------------------------------------------
# Test 13 — Format Detection: porcentagem
# ---------------------------------------------------------------------------


def test_format_detection_percentage():
    """'12,5%' should be detected as percentage."""
    from services.stages.format_detection import detect_format

    assert detect_format("12,5%") == "percentage"
    assert detect_format("100%") == "percentage"


# ---------------------------------------------------------------------------
# Test 14 — Format Detection: texto sem formato → None
# ---------------------------------------------------------------------------


def test_format_detection_unknown_returns_none():
    """Plain text with no special format should return None."""
    from services.stages.format_detection import detect_format

    assert detect_format("João Silva") is None
    assert detect_format("Contrato de Prestação") is None


# ---------------------------------------------------------------------------
# Test 15 — Format Detection: execute enriquece field_mappings e gera JS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_format_detection_execute_enriches_mappings():
    """Stage 24 execute should enrich field_mappings and populate format_functions."""
    from services.stages.format_detection import execute

    mappings = [
        {"pdf_text": "R$ 1.500,00", "label_text": "Valor", "xsd_field_path": "pagamento.valor"},
        {"pdf_text": "123.456.789-01", "label_text": "CPF", "xsd_field_path": "cliente.cpf"},
        {"pdf_text": "João Silva", "label_text": "Nome", "xsd_field_path": "cliente.nome"},
    ]

    context: Dict[str, Any] = {"field_mappings": mappings}
    result = await execute(context)

    assert result["formats_detected"] == 2  # currency + cpf
    assert "currency_brl" in context["format_functions"]
    assert "cpf" in context["format_functions"]
    assert "currency_brl" in result["format_types"]
    assert "cpf" in result["format_types"]

    # Verify detected_format enrichment
    assert mappings[0]["detected_format"] == "currency_brl"
    assert mappings[1]["detected_format"] == "cpf"
    assert mappings[2]["detected_format"] is None


# ---------------------------------------------------------------------------
# Test 16 — Format Detection: JS para CPF contém formatCPF
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_format_detection_js_cpf_function():
    """Generated JS for cpf should contain the formatCPF function."""
    from services.stages.format_detection import execute

    mappings = [{"pdf_text": "123.456.789-01", "label_text": "CPF", "xsd_field_path": "cliente.cpf"}]
    context: Dict[str, Any] = {"field_mappings": mappings}
    await execute(context)

    js = context["format_functions"].get("cpf", "")
    assert "formatCPF" in js


# ---------------------------------------------------------------------------
# Test 17 — Confidence Scoring: 5 fatores calculados
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_scoring_five_factors():
    """All 5 factors should be present in confidence_scores."""
    from services.stages.confidence_scoring import execute

    mappings = [
        {"label_text": "Nome", "pdf_text": "João"},
        {"label_text": "CPF", "pdf_text": "123.456.789-01"},
        {"label_text": "", "pdf_text": "algum valor"},
    ]
    intelligence = {"layout_stability": 0.9, "field_variability": 0.7}
    visual_analysis = {"0:0": {"consistency_score": 0.85}}

    context: Dict[str, Any] = {
        "field_mappings": mappings,
        "intelligence": intelligence,
        "visual_analysis": visual_analysis,
        "parsed_documents": [],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        result = await execute(context)

    scores = context["confidence_scores"]
    factors = scores["factors"]
    assert "layout_stability" in factors
    assert "anchor_detection" in factors
    assert "grid_quality" in factors
    assert "field_variability" in factors
    assert "vision_agreement" in factors

    assert factors["layout_stability"] == 0.9
    assert factors["field_variability"] == 0.7
    # 2 out of 3 have label_text → 0.6667
    assert abs(factors["anchor_detection"] - 2 / 3) < 0.01


# ---------------------------------------------------------------------------
# Test 18 — Confidence Scoring: threshold "approved" >= 0.95
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_scoring_threshold_approved():
    """Score >= 0.95 should set status 'approved'."""
    from services.stages.confidence_scoring import execute, _status_from_score

    assert _status_from_score(0.95) == "approved"
    assert _status_from_score(1.0) == "approved"


# ---------------------------------------------------------------------------
# Test 19 — Confidence Scoring: threshold "review_recommended"
# ---------------------------------------------------------------------------


def test_confidence_scoring_threshold_review():
    """Score between 0.80 and 0.95 should set status 'review_recommended'."""
    from services.stages.confidence_scoring import _status_from_score

    assert _status_from_score(0.85) == "review_recommended"
    assert _status_from_score(0.80) == "review_recommended"


# ---------------------------------------------------------------------------
# Test 20 — Confidence Scoring: threshold "human_review_required"
# ---------------------------------------------------------------------------


def test_confidence_scoring_threshold_human_review():
    """Score < 0.80 should set status 'human_review_required'."""
    from services.stages.confidence_scoring import _status_from_score

    assert _status_from_score(0.79) == "human_review_required"
    assert _status_from_score(0.0) == "human_review_required"


# ---------------------------------------------------------------------------
# Test 21 — Confidence Scoring: LLM mock retorna score correto
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_scoring_llm_mock():
    """With mocked OpenRouter client, LLM score should be used."""
    from services.stages.confidence_scoring import execute

    llm_response = json.dumps({"global_score": 0.92})
    mock_client = AsyncMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_completion(llm_response)
    )

    context: Dict[str, Any] = {
        "field_mappings": [{"label_text": "Nome", "pdf_text": "João"}],
        "parsed_documents": [],
        "openrouter_client": mock_client,
    }

    result = await execute(context)

    assert result["global_score"] == 0.92
    assert result["score_method"] == "llm"
    assert context["confidence_scores"]["status"] == "review_recommended"


# ---------------------------------------------------------------------------
# Test 22 — Confidence Scoring: grid_quality 0.8 quando colunas > 1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_scoring_grid_quality_multi_column():
    """Pages with grid_info.columns > 1 should produce grid_quality=0.8."""
    from services.stages.confidence_scoring import _get_grid_quality

    doc = _make_doc([_make_page([], grid_info={"columns": 3, "rows": 5, "column_positions": [], "row_positions": []})])
    context: Dict[str, Any] = {"parsed_documents": [doc]}
    assert _get_grid_quality(context) == 0.8


# ---------------------------------------------------------------------------
# Test 23 — Confidence Scoring: SSE emitido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_scoring_emits_sse():
    """Stage 25 should emit an SSE event when emit_progress is provided."""
    from services.stages.confidence_scoring import execute

    events: List[Dict[str, Any]] = []
    context: Dict[str, Any] = {
        "field_mappings": [],
        "parsed_documents": [],
        "emit_progress": lambda e: events.append(e),
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    assert any(e.get("stage") == 25 for e in events)
    assert events[-1]["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 24 — register_bloco7 wires stages 23–24 into registry
# ---------------------------------------------------------------------------


def test_register_bloco7_wires_stages():
    """register_bloco7 should replace stubs 23-24 with real implementations."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco7

    registry = build_default_registry()

    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[23]._execute_fn is None
    assert stages_before[24]._execute_fn is None

    register_bloco7(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}
    assert stages_after[23]._execute_fn is not None, "Stage 23 still stub after register_bloco7"
    assert stages_after[24]._execute_fn is not None, "Stage 24 still stub after register_bloco7"

    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 28


# ---------------------------------------------------------------------------
# Test 25 — register_bloco8_confidence wires stage 25 into registry
# ---------------------------------------------------------------------------


def test_register_bloco8_confidence_wires_stage25():
    """register_bloco8_confidence should replace stub 25 with real implementation."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco8_confidence

    registry = build_default_registry()

    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[25]._execute_fn is None

    register_bloco8_confidence(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}
    assert stages_after[25]._execute_fn is not None, "Stage 25 still stub after register_bloco8_confidence"

    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 28


# ---------------------------------------------------------------------------
# Story 10.15 — Tests: field_mappings vazio (aba Campos mostra 0 de 0)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_matching_with_empty_semantic_label():
    """Blocks with semantic_label='' (not yet classified by Stage 19) must produce mappings.

    AC #2: Stage 23 treats ALL non-structural blocks as candidates, including
    blocks where semantic_label is empty string (Stage 19 not yet run or skipped).
    """
    from services.stages.field_matching import execute

    # Block with NO semantic_label (default empty string)
    block = _make_block("João Silva", (100.0, 200.0, 300.0, 212.0), semantic_label="")
    page = _make_page([block])
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    mappings = context["field_mappings"]
    assert len(mappings) == 1, "Block with empty semantic_label must produce a mapping"
    assert mappings[0]["pdf_text"] == "João Silva"


@pytest.mark.asyncio
async def test_field_matching_non_structural_labels_produce_mappings():
    """All non-structural labels ('value', 'field', 'text', '') must produce mappings.

    AC #2: Stage 23 should exclude only structural labels (header, footer_text,
    page_number, title, table_header, table_cell, label, image). All other labels
    (including 'value', 'field', '' and any unknown label) must produce entries.
    """
    from services.stages.field_matching import execute, _STRUCTURAL_LABELS

    # One block per non-structural label
    non_structural = ["value", "field", "", "text", "body", "paragraph"]
    blocks = [
        _make_block(f"content-{lbl or 'empty'}", (10.0 * i, 100.0, 10.0 * i + 80.0, 112.0), semantic_label=lbl)
        for i, lbl in enumerate(non_structural)
    ]
    page = _make_page(blocks)
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    mappings = context["field_mappings"]
    assert len(mappings) == len(non_structural), (
        f"Expected {len(non_structural)} mappings (one per non-structural block), got {len(mappings)}"
    )
    # Verify none of the structural labels slipped through
    for lbl in _STRUCTURAL_LABELS:
        assert all(m["pdf_text"] != f"content-{lbl}" for m in mappings), (
            f"Structural label '{lbl}' should not produce a mapping"
        )


@pytest.mark.asyncio
async def test_field_matching_structural_labels_are_excluded():
    """Blocks with structural semantic_labels must NOT produce mappings.

    AC #2: header, footer_text, page_number, title, table_header, table_cell,
    label, and image blocks should be excluded from field_mappings.
    """
    from services.stages.field_matching import execute, _STRUCTURAL_LABELS

    structural_blocks = [
        _make_block(f"text-{lbl}", (0.0, float(i * 20), 100.0, float(i * 20 + 12)), semantic_label=lbl)
        for i, lbl in enumerate(_STRUCTURAL_LABELS)
    ]
    page = _make_page(structural_blocks)
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    mappings = context["field_mappings"]
    assert len(mappings) == 0, (
        f"No structural blocks should produce mappings, but got {len(mappings)}: {mappings}"
    )


@pytest.mark.asyncio
async def test_make_mapping_includes_name_and_path_aliases():
    """_make_mapping() must return a dict with both 'name' and 'path' keys.

    AC #3/#4: frontend FieldMappingEntry expects 'name' (= label_text or pdf_text)
    and 'path' (= xsd_field_path). These aliases must be present in every mapping.
    """
    from services.stages.field_matching import _make_mapping

    mapping = _make_mapping(
        pdf_text="123.456.789-01",
        label_text="CPF",
        xsd_field_path="cliente.cpf",
        confidence=0.9,
        is_ambiguous=False,
        candidates=[],
        page_number=0,
        pdf_index=0,
    )

    # Frontend-compatible aliases
    assert "name" in mapping, "'name' alias is required for frontend FieldMappingEntry"
    assert "path" in mapping, "'path' alias is required for frontend FieldMappingEntry"
    assert mapping["name"] == "CPF", "name should prefer label_text over pdf_text"
    assert mapping["path"] == "cliente.cpf", "path must equal xsd_field_path"

    # When label_text is empty, name should fall back to pdf_text
    mapping_no_label = _make_mapping(
        pdf_text="valor sem label",
        label_text="",
        xsd_field_path="",
        confidence=0.0,
        is_ambiguous=False,
        candidates=[],
        page_number=0,
        pdf_index=0,
    )
    assert mapping_no_label["name"] == "valor sem label", "name must fall back to pdf_text when label_text is empty"


@pytest.mark.asyncio
async def test_pipeline_result_field_mappings_has_name_and_path():
    """Stage 28 must include field_mappings with 'name' and 'path' keys in result_json.

    AC #4: result.field_mappings in the final JSON must have the frontend-compatible
    keys so mappingStore.loadPipelineFields() works correctly.
    """
    from services.stages.pipeline_result import execute

    # Simulate field_mappings as produced by Stage 23 (with aliases already set)
    field_mappings = [
        {
            "pdf_text": "João Silva",
            "label_text": "Nome",
            "xsd_field_path": "cliente.nome",
            "confidence": 0.8,
            "is_ambiguous": False,
            "candidates": [],
            "page_number": 0,
            "pdf_index": 0,
            # Frontend aliases
            "name": "Nome",
            "path": "cliente.nome",
            "type": "text",
            "status": "mapped",
            "isOptional": False,
        }
    ]

    context: Dict[str, Any] = {
        "field_mappings": field_mappings,
        "parsed_documents": [],
    }

    await execute(context)

    result_json = context["result_json"]
    assert "field_mappings" in result_json, "result_json must contain 'field_mappings'"
    assert len(result_json["field_mappings"]) == 1

    entry = result_json["field_mappings"][0]
    assert "name" in entry, "field_mappings entry must have 'name' key for frontend"
    assert "path" in entry, "field_mappings entry must have 'path' key for frontend"
    assert entry["name"] == "Nome"
    assert entry["path"] == "cliente.nome"


@pytest.mark.asyncio
async def test_field_matching_produces_mappings_without_xsd():
    """Stage 23 without XSD field_tree must still produce minimal mappings for every value block.

    AC #1/#2: Even without XSD, aba Campos should show extracted fields. Stage 23
    must create a mapping entry for each non-structural text block, with empty
    xsd_field_path but a non-empty pdf_text (from the block's text).
    """
    from services.stages.field_matching import execute

    # Simulate a realistic PDF page with multiple content blocks
    blocks = [
        _make_block("CONTRATO DE PRESTAÇÃO DE SERVIÇOS", (50.0, 50.0, 400.0, 62.0), semantic_label="title"),
        _make_block("Nome:", (50.0, 100.0, 130.0, 112.0), semantic_label="label"),
        _make_block("Maria Souza", (140.0, 100.0, 300.0, 112.0), semantic_label="value"),
        _make_block("CPF:", (50.0, 120.0, 100.0, 132.0), semantic_label="label"),
        _make_block("987.654.321-00", (110.0, 120.0, 280.0, 132.0), semantic_label="value"),
        _make_block("Cabeçalho página 1", (0.0, 0.0, 500.0, 12.0), semantic_label="header"),
    ]
    page = _make_page(blocks)
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
        # No field_tree — simulates upload without XSD
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    mappings = context["field_mappings"]
    # title, label, header are excluded; 2 value blocks should produce 2 mappings
    assert len(mappings) == 2, (
        f"Expected 2 mappings from 2 non-structural, non-label blocks; got {len(mappings)}: "
        f"{[m['pdf_text'] for m in mappings]}"
    )
    texts = {m["pdf_text"] for m in mappings}
    assert "Maria Souza" in texts
    assert "987.654.321-00" in texts
    # Each entry must have empty path (no XSD)
    for m in mappings:
        assert m["xsd_field_path"] == "", f"Without XSD, xsd_field_path must be ''; got '{m['xsd_field_path']}'"
        assert m["name"] != "", "name alias must not be empty"


# ---------------------------------------------------------------------------
# Story 10.19 — Tests: bbox propagation in field_matching (Stage 23)
# ---------------------------------------------------------------------------


def test_make_mapping_includes_bbox_when_provided():
    """_make_mapping() with bbox kwarg must include 'bbox' key as a list.

    AC #2: field_mappings[i]['bbox'] must be present when the source block has bbox.
    """
    from services.stages.field_matching import _make_mapping

    mapping = _make_mapping(
        pdf_text="MAG SEGUROS",
        label_text="Beneficiário",
        xsd_field_path="contrato.beneficiario",
        confidence=0.9,
        is_ambiguous=False,
        candidates=[],
        page_number=0,
        pdf_index=0,
        bbox=(42.0, 84.0, 200.0, 96.0),
    )

    assert "bbox" in mapping, "bbox must be present in mapping when block has bbox"
    assert mapping["bbox"] == [42.0, 84.0, 200.0, 96.0], "bbox must be serialized as list"


def test_make_mapping_excludes_bbox_when_absent():
    """_make_mapping() without bbox must NOT include 'bbox' key (fallback to linear flow).

    AC #3: fields without bbox continue using linear flow — no bbox key in mapping.
    """
    from services.stages.field_matching import _make_mapping

    mapping = _make_mapping(
        pdf_text="Valor",
        label_text="",
        xsd_field_path="",
        confidence=0.0,
        is_ambiguous=False,
        candidates=[],
        page_number=0,
        pdf_index=0,
    )

    assert "bbox" not in mapping, "bbox must not be present in mapping when block has no bbox"


@pytest.mark.asyncio
async def test_field_matching_propagates_bbox_to_mappings():
    """execute() must propagate block bbox to field_mappings entries.

    AC #2: When a value block has bbox coordinates, the resulting mapping must
    contain the bbox as a list [x0, y0, x1, y1].
    """
    from services.stages.field_matching import execute

    value_blk = _make_block(
        "MAG SEGUROS",
        bbox=(42.0, 84.0, 200.0, 96.0),
        semantic_label="value",
    )
    page = _make_page([value_blk])
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    mappings = context["field_mappings"]
    assert len(mappings) == 1
    assert "bbox" in mappings[0], "bbox must be propagated from block to mapping"
    assert mappings[0]["bbox"] == [42.0, 84.0, 200.0, 96.0]


@pytest.mark.asyncio
async def test_field_matching_no_bbox_in_block_no_bbox_in_mapping():
    """execute() must not include bbox in mapping when block lacks bbox.

    AC #3: Fallback — blocks without bbox produce mappings without bbox,
    which will continue using linear flow in the canvas.
    """
    from services.stages.field_matching import execute

    # _make_block always adds bbox, so override manually
    blk: Dict[str, Any] = {
        "text": "Sem coordenada",
        "page_number": 0,
        "pdf_index": 0,
        "font_name": "Arial",
        "font_size": 10.0,
        "semantic_label": "value",
        # No "bbox" key at all
    }
    page = _make_page([blk])
    doc = _make_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        await execute(context)

    mappings = context["field_mappings"]
    assert len(mappings) == 1
    assert "bbox" not in mappings[0], "mapping must not have bbox when block has no bbox"
