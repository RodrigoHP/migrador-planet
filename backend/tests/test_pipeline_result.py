"""Tests for Stage 28 — pipeline_result.py (Story 10.16).

Verifies that _get_confidence_scores() and _get_coverage() transform the flat
backend format (Stage 25 / Stage 27) into the layout-keyed format expected by
the frontend confidenceStore and coverageStore.
"""

from __future__ import annotations

import pytest
from services.stages.pipeline_result import (
    _get_confidence_scores,
    _get_coverage,
    _bbox_to_layout,
    _bbox_to_css_layout,
    _build_document_tree_root,
)


# ---------------------------------------------------------------------------
# _bbox_to_layout tests (Story 10.20 — concern #1)
# ---------------------------------------------------------------------------

_NULL_BBOX = {"x": None, "y": None, "width": None, "height": None}


class TestBboxToLayout:
    """_bbox_to_layout converts (x0,y0,x1,y1) tuples to layout dicts safely."""

    def test_valid_bbox_returns_correct_xywh(self):
        result = _bbox_to_layout((10, 20, 110, 70))
        assert result == {"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0}

    def test_decimal_values_rounded_to_2dp(self):
        result = _bbox_to_layout((1.234, 2.567, 11.234, 12.567))
        assert result["x"] == 1.23
        assert result["y"] == 2.57
        assert result["width"] == 10.0
        assert result["height"] == 10.0

    def test_zero_area_degenerate_bbox(self):
        """x0==x1 and y0==y1 → zero width and height (valid, not an error)."""
        result = _bbox_to_layout((5, 5, 5, 5))
        assert result == {"x": 5.0, "y": 5.0, "width": 0.0, "height": 0.0}

    def test_none_returns_null_values(self):
        assert _bbox_to_layout(None) == _NULL_BBOX

    def test_empty_list_returns_null_values(self):
        assert _bbox_to_layout([]) == _NULL_BBOX

    def test_too_short_bbox_returns_null_values(self):
        assert _bbox_to_layout((1, 2, 3)) == _NULL_BBOX

    def test_too_long_bbox_returns_null_values(self):
        assert _bbox_to_layout((1, 2, 3, 4, 5)) == _NULL_BBOX

    def test_non_numeric_elements_returns_null_not_raises(self):
        """Upstream data quality issue: non-numeric bbox must not propagate TypeError."""
        result = _bbox_to_layout(("a", "b", "c", "d"))
        assert result == _NULL_BBOX

    def test_none_mixed_with_numbers_returns_null(self):
        result = _bbox_to_layout((0, None, 100, 200))
        assert result == _NULL_BBOX

    def test_list_bbox_accepted_same_as_tuple(self):
        """bbox may arrive as list from JSON deserialisation."""
        result = _bbox_to_layout([0, 0, 50, 30])
        assert result == {"x": 0.0, "y": 0.0, "width": 50.0, "height": 30.0}


# ---------------------------------------------------------------------------
# _get_confidence_scores tests
# ---------------------------------------------------------------------------


class TestGetConfidenceScores:
    """AC #3: confidenceByLayout has at least one entry accessible by activeLayoutId."""

    def test_flat_stage25_format_with_layout_types(self):
        """Stage 25 flat output keyed by layout id from layout_types."""
        context = {
            "confidence_scores": {
                "factors": {
                    "layout_stability": 0.7,
                    "anchor_detection": 0.5,
                    "grid_quality": 0.6,
                    "field_variability": 0.8,
                    "vision_agreement": 0.9,
                },
                "global_score": 0.72,
                "local_weighted_average": 0.68,
                "score_method": "weighted_average",
                "status": "review_recommended",
                "thresholds": {"approved": 0.95, "review_recommended": 0.80},
            },
            "layout_types": [
                {"id": "cluster_0", "label": "Layout A"},
                {"id": "cluster_1", "label": "Layout B"},
            ],
        }
        result = _get_confidence_scores(context)

        # Must be keyed by layout ids, not by "factors" / "global_score"
        assert "cluster_0" in result, "Missing key cluster_0"
        assert "cluster_1" in result, "Missing key cluster_1"
        assert "factors" not in result, "'factors' must NOT be a top-level key"
        assert "global_score" not in result, "'global_score' must NOT be a top-level key"

    def test_flat_stage25_format_confidence_entry_structure(self):
        """Each layout entry has ConfidenceFactors-compatible fields."""
        context = {
            "confidence_scores": {
                "factors": {
                    "layout_stability": 0.7,
                    "anchor_detection": 0.5,
                    "grid_quality": 0.6,
                    "field_variability": 0.8,
                    "vision_agreement": 0.9,
                },
                "global_score": 0.72,
            },
            "layout_types": [{"id": "cluster_0"}],
        }
        result = _get_confidence_scores(context)
        entry = result["cluster_0"]

        assert "layout_stability" in entry
        assert "anchor_detection" in entry
        assert "grid_quality" in entry
        assert "field_variability" in entry
        assert "vision_agreement" in entry
        assert "overall" in entry
        # overall must be 0-100 integer (frontend convention)
        assert isinstance(entry["overall"], int)
        assert entry["overall"] == 72  # round(0.72 * 100)

    def test_flat_format_without_layout_types_uses_global_fallback(self):
        """When no layout_types, fallback key 'global' is used."""
        context = {
            "confidence_scores": {
                "factors": {"layout_stability": 0.5},
                "global_score": 0.5,
            },
        }
        result = _get_confidence_scores(context)
        assert "global" in result, "Fallback key 'global' expected when no layout_types"

    def test_already_keyed_format_returned_as_is(self):
        """If scores are already keyed by layoutId (saved project), return as-is."""
        pre_keyed = {
            "cluster_0": {
                "layout_stability": 0.7,
                "anchor_detection": 0.5,
                "grid_quality": 0.6,
                "field_variability": 0.8,
                "vision_agreement": 0.9,
                "overall": 72,
            }
        }
        context = {"confidence_scores": pre_keyed}
        result = _get_confidence_scores(context)
        assert result == pre_keyed

    def test_empty_confidence_scores_returns_default_entry(self):
        """Missing confidence_scores produces sensible defaults keyed by layout."""
        context = {
            "confidence_scores": {},
            "layout_types": [{"id": "cluster_0"}],
        }
        result = _get_confidence_scores(context)
        assert "cluster_0" in result
        entry = result["cluster_0"]
        assert entry["overall"] == 50  # neutral default

    def test_no_confidence_scores_key_at_all(self):
        """No confidence_scores key in context — returns global with defaults."""
        context = {}
        result = _get_confidence_scores(context)
        assert "global" in result
        assert result["global"]["overall"] == 50

    def test_multiple_layout_types_all_receive_same_scores(self):
        """All layout_types receive a copy of the same confidence entry."""
        context = {
            "confidence_scores": {
                "factors": {"layout_stability": 0.8},
                "global_score": 0.80,
            },
            "layout_types": [
                {"id": "lt-0"},
                {"id": "lt-1"},
                {"id": "lt-2"},
            ],
        }
        result = _get_confidence_scores(context)
        assert set(result.keys()) == {"lt-0", "lt-1", "lt-2"}
        for key in result:
            assert result[key]["overall"] == 80


# ---------------------------------------------------------------------------
# _get_coverage tests
# ---------------------------------------------------------------------------


class TestGetCoverage:
    """AC #4: coverageByLayout has at least one entry accessible by activeLayoutId."""

    def test_flat_stage27_format_with_layout_types(self):
        """Stage 27 flat output keyed by layout id from layout_types."""
        context = {
            "template_draft": {
                "coverage": {"fields": {"mapped": 3, "total": 10}},
                "html": "",
                "css": "",
            },
            "layout_types": [
                {"id": "cluster_0"},
                {"id": "cluster_1"},
            ],
        }
        result = _get_coverage(context)

        # Must be keyed by layout ids, not by "fields"
        assert "cluster_0" in result, "Missing key cluster_0"
        assert "cluster_1" in result, "Missing key cluster_1"
        assert "fields" not in result, "'fields' must NOT be a top-level key"

    def test_flat_stage27_format_coverage_entry_structure(self):
        """Each layout entry has CoverageData-compatible fields."""
        context = {
            "template_draft": {
                "coverage": {"fields": {"mapped": 3, "total": 10}},
            },
            "layout_types": [{"id": "cluster_0"}],
        }
        result = _get_coverage(context)
        entry = result["cluster_0"]

        assert "fields" in entry
        assert entry["fields"]["mapped"] == 3
        assert entry["fields"]["total"] == 10
        assert "percentage" in entry
        assert entry["percentage"] == 30  # round(3/10 * 100)

    def test_coverage_percentage_zero_when_total_zero(self):
        """No division by zero when total is 0."""
        context = {
            "template_draft": {
                "coverage": {"fields": {"mapped": 0, "total": 0}},
            },
            "layout_types": [{"id": "cluster_0"}],
        }
        result = _get_coverage(context)
        assert result["cluster_0"]["percentage"] == 0

    def test_flat_format_without_layout_types_uses_global_fallback(self):
        """When no layout_types, fallback key 'global' is used."""
        context = {
            "template_draft": {
                "coverage": {"fields": {"mapped": 5, "total": 10}},
            },
        }
        result = _get_coverage(context)
        assert "global" in result, "Fallback key 'global' expected when no layout_types"
        assert result["global"]["percentage"] == 50

    def test_no_template_draft_returns_zero_entry(self):
        """Missing template_draft produces zero coverage."""
        context = {"layout_types": [{"id": "cluster_0"}]}
        result = _get_coverage(context)
        assert "cluster_0" in result
        assert result["cluster_0"]["fields"]["mapped"] == 0
        assert result["cluster_0"]["percentage"] == 0

    def test_multiple_layout_types_all_receive_same_coverage(self):
        """All layout_types receive a copy of the same coverage entry."""
        context = {
            "template_draft": {
                "coverage": {"fields": {"mapped": 7, "total": 10}},
            },
            "layout_types": [
                {"id": "lt-0"},
                {"id": "lt-1"},
            ],
        }
        result = _get_coverage(context)
        assert set(result.keys()) == {"lt-0", "lt-1"}
        for key in result:
            assert result[key]["fields"]["mapped"] == 7
            assert result[key]["percentage"] == 70

    def test_coverage_entry_includes_all_required_keys(self):
        """CoverageData shape includes fields, tables, images, charts, percentage."""
        context = {
            "template_draft": {
                "coverage": {"fields": {"mapped": 1, "total": 2}},
            },
            "layout_types": [{"id": "layout-0"}],
        }
        result = _get_coverage(context)
        entry = result["layout-0"]
        for key in ("fields", "tables", "images", "charts", "percentage"):
            assert key in entry, f"Missing key '{key}' in coverage entry"


# ---------------------------------------------------------------------------
# Integration: execute() produces correctly shaped result_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_produces_keyed_confidence_and_coverage():
    """Full execute() call results in result_json with layout-keyed scores."""
    from services.stages.pipeline_result import execute

    context = {
        "confidence_scores": {
            "factors": {
                "layout_stability": 0.7,
                "anchor_detection": 0.5,
                "grid_quality": 0.6,
                "field_variability": 0.8,
                "vision_agreement": 0.9,
            },
            "global_score": 0.72,
        },
        "template_draft": {
            "coverage": {"fields": {"mapped": 3, "total": 10}},
            "html": "<p>test</p>",
            "css": "",
        },
        "layout_types": [{"id": "cluster_0", "label": "Main"}],
        "field_mappings": [],
        "parsed_documents": [],
    }

    await execute(context)
    result = context["result_json"]

    # confidence_scores must be layout-keyed
    conf = result["confidence_scores"]
    assert "cluster_0" in conf, "confidence_scores not keyed by layout id"
    assert "factors" not in conf, "flat 'factors' key must not appear at top level"
    assert "global_score" not in conf, "flat 'global_score' must not appear at top level"
    assert conf["cluster_0"]["overall"] == 72

    # coverage must be layout-keyed
    cov = result["coverage"]
    assert "cluster_0" in cov, "coverage not keyed by layout id"
    assert "fields" not in cov or isinstance(cov.get("fields"), dict) is False, \
        "flat 'fields' key must not appear at top level"
    assert cov["cluster_0"]["fields"]["mapped"] == 3
    assert cov["cluster_0"]["percentage"] == 30


# ---------------------------------------------------------------------------
# Story 12.5 — _bbox_to_css_layout: CSS pixels with Y-inversion
# ---------------------------------------------------------------------------


class TestBboxToCssLayout:
    """_bbox_to_css_layout converts PDF bbox to CSS pixel coordinates (AC5/AC6)."""

    def test_a4_origin_block_x_scales_correctly(self):
        """x = round(x0 * SCALE_X, 1) for A4 default."""
        from services.stages.pipeline_result import _SCALE_X
        result = _bbox_to_css_layout((42.0, 700.0, 200.0, 720.0))
        assert result["x"] == round(42.0 * _SCALE_X, 1)

    def test_y_is_inverted_from_pdf_origin(self):
        """y = round((page_height - y1) * SCALE_Y, 1) — PDF origin is bottom-left."""
        from services.stages.pipeline_result import _SCALE_Y, _A4_HEIGHT_PTS
        result = _bbox_to_css_layout((0.0, 700.0, 100.0, 730.0))
        # y1=730 → css_y = (842 - 730) * SCALE_Y = 112 * SCALE_Y
        expected_y = round((842.0 - 730.0) * _SCALE_Y, 1)
        assert result["y"] == expected_y

    def test_width_and_height_computed_correctly(self):
        """w = (x1-x0)*SCALE_X, h = (y1-y0)*SCALE_Y."""
        from services.stages.pipeline_result import _SCALE_X, _SCALE_Y
        result = _bbox_to_css_layout((42.0, 84.0, 200.0, 96.0))
        assert result["width"] == round((200.0 - 42.0) * _SCALE_X, 1)
        assert result["height"] == round((96.0 - 84.0) * _SCALE_Y, 1)

    def test_none_bbox_returns_null_values(self):
        result = _bbox_to_css_layout(None)
        assert result == {"x": None, "y": None, "width": None, "height": None}

    def test_short_bbox_returns_null_values(self):
        result = _bbox_to_css_layout([10, 20])
        assert result == {"x": None, "y": None, "width": None, "height": None}

    def test_non_a4_page_height_used_for_y_inversion(self):
        """AC6: non-A4 page height recalculates both scale_y AND y-inversion origin."""
        letter_height = 792.0
        result = _bbox_to_css_layout((0.0, 50.0, 100.0, 80.0), page_height_pts=letter_height)
        # For non-A4 pages, scale_y = 1123 / page_height_pts (not global _SCALE_Y)
        scale_y = 1123 / letter_height
        expected_y = round((letter_height - 80.0) * scale_y, 1)
        assert result["y"] == expected_y

    def test_non_a4_differs_from_a4_for_same_bbox(self):
        """AC6: different page heights produce different y values."""
        a4_result = _bbox_to_css_layout((0.0, 50.0, 100.0, 80.0))
        letter_result = _bbox_to_css_layout((0.0, 50.0, 100.0, 80.0), page_height_pts=792.0)
        assert a4_result["y"] != letter_result["y"], (
            "Same bbox on different page heights should produce different CSS y values"
        )


# ---------------------------------------------------------------------------
# Story 12.5 — _build_document_tree_root: properties.x/y in CSS pixels
# ---------------------------------------------------------------------------


class TestBuildDocumentTreeRoot:
    """_build_document_tree_root() block properties use CSS pixels (Story 12.5 AC1/AC5)."""

    def _make_doc(self, bbox=(42.0, 700.0, 200.0, 720.0), font_name="Arial", font_size=10.0):
        return [{
            "pdf_name": "test.pdf",
            "pdf_index": 0,
            "pages": [{
                "page_number": 0,
                "text_blocks": [{
                    "id": "block-abc",
                    "text": "Pagador",
                    "semantic_label": "table_cell",
                    "font_name": font_name,
                    "font_size": font_size,
                    "bbox": list(bbox),
                }],
            }],
        }]

    def test_properties_x_is_css_pixels_not_pdf_points(self):
        """AC1/AC5: properties.x = x0 * SCALE_X (not raw x0 in pts)."""
        from services.stages.pipeline_result import _SCALE_X
        docs = self._make_doc(bbox=(42.0, 700.0, 200.0, 720.0))
        root = _build_document_tree_root(docs)
        assert root is not None
        page_node = root["children"][0]
        block_node = page_node["children"][0]
        props = block_node["properties"]
        expected_x = round(42.0 * _SCALE_X, 1)
        assert props["x"] == expected_x, (
            f"Expected CSS px x={expected_x}, got {props['x']} (raw PDF pt=42.0)"
        )

    def test_properties_y_uses_y_inversion(self):
        """AC1/AC5: properties.y = (page_height - y1) * SCALE_Y (not raw y0)."""
        from services.stages.pipeline_result import _SCALE_Y, _A4_HEIGHT_PTS
        docs = self._make_doc(bbox=(42.0, 700.0, 200.0, 720.0))
        root = _build_document_tree_root(docs)
        assert root is not None
        page_node = root["children"][0]
        block_node = page_node["children"][0]
        props = block_node["properties"]
        # y1=720 → css_y = (842 - 720) * SCALE_Y = 122 * SCALE_Y
        expected_y = round((842.0 - 720.0) * _SCALE_Y, 1)
        assert props["y"] == expected_y

    def test_properties_font_family_and_font_size_populated(self):
        """AC2: font_family and font_size present in node properties."""
        docs = self._make_doc(font_name="Helvetica", font_size=12.0)
        root = _build_document_tree_root(docs)
        assert root is not None
        props = root["children"][0]["children"][0]["properties"]
        assert props["font_family"] == "Helvetica"
        assert props["font_size"] == 12.0

    def test_properties_none_when_no_bbox(self):
        """AC3: x/y/width/height are None when block has no bbox."""
        docs = [{
            "pdf_name": "test.pdf",
            "pdf_index": 0,
            "pages": [{
                "page_number": 0,
                "text_blocks": [{
                    "id": "block-no-bbox",
                    "text": "No bbox",
                    "semantic_label": "value",
                }],
            }],
        }]
        root = _build_document_tree_root(docs)
        assert root is not None
        props = root["children"][0]["children"][0]["properties"]
        assert props["x"] is None
        assert props["y"] is None
        assert props["width"] is None
        assert props["height"] is None
