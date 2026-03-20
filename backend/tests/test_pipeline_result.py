"""Tests for Stage 28 — pipeline_result.py (Story 10.16).

Verifies that _get_confidence_scores() and _get_coverage() transform the flat
backend format (Stage 25 / Stage 27) into the layout-keyed format expected by
the frontend confidenceStore and coverageStore.
"""

from __future__ import annotations

import pytest
from services.stages.pipeline_result import _get_confidence_scores, _get_coverage


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
