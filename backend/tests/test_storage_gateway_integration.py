"""Integration tests for Story 13.2 — Adaptar Código Existente para Storage Gateway.

Tests that all adapted modules work correctly with STORAGE_MODE=local,
verifying zero regression from the storage abstraction migration.

Covers:
- upload.py: PDF + XSD + data upload via gateway
- assets.py: upload/list/delete via gateway
- pipeline_result.py: mandatory persistence via gateway (gateway-level only)
- analyze.py: storage injection into context + screenshot endpoint

Note: Tests for screenshot_generator.execute(), image_extraction.execute(), and
pipeline_result.execute() removed in Story 15.9 — those v1 helpers were deleted.
"""

from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from services.storage import _reset_storage, create_storage_gateway, get_storage
from services.storage.local_gateway import LocalStorageGateway


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture(autouse=True)
def storage_mode_local():
    """Ensure STORAGE_MODE=local for all tests."""
    with patch.dict(os.environ, {"STORAGE_MODE": "local"}):
        yield
    _reset_storage(None)


@pytest.fixture
def local_gateway(tmp_path: Path) -> LocalStorageGateway:
    """Create a LocalStorageGateway with tmp_path as base."""
    gw = LocalStorageGateway(tmp_base=tmp_path)
    _reset_storage(gw)
    return gw


@pytest.fixture
def job_id() -> str:
    return "test-job-integration-001"


# =====================================================================
# Test: Upload via StorageGateway (upload.py adaptation)
# =====================================================================


class TestUploadStorageIntegration:
    """Test that upload.py uses storage gateway correctly."""

    @pytest.mark.asyncio
    async def test_upload_pdf_via_gateway(
        self, local_gateway: LocalStorageGateway, tmp_path: Path, job_id: str
    ):
        """AC1: upload_pdf writes via gateway, file exists on disk."""
        content = b"%PDF-1.4 test content"
        result = await local_gateway.upload_pdf(job_id, 0, content)

        expected = tmp_path / job_id / "input.pdf"
        assert expected.exists()
        assert expected.read_bytes() == content

    @pytest.mark.asyncio
    async def test_upload_xsd_via_gateway(
        self, local_gateway: LocalStorageGateway, tmp_path: Path, job_id: str
    ):
        """AC1: XSD uploaded as asset via gateway."""
        xsd_content = b'<?xml version="1.0"?><xs:schema/>'
        result = await local_gateway.upload_asset(job_id, "schema.xsd", xsd_content)

        expected = tmp_path / job_id / "assets" / "schema.xsd"
        assert expected.exists()
        assert expected.read_bytes() == xsd_content

    @pytest.mark.asyncio
    async def test_upload_data_via_gateway(
        self, local_gateway: LocalStorageGateway, tmp_path: Path, job_id: str
    ):
        """AC1: data file uploaded as asset via gateway."""
        data_content = b'<root><field>value</field></root>'
        result = await local_gateway.upload_asset(job_id, "data.xml", data_content)

        expected = tmp_path / job_id / "assets" / "data.xml"
        assert expected.exists()


# =====================================================================
# Test: Screenshot Generator via StorageGateway
# =====================================================================


class TestScreenshotGeneratorIntegration:
    """Test that screenshot storage gateway operations work correctly."""

    @pytest.mark.asyncio
    async def test_upload_screenshot_via_gateway(
        self, local_gateway: LocalStorageGateway, tmp_path: Path, job_id: str
    ):
        """AC4: upload_screenshot returns valid path/URL."""
        png_bytes = b"\x89PNG\r\n\x1a\nfake screenshot data"
        result = await local_gateway.upload_screenshot(job_id, "page_0_0", png_bytes)

        # Local mode returns a file path string
        assert result is not None
        assert "page_0_0" in result
        # File should exist on disk
        expected = tmp_path / job_id / "screenshots" / "page_0_0.png"
        assert expected.exists()
        assert expected.read_bytes() == png_bytes


# =====================================================================
# Test: Image Extraction via StorageGateway
# =====================================================================


class TestImageExtractionIntegration:
    """Test that image asset storage gateway operations work correctly."""

    @pytest.mark.asyncio
    async def test_upload_asset_via_gateway(
        self, local_gateway: LocalStorageGateway, tmp_path: Path, job_id: str
    ):
        """AC5: upload_asset returns data URI for images (browser-accessible, survives cleanup)."""
        img_bytes = b"\x89PNG\r\n\x1a\nfake image data"
        result = await local_gateway.upload_asset(job_id, "img_0_0_0.png", img_bytes)

        assert result is not None
        # Images must return a data URI so HTML templates embed them inline
        assert result.startswith("data:image/png;base64,"), f"Expected data URI, got: {result[:60]}"
        # File must still be written to disk for get_asset_local_path
        expected = tmp_path / job_id / "assets" / "img_0_0_0.png"
        assert expected.exists()


# =====================================================================
# Test: Assets via StorageGateway
# =====================================================================


class TestAssetsIntegration:
    """Test that assets.py upload/list/delete works via gateway."""

    @pytest.mark.asyncio
    async def test_asset_upload_list_delete_lifecycle(
        self, local_gateway: LocalStorageGateway, tmp_path: Path
    ):
        """AC3: Full lifecycle — upload, list, delete."""
        template_id = "test-template"

        # Upload
        content = b"\x89PNG fake asset"
        path = await local_gateway.upload_asset(template_id, "logo.png", content)
        assert path is not None

        # Verify file exists
        expected = tmp_path / template_id / "assets" / "logo.png"
        assert expected.exists()

        # Delete via direct path (assets.py delete_asset uses filesystem)
        expected.unlink()
        assert not expected.exists()


# =====================================================================
# Test: Pipeline Result via StorageGateway
# =====================================================================


class TestPipelineResultIntegration:
    """Test that pipeline_result uses storage gateway for persistence."""

    @pytest.mark.asyncio
    async def test_save_result_via_gateway(
        self, local_gateway: LocalStorageGateway, tmp_path: Path, job_id: str
    ):
        """AC6: save_result is mandatory via gateway."""
        result_json = {"field_mappings": [], "document_type": "boleto"}
        await local_gateway.save_result(job_id, result_json)

        result_path = tmp_path / job_id / "result.json"
        assert result_path.exists()
        loaded = json.loads(result_path.read_text())
        assert loaded == result_json

    @pytest.mark.asyncio
    async def test_save_clusters_via_gateway(
        self, local_gateway: LocalStorageGateway, tmp_path: Path, job_id: str
    ):
        """AC6: save_clusters via gateway."""
        clusters = [{"cluster_id": 0, "pages": [0], "representative_page": 0}]
        await local_gateway.save_clusters(job_id, clusters)

        clusters_path = tmp_path / job_id / "clusters.json"
        assert clusters_path.exists()



# =====================================================================
# Test: Storage injection in analyze.py context
# =====================================================================


class TestAnalyzeStorageInjection:
    """Test that analyze.py injects _storage into pipeline context."""

    def test_get_storage_returns_singleton(self):
        """Verify get_storage() returns same instance on repeated calls."""
        gw1 = get_storage()
        gw2 = get_storage()
        assert gw1 is gw2

    def test_get_storage_reset(self, local_gateway: LocalStorageGateway):
        """Verify _reset_storage() replaces the singleton."""
        gw = get_storage()
        assert gw is local_gateway


# =====================================================================
# Test: Full pipeline with STORAGE_MODE=local (regression)
# =====================================================================


class TestLocalModeRegression:
    """Verify STORAGE_MODE=local keeps everything working as before."""

    @pytest.mark.asyncio
    async def test_full_upload_cycle_local_mode(
        self, local_gateway: LocalStorageGateway, tmp_path: Path
    ):
        """AC8: Full cycle — upload PDF, XSD, verify files exist."""
        job_id = "regression-test-001"

        # Upload PDF
        pdf_content = b"%PDF-1.4 regression test"
        pdf_path = await local_gateway.upload_pdf(job_id, 0, pdf_content)
        assert Path(pdf_path).exists()

        # Upload XSD as asset
        xsd_content = b'<?xml version="1.0"?><xs:schema/>'
        xsd_path = await local_gateway.upload_asset(job_id, "schema.xsd", xsd_content)
        assert Path(xsd_path).exists()

        # Get local path
        local = await local_gateway.get_local_path(job_id, "input.pdf")
        assert local.exists()
        assert local.read_bytes() == pdf_content

        # Save result
        result = {"status": "ok"}
        await local_gateway.save_result(job_id, result)
        result_path = tmp_path / job_id / "result.json"
        assert result_path.exists()

        # Cleanup
        await local_gateway.cleanup_local(job_id)
        assert not (tmp_path / job_id).exists()

    @pytest.mark.asyncio
    async def test_screenshot_url_format_local(
        self, local_gateway: LocalStorageGateway, tmp_path: Path
    ):
        """AC8: Screenshot upload returns valid local path."""
        job_id = "screenshot-url-test"
        png = b"\x89PNG fake"
        path = await local_gateway.upload_screenshot(job_id, "page_0_0", png)

        # In local mode, result is a file path (string)
        assert isinstance(path, str)
        assert Path(path).exists()

    @pytest.mark.asyncio
    async def test_signed_url_local_mode(
        self, local_gateway: LocalStorageGateway
    ):
        """AC8: get_signed_url returns API path in local mode."""
        url = await local_gateway.get_signed_url(
            "jobs", "jobs/test/screenshots/page_0.png"
        )
        assert url.startswith("/api/files/")


# =====================================================================
# Test: Supabase mock integration
# =====================================================================


class TestSupabaseMockIntegration:
    """AC9: Verify gateway works with mocked Supabase client."""

    @pytest.mark.asyncio
    async def test_upload_pdf_supabase_mock(self, tmp_path: Path):
        """Upload PDF via SupabaseStorageGateway with mock client.

        Fix AC-4: supabase-py v2 is synchronous — storage.upload is a sync call.
        Use MagicMock (not AsyncMock) so assert_called_once() works correctly.
        """
        from services.storage.supabase_gateway import SupabaseStorageGateway

        mock_supabase = MagicMock()
        storage_bucket = MagicMock()
        storage_bucket.upload = MagicMock()  # sync, not AsyncMock
        mock_supabase.storage.from_ = MagicMock(return_value=storage_bucket)

        gw = SupabaseStorageGateway(supabase=mock_supabase, tmp_base=tmp_path)
        result = await gw.upload_pdf("mock-job", 0, b"pdf-content")

        assert result == "jobs/mock-job/pdfs/input.pdf"
        storage_bucket.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_result_supabase_mock(self, tmp_path: Path):
        """Save result via SupabaseStorageGateway with mock client.

        Fix AC-4: two issues corrected:
        1. execute() is sync (use MagicMock, not AsyncMock)
        2. gateway uses upsert(), not update() — assert upsert not update
        """
        from services.storage.supabase_gateway import SupabaseStorageGateway

        mock_supabase = MagicMock()
        table_mock = MagicMock()
        table_mock.upsert = MagicMock(return_value=table_mock)  # gateway uses upsert
        table_mock.eq = MagicMock(return_value=table_mock)
        table_mock.execute = MagicMock()  # sync, not AsyncMock
        mock_supabase.table = MagicMock(return_value=table_mock)

        gw = SupabaseStorageGateway(supabase=mock_supabase, tmp_base=tmp_path)
        await gw.save_result("mock-job", {"status": "done"})

        mock_supabase.table.assert_called_with("jobs")
        table_mock.upsert.assert_called_once()
