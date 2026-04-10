"""Residual tests from Story 11.8 — GET /api/jobs/{id}/pdf endpoint tests only.

Test 1 (text_extraction multi-PDF) removed in Story 15.9 — text_extraction helper deleted.
Preserved: endpoint tests (Tests 2-5) for GET /api/jobs/{job_id}/pdf.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_mod():
    import routers.analyze as mod

    return mod


# ---------------------------------------------------------------------------
# Tests: GET /api/jobs/{job_id}/pdf endpoint
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
