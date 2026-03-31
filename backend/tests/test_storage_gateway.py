"""Tests for the StorageGateway abstraction, implementations, and factory.

Story 13.1 -- Storage Gateway: Abstraction + Supabase/Local implementations.

Covers:
- LocalStorageGateway: all 10 methods with real filesystem (tmp_path)
- SupabaseStorageGateway: all 10 methods with AsyncMock Supabase client
- Factory: valid configs, missing config (error), invalid config (error)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# We import from the package directly (backend is the CWD when running tests)
from services.storage import (
    ConfigurationError,
    StorageMode,
    create_storage_gateway,
)
from services.storage.gateway import StorageGateway
from services.storage.local_gateway import LocalStorageGateway
from services.storage.supabase_gateway import SupabaseStorageGateway


# =====================================================================
# LocalStorageGateway tests
# =====================================================================


class TestLocalStorageGateway:
    """Test LocalStorageGateway with real filesystem via tmp_path."""

    @pytest.fixture
    def gateway(self, tmp_path: Path) -> LocalStorageGateway:
        return LocalStorageGateway(tmp_base=tmp_path)

    @pytest.fixture
    def job_id(self) -> str:
        return "test-job-001"

    @pytest.mark.asyncio
    async def test_upload_pdf_first(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        content = b"%PDF-1.4 fake pdf content"
        result = await gateway.upload_pdf(job_id, 0, content)

        expected_path = tmp_path / job_id / "input.pdf"
        assert result == str(expected_path)
        assert expected_path.exists()
        assert expected_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_upload_pdf_subsequent(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        content = b"%PDF-1.4 second pdf"
        result = await gateway.upload_pdf(job_id, 1, content)

        expected_path = tmp_path / job_id / "input_2.pdf"
        assert result == str(expected_path)
        assert expected_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_upload_screenshot(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        png = b"\x89PNG fake screenshot"
        result = await gateway.upload_screenshot(job_id, "page_0", png)

        expected = tmp_path / job_id / "screenshots" / "page_0.png"
        assert result == str(expected)
        assert expected.read_bytes() == png

    @pytest.mark.asyncio
    async def test_upload_thumbnail(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        png = b"\x89PNG fake thumbnail"
        result = await gateway.upload_thumbnail(job_id, "page_0", png)

        expected = tmp_path / job_id / "thumbnails" / "page_0.png"
        assert result == str(expected)
        assert expected.read_bytes() == png

    @pytest.mark.asyncio
    async def test_upload_asset(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        img = b"\x89PNG asset image"
        result = await gateway.upload_asset(job_id, "img_0_3.png", img)

        expected = tmp_path / job_id / "assets" / "img_0_3.png"
        assert result == str(expected)
        assert expected.read_bytes() == img

    @pytest.mark.asyncio
    async def test_get_local_path(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        path = await gateway.get_local_path(job_id, "input.pdf")
        assert path == tmp_path / job_id / "input.pdf"

    @pytest.mark.asyncio
    async def test_get_signed_url(self, gateway: LocalStorageGateway):
        url = await gateway.get_signed_url("jobs", "jobs/abc/pdfs/input.pdf")
        assert url == "/api/files/jobs/abc/pdfs/input.pdf"

    @pytest.mark.asyncio
    async def test_save_result(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        result = {"field_mappings": [], "document_type": "boleto"}
        await gateway.save_result(job_id, result)

        result_path = tmp_path / job_id / "result.json"
        assert result_path.exists()
        loaded = json.loads(result_path.read_text())
        assert loaded == result

    @pytest.mark.asyncio
    async def test_save_clusters(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        clusters = [
            {"cluster_id": 0, "pages": [0, 1], "representative_page": 0},
            {"cluster_id": 1, "pages": [2], "representative_page": 2},
        ]
        await gateway.save_clusters(job_id, clusters)

        clusters_path = tmp_path / job_id / "clusters.json"
        assert clusters_path.exists()
        loaded = json.loads(clusters_path.read_text())
        assert loaded == clusters

    @pytest.mark.asyncio
    async def test_save_visual_data(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        data = {"pages": [{"page_index": 0, "cluster_id": "A", "drawn_elements": [{"type": "line"}], "text_blocks": [{"text": "hello"}]}]}
        await gateway.save_visual_data(job_id, data)

        vd_path = tmp_path / job_id / "visual_data.json"
        assert vd_path.exists()
        loaded = json.loads(vd_path.read_text())
        assert loaded == data

    @pytest.mark.asyncio
    async def test_load_visual_data_exists(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        data = {"pages": [{"page_index": 0, "cluster_id": "A", "drawn_elements": [], "text_blocks": []}]}
        await gateway.save_visual_data(job_id, data)

        loaded = await gateway.load_visual_data(job_id)
        assert loaded == data

    @pytest.mark.asyncio
    async def test_load_visual_data_not_exists(self, gateway: LocalStorageGateway, job_id: str):
        result = await gateway.load_visual_data(job_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_save_visual_data_format(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        data = {"pages": [{"page_index": 0, "cluster_id": "B", "drawn_elements": [{"type": "rect", "fill_color": "#fff"}], "text_blocks": [{"text": "ação", "font_size": 12}]}]}
        await gateway.save_visual_data(job_id, data)

        loaded = await gateway.load_visual_data(job_id)
        assert "pages" in loaded
        page = loaded["pages"][0]
        assert "page_index" in page
        assert "cluster_id" in page
        assert "drawn_elements" in page
        assert "text_blocks" in page

    @pytest.mark.asyncio
    async def test_cleanup_local(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        # Create some files first
        await gateway.upload_pdf(job_id, 0, b"pdf content")
        job_dir = tmp_path / job_id
        assert job_dir.exists()

        await gateway.cleanup_local(job_id)
        assert not job_dir.exists()

    @pytest.mark.asyncio
    async def test_cleanup_local_nonexistent(self, gateway: LocalStorageGateway, job_id: str):
        # Should not raise
        await gateway.cleanup_local(job_id)

    @pytest.mark.asyncio
    async def test_delete_job(self, gateway: LocalStorageGateway, tmp_path: Path, job_id: str):
        await gateway.upload_pdf(job_id, 0, b"pdf content")
        await gateway.upload_screenshot(job_id, "page_0", b"png")
        job_dir = tmp_path / job_id
        assert job_dir.exists()

        await gateway.delete_job(job_id)
        assert not job_dir.exists()


# =====================================================================
# SupabaseStorageGateway tests (mocked Supabase client)
# =====================================================================


def _make_mock_supabase() -> MagicMock:
    """Build a mock Supabase client with storage and table methods.

    supabase-py v2 is synchronous: all storage/db calls are sync, so we use
    MagicMock (not AsyncMock) for every storage and execute method.
    """
    mock = MagicMock()

    # storage.from_("bucket") returns a mock with upload/download/etc.
    storage_bucket = MagicMock()
    storage_bucket.upload = MagicMock()
    storage_bucket.download = MagicMock(return_value=b"downloaded-content")
    storage_bucket.create_signed_url = MagicMock(
        return_value={"signedURL": "https://example.com/signed"}
    )
    storage_bucket.list = MagicMock(return_value=[])
    storage_bucket.remove = MagicMock()
    mock.storage.from_ = MagicMock(return_value=storage_bucket)

    # table("name") returns a chainable mock
    table_mock = MagicMock()
    table_mock.update = MagicMock(return_value=table_mock)
    table_mock.upsert = MagicMock(return_value=table_mock)
    table_mock.delete = MagicMock(return_value=table_mock)
    table_mock.eq = MagicMock(return_value=table_mock)
    table_mock.execute = MagicMock()
    mock.table = MagicMock(return_value=table_mock)

    return mock


class TestSupabaseStorageGateway:
    """Test SupabaseStorageGateway with mocked Supabase client."""

    @pytest.fixture
    def mock_supabase(self) -> MagicMock:
        return _make_mock_supabase()

    @pytest.fixture
    def gateway(self, mock_supabase: MagicMock, tmp_path: Path) -> SupabaseStorageGateway:
        return SupabaseStorageGateway(supabase=mock_supabase, tmp_base=tmp_path)

    @pytest.fixture
    def job_id(self) -> str:
        return "supa-job-001"

    @pytest.mark.asyncio
    async def test_upload_pdf(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock,
        tmp_path: Path, job_id: str,
    ):
        content = b"%PDF-1.4 real content"
        result = await gateway.upload_pdf(job_id, 0, content)

        assert result == f"jobs/{job_id}/pdfs/input.pdf"
        # Verify Supabase upload was called
        mock_supabase.storage.from_("jobs").upload.assert_called_once()
        # Verify local copy was also written
        local_copy = tmp_path / job_id / "input.pdf"
        assert local_copy.exists()
        assert local_copy.read_bytes() == content

    @pytest.mark.asyncio
    async def test_upload_pdf_subsequent(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        result = await gateway.upload_pdf(job_id, 2, b"pdf3")
        assert result == f"jobs/{job_id}/pdfs/input_3.pdf"

    @pytest.mark.asyncio
    async def test_upload_screenshot(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        result = await gateway.upload_screenshot(job_id, "page_0", b"png-data")
        assert result == f"jobs/{job_id}/screenshots/page_0.png"
        mock_supabase.storage.from_("jobs").upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_thumbnail(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        result = await gateway.upload_thumbnail(job_id, "page_1", b"thumb")
        assert result == f"jobs/{job_id}/thumbnails/page_1.png"

    @pytest.mark.asyncio
    async def test_upload_asset(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        result = await gateway.upload_asset(job_id, "logo.png", b"logo-bytes")
        assert result == f"jobs/{job_id}/assets/logo.png"

    @pytest.mark.asyncio
    async def test_get_local_path_cache_miss(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock,
        tmp_path: Path, job_id: str,
    ):
        path = await gateway.get_local_path(job_id, "input.pdf")
        assert path == tmp_path / job_id / "input.pdf"
        assert path.exists()
        assert path.read_bytes() == b"downloaded-content"
        mock_supabase.storage.from_("jobs").download.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_local_path_cache_hit(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock,
        tmp_path: Path, job_id: str,
    ):
        # Pre-populate cache
        local_path = tmp_path / job_id / "input.pdf"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"cached-content")

        path = await gateway.get_local_path(job_id, "input.pdf")
        assert path == local_path
        # Download should NOT have been called
        mock_supabase.storage.from_("jobs").download.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_signed_url(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock,
    ):
        url = await gateway.get_signed_url("jobs", "jobs/abc/pdfs/input.pdf", 7200)
        assert url == "https://example.com/signed"

    @pytest.mark.asyncio
    async def test_save_result(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        result = {"field_mappings": []}
        await gateway.save_result(job_id, result)

        mock_supabase.table.assert_called_with("jobs")
        table = mock_supabase.table("jobs")
        table.upsert.assert_called_once_with(
            {"id": job_id, "result_json": result, "status": "completed"}
        )

    @pytest.mark.asyncio
    async def test_save_result_upserts_when_no_prior_row(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        """save_result must upsert (not update) so it works even without a pre-existing row."""
        result = {"field_mappings": [{"name": "field_a"}]}
        await gateway.save_result(job_id, result)

        table = mock_supabase.table("jobs")
        # Must use upsert, never update — update silently affects 0 rows when row absent
        table.upsert.assert_called_once()
        table.update.assert_not_called()
        payload = table.upsert.call_args[0][0]
        assert payload["id"] == job_id
        assert payload["status"] == "completed"
        assert payload["result_json"] == result

    @pytest.mark.asyncio
    async def test_save_clusters(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        clusters = [
            {
                "cluster_id": 0,
                "pages": [0, 1],
                "representative_page": 0,
                "confidence": {"score": 0.95},
            }
        ]
        await gateway.save_clusters(job_id, clusters)

        mock_supabase.table.assert_called_with("job_clusters")
        table = mock_supabase.table("job_clusters")
        table.upsert.assert_called_once()
        upserted = table.upsert.call_args[0][0]
        assert len(upserted) == 1
        assert upserted[0]["job_id"] == job_id
        assert upserted[0]["cluster_id"] == 0
        assert upserted[0]["representative"] == 0

    @pytest.mark.asyncio
    async def test_save_visual_data(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        data = {"pages": [{"page_index": 0, "cluster_id": "A", "drawn_elements": [], "text_blocks": []}]}
        await gateway.save_visual_data(job_id, data)

        mock_supabase.storage.from_("jobs").upload.assert_called_once()
        call_args = mock_supabase.storage.from_("jobs").upload.call_args
        assert call_args[0][0] == f"jobs/{job_id}/visual_data.json"

    @pytest.mark.asyncio
    async def test_load_visual_data_exists(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        import json as _json
        data = {"pages": [{"page_index": 0, "cluster_id": "A", "drawn_elements": [], "text_blocks": []}]}
        mock_supabase.storage.from_("jobs").download = MagicMock(
            return_value=_json.dumps(data).encode("utf-8")
        )

        loaded = await gateway.load_visual_data(job_id)
        assert loaded == data

    @pytest.mark.asyncio
    async def test_load_visual_data_not_exists(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock, job_id: str,
    ):
        mock_supabase.storage.from_("jobs").download = MagicMock(
            side_effect=Exception("Not found")
        )

        result = await gateway.load_visual_data(job_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_local(
        self, gateway: SupabaseStorageGateway, tmp_path: Path, job_id: str,
    ):
        job_dir = tmp_path / job_id
        job_dir.mkdir()
        (job_dir / "test.txt").write_text("data")

        await gateway.cleanup_local(job_id)
        assert not job_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_job(
        self, gateway: SupabaseStorageGateway, mock_supabase: MagicMock,
        tmp_path: Path, job_id: str,
    ):
        # Pre-create local cache
        job_dir = tmp_path / job_id
        job_dir.mkdir()
        (job_dir / "input.pdf").write_bytes(b"pdf")

        await gateway.delete_job(job_id)

        # Verify storage list + DB delete were called
        mock_supabase.storage.from_("jobs").list.assert_called_once()
        mock_supabase.table("jobs").delete.assert_called_once()
        # Verify local cache was cleaned
        assert not job_dir.exists()


# =====================================================================
# Factory tests
# =====================================================================


class TestFactory:
    """Test create_storage_gateway() factory."""

    def test_create_local_gateway(self):
        gw = create_storage_gateway(mode="local")
        assert isinstance(gw, LocalStorageGateway)

    def test_create_local_gateway_enum(self):
        gw = create_storage_gateway(mode=StorageMode.LOCAL)
        assert isinstance(gw, LocalStorageGateway)

    def test_create_supabase_gateway_with_client(self):
        mock_client = MagicMock()
        gw = create_storage_gateway(mode="supabase", supabase_client=mock_client)
        assert isinstance(gw, SupabaseStorageGateway)

    def test_missing_config_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            # Ensure STORAGE_MODE is not set
            env = os.environ.copy()
            env.pop("STORAGE_MODE", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ConfigurationError, match="STORAGE_MODE is not set"):
                    create_storage_gateway()

    def test_invalid_config_raises_error(self):
        with pytest.raises(ConfigurationError, match="invalid"):
            create_storage_gateway(mode="s3")

    def test_supabase_without_url_raises_error(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}, clear=False):
            # Remove both URL and KEY
            env = os.environ.copy()
            env.pop("SUPABASE_URL", None)
            env.pop("SUPABASE_KEY", None)
            env.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ConfigurationError, match="SUPABASE_URL"):
                    create_storage_gateway(mode="supabase")

    def test_from_env_var(self):
        with patch.dict(os.environ, {"STORAGE_MODE": "local"}):
            gw = create_storage_gateway()
            assert isinstance(gw, LocalStorageGateway)

    def test_case_insensitive(self):
        gw = create_storage_gateway(mode="LOCAL")
        assert isinstance(gw, LocalStorageGateway)


# =====================================================================
# ABC contract test
# =====================================================================


class TestABCContract:
    """Verify StorageGateway cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            StorageGateway()  # type: ignore[abstract]
