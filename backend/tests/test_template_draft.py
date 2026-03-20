"""Tests for Stage 27 canvas positioning — Story 10.19 (base) + Story 12.1 (Y-inversion fix).

Covers:
- SCALE_X/SCALE_Y A4 constants
- _bbox_to_style(): Y-axis inversion, width/height, font params, null handling
- _generate_field_element(): <span> with data attributes (positioned + unpositioned)
- _generate_page_html(): flow class, page dimensions
- Story 12.1 ACs: AC1 positioning, AC2 page dims, AC3 font, AC4 data-attrs,
  AC5 fallback, AC6 non-A4 scale, AC7 test coverage
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import pytest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_mapping(
    pdf_text: str = "value",
    label_text: str = "Label",
    xsd_field_path: str = "doc.field",
    bbox: Optional[List[float]] = None,
    status: str = "mapped",
    font_name: Optional[str] = None,
    font_size: Optional[float] = None,
) -> Dict[str, Any]:
    m: Dict[str, Any] = {
        "pdf_text": pdf_text,
        "label_text": label_text,
        "xsd_field_path": xsd_field_path,
        "status": status,
        "confidence": 0.9,
        "is_ambiguous": False,
        "candidates": [],
        "page_number": 0,
        "pdf_index": 0,
    }
    if bbox is not None:
        m["bbox"] = bbox
    if font_name is not None:
        m["font_name"] = font_name
    if font_size is not None:
        m["font_size"] = font_size
    return m


# ---------------------------------------------------------------------------
# Test 1 — SCALE_X / SCALE_Y constants
# ---------------------------------------------------------------------------


def test_scale_constants_a4():
    """SCALE_X ≈ 1.3345 and SCALE_Y ≈ 1.3337 for A4 (595×842 pt → 794×1123 px).

    AC #4: escala adequada para converter coordenadas PDF pt → canvas px.
    """
    from services.stages.template_draft import SCALE_X, SCALE_Y

    assert abs(SCALE_X - 794 / 595) < 0.0001
    assert abs(SCALE_Y - 1123 / 842) < 0.0001


# ---------------------------------------------------------------------------
# Test 2 — _bbox_to_style: correct pixel values with Y-axis inversion
# ---------------------------------------------------------------------------


def test_bbox_to_style_converts_pt_to_px_with_y_inversion():
    """_bbox_to_style([42, 84, 200, 96]) must produce correct pixel CSS with Y-inversion.

    Story 12.1 AC#1: Y-axis inverted — css_y = (page_height - bbox[3]) * SCALE_Y.
    pdf bbox[3]=96 (top of element in PDF coords) → css top = (842-96)*SCALE_Y.
    """
    from services.stages.template_draft import _bbox_to_style, SCALE_X, SCALE_Y

    result = _bbox_to_style([42.0, 84.0, 200.0, 96.0])
    assert result is not None

    expected_x = round(42.0 * SCALE_X)
    # Y-inversion: use bbox[3]=96 as PDF top edge; CSS top = (842-96)*SCALE_Y
    expected_y = round((842.0 - 96.0) * SCALE_Y)

    assert f"left:{expected_x}px" in result, f"Expected left:{expected_x}px in '{result}'"
    assert f"top:{expected_y}px" in result, f"Expected top:{expected_y}px in '{result}'"


def test_bbox_to_style_includes_width_and_height():
    """_bbox_to_style must include width and height in the CSS string.

    Story 12.1 AC#1: w = (x1-x0)*SCALE_X, h = (y1-y0)*SCALE_Y.
    """
    from services.stages.template_draft import _bbox_to_style, SCALE_X, SCALE_Y

    result = _bbox_to_style([42.0, 84.0, 200.0, 96.0])
    assert result is not None

    expected_w = round((200.0 - 42.0) * SCALE_X)
    expected_h = round((96.0 - 84.0) * SCALE_Y)

    assert f"width:{expected_w}px" in result, f"Expected width:{expected_w}px in '{result}'"
    assert f"height:{expected_h}px" in result, f"Expected height:{expected_h}px in '{result}'"


def test_bbox_to_style_includes_position_absolute():
    """_bbox_to_style must include position:absolute."""
    from services.stages.template_draft import _bbox_to_style

    result = _bbox_to_style([42.0, 84.0, 200.0, 96.0])
    assert result is not None
    assert "position:absolute" in result


def test_bbox_to_style_returns_none_for_none():
    """_bbox_to_style(None) must return None.

    AC #5: fallback — fields without bbox do not get absolute positioning.
    """
    from services.stages.template_draft import _bbox_to_style

    assert _bbox_to_style(None) is None


def test_bbox_to_style_returns_none_for_empty():
    """_bbox_to_style([]) must return None."""
    from services.stages.template_draft import _bbox_to_style

    assert _bbox_to_style([]) is None


def test_bbox_to_style_handles_partial_bbox():
    """_bbox_to_style with fewer than 4 elements must return None (needs x0,y0,x1,y1)."""
    from services.stages.template_draft import _bbox_to_style

    assert _bbox_to_style([100.0]) is None
    assert _bbox_to_style([100.0, 200.0]) is None
    assert _bbox_to_style([100.0, 200.0, 300.0]) is None


# ---------------------------------------------------------------------------
# Story 12.1 AC#3 — Font properties in style
# ---------------------------------------------------------------------------


def test_bbox_to_style_includes_font_when_provided():
    """When font_name and font_size are provided, they appear in the style string.

    Story 12.1 AC#3: font-family and font-size from PDF extraction.
    """
    from services.stages.template_draft import _bbox_to_style

    result = _bbox_to_style(
        [42.0, 84.0, 200.0, 96.0],
        font_name="Arial",
        font_size=10.5,
    )
    assert result is not None
    assert "font-family:Arial" in result, f"Expected font-family:Arial in '{result}'"
    assert "font-size:10.5pt" in result, f"Expected font-size:10.5pt in '{result}'"


def test_bbox_to_style_no_font_properties_when_absent():
    """When no font params given, style must not contain font-family or font-size."""
    from services.stages.template_draft import _bbox_to_style

    result = _bbox_to_style([42.0, 84.0, 200.0, 96.0])
    assert result is not None
    assert "font-family" not in result
    assert "font-size" not in result


# ---------------------------------------------------------------------------
# Story 12.1 AC#6 — Non-A4 scale via page_height_pts
# ---------------------------------------------------------------------------


def test_bbox_to_style_non_a4_page_height():
    """Y-inversion uses the provided page_height_pts, not the hardcoded A4 default.

    Story 12.1 AC#6: escala calculada das dimensões reais da página.
    """
    from services.stages.template_draft import _bbox_to_style, SCALE_Y

    # Letter format: 792pt tall (US Letter)
    letter_height = 792.0
    result = _bbox_to_style([10.0, 50.0, 100.0, 80.0], page_height_pts=letter_height)
    assert result is not None

    expected_y = round((letter_height - 80.0) * SCALE_Y)
    assert f"top:{expected_y}px" in result, (
        f"Expected top:{expected_y}px for Letter page in '{result}'"
    )


# ---------------------------------------------------------------------------
# Story 12.1 AC#4 — data-node-id, data-xsd-path, data-status in <span>
# ---------------------------------------------------------------------------


def test_generate_field_element_with_bbox_has_data_attributes():
    """Positioned field must have data-node-id, data-xsd-path, data-status.

    Story 12.1 AC#4.
    """
    from services.stages.template_draft import _generate_field_element

    mapping = _make_mapping(
        pdf_text="MAG SEGUROS",
        label_text="Beneficiário",
        xsd_field_path="contrato.beneficiario",
        bbox=[42.0, 84.0, 200.0, 96.0],
        status="mapped",
    )

    html = _generate_field_element(mapping, None)

    assert 'data-xsd-path="contrato.beneficiario"' in html, (
        f"Expected data-xsd-path attribute in: {html}"
    )
    assert 'data-status="mapped"' in html, f"Expected data-status in: {html}"
    assert "data-node-id=" in html, f"Expected data-node-id attribute in: {html}"


def test_generate_field_element_with_bbox_uses_span_element():
    """Positioned field must use <span> element (not <div>).

    Story 12.1: changed from <div class='field-group'> to <span>.
    """
    from services.stages.template_draft import _generate_field_element

    mapping = _make_mapping(
        pdf_text="MAG SEGUROS",
        xsd_field_path="contrato.beneficiario",
        bbox=[42.0, 84.0, 200.0, 96.0],
    )

    html = _generate_field_element(mapping, None)

    assert html.lstrip().startswith("<span"), f"Expected <span> element, got: {html[:60]}"
    assert "<div" not in html, f"Should not contain <div> when using <span>: {html}"


def test_generate_field_element_with_bbox_has_absolute_positioning():
    """Positioned field must have position:absolute in style.

    Story 12.1 AC#1.
    """
    from services.stages.template_draft import _generate_field_element, SCALE_X, SCALE_Y

    mapping = _make_mapping(
        xsd_field_path="contrato.beneficiario",
        bbox=[42.0, 84.0, 200.0, 96.0],
    )

    html = _generate_field_element(mapping, None)

    expected_x = round(42.0 * SCALE_X)
    expected_y = round((842.0 - 96.0) * SCALE_Y)

    assert "position:absolute" in html, f"Expected position:absolute in: {html}"
    assert f"left:{expected_x}px" in html, f"Expected left:{expected_x}px in: {html}"
    assert f"top:{expected_y}px" in html, f"Expected top:{expected_y}px in: {html}"


# ---------------------------------------------------------------------------
# Story 12.1 AC#5 — Fallback: unpositioned class when no bbox
# ---------------------------------------------------------------------------


def test_generate_field_element_without_bbox_uses_unpositioned_class():
    """Field without bbox must use class='unpositioned' with position:relative.

    Story 12.1 AC#5: fallback for elements without bbox.
    """
    from services.stages.template_draft import _generate_field_element

    mapping = _make_mapping(
        pdf_text="Valor",
        xsd_field_path="doc.valor",
        bbox=None,
        status="unmapped",
    )

    html = _generate_field_element(mapping, None)

    assert 'class="unpositioned"' in html, (
        f"Expected class='unpositioned' for field without bbox: {html}"
    )
    assert "position:relative" in html, f"Expected position:relative for fallback: {html}"
    assert "position:absolute" not in html, (
        f"Should not have position:absolute when no bbox: {html}"
    )


def test_generate_field_element_without_bbox_has_data_attributes():
    """Unpositioned field must still have data-xsd-path and data-status.

    Story 12.1 AC#4/#5.
    """
    from services.stages.template_draft import _generate_field_element

    mapping = _make_mapping(
        xsd_field_path="doc.valor",
        status="unmapped",
        bbox=None,
    )

    html = _generate_field_element(mapping, None)

    assert 'data-xsd-path="doc.valor"' in html
    assert 'data-status="unmapped"' in html
    assert "data-node-id=" in html


# ---------------------------------------------------------------------------
# Test 5 — _generate_page_html: all positioned → flow has positioned-layout
# ---------------------------------------------------------------------------


def test_generate_page_html_positioned_layout_class_when_has_bbox():
    """When all mappings have bbox, the .flow div must include 'positioned-layout' class.

    AC #2: '<div class="flow positioned-layout">'
    """
    from services.stages.template_draft import _generate_page_html

    mappings = [
        _make_mapping("MAG SEGUROS", "Beneficiário", "contrato.beneficiario", bbox=[42.0, 84.0, 200.0, 96.0]),
        _make_mapping("62.085.678/0001-40", "CNPJ", "contrato.cnpj", bbox=[42.0, 106.0, 200.0, 118.0]),
    ]

    html = _generate_page_html("default", mappings, [], None)

    assert 'class="flow positioned-layout"' in html, (
        f"Expected 'flow positioned-layout' class when mappings have bbox: {html[:300]}"
    )


# ---------------------------------------------------------------------------
# Test 6 — _generate_page_html: no bbox → flow does NOT have positioned-layout
# ---------------------------------------------------------------------------


def test_generate_page_html_no_positioned_layout_class_when_no_bbox():
    """When no mapping has bbox, the .flow div must use plain 'flow' class.

    AC #5: fields without bbox → no positioned-layout class on .flow.
    """
    from services.stages.template_draft import _generate_page_html

    mappings = [
        _make_mapping("Valor A", "Campo A", "doc.campo_a", bbox=None),
        _make_mapping("Valor B", "Campo B", "doc.campo_b", bbox=None),
    ]

    html = _generate_page_html("default", mappings, [], None)

    assert 'class="flow"' in html, f"Expected plain 'flow' class when no bbox: {html[:300]}"
    assert "positioned-layout" not in html, (
        f"Should not contain 'positioned-layout' when no mapping has bbox: {html[:300]}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Mix of positioned and non-positioned fields
# ---------------------------------------------------------------------------


def test_generate_page_html_mix_positioned_and_plain():
    """Mix of mappings: some with bbox (positioned), some without (unpositioned).

    Story 12.1 AC#1/#5:
    - Fields with bbox → position:absolute with data attributes
    - Fields without bbox → class="unpositioned" with position:relative
    - .flow has 'positioned-layout' class (because at least one has bbox)
    """
    from services.stages.template_draft import _generate_page_html

    mapping_with_bbox = _make_mapping(
        "MAG SEGUROS", "Beneficiário", "contrato.beneficiario", bbox=[42.0, 84.0, 200.0, 96.0]
    )
    mapping_without_bbox = _make_mapping(
        "R$ 120,00", "Valor", "contrato.valor", bbox=None
    )

    html = _generate_page_html("default", [mapping_with_bbox, mapping_without_bbox], [], None)

    # Flow must have positioned-layout (at least one bbox)
    assert 'class="flow positioned-layout"' in html

    # Positioned field uses position:absolute
    assert "position:absolute" in html

    # Unpositioned fallback uses class="unpositioned"
    assert 'class="unpositioned"' in html


# ---------------------------------------------------------------------------
# Story 12.1 AC#2 — Page container uses px dimensions
# ---------------------------------------------------------------------------


def test_css_page_uses_px_dimensions():
    """CSS .page must use 794px × 1123px, not inches.

    Story 12.1 AC#2: canvas A4 dimensions in pixels.
    """
    from services.stages.template_draft import _generate_css

    css = _generate_css()

    assert "width: 794px" in css, f"Expected 'width: 794px' in CSS: {css[:300]}"
    assert "height: 1123px" in css, f"Expected 'height: 1123px' in CSS: {css[:300]}"
    assert "8.27in" not in css, f"CSS should not use inches: {css[:300]}"
    assert "11.69in" not in css, f"CSS should not use inches: {css[:300]}"


# ---------------------------------------------------------------------------
# Story 12.1 AC#6 — Non-A4 page height propagated to _generate_page_html
# ---------------------------------------------------------------------------


def test_generate_page_html_uses_custom_page_height():
    """_generate_page_html propagates page_height_pts to _generate_field_element.

    Story 12.1 AC#6: Y-inversion uses real page height, not hardcoded 842.
    """
    from services.stages.template_draft import _generate_page_html, SCALE_Y

    # US Letter: 792pt tall — Y calculation should differ from A4
    letter_height = 792.0
    mapping = _make_mapping(
        xsd_field_path="doc.campo",
        bbox=[10.0, 50.0, 100.0, 80.0],
    )

    html = _generate_page_html("letter", [mapping], [], None, page_height_pts=letter_height)

    expected_y = round((letter_height - 80.0) * SCALE_Y)
    assert f"top:{expected_y}px" in html, (
        f"Expected top:{expected_y}px for Letter page in HTML: {html[:400]}"
    )


# ---------------------------------------------------------------------------
# Test 8 — execute() end-to-end with positioned mappings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_generates_positioned_html():
    """Stage 27 execute() must produce positioned HTML when mappings have bbox.

    Story 12.1 AC#1/#4: full pipeline context with field_mappings containing bbox.
    """
    from services.stages.template_draft import execute, SCALE_X, SCALE_Y

    field_mappings = [
        {
            "pdf_text": "MAG SEGUROS",
            "label_text": "Beneficiário",
            "xsd_field_path": "contrato.beneficiario",
            "status": "mapped",
            "confidence": 0.9,
            "is_ambiguous": False,
            "candidates": [],
            "page_number": 0,
            "pdf_index": 0,
            "bbox": [42.0, 84.0, 200.0, 96.0],
        }
    ]

    context: Dict[str, Any] = {
        "field_mappings": field_mappings,
        "layout_types": [{"name": "default", "pages": []}],
        "field_tree": None,
        "variants": [],
    }

    await execute(context)

    template_draft = context["template_draft"]
    html = template_draft["html"]
    css = template_draft["css"]

    # HTML must have positioned-layout on flow container
    assert 'class="flow positioned-layout"' in html

    # HTML must have position:absolute (Y-inverted coordinates)
    expected_x = round(42.0 * SCALE_X)
    expected_y = round((842.0 - 96.0) * SCALE_Y)
    assert "position:absolute" in html
    assert f"left:{expected_x}px" in html, f"Expected left:{expected_x}px in html"
    assert f"top:{expected_y}px" in html, f"Expected top:{expected_y}px in html"

    # HTML must have data attributes
    assert 'data-xsd-path="contrato.beneficiario"' in html
    assert 'data-status="mapped"' in html
    assert "data-node-id=" in html

    # CSS must include positioned rules
    assert ".flow.positioned-layout" in css
    assert "794px" in css  # page uses px dimensions


@pytest.mark.asyncio
async def test_execute_generates_unpositioned_fallback():
    """Stage 27 execute() produces unpositioned fallback for mappings without bbox.

    Story 12.1 AC#5: fallback for missing bbox.
    """
    from services.stages.template_draft import execute

    field_mappings = [
        {
            "pdf_text": "Valor",
            "label_text": "Valor",
            "xsd_field_path": "doc.valor",
            "status": "unmapped",
            "confidence": 0.5,
        }
    ]

    context: Dict[str, Any] = {
        "field_mappings": field_mappings,
        "layout_types": [{"name": "default", "pages": []}],
        "field_tree": None,
        "variants": [],
    }

    await execute(context)

    html = context["template_draft"]["html"]

    assert 'class="unpositioned"' in html, f"Expected unpositioned class in: {html[:400]}"
    assert "position:relative" in html
    assert "position:absolute" not in html
