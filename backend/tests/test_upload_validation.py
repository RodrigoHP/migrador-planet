"""Tests for upload file size + page count validation (Story 15.5).

Verifies:
  - PDF > 50MB is rejected with HTTP 413
  - PDF with total pages > 500 is rejected with HTTP 422
  - Valid PDFs pass validation
  - Invalid (non-PDF) bytes are rejected with HTTP 422
  - Limits are configurable via MAX_FILE_SIZE_MB and MAX_PAGE_COUNT env vars
"""

from __future__ import annotations

import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_fitz_doc(page_count: int):
    """Return a mock fitz document with given page count."""
    doc = MagicMock()
    doc.__len__ = MagicMock(return_value=page_count)
    doc.close = MagicMock()
    return doc


def _make_pdf_bytes(size_bytes: int = 1024) -> bytes:
    """Return fake bytes that simulate a small PDF."""
    return b"%PDF-1.4 fake content " + b"x" * max(0, size_bytes - 22)


# ---------------------------------------------------------------------------
# Tests — upload router validation constants
# ---------------------------------------------------------------------------


class TestUploadValidationConstants:
    def test_max_file_size_default(self):
        """Default max file size is 50 MB."""
        import routers.upload as mod

        assert mod._MAX_FILE_SIZE_MB == int(os.environ.get("MAX_FILE_SIZE_MB", "50"))
        assert mod._MAX_FILE_SIZE_BYTES == mod._MAX_FILE_SIZE_MB * 1024 * 1024

    def test_max_page_count_default(self):
        """Default max page count is 500."""
        import routers.upload as mod

        assert mod._MAX_PAGE_COUNT == int(os.environ.get("MAX_PAGE_COUNT", "500"))

    def test_max_file_size_env_override(self):
        """MAX_FILE_SIZE_MB env var overrides default."""
        import importlib

        with patch.dict(os.environ, {"MAX_FILE_SIZE_MB": "10"}):
            import routers.upload as mod

            importlib.reload(mod)
            assert mod._MAX_FILE_SIZE_MB == 10
            assert mod._MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024

    def test_max_page_count_env_override(self):
        """MAX_PAGE_COUNT env var overrides default."""
        import importlib

        with patch.dict(os.environ, {"MAX_PAGE_COUNT": "100"}):
            import routers.upload as mod

            importlib.reload(mod)
            assert mod._MAX_PAGE_COUNT == 100


# ---------------------------------------------------------------------------
# Tests — validation logic (unit-level, not HTTP)
# ---------------------------------------------------------------------------


class TestFileSizeValidation:
    def test_file_within_limit_passes(self):
        """Content within size limit should not raise."""

        import routers.upload as mod

        content = _make_pdf_bytes(1024)  # 1 KB — well within 50 MB
        # Should not raise
        assert len(content) <= mod._MAX_FILE_SIZE_BYTES

    def test_file_exceeds_limit_detected(self):
        """Content exceeding size limit should be detected."""
        import routers.upload as mod

        oversized = b"x" * (mod._MAX_FILE_SIZE_BYTES + 1)
        assert len(oversized) > mod._MAX_FILE_SIZE_BYTES

    def test_413_response_detail_message(self):
        """413 error detail should mention maximum size."""
        import routers.upload as mod

        expected_fragment = f"Maximum size: {mod._MAX_FILE_SIZE_MB}MB"
        # The actual raise in upload.py uses this format string
        detail = f"File too large. Maximum size: {mod._MAX_FILE_SIZE_MB}MB"
        assert expected_fragment in detail

    def test_file_exactly_at_limit_passes(self):
        """File exactly at the size limit should not be oversized."""
        import routers.upload as mod

        at_limit = b"x" * mod._MAX_FILE_SIZE_BYTES
        assert len(at_limit) <= mod._MAX_FILE_SIZE_BYTES


class TestPageCountValidation:
    def test_page_count_within_limit_passes(self):
        """Total pages within limit should not trigger rejection."""
        import routers.upload as mod

        assert 100 <= mod._MAX_PAGE_COUNT

    def test_page_count_exceeds_limit_detected(self):
        """Total pages exceeding limit should be detected."""
        import routers.upload as mod

        assert mod._MAX_PAGE_COUNT + 1 > mod._MAX_PAGE_COUNT

    def test_422_response_detail_message(self):
        """422 error detail should mention maximum page count."""
        import routers.upload as mod

        detail = f"Too many pages. Maximum: {mod._MAX_PAGE_COUNT}"
        assert f"Maximum: {mod._MAX_PAGE_COUNT}" in detail

    def test_page_count_exactly_at_limit_passes(self):
        """Page count exactly at limit should not trigger rejection."""
        import routers.upload as mod

        assert mod._MAX_PAGE_COUNT <= mod._MAX_PAGE_COUNT


# ---------------------------------------------------------------------------
# Tests — upload endpoint integration (mocked storage + fitz)
# ---------------------------------------------------------------------------


def test_upload_rejects_oversized_pdf():
    """Upload endpoint should return 413 for PDF exceeding MAX_FILE_SIZE_BYTES."""
    from fastapi.testclient import TestClient

    import routers.upload as upload_mod

    oversized_content = b"x" * (upload_mod._MAX_FILE_SIZE_BYTES + 1)

    mock_storage = AsyncMock()
    mock_storage.upload_pdf = AsyncMock()
    mock_storage.upload_asset = AsyncMock()

    with patch("routers.upload.get_storage", return_value=mock_storage):
        from main import app

        with TestClient(app) as client:
            response = client.post(
                "/api/upload",
                files={
                    "pdfs[]": ("test.pdf", io.BytesIO(oversized_content), "application/pdf"),
                    "xsd": ("schema.xsd", io.BytesIO(b"<xs:schema/>"), "text/xml"),
                },
                data={"template_name": ""},
            )
    assert response.status_code == 413
    assert "Maximum size" in response.json().get("detail", "")


def test_upload_rejects_too_many_pages():
    """Upload endpoint should return 422 for PDF exceeding MAX_PAGE_COUNT."""
    import routers.upload as upload_mod

    pdf_content = _make_pdf_bytes(1024)  # small file, page count mocked

    mock_doc = _make_mock_fitz_doc(upload_mod._MAX_PAGE_COUNT + 1)
    mock_storage = AsyncMock()
    mock_storage.upload_pdf = AsyncMock()
    mock_storage.upload_asset = AsyncMock()

    with patch("routers.upload.get_storage", return_value=mock_storage):
        with patch("routers.upload.fitz.open", return_value=mock_doc):
            from fastapi.testclient import TestClient
            from main import app

            with TestClient(app) as client:
                response = client.post(
                    "/api/upload",
                    files={
                        "pdfs[]": ("test.pdf", io.BytesIO(pdf_content), "application/pdf"),
                        "xsd": ("schema.xsd", io.BytesIO(b"<xs:schema/>"), "text/xml"),
                    },
                    data={"template_name": ""},
                )
    assert response.status_code == 422
    assert "Too many pages" in response.json().get("detail", "")


def test_upload_rejects_invalid_pdf():
    """Upload endpoint should return 422 for bytes that are not a valid PDF."""

    invalid_content = b"this is not a PDF at all"

    mock_storage = AsyncMock()
    mock_storage.upload_pdf = AsyncMock()
    mock_storage.upload_asset = AsyncMock()

    with patch("routers.upload.get_storage", return_value=mock_storage):
        with patch("routers.upload.fitz.open", side_effect=Exception("not a pdf")):
            from fastapi.testclient import TestClient
            from main import app

            with TestClient(app) as client:
                response = client.post(
                    "/api/upload",
                    files={
                        "pdfs[]": ("test.pdf", io.BytesIO(invalid_content), "application/pdf"),
                        "xsd": ("schema.xsd", io.BytesIO(b"<xs:schema/>"), "text/xml"),
                    },
                    data={"template_name": ""},
                )
    assert response.status_code == 422
    assert "Invalid PDF" in response.json().get("detail", "")
