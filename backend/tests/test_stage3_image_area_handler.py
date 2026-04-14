"""Tests for Story 43.8 — image_area handler in section_utils.py.

Covers:
- AC2: _classify_image_area_heuristic returns 'barcode' for high-aspect B&W crop
- AC2: _classify_image_area_heuristic returns 'logo' for colorful low-aspect crop
- AC2: _classify_image_area_heuristic returns 'logo' when screenshot_path is None
- AC2: edge case — logo_cedente (aspect 3.2 but pct_bw 67.7%) → logo, not barcode
- AC3: image_area refined as barcode → section["barcodes"] with source="image_area_refined"
- AC4: image_area refined as logo → section["images"] with render_strategy="preserve_as_image_crop"
- AC1: "image_area" is now included in allowed types (not silently discarded)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_solid_image(tmp_path, color: tuple[int, int, int], size: tuple[int, int]):
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", size, color)
    path = tmp_path / "page.png"
    img.save(path)
    return str(path)


def _make_striped_barcode_image(tmp_path, size: tuple[int, int] = (400, 105)):
    """Alternating black/white vertical stripes to simulate a barcode crop."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", size, (255, 255, 255))
    # Draw black stripes every 4 pixels (simulates barcode bars)
    pixels = img.load()
    for x in range(size[0]):
        if (x // 4) % 2 == 0:
            for y in range(size[1]):
                pixels[x, y] = (0, 0, 0)
    path = tmp_path / "page.png"
    img.save(path)
    return str(path)


def _zones_with_one_section():
    section = {}
    zone = {"bbox": [0, 0, 600, 800], "sections": [section]}
    return [zone], section


# ---------------------------------------------------------------------------
# _classify_image_area_heuristic
# ---------------------------------------------------------------------------


def test_classify_heuristic_no_screenshot():
    from services.stages.stage3_structural.section_utils import (
        _classify_image_area_heuristic,
    )

    result = _classify_image_area_heuristic([0, 0, 200, 50], None)
    assert result == "logo"


def test_classify_heuristic_barcode(tmp_path):
    """High aspect ratio + mostly B&W → barcode."""
    from services.stages.stage3_structural.section_utils import (
        _classify_image_area_heuristic,
    )

    # 400×105 px barcode-like image at 150dpi — bbox in PDF pts (72dpi): /scale ~ 192×50pts
    scale = 150.0 / 72.0
    screenshot_path = _make_striped_barcode_image(tmp_path, size=(400, 105))
    # bbox in PDF points such that crop maps to full image
    bbox = [0.0, 0.0, 400.0 / scale, 105.0 / scale]
    result = _classify_image_area_heuristic(bbox, screenshot_path)
    assert result == "barcode"


def test_classify_heuristic_colorful_logo(tmp_path):
    """Colorful solid image (low aspect) → logo."""
    from services.stages.stage3_structural.section_utils import (
        _classify_image_area_heuristic,
    )

    scale = 150.0 / 72.0
    # 131×68 px colorful logo crop at 150dpi
    screenshot_path = _make_solid_image(tmp_path, color=(34, 100, 200), size=(131, 68))
    bbox = [0.0, 0.0, 131.0 / scale, 68.0 / scale]
    result = _classify_image_area_heuristic(bbox, screenshot_path)
    assert result == "logo"


def test_classify_heuristic_logo_high_aspect(tmp_path):
    """Edge case: aspect > 3 but pct_bw < 85% → logo (not barcode).

    Mirrors logo_cedente sample from spike 43.7:
    aspect=3.21, pct_bw=67.7%, unique_colors=471.
    """
    from services.stages.stage3_structural.section_utils import (
        _classify_image_area_heuristic,
    )

    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    # Create image: wide (320×100) with mixed gray tones (not pure B&W)
    scale = 150.0 / 72.0
    img = Image.new("RGB", (320, 100), (255, 255, 255))
    pixels = img.load()
    # Fill ~65% with medium gray (not black, not white) to keep pct_bw below 85
    for x in range(320):
        for y in range(100):
            if x % 3 != 0:
                pixels[x, y] = (128, 100 + (x % 50), 80 + (y % 60))
    path = tmp_path / "logo_wide.png"
    img.save(path)

    # aspect = 320/100 = 3.2 > 3.0 — but pct_bw should be well below 85%
    bbox = [0.0, 0.0, 320.0 / scale, 100.0 / scale]
    result = _classify_image_area_heuristic(str(path), bbox)
    # Even though aspect > 3, pct_bw < 85% → should return logo
    # (Note: function signature is (bbox, screenshot_path) so reorder)
    result = _classify_image_area_heuristic(bbox, str(path))
    assert result == "logo", f"Expected logo for high-aspect gray image, got {result}"


def test_classify_heuristic_bad_path():
    """Non-existent screenshot → fallback to logo."""
    from services.stages.stage3_structural.section_utils import (
        _classify_image_area_heuristic,
    )

    result = _classify_image_area_heuristic([0, 0, 100, 50], "/nonexistent/path.png")
    assert result == "logo"


# ---------------------------------------------------------------------------
# _assign_visual_elements_to_sections — image_area routing
# ---------------------------------------------------------------------------


def _make_visual_analysis(rtype: str, bbox: list[float], page_key: str = "pdf1:0"):
    return {
        page_key: {
            "regions": [
                {
                    "type": rtype,
                    "bbox": bbox,
                    "description": "test region",
                    "confidence": 75,
                }
            ],
            "consistency_score": 1,
        }
    }


def test_image_area_not_discarded(tmp_path):
    """AC1: image_area regions are no longer silently discarded."""
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
    )

    zones, section = _zones_with_one_section()
    va = _make_visual_analysis("image_area", [0.0, 10.0, 200.0, 60.0])
    # Without screenshot — heuristic returns "logo" → goes to section["images"]
    _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=None)
    assert "images" in section or "barcodes" in section, "image_area must not be silently discarded"


def test_image_area_refined_as_logo_goes_to_images(tmp_path):
    """AC4: image_area refined as logo → section['images'] with render_strategy."""
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
    )

    # No screenshot → heuristic returns "logo"
    zones, section = _zones_with_one_section()
    va = _make_visual_analysis("image_area", [0.0, 10.0, 200.0, 110.0])
    _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=None)

    assert "images" in section
    img_entry = section["images"][0]
    assert img_entry["render_strategy"] == "preserve_as_image_crop"
    assert img_entry["image_type"] == "logo"
    assert img_entry["bbox"] == [0.0, 10.0, 200.0, 110.0]


def test_image_area_refined_as_barcode_goes_to_barcodes(tmp_path):
    """AC3: image_area refined as barcode → section['barcodes'] with source=image_area_refined."""
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
        _classify_image_area_heuristic,
    )

    # Build a barcode-like screenshot
    screenshot_path = _make_striped_barcode_image(tmp_path, size=(400, 105))
    scale = 150.0 / 72.0
    bbox = [0.0, 0.0, 400.0 / scale, 105.0 / scale]

    # Verify the heuristic classifies this as barcode first
    assert _classify_image_area_heuristic(bbox, screenshot_path) == "barcode"

    zones, section = _zones_with_one_section()
    # Update zone bbox to match
    zones[0]["bbox"] = [0.0, 0.0, 600.0, 800.0]
    # Use bbox that maps inside zone
    va = _make_visual_analysis("image_area", bbox)
    _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=screenshot_path)

    assert "barcodes" in section, f"Expected barcodes in section, got keys: {list(section.keys())}"
    barcode_entry = section["barcodes"][0]
    assert barcode_entry["source"] == "image_area_refined"
    assert barcode_entry["bbox"] == bbox


def test_existing_types_unaffected():
    """Existing types (chart_area, barcode_area, svg_area, table_area) still work."""
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
    )

    for rtype, expected_key in [
        ("chart_area", "charts"),
        ("barcode_area", "barcodes"),
        ("svg_area", "svgs"),
    ]:
        zones, section = _zones_with_one_section()
        va = _make_visual_analysis(rtype, [0.0, 10.0, 200.0, 110.0])
        _assign_visual_elements_to_sections(zones, va, "pdf1:0")
        assert expected_key in section, f"Expected {expected_key} for rtype={rtype}"


# ---------------------------------------------------------------------------
# RCA 2026-04-13 regression tests — P2a (logo path) and P2b (barcode_format)
# ---------------------------------------------------------------------------


def test_image_area_logo_has_path(tmp_path):
    """P2a fix (RCA 2026-04-13): logo image entry must include 'path' for Stage 5 crop.

    Without this fix, image_path="" in DocumentTreeNode → Stage 5 skips the logo.
    """
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
    )

    screenshot_path = _make_solid_image(tmp_path, color=(34, 100, 200), size=(200, 100))
    zones, section = _zones_with_one_section()
    va = _make_visual_analysis("image_area", [0.0, 10.0, 200.0, 110.0])
    _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=screenshot_path)

    assert "images" in section, "Logo should be in section['images']"
    img_entry = section["images"][0]
    assert "path" in img_entry, "P2a: logo entry must have 'path' key for Stage 5"
    assert img_entry["path"] == screenshot_path, "path must be the screenshot_path"


def test_image_area_logo_path_none_when_no_screenshot():
    """P2a: When screenshot_path is None, path is empty string (not KeyError)."""
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
    )

    zones, section = _zones_with_one_section()
    va = _make_visual_analysis("image_area", [0.0, 10.0, 200.0, 110.0])
    _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=None)

    if "images" in section:
        img_entry = section["images"][0]
        assert "path" in img_entry, "path key must always be present"
        assert img_entry["path"] == "", "path should be '' when screenshot_path is None"


def test_image_area_barcode_has_barcode_format(tmp_path):
    """P2b fix (RCA 2026-04-13): barcode entry must include 'barcode_format' key.

    Without this fix, tree_builder.py defaults CODE128 for all barcodes, but
    boleto barcodes are ITF (Interleaved 2of5).
    """
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
        _classify_image_area_heuristic,
    )

    screenshot_path = _make_striped_barcode_image(tmp_path)
    scale = 150.0 / 72.0
    bbox = [0.0, 0.0, 400.0 / scale, 105.0 / scale]
    assert _classify_image_area_heuristic(bbox, screenshot_path) == "barcode"

    zones, section = _zones_with_one_section()
    va = _make_visual_analysis("image_area", bbox)
    _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=screenshot_path)

    assert "barcodes" in section
    barcode_entry = section["barcodes"][0]
    assert "barcode_format" in barcode_entry, "P2b: barcode entry must have 'barcode_format' key"


def test_image_area_elongated_barcode_uses_itf(tmp_path):
    """P2b: very elongated barcode bbox (w/h > 5) → barcode_format = ITF (boleto).

    Boleto ITF barcodes are typically 400×25 pts (w/h = 16).
    """
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
    )

    # Elongated bbox: w=400, h=25 → w/h = 16 → ITF
    elongated_bbox = [10.0, 700.0, 410.0, 725.0]
    screenshot_path = _make_striped_barcode_image(tmp_path, size=(800, 50))
    zones, section = _zones_with_one_section()
    zones[0]["bbox"] = [0.0, 0.0, 600.0, 800.0]

    va = _make_visual_analysis("image_area", elongated_bbox)

    # Mock heuristic to return "barcode" to isolate format test
    from unittest.mock import patch

    import services.stages.stage3_structural.section_utils as su_mod

    with patch.object(su_mod, "_classify_image_area_heuristic", return_value="barcode"):
        _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=screenshot_path)

    assert "barcodes" in section
    barcode_entry = section["barcodes"][0]
    assert barcode_entry.get("barcode_format") == "ITF", (
        f"Expected ITF for w/h=16 barcode, got {barcode_entry.get('barcode_format')}"
    )


def test_image_area_square_barcode_uses_code128(tmp_path):
    """P2b: barcode bbox with w/h <= 5 → barcode_format = CODE128."""
    from services.stages.stage3_structural.section_utils import (
        _assign_visual_elements_to_sections,
    )

    # Near-square bbox: w=100, h=100 → w/h = 1 → CODE128
    square_bbox = [10.0, 10.0, 110.0, 110.0]
    zones, section = _zones_with_one_section()
    va = _make_visual_analysis("image_area", square_bbox)

    from unittest.mock import patch

    import services.stages.stage3_structural.section_utils as su_mod

    with patch.object(su_mod, "_classify_image_area_heuristic", return_value="barcode"):
        _assign_visual_elements_to_sections(zones, va, "pdf1:0", screenshot_path=None)

    assert "barcodes" in section
    barcode_entry = section["barcodes"][0]
    assert barcode_entry.get("barcode_format") == "CODE128"
