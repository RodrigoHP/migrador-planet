"""Tests for Story 11.8 — Multi-PDF pipeline support + GET /api/jobs/{id}/pdf.

Covers:
1. Stage 2 (text_extraction) processes multiple PDFs in a job directory.
2. GET /api/jobs/{job_id}/pdf endpoint returns input.pdf (index 0).
3. GET /api/jobs/{job_id}/pdf?index=1 returns input_2.pdf.
4. GET /api/jobs/{job_id}/pdf returns 404 when PDF does not exist.
5. GET /api/jobs/{job_id}/pdf returns 400 for invalid job_id.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_mod():
    import routers.analyze as mod
    return mod


# ---------------------------------------------------------------------------
# Test 1: Stage 2 processes all PDFs in job dir (multi-PDF)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_text_extraction_processes_multiple_pdfs():
    """Stage 2 execute() processes all input*.pdf files, not just input.pdf."""
    from unittest.mock import MagicMock, patch
    from services.stages.text_extraction import execute

    fitz_mock = MagicMock()

    def _make_doc(name: str):
        doc = MagicMock()
        doc.is_encrypted = False
        doc.__len__ = lambda self: 1
        page = MagicMock()
        page.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {"spans": [{"text": f"Content of {name}", "bbox": [0, 0, 100, 12],
                                    "font": "Arial", "size": 12.0}]}
                    ],
                }
            ]
        }
        doc.__getitem__ = lambda self, idx: page
        return doc

    fitz_mock.open.side_effect = lambda path: _make_doc(str(path))

    with tempfile.TemporaryDirectory() as tmpdir:
        job_id = str(uuid.uuid4())
        job_dir = Path(tmpdir) / job_id
        job_dir.mkdir()

        # Create two fake PDFs
        (job_dir / "input.pdf").write_bytes(b"%PDF-1.4 first")
        (job_dir / "input_2.pdf").write_bytes(b"%PDF-1.4 second")

        with patch.dict("sys.modules", {"fitz": fitz_mock}):
            import importlib
            import services.stages.text_extraction as te_mod
            importlib.reload(te_mod)

            context: Dict[str, Any] = {
                "job_id": job_id,
                "tmp_base": str(tmpdir),
            }
            result = await te_mod.execute(context)

            importlib.reload(te_mod)  # restore after test

        assert result["pdf_count"] == 2, (
            f"Expected 2 PDFs processed, got {result['pdf_count']}"
        )
        assert result["parsed_count"] == 2, (
            f"Expected 2 ParsedDocuments, got {result['parsed_count']}"
        )
        assert len(context["parsed_documents"]) == 2


# ---------------------------------------------------------------------------
# Test 2 & 3: GET /api/jobs/{job_id}/pdf endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pdf_endpoint_returns_input_pdf():
    """GET /api/jobs/{job_id}/pdf returns input.pdf for index 0."""
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        job_dir = tmp_base / job_id
        job_dir.mkdir()
        (job_dir / "input.pdf").write_bytes(b"%PDF-1.4 test content")

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            response = await mod.get_pdf(job_id, index=0)
            # FileResponse is returned — verify the path
            assert str(response.path) == str(job_dir / "input.pdf")
        finally:
            mod.TMP_BASE = original_tmp


@pytest.mark.asyncio
async def test_get_pdf_endpoint_returns_second_pdf():
    """GET /api/jobs/{job_id}/pdf?index=1 returns input_2.pdf."""
    from fastapi import HTTPException
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        job_dir = tmp_base / job_id
        job_dir.mkdir()
        (job_dir / "input.pdf").write_bytes(b"%PDF-1.4 first")
        (job_dir / "input_2.pdf").write_bytes(b"%PDF-1.4 second")

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            response = await mod.get_pdf(job_id, index=1)
            assert str(response.path) == str(job_dir / "input_2.pdf")
        finally:
            mod.TMP_BASE = original_tmp


@pytest.mark.asyncio
async def test_get_pdf_endpoint_returns_404_when_missing():
    """GET /api/jobs/{job_id}/pdf returns 404 when PDF file not present."""
    from fastapi import HTTPException
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        job_dir = tmp_base / job_id
        job_dir.mkdir()
        # No PDF file created

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            with pytest.raises(HTTPException) as exc_info:
                await mod.get_pdf(job_id, index=0)
            assert exc_info.value.status_code == 404
        finally:
            mod.TMP_BASE = original_tmp


@pytest.mark.asyncio
async def test_get_pdf_endpoint_returns_404_for_unknown_job():
    """GET /api/jobs/{job_id}/pdf returns 404 when job directory does not exist."""
    from fastapi import HTTPException
    mod = _get_mod()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        # No job directory created

        original_tmp = mod.TMP_BASE
        mod.TMP_BASE = tmp_base
        try:
            with pytest.raises(HTTPException) as exc_info:
                await mod.get_pdf(job_id, index=0)
            assert exc_info.value.status_code == 404
        finally:
            mod.TMP_BASE = original_tmp


@pytest.mark.asyncio
async def test_get_pdf_endpoint_returns_400_for_invalid_job_id():
    """GET /api/jobs/{job_id}/pdf returns 400 for non-UUID job_id."""
    from fastapi import HTTPException
    mod = _get_mod()

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_pdf("../etc/passwd", index=0)
    assert exc_info.value.status_code == 400
