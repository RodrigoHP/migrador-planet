"""Tests for Story 43.6 — Integrar Layout Schema completo no pipeline.

Covers:
- AC2: extract_dominant_font() uses PyMuPDF text_blocks (Stage 2 data)
- AC3: PIL per-row sampling called via _enrich_raster_table_style()
- AC4: Full schema stored in table dict with bbox, headers, rows, layout, style
- AC5: Unit tests for each data source (mock text_blocks, mock PIL, mock screenshot)
- AC6: Suite completa passa sem regressões
"""

from __future__ import annotations

import os
from typing import Any

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_text_block(
    bbox: list[float],
    font_name: str = "ArialMT",
    font_size: float = 8.0,
    is_bold: bool = False,
    font_color: str = "#000000",
) -> dict[str, Any]:
    return {
        "bbox": bbox,
        "font_name": font_name,
        "font_size": font_size,
        "is_bold": is_bold,
        "font_color": font_color,
        "text": "sample",
    }


def _make_solid_png(tmp_path, color=(255, 255, 255), size=(200, 100)):
    """Create a solid-color PNG for testing."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", size, color)
    path = str(tmp_path / "screenshot.png")
    img.save(path)
    return path


# ---------------------------------------------------------------------------
# AC2: extract_dominant_font
# ---------------------------------------------------------------------------


class TestExtractDominantFont:
    """Tests for dominant font extraction from Stage 2 text_blocks."""

    def test_returns_dominant_font_in_bbox(self):
        """AC2: Most common font in overlapping blocks is returned."""
        from services.stages.stage3_structural.visual_analysis import extract_dominant_font

        blocks = [
            _make_text_block([10, 10, 100, 20], font_name="ArialMT", font_size=8.0),
            _make_text_block([10, 20, 100, 30], font_name="ArialMT", font_size=8.0),
            _make_text_block([10, 30, 100, 40], font_name="TimesNewRoman", font_size=10.0),
        ]
        result = extract_dominant_font(blocks, [0, 0, 200, 100])

        assert result["font_family"] == "ArialMT"
        assert result["font_size_pt"] == pytest.approx(8.67, abs=0.1)  # mean of 8,8,10

    def test_normalizes_font_name(self):
        """AC2: Font names like 'ArialMT_feDefaultFont[0]' are normalized to 'ArialMT'."""
        from services.stages.stage3_structural.visual_analysis import extract_dominant_font

        blocks = [_make_text_block([0, 0, 100, 100], font_name="ArialMT_feDefaultFont[0]")]
        result = extract_dominant_font(blocks, [0, 0, 200, 200])

        assert result["font_family"] == "ArialMT"

    def test_returns_bold_when_majority_bold(self):
        """AC2: font_weight='bold' when more than half of blocks are bold."""
        from services.stages.stage3_structural.visual_analysis import extract_dominant_font

        blocks = [
            _make_text_block([0, 0, 100, 10], is_bold=True),
            _make_text_block([0, 10, 100, 20], is_bold=True),
            _make_text_block([0, 20, 100, 30], is_bold=False),
        ]
        result = extract_dominant_font(blocks, [0, 0, 200, 100])

        assert result["font_weight"] == "bold"

    def test_returns_normal_when_majority_not_bold(self):
        from services.stages.stage3_structural.visual_analysis import extract_dominant_font

        blocks = [
            _make_text_block([0, 0, 100, 10], is_bold=False),
            _make_text_block([0, 10, 100, 20], is_bold=False),
        ]
        result = extract_dominant_font(blocks, [0, 0, 200, 100])

        assert result["font_weight"] == "normal"

    def test_returns_empty_when_no_overlapping_blocks(self):
        """AC2: Returns {} when no text blocks overlap with bbox."""
        from services.stages.stage3_structural.visual_analysis import extract_dominant_font

        blocks = [_make_text_block([500, 500, 600, 600])]
        result = extract_dominant_font(blocks, [0, 0, 100, 100])

        assert result == {}

    def test_returns_empty_for_empty_block_list(self):
        from services.stages.stage3_structural.visual_analysis import extract_dominant_font

        result = extract_dominant_font([], [0, 0, 100, 100])
        assert result == {}

    def test_text_color_from_most_common(self):
        """AC2: text_color is the most common font_color among overlapping blocks."""
        from services.stages.stage3_structural.visual_analysis import extract_dominant_font

        blocks = [
            _make_text_block([0, 0, 100, 10], font_color="#000000"),
            _make_text_block([0, 10, 100, 20], font_color="#000000"),
            _make_text_block([0, 20, 100, 30], font_color="#FF0000"),
        ]
        result = extract_dominant_font(blocks, [0, 0, 200, 100])

        assert result["text_color"] == "#000000"


# ---------------------------------------------------------------------------
# AC2: _crop_table_image
# ---------------------------------------------------------------------------


class TestCropTableImage:
    """Tests for screenshot cropping to table bbox."""

    def test_creates_crop_png(self, tmp_path):
        """Returns path to a temp PNG file cropped to table bbox."""
        from services.stages.stage3_structural.visual_analysis import _crop_table_image

        screenshot = _make_solid_png(tmp_path, color=(200, 200, 200), size=(600, 800))
        # PDF bbox [100, 100, 300, 300] in 72dpi → [208, 208, 625, 625] in 150dpi
        crop_path = _crop_table_image(screenshot, [100.0, 100.0, 300.0, 300.0])

        assert crop_path is not None
        assert os.path.exists(crop_path)
        os.unlink(crop_path)

    def test_returns_none_for_invalid_bbox(self, tmp_path):
        """Returns None when bbox has zero or negative size."""
        from services.stages.stage3_structural.visual_analysis import _crop_table_image

        screenshot = _make_solid_png(tmp_path)
        crop_path = _crop_table_image(screenshot, [100.0, 100.0, 100.0, 100.0])  # zero size

        assert crop_path is None

    def test_returns_none_for_missing_screenshot(self):
        from services.stages.stage3_structural.visual_analysis import _crop_table_image

        crop_path = _crop_table_image("/nonexistent/screenshot.png", [0, 0, 100, 100])
        assert crop_path is None


# ---------------------------------------------------------------------------
# AC3 + AC4: _enrich_raster_table_style
# ---------------------------------------------------------------------------


class TestEnrichRasterTableStyle:
    """Tests for the full style enrichment pipeline."""

    def _make_table(self, bbox=(50.0, 200.0, 500.0, 400.0)):
        return {
            "bbox": list(bbox),
            "raw_cells": [["A", "B"], ["1", "2"]],
            "has_ruling_lines": False,
            "col_count": 2,
            "row_count": 2,
            "source": "mistral_ocr_raster",
            "layout": {
                "col_widths_pct": [0.5, 0.5],
                "row_heights_pct": [1.0],
            },
        }

    def test_adds_style_key_to_table(self, tmp_path):
        """AC4: After enrichment, table has 'style' key with expected fields."""
        from services.stages.stage3_structural.visual_analysis import _enrich_raster_table_style

        screenshot = _make_solid_png(tmp_path)
        table = self._make_table()
        page_data = {"text_blocks": [_make_text_block([50, 200, 500, 400])]}

        _enrich_raster_table_style(table, page_data, screenshot)

        assert "style" in table
        style = table["style"]
        assert "font_family" in style
        assert "font_size_pt" in style
        assert "font_weight" in style
        assert "text_color" in style
        assert "header_bg_color" in style
        assert "border_color" in style
        assert "border_width_pt" in style
        assert style["border_width_pt"] == 1.0

    def test_font_from_overlapping_text_blocks(self, tmp_path):
        """AC2: Font data comes from text_blocks in the table bbox region."""
        from services.stages.stage3_structural.visual_analysis import _enrich_raster_table_style

        screenshot = _make_solid_png(tmp_path)
        table = self._make_table(bbox=(50.0, 200.0, 500.0, 400.0))
        page_data = {
            "text_blocks": [
                _make_text_block([100, 210, 400, 230], font_name="ArialMT", font_size=8.0),
            ]
        }

        _enrich_raster_table_style(table, page_data, screenshot)

        assert table["style"]["font_family"] == "ArialMT"
        assert table["style"]["font_size_pt"] == 8.0

    def test_no_screenshot_produces_null_colors(self):
        """AC3: Without screenshot, color fields are None but no exception."""
        from services.stages.stage3_structural.visual_analysis import _enrich_raster_table_style

        table = self._make_table()
        page_data = {"text_blocks": []}

        _enrich_raster_table_style(table, page_data, screenshot_path=None)

        assert "style" in table
        assert table["style"]["header_bg_color"] is None
        assert table["style"]["border_color"] is None

    def test_row_bg_colors_present_when_row_heights_given(self, tmp_path):
        """AC3: row_bg_colors list populated when row_heights_pct available."""
        from services.stages.stage3_structural.visual_analysis import _enrich_raster_table_style

        screenshot = _make_solid_png(tmp_path, size=(600, 800))
        table = self._make_table(bbox=(0.0, 0.0, 200.0, 100.0))
        table["layout"]["row_heights_pct"] = [0.5, 0.5]
        page_data = {"text_blocks": []}

        _enrich_raster_table_style(table, page_data, screenshot)

        assert "row_bg_colors" in table["style"]
        assert len(table["style"]["row_bg_colors"]) == 2

    def test_enrich_is_idempotent_shape(self, tmp_path):
        """AC4: Second enrich call overwrites style — no duplicate keys."""
        from services.stages.stage3_structural.visual_analysis import _enrich_raster_table_style

        screenshot = _make_solid_png(tmp_path)
        table = self._make_table()
        page_data = {"text_blocks": []}

        _enrich_raster_table_style(table, page_data, screenshot)
        first_style = dict(table["style"])
        _enrich_raster_table_style(table, page_data, screenshot)

        assert table["style"].keys() == first_style.keys()
