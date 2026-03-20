"""Tests for Story 10.19 — Stage 27: Canvas positioned layout.

Covers:
- AC #2: field with bbox generates positioned HTML with style="left:Xpx; top:Ypx;"
- AC #3: field without bbox generates plain field-group (linear flow, no style)
- AC #4: SCALE_X/SCALE_Y constants and _bbox_to_style() conversion
- AC #2/#3: mix of positioned and non-positioned fields; flow gets positioned-layout class
"""

from __future__ import annotations

import asyncio
import math
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
) -> Dict[str, Any]:
    m: Dict[str, Any] = {
        "pdf_text": pdf_text,
        "label_text": label_text,
        "xsd_field_path": xsd_field_path,
        "confidence": 0.9,
        "is_ambiguous": False,
        "candidates": [],
        "page_number": 0,
        "pdf_index": 0,
    }
    if bbox is not None:
        m["bbox"] = bbox
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
# Test 2 — _bbox_to_style: correct pixel values
# ---------------------------------------------------------------------------


def test_bbox_to_style_converts_pt_to_px():
    """_bbox_to_style([42, 84, 200, 96]) must produce correct pixel CSS.

    AC #2/#4: x_px = round(42 * SCALE_X), y_px = round(84 * SCALE_Y).
    Tolerance: ±2px to account for rounding.
    """
    from services.stages.template_draft import _bbox_to_style, SCALE_X, SCALE_Y

    result = _bbox_to_style([42.0, 84.0, 200.0, 96.0])
    assert result is not None

    expected_x = round(42.0 * SCALE_X)
    expected_y = round(84.0 * SCALE_Y)

    assert f"left: {expected_x}px;" in result, f"Expected left:{expected_x}px in '{result}'"
    assert f"top: {expected_y}px;" in result, f"Expected top:{expected_y}px in '{result}'"


def test_bbox_to_style_returns_none_for_none():
    """_bbox_to_style(None) must return None (no positioning for fields without bbox).

    AC #3: fallback — fields without bbox do not get absolute positioning.
    """
    from services.stages.template_draft import _bbox_to_style

    assert _bbox_to_style(None) is None


def test_bbox_to_style_returns_none_for_empty():
    """_bbox_to_style([]) must return None."""
    from services.stages.template_draft import _bbox_to_style

    assert _bbox_to_style([]) is None


def test_bbox_to_style_handles_single_element():
    """_bbox_to_style([x]) with only 1 element must return None (needs at least 2)."""
    from services.stages.template_draft import _bbox_to_style

    assert _bbox_to_style([100.0]) is None


# ---------------------------------------------------------------------------
# Test 3 — _generate_field_element: mapping WITH bbox → positioned div
# ---------------------------------------------------------------------------


def test_generate_field_element_with_bbox_produces_positioned_class():
    """Mapping with bbox must produce div with class 'field-group positioned' and style.

    AC #2: '<div class="field-group positioned" style="left: Xpx; top: Ypx;">'
    """
    from services.stages.template_draft import _generate_field_element, SCALE_X, SCALE_Y

    mapping = _make_mapping(
        pdf_text="MAG SEGUROS",
        label_text="Beneficiário",
        xsd_field_path="contrato.beneficiario",
        bbox=[42.0, 84.0, 200.0, 96.0],
    )

    html = _generate_field_element(mapping, None)

    assert 'class="field-group positioned"' in html, (
        f"Expected 'field-group positioned' class in: {html}"
    )
    expected_x = round(42.0 * SCALE_X)
    expected_y = round(84.0 * SCALE_Y)
    assert f"left: {expected_x}px;" in html
    assert f"top: {expected_y}px;" in html


# ---------------------------------------------------------------------------
# Test 4 — _generate_field_element: mapping WITHOUT bbox → plain field-group
# ---------------------------------------------------------------------------


def test_generate_field_element_without_bbox_plain_class():
    """Mapping without bbox must produce plain 'field-group' div without style.

    AC #3: fallback — fields without bbox continue using linear flow.
    """
    from services.stages.template_draft import _generate_field_element

    mapping = _make_mapping(
        pdf_text="Valor",
        label_text="Valor",
        xsd_field_path="doc.valor",
        bbox=None,
    )

    html = _generate_field_element(mapping, None)

    assert 'class="field-group"' in html, f"Expected plain 'field-group' class in: {html}"
    assert "positioned" not in html, f"Should not contain 'positioned' when no bbox: {html}"
    assert "style=" not in html, f"Should not contain 'style' attribute when no bbox: {html}"


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

    AC #3: fields without bbox → no positioned-layout class on .flow.
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
    """Mix of mappings: some with bbox (positioned), some without (linear flow).

    AC #2/#3:
    - Fields with bbox → class="field-group positioned" with style
    - Fields without bbox → class="field-group" without style
    - .flow has 'positioned-layout' class (because at least one has bbox)
    """
    from services.stages.template_draft import _generate_page_html, SCALE_X, SCALE_Y

    mapping_with_bbox = _make_mapping(
        "MAG SEGUROS", "Beneficiário", "contrato.beneficiario", bbox=[42.0, 84.0, 200.0, 96.0]
    )
    mapping_without_bbox = _make_mapping(
        "R$ 120,00", "Valor", "contrato.valor", bbox=None
    )

    html = _generate_page_html("default", [mapping_with_bbox, mapping_without_bbox], [], None)

    # Flow must have positioned-layout (at least one bbox)
    assert 'class="flow positioned-layout"' in html

    # Positioned field
    assert 'class="field-group positioned"' in html

    # Plain field (without positioning style)
    expected_x = round(42.0 * SCALE_X)
    expected_y = round(42.0 * SCALE_Y)  # Should NOT appear for the plain mapping


# ---------------------------------------------------------------------------
# Test 8 — execute() end-to-end with positioned mappings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_generates_positioned_html():
    """Stage 27 execute() must produce positioned HTML when mappings have bbox.

    AC #2: full pipeline context with field_mappings containing bbox.
    """
    from services.stages.template_draft import execute, SCALE_X, SCALE_Y

    field_mappings = [
        {
            "pdf_text": "MAG SEGUROS",
            "label_text": "Beneficiário",
            "xsd_field_path": "contrato.beneficiario",
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

    # HTML must have positioned-layout
    assert 'class="flow positioned-layout"' in html

    # HTML must have positioned field-group
    assert 'class="field-group positioned"' in html

    expected_x = round(42.0 * SCALE_X)
    expected_y = round(84.0 * SCALE_Y)
    assert f"left: {expected_x}px;" in html
    assert f"top: {expected_y}px;" in html

    # CSS must include positioned rules
    assert ".flow.positioned-layout" in css
    assert ".field-group.positioned" in css
