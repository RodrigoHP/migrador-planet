"""Tests for Story 43.2 — Raster Table Vision API Fallback.

Covers:
- AC1: When _build_visual_table_from_blocks returns None AND table_area detected, Vision API is called
- AC3: Vision API result converted to vision_raster_fallback table structure
- AC4: Extracted table assigned to correct section via _assign_visual_elements_to_sections
- AC5: Cost tracked in api_cost_total (via _extract_raster_table_via_vision return)
- AC6: Vision failure logs warning and continues without table (no exception propagation)
- AC7: Unit test with mocks for _build_visual_table_from_blocks and chat_with_vision
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_VISION_TABLE_RESPONSE = json.dumps(
    {
        "headers": ["Parcela", "Vencimento", "Valor"],
        "rows": [
            ["1", "10/01/2026", "R$ 150,00"],
            ["2", "10/02/2026", "R$ 150,00"],
        ],
    }
)


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
        "bbox": [0, 0, 600, 800],  # Full-page bbox so region_cy is always inside
        "sections": [
            {
                "section_id": "sec-0",
                "blocks": blocks or [],
                "tables": [],
            }
        ],
    }


# ---------------------------------------------------------------------------
# AC7: _parse_raster_table_response
# ---------------------------------------------------------------------------


class TestParseRasterTableResponse:
    """Unit tests for the JSON parser used in raster table extraction."""

    def test_parses_valid_json_with_headers_and_rows(self):
        from services.stages.stage3_structural.visual_analysis import _parse_raster_table_response

        raw = json.dumps({"headers": ["A", "B"], "rows": [["1", "2"]]})
        result = _parse_raster_table_response(raw)
        assert result is not None
        assert result["headers"] == ["A", "B"]
        assert result["rows"] == [["1", "2"]]

    def test_parses_json_wrapped_in_markdown_fences(self):
        from services.stages.stage3_structural.visual_analysis import _parse_raster_table_response

        raw = "```json\n" + json.dumps({"headers": ["X"], "rows": []}) + "\n```"
        result = _parse_raster_table_response(raw)
        assert result is not None
        assert result["headers"] == ["X"]

    def test_returns_none_for_invalid_json(self):
        from services.stages.stage3_structural.visual_analysis import _parse_raster_table_response

        result = _parse_raster_table_response("not json at all")
        assert result is None

    def test_returns_none_for_missing_headers_and_rows(self):
        from services.stages.stage3_structural.visual_analysis import _parse_raster_table_response

        raw = json.dumps({"other_key": "value"})
        result = _parse_raster_table_response(raw)
        assert result is None

    def test_accepts_dict_with_only_headers(self):
        from services.stages.stage3_structural.visual_analysis import _parse_raster_table_response

        raw = json.dumps({"headers": ["Col1", "Col2"]})
        result = _parse_raster_table_response(raw)
        assert result is not None
        assert "headers" in result

    def test_accepts_dict_with_only_rows(self):
        from services.stages.stage3_structural.visual_analysis import _parse_raster_table_response

        raw = json.dumps({"rows": [["a", "b"]]})
        result = _parse_raster_table_response(raw)
        assert result is not None
        assert "rows" in result


# ---------------------------------------------------------------------------
# AC7: _extract_raster_table_via_vision
# ---------------------------------------------------------------------------


class TestExtractRasterTableViaVision:
    """Tests for the async Vision API table extractor."""

    @pytest.mark.asyncio
    async def test_returns_vision_raster_fallback_table(self):
        """Returns table dict with source=vision_raster_fallback on valid Vision response."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_via_vision

        mock_client = MagicMock()
        bbox = [50, 200, 500, 400]

        with patch(
            "services.openrouter_client.chat_with_vision",
            new=AsyncMock(return_value=(_MOCK_VISION_TABLE_RESPONSE, 0.03)),
        ):
            table, cost = await _extract_raster_table_via_vision(mock_client, "img_b64", bbox)

        assert table is not None
        assert table["source"] == "vision_raster_fallback"
        assert table["bbox"] == bbox
        assert table["has_ruling_lines"] is False
        assert table["col_count"] == 3
        assert table["row_count"] == 3  # 1 header row + 2 data rows
        assert table["raw_cells"][0] == ["Parcela", "Vencimento", "Valor"]
        assert cost == pytest.approx(0.03)

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_response(self):
        """Returns (None, cost) when Vision API returns non-parseable response."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_via_vision

        mock_client = MagicMock()

        with patch(
            "services.openrouter_client.chat_with_vision",
            new=AsyncMock(return_value=("this is not json", 0.01)),
        ):
            table, cost = await _extract_raster_table_via_vision(mock_client, "img_b64", [0, 0, 100, 100])

        assert table is None
        assert cost == pytest.approx(0.01)

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_headers_and_rows(self):
        """Returns (None, cost) when Vision API returns empty headers and rows."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_via_vision

        mock_client = MagicMock()
        empty_response = json.dumps({"headers": [], "rows": []})

        with patch(
            "services.openrouter_client.chat_with_vision",
            new=AsyncMock(return_value=(empty_response, 0.02)),
        ):
            table, cost = await _extract_raster_table_via_vision(mock_client, "img_b64", [0, 0, 100, 100])

        assert table is None

    @pytest.mark.asyncio
    async def test_propagates_cost_even_on_parse_failure(self):
        """Cost is returned even when table parsing fails (API call was made)."""
        from services.stages.stage3_structural.visual_analysis import _extract_raster_table_via_vision

        mock_client = MagicMock()

        with patch(
            "services.openrouter_client.chat_with_vision",
            new=AsyncMock(return_value=("bad json", 0.025)),
        ):
            table, cost = await _extract_raster_table_via_vision(mock_client, "img_b64", [0, 0, 100, 100])

        assert table is None
        assert cost == pytest.approx(0.025)


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
            "source": "vision_raster_fallback",
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
        assert tables[0]["source"] == "vision_raster_fallback"
        assert tables[0]["col_count"] == 2

    def test_prefers_build_result_over_extracted_table(self):
        """AC4: When _build_visual_table_from_blocks succeeds, extracted_table is NOT used."""
        region = _make_region("table_area", [50, 200, 500, 400])
        region["extracted_table"] = {
            "bbox": [50, 200, 500, 400],
            "raw_cells": [["A"], ["1"]],
            "has_ruling_lines": False,
            "col_count": 1,
            "row_count": 2,
            "source": "vision_raster_fallback",
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
