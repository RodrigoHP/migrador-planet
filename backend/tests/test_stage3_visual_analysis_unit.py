"""Unit tests for Stage 3 visual_analysis helpers (Story 46.2).

Covers AC5:
- _get_raster_image_bboxes_pymupdf: area filter, ImportError fallback
- _build_regions_from_mistral: output structure, footer "#" sentinel
- _extract_raster_table_mistral: footer "#" treatment, no-table-no-image path
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _va():
    import services.stages.stage3_structural.visual_analysis as mod

    return mod


# ---------------------------------------------------------------------------
# _get_raster_image_bboxes_pymupdf
# ---------------------------------------------------------------------------


class TestGetRasterImageBboxesPyMuPDF:
    def test_filters_small_images(self):
        """Images below _MIN_TABLE_AREA_PTS are excluded."""
        mod = _va()

        # Build mock: one small image (logo 50x30 = 1500 pts²) and one large (300x200 = 60000 pts²)
        small_rect = MagicMock()
        small_rect.x0, small_rect.y0, small_rect.x1, small_rect.y1 = 10.0, 10.0, 60.0, 40.0  # 50x30 = 1500 pts²

        large_rect = MagicMock()
        large_rect.x0, large_rect.y0, large_rect.x1, large_rect.y1 = 50.0, 200.0, 350.0, 400.0  # 300x200 = 60000 pts²

        mock_page = MagicMock()
        mock_page.get_images.return_value = [("img1",), ("img2",)]
        mock_page.get_image_bbox.side_effect = [small_rect, large_rect]

        mock_doc = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_doc.close = MagicMock()

        with patch("fitz.open", return_value=mock_doc):
            result = mod._get_raster_image_bboxes_pymupdf("/fake/pdf", 0)

        # Only large image passes the area filter
        assert len(result) == 1
        assert result[0] == [50.0, 200.0, 350.0, 400.0]

    def test_sorted_by_area_descending(self):
        """Largest image is returned first."""
        mod = _va()

        rects = []
        for x1, y1 in [(200.0, 200.0), (400.0, 300.0), (150.0, 150.0)]:
            r = MagicMock()
            r.x0, r.y0, r.x1, r.y1 = 0.0, 0.0, x1, y1
            rects.append(r)

        mock_page = MagicMock()
        mock_page.get_images.return_value = [("img1",), ("img2",), ("img3",)]
        mock_page.get_image_bbox.side_effect = rects

        mock_doc = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_doc.close = MagicMock()

        with patch("fitz.open", return_value=mock_doc):
            result = mod._get_raster_image_bboxes_pymupdf("/fake/pdf", 0)

        # 400*300=120000 is largest
        assert result[0][2] == 400.0 and result[0][3] == 300.0

    def test_import_error_returns_empty(self):
        """If fitz is not importable, returns empty list."""
        mod = _va()

        with patch.dict("sys.modules", {"fitz": None}):
            result = mod._get_raster_image_bboxes_pymupdf("/fake/pdf", 0)

        assert result == []

    def test_exception_returns_empty(self):
        """If fitz.open raises, returns empty list (no exception propagated)."""
        mod = _va()

        with patch("fitz.open", side_effect=RuntimeError("file not found")):
            result = mod._get_raster_image_bboxes_pymupdf("/fake/pdf", 0)

        assert result == []


# ---------------------------------------------------------------------------
# _build_regions_from_mistral
# ---------------------------------------------------------------------------


class TestBuildRegionsFromMistral:
    def test_table_region_present(self):
        """When extracted_table is provided, a table_area region is included."""
        mod = _va()

        table: dict[str, Any] = {
            "bbox": [50.0, 100.0, 545.0, 700.0],
            "raw_cells": [["A", "B"]],
            "source": "mistral_ocr_raster",
        }
        zones: dict[str, str | None] = {"header": None, "footer": None}
        result = mod._build_regions_from_mistral(table, zones, 595.0, 842.0)

        region_types = [r["type"] for r in result["regions"]]
        assert "table_area" in region_types
        assert "body" in region_types

        table_region = next(r for r in result["regions"] if r["type"] == "table_area")
        assert table_region["bbox"] == [50, 100, 545, 700]
        assert table_region["confidence"] == 95

    def test_footer_hash_sentinel_excluded(self):
        """Footer '#' sentinel is treated as absent — no footer region generated."""
        mod = _va()

        zones: dict[str, str | None] = {"header": None, "footer": "#"}
        result = mod._build_regions_from_mistral(None, zones, 595.0, 842.0)

        region_types = [r["type"] for r in result["regions"]]
        assert "footer" not in region_types
        assert "body" in region_types

    def test_real_footer_generates_region(self):
        """A real footer text generates a footer region."""
        mod = _va()

        zones: dict[str, str | None] = {"header": None, "footer": "Page 1 of 5"}
        result = mod._build_regions_from_mistral(None, zones, 595.0, 842.0)

        region_types = [r["type"] for r in result["regions"]]
        assert "footer" in region_types
        footer = next(r for r in result["regions"] if r["type"] == "footer")
        assert "Page 1 of 5" in footer["description"]

    def test_header_zone_generates_region(self):
        """A real header text generates a header region."""
        mod = _va()

        zones: dict[str, str | None] = {"header": "EMPRESA S/A CNPJ 00.000", "footer": None}
        result = mod._build_regions_from_mistral(None, zones, 595.0, 842.0)

        region_types = [r["type"] for r in result["regions"]]
        assert "header" in region_types

    def test_no_header_no_footer_only_body(self):
        """Without header or footer zones, only body region is generated."""
        mod = _va()

        zones: dict[str, str | None] = {"header": None, "footer": None}
        result = mod._build_regions_from_mistral(None, zones, 595.0, 842.0)

        region_types = [r["type"] for r in result["regions"]]
        assert region_types == ["body"]

    def test_consistency_score_is_85(self):
        """consistency_score is always 85 for Mistral-based result."""
        mod = _va()

        result = mod._build_regions_from_mistral(None, {"header": None, "footer": None}, 595.0, 842.0)
        assert result["consistency_score"] == 85

    def test_consistency_level_is_consistent(self):
        """consistency_level field is present and equals 'consistent'."""
        mod = _va()

        result = mod._build_regions_from_mistral(None, {"header": None, "footer": None}, 595.0, 842.0)
        assert result.get("consistency_level") == "consistent"


# ---------------------------------------------------------------------------
# _extract_raster_table_mistral — footer "#" and no-table path
# ---------------------------------------------------------------------------


class TestExtractRasterTableMistral:
    @pytest.mark.asyncio
    async def test_footer_hash_becomes_none_in_zones(self):
        """Mistral '#' footer sentinel is converted to None in returned zones."""

        mod = _va()

        mock_mistral_response = {
            "pages": [
                {
                    "header": "HEADER TEXT",
                    "footer": "#",
                    "tables": [],
                }
            ],
            "usage_info": {"pages_processed": 1},
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_mistral_response

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch("pathlib.Path.read_bytes", return_value=b"%PDF-1.4 fake"),
            patch("httpx.AsyncClient", return_value=mock_async_client),
        ):
            table, cost, zones = await mod._extract_raster_table_mistral("/fake/test.pdf", 0, "test-key", {})

        assert zones["footer"] is None  # "#" → None
        assert zones["header"] == "HEADER TEXT"
        assert table is None  # no tables[] → no table returned
        assert cost > 0.0

    @pytest.mark.asyncio
    async def test_no_raster_image_returns_none(self):
        """Mistral finds table but PyMuPDF finds no raster image → None (vector table)."""
        mod = _va()

        mock_mistral_response = {
            "pages": [
                {
                    "header": None,
                    "footer": None,
                    "tables": [{"content": "<table><tr><td>Val</td></tr></table>"}],
                }
            ],
            "usage_info": {"pages_processed": 1},
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_mistral_response

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch("pathlib.Path.read_bytes", return_value=b"%PDF-1.4 fake"),
            patch("httpx.AsyncClient", return_value=mock_async_client),
            patch.object(mod, "_get_raster_image_bboxes_pymupdf", return_value=[]),
        ):
            table, cost, zones = await mod._extract_raster_table_mistral("/fake/test.pdf", 0, "test-key", {})

        # No raster bboxes → vector table, pdfplumber handles it → return None
        assert table is None

    @pytest.mark.asyncio
    async def test_pdf_path_none_returns_empty(self):
        """When pdf_path is None, returns (None, 0.0, empty_zones) without error."""
        mod = _va()

        table, cost, zones = await mod._extract_raster_table_mistral(None, 0, "test-key", {})

        assert table is None
        assert cost == 0.0
        assert zones == {"header": None, "footer": None}

    @pytest.mark.asyncio
    async def test_per_page_cache_key(self):
        """Cache key is '{pdf_path}:{page_index}' to allow per-page caching."""
        mod = _va()

        cache: dict[str, Any] = {}
        mock_pages = [{"header": None, "footer": None, "tables": []}]
        cache["test.pdf:2"] = {"pages": mock_pages}

        # With cache populated for page 2, no HTTP call should be made
        table, cost, zones = await mod._extract_raster_table_mistral("test.pdf", 2, "test-key", cache)

        assert cost == 0.0  # cache hit → cost is 0
        assert table is None
