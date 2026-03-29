"""Residual tests from Story 5.12 — v2 endpoint and model tests only.

All v1 stage-level tests (layout_consistency, template_draft, pipeline_result,
register_bloco9) removed in Story 15.9 — helpers deleted.
Preserved: endpoint tests (Tests 15-16) and LayoutType model test (Test 18).
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest


# ===========================================================================
# Endpoint GET /api/analyze/{job_id}/result
# ===========================================================================


@pytest.mark.asyncio
async def test_endpoint_result_404_when_job_not_found():
    """GET /api/analyze/{job_id}/result must return 404 when job is unknown."""
    import routers.analyze as mod
    from fastapi import HTTPException

    mod._pipeline_jobs.pop("nonexistent-job-xyz", None)

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_result("nonexistent-job-xyz")

    assert exc_info.value.status_code == 404


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
# Story 10.16 — LayoutType.to_dict() inclui campo "id"
# ===========================================================================


def test_layout_type_to_dict_includes_id():
    """LayoutType.to_dict() must include 'id' = 'layout-{cluster_id}'."""
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
