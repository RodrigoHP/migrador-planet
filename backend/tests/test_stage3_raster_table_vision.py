"""Tests for Story 43.2 (rev) — Raster Table Extraction via Mistral OCR PDF.

ADR 2026-04-13: mistral-ocr-pdf replaces GPT-4o for raster table extraction.

Covers:
- AC1: When _build_visual_table_from_blocks returns None AND table_area detected, Mistral OCR is called
- AC3: Mistral result converted to mistral_ocr_raster table structure with layout
- AC4: Extracted table assigned to correct section via _assign_visual_elements_to_sections
- AC5: Cost tracked in api_cost_total (Mistral $0.001/page)
- AC6: Failure logs warning and continues without table (no exception propagation)
- AC7: Unit tests with mocks for Mistral HTTP call and HTML parser
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_MISTRAL_HTML_TABLE = """
<table>
<tr><th>Parcela</th><th>Vencimento</th><th>Valor</th></tr>
<tr><td>1</td><td>10/01/2026</td><td>R$ 150,00</td></tr>
<tr><td>2</td><td>10/02/2026</td><td>R$ 150,00</td></tr>
</table>
"""

_MOCK_MISTRAL_RESPONSE = {
    "pages": [
        {
            "tables": [{"content": _MOCK_MISTRAL_HTML_TABLE}],
        }
    ],
    "usage_info": {"pages_processed": 1},
}

_MOCK_MISTRAL_HTML_WITH_COLSPAN = """
<table>
<tr><th colspan="2">Header A</th><th>Header B</th></tr>
<tr><td>v1a</td><td>v1b</td><td>v2</td></tr>
</table>
"""


def _make_region(rtype: str = "table_area", bbox: list[int] | None = None) -> dict[str, Any]:
    return {
        "type": rtype,
        "bbox": bbox or [50, 200, 500, 400],
        "description": "Tabela de parcelas",
        "html_suggestion": "<table></table>",
        "chart_type": None,
        "barcode_format": None,
        "confidence": 90,
    }


def _make_zone_with_section(blocks: list | None = None) -> dict[str, Any]:
    return {
        "zone_id": "zone-0",
        "bbox": [0, 0, 600, 800],
        "sections": [
            {
                "section_id": "sec-0",
                "blocks": blocks or [],
                "tables": [],
            }
        ],
    }


# ---------------------------------------------------------------------------
# AC7: _parse_html_table_mistral
# ---------------------------------------------------------------------------


class TestParseHtmlTableMistral:
    """Unit tests for the generic HTML table parser (Mistral OCR output)."""

    def test_parses_simple_table(self):
        from services.stages.stage3_structural.visual_analysis import _parse_html_table_mistral

        html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        result = _parse_html_table_mistral(html)
        assert result is not None
        assert result["headers"] == ["A", "B"]
        assert result["rows"] == [["1", "2"]]

    def test_returns_layout_with_col_widths(self):
        from services.stages.stage3_structural.visual_analysis import _parse_html_table_mistral

        html = "<table><tr><th>A</th><th>B</th><th>C</th></tr><tr><td>1</td><td>2</td><td>3</td></tr></table>"
        result = _parse_html_table_mistral(html)
        assert result is not None
        assert "layout" in result
        assert len(result["layout"]["col_widths_pct"]) == 3
        assert abs(sum(result["layout"]["col_widths_pct"]) - 1.0) < 0.001

    def test_colspan_computes_proportional_widths(self):
        from services.stages.stage3_structural.visual_analysis import _parse_html_table_mistral

        result = _parse_html_table_mistral(_MOCK_MISTRAL_HTML_WITH_COLSPAN)
        assert result is not None
        # "Header A" has colspan=2 → [0.667, 0.333] approx
        assert result["layout"]["col_widths_pct"][0] == pytest.approx(2 / 3, abs=0.01)

    def test_br_in_cell_joins_parts(self):
        from services.stages.stage3_structural.visual_analysis import _parse_html_table_mistral

        html = "<table><tr><th>Label<br/>Value</th></tr></table>"
        result = _parse_html_table_mistral(html)
        assert result is not None
        assert "Label" in result["headers"][0]
        assert "Value" in result["headers"][0]

    def test_returns_none_for_empty_table(self):
        from services.stages.stage3_structural.visual_analysis import _parse_html_table_mistral

        result = _parse_html_table_mistral("<table></table>")
        assert result is None

    def test_returns_none_for_no_html(self):
        from services.stages.stage3_structural.visual_analysis import _parse_html_table_mistral

        result = _parse_html_table_mistral("")
        assert result is None

    def test_row_heights_pct_uniform(self):
        from services.stages.stage3_structural.visual_analysis import _parse_html_table_mistral

        html = "<table><tr><th>A</th></tr><tr><td>1</td></tr><tr><td>2</td></tr></table>"
        result = _parse_html_table_mistral(html)
        assert result is not None
        rh = result["layout"]["row_heights_pct"]
        assert len(rh) == 2  # 2 data rows
        assert all(abs(v - 0.5) < 0.001 for v in rh)


# ---------------------------------------------------------------------------
# AC7: _extract_raster_table_mistral
# ---------------------------------------------------------------------------


class TestExtractRasterTableMistral:
    """Tests for the async Mistral OCR raster table extractor."""

    def _mock_mistral_response(self, data: dict) -> MagicMock:
        """Return an httpx mock that yields the given JSON."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = data
        return mock_resp

    @pytest.mark.asyncio
    async def test_returns_mistral_ocr_raster_source(self, tmp_path):
        """AC3: Returns table dict with source=mistral_ocr_raster on valid Mistral response."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_mistral

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        bbox = [50, 200, 500, 400]
        cache: dict = {}

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value.post = AsyncMock(return_value=self._mock_mistral_response(_MOCK_MISTRAL_RESPONSE))

            table, cost = await _extract_raster_table_mistral(str(pdf), 0, bbox, "fake-key", cache)

        assert table is not None
        assert table["source"] == "mistral_ocr_raster"
        assert table["bbox"] == bbox
        assert table["has_ruling_lines"] is False
        assert table["col_count"] == 3
        assert "layout" in table
        assert cost == pytest.approx(0.001)

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self, tmp_path):
        """AC5: Second call for same pdf_path uses cache — no duplicate API call."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_mistral

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        cache: dict = {}

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
            post_mock = AsyncMock(return_value=self._mock_mistral_response(_MOCK_MISTRAL_RESPONSE))
            mock_http.return_value.post = post_mock

            # First call
            await _extract_raster_table_mistral(str(pdf), 0, [0, 0, 100, 100], "fake-key", cache)
            # Second call — same pdf
            table2, cost2 = await _extract_raster_table_mistral(str(pdf), 0, [0, 0, 100, 100], "fake-key", cache)

        # API should only be called once
        assert post_mock.call_count == 1
        assert cost2 == pytest.approx(0.0)  # cached, no charge
        assert table2 is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_tables_on_page(self, tmp_path):
        """Returns (None, cost) when Mistral page has no tables[]."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_mistral

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        no_tables_resp = {"pages": [{"tables": []}], "usage_info": {"pages_processed": 1}}

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value.post = AsyncMock(return_value=self._mock_mistral_response(no_tables_resp))

            table, cost = await _extract_raster_table_mistral(str(pdf), 0, [0, 0, 100, 100], "fake-key", {})

        assert table is None
        assert cost > 0  # API was called

    @pytest.mark.asyncio
    async def test_returns_none_on_missing_pdf(self, tmp_path):
        """AC6: Returns (None, 0.0) when PDF path does not exist — no exception."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_mistral

        table, cost = await _extract_raster_table_mistral("/nonexistent/path.pdf", 0, [0, 0, 100, 100], "fake-key", {})

        assert table is None
        assert cost == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_raises_on_mistral_api_error(self, tmp_path):
        """AC6: RuntimeError raised on Mistral API error response."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_mistral

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        error_resp = {"object": "error", "message": "Unauthorized"}

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value.post = AsyncMock(return_value=self._mock_mistral_response(error_resp))

            with pytest.raises(RuntimeError, match="Mistral OCR error"):
                await _extract_raster_table_mistral(str(pdf), 0, [0, 0, 100, 100], "fake-key", {})


# ---------------------------------------------------------------------------
# AC1 + AC4 + AC6: section_utils.py raster fallback path
# ---------------------------------------------------------------------------


class TestSectionUtilsRasterFallback:
    """Tests for the raster table consumption in _assign_visual_elements_to_sections."""

    def _run_assign(self, zones: list, visual_analysis: dict, page_key: str) -> list:
        from services.stages.stage3_structural.section_utils import _assign_visual_elements_to_sections

        _assign_visual_elements_to_sections(zones, visual_analysis, page_key)
        tables = []
        for zone in zones:
            for section in zone.get("sections", []):
                tables.extend(section.get("tables", []))
        return tables

    def test_uses_extracted_table_when_build_returns_none(self):
        """AC1+AC4: When _build_visual_table_from_blocks returns None AND extracted_table present, table is added."""
        region = _make_region("table_area", [50, 200, 500, 400])
        region["extracted_table"] = {
            "bbox": [50, 200, 500, 400],
            "raw_cells": [["A", "B"], ["1", "2"]],
            "has_ruling_lines": False,
            "col_count": 2,
            "row_count": 2,
            "source": "mistral_ocr_raster",
            "layout": {"col_widths_pct": [0.5, 0.5], "row_heights_pct": [1.0]},
        }

        zone = _make_zone_with_section(blocks=[])  # No text blocks → _build returns None
        visual_analysis = {
            "page-0": {
                "regions": [region],
                "consistency_score": 80,
                "consistency_notes": "",
            }
        }

        with patch(
            "services.stages.stage3_structural.section_utils._build_visual_table_from_blocks",
            return_value=None,
        ):
            tables = self._run_assign([zone], visual_analysis, "page-0")

        assert len(tables) == 1
        assert tables[0]["source"] == "mistral_ocr_raster"
        assert tables[0]["col_count"] == 2
        assert "layout" in tables[0]

    def test_prefers_build_result_over_extracted_table(self):
        """AC4: When _build_visual_table_from_blocks succeeds, extracted_table is NOT used."""
        region = _make_region("table_area", [50, 200, 500, 400])
        region["extracted_table"] = {
            "bbox": [50, 200, 500, 400],
            "raw_cells": [["A"], ["1"]],
            "has_ruling_lines": False,
            "col_count": 1,
            "row_count": 2,
            "source": "mistral_ocr_raster",
        }

        synthetic_table = {
            "bbox": [50, 200, 500, 400],
            "raw_cells": [["X", "Y"]],
            "has_ruling_lines": True,
            "col_count": 2,
            "row_count": 1,
            "source": "visual_analysis_fallback",
        }

        zone = _make_zone_with_section()
        visual_analysis = {
            "page-0": {
                "regions": [region],
                "consistency_score": 80,
                "consistency_notes": "",
            }
        }

        with patch(
            "services.stages.stage3_structural.section_utils._build_visual_table_from_blocks",
            return_value=synthetic_table,
        ):
            tables = self._run_assign([zone], visual_analysis, "page-0")

        assert len(tables) == 1
        assert tables[0]["source"] == "visual_analysis_fallback"

    def test_no_table_added_when_both_build_and_extracted_are_none(self):
        """AC6: When both _build and extracted_table are None, no table added (no exception)."""
        region = _make_region("table_area")
        # No extracted_table key

        zone = _make_zone_with_section()
        visual_analysis = {
            "page-0": {
                "regions": [region],
                "consistency_score": 80,
                "consistency_notes": "",
            }
        }

        with patch(
            "services.stages.stage3_structural.section_utils._build_visual_table_from_blocks",
            return_value=None,
        ):
            tables = self._run_assign([zone], visual_analysis, "page-0")

        assert len(tables) == 0

    def test_non_table_area_region_not_affected(self):
        """AC4: image_area and body regions are not treated as raster tables."""
        region_image = _make_region("image_area")
        region_body = _make_region("body")

        zone = _make_zone_with_section()
        visual_analysis = {
            "page-0": {
                "regions": [region_image, region_body],
                "consistency_score": 80,
                "consistency_notes": "",
            }
        }

        tables = self._run_assign([zone], visual_analysis, "page-0")
        assert len(tables) == 0
