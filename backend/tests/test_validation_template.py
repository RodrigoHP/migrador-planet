"""Tests for Story 5.12 — Bloco 9: Validation + Template Draft.

Covers:
- Stage 26 — Layout Consistency Validation: skeleton coverage, orphan detection, table check
- Stage 27 — Template Draft Generation: HTML/CSS generation, coverage, foreach, conditional
- Stage 28 — Pipeline Result Consolidation: JSON schema, filtering, persistence mock
- Endpoint GET /api/analyze/{job_id}/result: 404 and result scenarios
- register_bloco9 wires stages 26-28 into registry
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_field_tree(paths: List[str]) -> Dict[str, Any]:
    return {"root_nodes": [], "flat_paths": paths}


def _make_mapping(
    xsd_field_path: str,
    pdf_text: str = "value",
    label_text: str = "label",
    is_ambiguous: bool = False,
    is_table_cell: bool = False,
) -> Dict[str, Any]:
    return {
        "pdf_text": pdf_text,
        "label_text": label_text,
        "xsd_field_path": xsd_field_path,
        "confidence": 0.9,
        "is_ambiguous": is_ambiguous,
        "is_table_cell": is_table_cell,
        "candidates": [],
        "page_number": 0,
        "pdf_index": 0,
    }


def _make_value_block(text: str = "val") -> Dict[str, Any]:
    return {
        "text": text,
        "bbox": (10.0, 10.0, 100.0, 22.0),
        "page_number": 0,
        "pdf_index": 0,
        "semantic_label": "value",
    }


def _make_page(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"page_number": 0, "text_blocks": blocks, "images": [], "fonts": []}


def _make_doc(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"job_id": "test", "pdf_index": 0, "pdf_name": "doc.pdf", "pages": pages}


# ===========================================================================
# Stage 26 — Layout Consistency Validation
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 1 — campo XSD sem mapeamento gera warning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_layout_consistency_unmapped_xsd_generates_warning():
    """XSD fields not covered by any mapping should produce a warning."""
    from services.stages.layout_consistency import execute

    field_tree = _make_field_tree(["cliente.nome", "cliente.cpf", "cliente.email"])
    mappings = [_make_mapping("cliente.nome")]

    context: Dict[str, Any] = {
        "field_tree": field_tree,
        "field_mappings": mappings,
        "parsed_documents": [],
        "tables": [],
    }

    await execute(context)

    result = context["validation_result"]
    assert len(result["warnings"]) >= 1, "Expected at least one warning for unmapped XSD fields"
    # Unmapped fields: cliente.cpf, cliente.email
    assert "cliente.cpf" in result["unmapped_xsd_fields"] or "cliente.email" in result["unmapped_xsd_fields"]
    assert result["unmapped_xsd_fields"] != []


# ---------------------------------------------------------------------------
# Test 2 — mapeamento órfão gera error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_layout_consistency_orphan_mapping_generates_error():
    """A mapping pointing to an XSD path not in field_tree should produce an error."""
    from services.stages.layout_consistency import execute

    field_tree = _make_field_tree(["cliente.nome"])
    # "nonexistent.path" is NOT in flat_paths
    mappings = [
        _make_mapping("cliente.nome"),
        _make_mapping("nonexistent.path"),
    ]

    context: Dict[str, Any] = {
        "field_tree": field_tree,
        "field_mappings": mappings,
        "parsed_documents": [],
        "tables": [],
    }

    await execute(context)

    result = context["validation_result"]
    assert result["orphan_count"] >= 1, "Expected orphan_count >= 1"
    assert len(result["errors"]) >= 1, "Expected at least one error"
    assert any("nonexistent.path" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Test 3 — sem erros quando tudo mapeado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_layout_consistency_no_errors_when_fully_mapped():
    """When all XSD paths are mapped and no orphans exist, there should be no errors."""
    from services.stages.layout_consistency import execute

    paths = ["cliente.nome", "cliente.cpf"]
    field_tree = _make_field_tree(paths)
    mappings = [_make_mapping(p) for p in paths]

    context: Dict[str, Any] = {
        "field_tree": field_tree,
        "field_mappings": mappings,
        "parsed_documents": [],
        "tables": [],
    }

    await execute(context)

    result = context["validation_result"]
    assert result["errors"] == [], f"Expected no errors, got: {result['errors']}"
    assert result["orphan_count"] == 0


# ---------------------------------------------------------------------------
# Test 4 — tabela com headers sem mapeamento de table cell gera warning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_layout_consistency_table_without_cell_mapping_warns():
    """Tables with headers but no table-cell mappings should generate a warning."""
    from services.stages.layout_consistency import execute

    field_tree = _make_field_tree(["item.descricao"])
    mappings = [_make_mapping("item.descricao", is_table_cell=False)]
    tables = [{"headers": ["Descrição", "Valor"], "rows": []}]

    context: Dict[str, Any] = {
        "field_tree": field_tree,
        "field_mappings": mappings,
        "parsed_documents": [],
        "tables": tables,
    }

    await execute(context)

    result = context["validation_result"]
    table_warnings = [w for w in result["warnings"] if "table" in w.lower()]
    assert len(table_warnings) >= 1, "Expected a table coverage warning"


# ===========================================================================
# Stage 27 — Template Draft Generation
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 5 — HTML gerado contém div.page
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_draft_html_contains_page_div():
    """Generated HTML must contain at least one .page div element."""
    from services.stages.template_draft import execute

    context: Dict[str, Any] = {
        "layout_types": [{"name": "Capa", "pages": [0]}],
        "field_mappings": [],
        "field_tree": None,
        "variants": [],
    }

    await execute(context)

    html = context["template_draft"]["html"]
    assert 'class="page' in html, "Expected .page div in HTML"
    assert 'data-layout-type="Capa"' in html


# ---------------------------------------------------------------------------
# Test 6 — HTML contém data-bind para field_mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_draft_html_contains_data_bind():
    """Each field mapping should produce a data-bind span in the HTML."""
    from services.stages.template_draft import execute

    mappings = [_make_mapping("cliente.nome", label_text="Nome")]

    context: Dict[str, Any] = {
        "layout_types": [{"name": "Capa", "pages": [0]}],
        "field_mappings": mappings,
        "field_tree": None,
        "variants": [],
    }

    await execute(context)

    html = context["template_draft"]["html"]
    assert 'data-bind="text: cliente.nome"' in html, "Expected data-bind for cliente.nome"


# ---------------------------------------------------------------------------
# Test 7 — CSS contém .page com dimensões A4
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_draft_css_contains_a4_dimensions():
    """Generated CSS must include A4 page dimensions."""
    from services.stages.template_draft import execute

    context: Dict[str, Any] = {
        "layout_types": [],
        "field_mappings": [],
        "field_tree": None,
        "variants": [],
    }

    await execute(context)

    css = context["template_draft"]["css"]
    assert "8.27in" in css, "Expected A4 width in CSS"
    assert "11.69in" in css, "Expected A4 height in CSS"
    assert ".page" in css


# ---------------------------------------------------------------------------
# Test 8 — coverage calculado corretamente (N/M)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_draft_coverage_calculated():
    """Coverage should reflect mapped vs total fields from field_tree."""
    from services.stages.template_draft import execute

    field_tree = _make_field_tree(["a.b", "a.c", "a.d"])
    mappings = [_make_mapping("a.b"), _make_mapping("a.c")]

    context: Dict[str, Any] = {
        "layout_types": [],
        "field_mappings": mappings,
        "field_tree": field_tree,
        "variants": [],
    }

    await execute(context)

    coverage = context["template_draft"]["coverage"]
    assert coverage["fields"]["total"] == 3
    assert coverage["fields"]["mapped"] == 2


# ---------------------------------------------------------------------------
# Test 9 — coverage 0 quando sem mapeamentos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_draft_coverage_zero_when_no_mappings():
    """Coverage should be 0 mapped when there are no field_mappings."""
    from services.stages.template_draft import execute

    field_tree = _make_field_tree(["x.y", "x.z"])

    context: Dict[str, Any] = {
        "layout_types": [],
        "field_mappings": [],
        "field_tree": field_tree,
        "variants": [],
    }

    await execute(context)

    coverage = context["template_draft"]["coverage"]
    assert coverage["fields"]["mapped"] == 0
    assert coverage["fields"]["total"] == 2


# ---------------------------------------------------------------------------
# Test 10 — array path gera foreach no HTML
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_draft_array_path_generates_foreach():
    """A field path containing '[]' should generate a ko foreach comment."""
    from services.stages.template_draft import execute

    mappings = [_make_mapping("itens[].descricao", label_text="Descrição")]

    context: Dict[str, Any] = {
        "layout_types": [{"name": "Extrato", "pages": [0]}],
        "field_mappings": mappings,
        "field_tree": None,
        "variants": [],
    }

    await execute(context)

    html = context["template_draft"]["html"]
    assert "ko foreach" in html, "Expected ko foreach for array field"


# ===========================================================================
# Stage 28 — Pipeline Result Consolidation
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 11 — result_json contém todas as chaves esperadas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_result_contains_all_keys():
    """result_json must contain all required top-level keys."""
    from services.stages.pipeline_result import execute

    context: Dict[str, Any] = {
        "field_mappings": [_make_mapping("a.b")],
        "layout_types": [{"name": "Capa", "pages": [0]}],
        "template_draft": {"html": "<div/>", "css": ".page{}", "coverage": {"fields": {"mapped": 1, "total": 2}}},
        "confidence_scores": {"global_score": 0.9, "status": "review_recommended"},
        "format_functions": {"cpf": "function formatCPF(){}"},
        "parsed_documents": [],
    }

    await execute(context)

    result = context["result_json"]
    required_keys = {
        "document_structure",
        "field_mappings",
        "confidence_scores",
        "coverage",
        "layout_types",
        "template_draft",
        "ambiguous_fields",
        "format_functions",
    }
    missing = required_keys - result.keys()
    assert not missing, f"result_json missing keys: {missing}"


# ---------------------------------------------------------------------------
# Test 12 — ambiguous_fields filtra apenas is_ambiguous=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_result_ambiguous_fields_filtered():
    """ambiguous_fields must contain only mappings with is_ambiguous=True."""
    from services.stages.pipeline_result import execute

    mappings = [
        _make_mapping("a.b", is_ambiguous=False),
        _make_mapping("a.c", is_ambiguous=True),
        _make_mapping("a.d", is_ambiguous=True),
        _make_mapping("a.e", is_ambiguous=False),
    ]

    context: Dict[str, Any] = {
        "field_mappings": mappings,
        "layout_types": [],
        "parsed_documents": [],
    }

    await execute(context)

    ambiguous = context["result_json"]["ambiguous_fields"]
    assert len(ambiguous) == 2
    assert all(m["is_ambiguous"] for m in ambiguous)


# ---------------------------------------------------------------------------
# Test 13 — format_functions lista correta
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_result_format_functions_present():
    """format_functions from context must be preserved in result_json."""
    from services.stages.pipeline_result import execute

    format_fns = {"cpf": "function formatCPF(){}", "currency_brl": "function formatBRL(){}"}

    context: Dict[str, Any] = {
        "field_mappings": [],
        "layout_types": [],
        "format_functions": format_fns,
        "parsed_documents": [],
    }

    await execute(context)

    assert context["result_json"]["format_functions"] == format_fns


# ---------------------------------------------------------------------------
# Test 14 — template_draft.html e css presentes em result_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_result_template_draft_html_css():
    """result_json.template_draft must contain html and css keys."""
    from services.stages.pipeline_result import execute

    context: Dict[str, Any] = {
        "field_mappings": [],
        "layout_types": [],
        "template_draft": {"html": "<div>test</div>", "css": ".page{width:8.27in}", "coverage": {}},
        "parsed_documents": [],
    }

    await execute(context)

    td = context["result_json"]["template_draft"]
    assert "html" in td
    assert "css" in td
    assert td["html"] == "<div>test</div>"
    assert td["css"] == ".page{width:8.27in}"


# ===========================================================================
# Endpoint GET /api/analyze/{job_id}/result
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 15 — 404 quando job não existe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_result_404_when_job_not_found():
    """GET /api/analyze/{job_id}/result must return 404 when job is unknown."""
    import routers.analyze as mod
    from fastapi import HTTPException

    # Ensure job is not present
    mod._pipeline_jobs.pop("nonexistent-job-xyz", None)

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_result("nonexistent-job-xyz")

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test 16 — retorna result_json quando job existe e está completo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_result_returns_result_json_when_complete():
    """GET /api/analyze/{job_id}/result must return the stored result when completed."""
    import routers.analyze as mod

    job_id = "test-result-job-complete"
    expected_result = {
        "document_structure": {},
        "field_mappings": [],
        "confidence_scores": {},
        "coverage": {},
        "layout_types": [],
        "template_draft": {"html": "", "css": ""},
        "ambiguous_fields": [],
        "format_functions": {},
    }

    mod._pipeline_jobs[job_id] = {
        "status": "completed",
        "result": expected_result,
        "error": None,
        "cancel_flag": None,
        "event_queue": None,
    }

    try:
        response = await mod.get_result(job_id)
        assert response["status"] == "completed"
        assert response["result"] == expected_result
    finally:
        mod._pipeline_jobs.pop(job_id, None)


# ===========================================================================
# Registration
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 17 — register_bloco9 wires stages 26, 27, 28 into registry
# ---------------------------------------------------------------------------


def test_register_bloco9_wires_stages():
    """register_bloco9 must replace stubs 26, 27, 28 with real implementations."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco9

    registry = build_default_registry()

    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[26]._execute_fn is None, "Stage 26 should be stub before register_bloco9"
    assert stages_before[27]._execute_fn is None, "Stage 27 should be stub before register_bloco9"
    assert stages_before[28]._execute_fn is None, "Stage 28 should be stub before register_bloco9"

    register_bloco9(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}
    assert stages_after[26]._execute_fn is not None, "Stage 26 still stub after register_bloco9"
    assert stages_after[27]._execute_fn is not None, "Stage 27 still stub after register_bloco9"
    assert stages_after[28]._execute_fn is not None, "Stage 28 still stub after register_bloco9"

    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 28


# ===========================================================================
# Story 10.16 — LayoutType.to_dict() inclui campo "id"
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 18 — LayoutType.to_dict() inclui chave "id" com valor "layout-{cluster_id}"
# ---------------------------------------------------------------------------


def test_layout_type_to_dict_includes_id():
    """LayoutType.to_dict() must include 'id' = 'layout-{cluster_id}' so that
    pipeline_result._get_confidence_scores() can key entries by layout id and
    the frontend activeLayoutId lookup works correctly."""
    from models.layout_type import LayoutFingerprint, LayoutType

    fingerprint = LayoutFingerprint(
        table_count=1.0,
        column_count=2,
        header_blocks=3.0,
        body_zone_ratio=0.75,
        footer_present=False,
        fingerprint_hash="abc123",
    )
    lt = LayoutType(
        cluster_id=0,
        name="Capa",
        representative_page={"page_number": 0, "pdf_index": 0},
        fingerprint=fingerprint,
        page_count=1,
    )

    d = lt.to_dict()
    assert "id" in d, "to_dict() deve conter chave 'id'"
    assert d["id"] == "layout-0", f"Esperado 'layout-0', recebido '{d['id']}'"

    lt2 = LayoutType(
        cluster_id=5,
        name="Corpo",
        representative_page={"page_number": 0, "pdf_index": 0},
        fingerprint=fingerprint,
        page_count=3,
    )
    d2 = lt2.to_dict()
    assert d2["id"] == "layout-5", f"Esperado 'layout-5', recebido '{d2['id']}'"


# ---------------------------------------------------------------------------
# Test 19 — _get_confidence_scores usa id do layout_type corretamente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_result_confidence_scores_keyed_by_layout_id():
    """_get_confidence_scores must key entries by LayoutType id ('layout-0', etc.)
    when layout_types contain the 'id' field produced by LayoutType.to_dict()."""
    from services.stages.pipeline_result import _get_confidence_scores

    # Simula layout_types gerados via LayoutType.to_dict() — com campo "id"
    layout_types = [
        {"id": "layout-0", "name": "Capa", "cluster_id": 0},
        {"id": "layout-1", "name": "Corpo", "cluster_id": 1},
    ]

    confidence_raw = {
        "factors": {
            "layout_stability": 0.8,
            "anchor_detection": 0.7,
            "grid_quality": 0.9,
            "field_variability": 0.6,
            "vision_agreement": 0.85,
        },
        "global_score": 0.77,
    }

    context: Dict[str, Any] = {
        "layout_types": layout_types,
        "confidence_scores": confidence_raw,
    }

    scores = _get_confidence_scores(context)

    assert "layout-0" in scores, "Esperado chave 'layout-0' em confidence_scores"
    assert "layout-1" in scores, "Esperado chave 'layout-1' em confidence_scores"
    assert scores["layout-0"]["overall"] == 77, (
        f"Esperado overall=77, recebido {scores['layout-0']['overall']}"
    )
