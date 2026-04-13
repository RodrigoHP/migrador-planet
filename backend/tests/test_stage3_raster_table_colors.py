"""Tests for Story 43.5 — PIL Pixel Sampling Per-Row para Background de Células Raster.

Covers:
- AC1: sample_table_colors(image_path, row_heights_pct) returns row_bg_colors: list[str]
- AC2: White (#FFFFFF ±30) and gray (#CCCCCC ±30) detected correctly in synthetic image
- AC3: Boleto all-white table: row_bg_colors = ["#FFFFFF", ...]
- AC4: header_bg_color remains separate
- AC5: Fallback: if row_heights_pct not provided, behavior unchanged (no row_bg_colors key)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _make_solid_image(tmp_path, color: tuple[int, int, int], size: tuple[int, int] = (200, 100)):
    """Create a solid-color PNG for testing."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", size, color)
    path = tmp_path / "test.png"
    img.save(path)
    return str(path)


def _make_striped_image(tmp_path, stripes: list[tuple[int, int, int]], width: int = 200):
    """Create a vertically striped PNG (each stripe same height)."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    stripe_h = 30
    h = stripe_h * len(stripes)
    img = Image.new("RGB", (width, h), (255, 255, 255))
    for i, color in enumerate(stripes):
        for y in range(i * stripe_h, (i + 1) * stripe_h):
            for x in range(width):
                img.putpixel((x, y), color)
    path = tmp_path / "striped.png"
    img.save(path)
    return str(path), stripe_h, h


class TestSampleTableColorsLegacy:
    """AC5: Legacy behavior (no row_heights_pct) — no row_bg_colors key returned."""

    def test_returns_header_bg_color_without_row_heights(self, tmp_path):
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        path = _make_solid_image(tmp_path, (255, 255, 255))
        result = sample_table_colors(path)

        assert "header_bg_color" in result
        assert "border_color" in result
        assert "row_bg_colors" not in result

    def test_header_is_white_for_white_image(self, tmp_path):
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        path = _make_solid_image(tmp_path, (255, 255, 255))
        result = sample_table_colors(path)

        assert result["header_bg_color"] == "#FFFFFF"

    def test_returns_none_for_nonexistent_image(self):
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        result = sample_table_colors("/nonexistent/path.png")

        assert result["header_bg_color"] is None
        assert result["border_color"] is None


class TestSampleTableColorsPerRow:
    """AC1: row_heights_pct provided → row_bg_colors: list[str]."""

    def test_returns_row_bg_colors_list(self, tmp_path):
        """AC1: Returns row_bg_colors with one entry per row."""
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        path = _make_solid_image(tmp_path, (255, 255, 255), size=(200, 150))
        row_heights_pct = [0.333, 0.333, 0.334]

        result = sample_table_colors(path, row_heights_pct=row_heights_pct)

        assert "row_bg_colors" in result
        assert len(result["row_bg_colors"]) == 3

    def test_all_white_rows_boleto(self, tmp_path):
        """AC3: Boleto with all-white rows returns ['#FFFFFF', '#FFFFFF', '#FFFFFF']."""
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        path = _make_solid_image(tmp_path, (255, 255, 255), size=(200, 150))
        row_heights_pct = [0.333, 0.333, 0.334]

        result = sample_table_colors(path, row_heights_pct=row_heights_pct)

        for color in result["row_bg_colors"]:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            assert r >= 225 and g >= 225 and b >= 225, f"Expected near-white, got {color}"

    def test_detects_alternating_white_and_gray(self, tmp_path):
        """AC2: Alternating white (#FFFFFF) and gray (#CCCCCC) rows detected correctly (±30)."""
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        white = (255, 255, 255)
        gray = (204, 204, 204)  # #CCCCCC
        path, stripe_h, total_h = _make_striped_image(tmp_path, [white, gray, white])
        row_heights_pct = [stripe_h / total_h] * 3

        result = sample_table_colors(path, row_heights_pct=row_heights_pct)
        colors = result["row_bg_colors"]

        assert len(colors) == 3

        def _channel(hex_color, offset):
            return int(hex_color[offset : offset + 2], 16)

        # Row 0: white (255,255,255) ± 30
        for offset in (1, 3, 5):
            assert abs(_channel(colors[0], offset) - 255) <= 30, f"Row 0 not white: {colors[0]}"

        # Row 1: gray (204,204,204) ± 30
        for offset in (1, 3, 5):
            assert abs(_channel(colors[1], offset) - 204) <= 30, f"Row 1 not gray: {colors[1]}"

        # Row 2: white again
        for offset in (1, 3, 5):
            assert abs(_channel(colors[2], offset) - 255) <= 30, f"Row 2 not white: {colors[2]}"

    def test_header_remains_separate_from_rows(self, tmp_path):
        """AC4: header_bg_color is independent from row_bg_colors."""
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        path = _make_solid_image(tmp_path, (255, 255, 255), size=(200, 150))
        result = sample_table_colors(path, row_heights_pct=[0.5, 0.5])

        assert "header_bg_color" in result
        assert "row_bg_colors" in result
        assert len(result["row_bg_colors"]) == 2

    def test_row_bg_colors_count_matches_row_heights_pct(self, tmp_path):
        """AC1: Number of entries in row_bg_colors matches len(row_heights_pct)."""
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        path = _make_solid_image(tmp_path, (200, 200, 200), size=(200, 200))
        row_heights_pct = [0.2, 0.2, 0.2, 0.2, 0.2]

        result = sample_table_colors(path, row_heights_pct=row_heights_pct)

        assert len(result["row_bg_colors"]) == 5

    def test_returns_none_items_for_nonexistent_image(self):
        """AC5 fallback: nonexistent image with row_heights_pct returns None items."""
        from services.stages.stage3_structural.visual_analysis import sample_table_colors

        result = sample_table_colors("/nonexistent.png", row_heights_pct=[0.5, 0.5])

        assert result["header_bg_color"] is None
        assert result["row_bg_colors"] == [None, None]
