"""Tests for rule-based auto-fix detection helpers (Story 14.10)."""

from typing import Any

from routers.auto_fix import (
    _bboxes_overlap,
    _colors_match,
    _detect_background_issues,
    _detect_border_issues,
    _detect_text_align_issues,
    _detect_zorder_issues,
    _flatten_nodes,
)

# ---------------------------------------------------------------------------
# _colors_match
# ---------------------------------------------------------------------------


class TestColorsMatch:
    def test_exact_match(self):
        assert _colors_match("#ff0000", "#ff0000") is True

    def test_within_tolerance(self):
        assert _colors_match("#ff0000", "#f50000", tolerance=10) is True

    def test_outside_tolerance(self):
        assert _colors_match("#ff0000", "#000000", tolerance=10) is False

    def test_case_insensitive_fallback(self):
        assert _colors_match("red", "RED") is True

    def test_invalid_hex_fallback(self):
        assert _colors_match("xyz", "xyz") is True
        assert _colors_match("xyz", "abc") is False


# ---------------------------------------------------------------------------
# _bboxes_overlap
# ---------------------------------------------------------------------------


class TestBboxesOverlap:
    def test_overlapping(self):
        a = {"x": 0, "y": 0, "width": 100, "height": 100}
        b = {"x": 50, "y": 50, "width": 100, "height": 100}
        assert _bboxes_overlap(a, b) is True

    def test_no_overlap(self):
        a = {"x": 0, "y": 0, "width": 50, "height": 50}
        b = {"x": 200, "y": 200, "width": 50, "height": 50}
        assert _bboxes_overlap(a, b) is False

    def test_zero_size(self):
        a = {"x": 0, "y": 0, "width": 0, "height": 0}
        b = {"x": 0, "y": 0, "width": 100, "height": 100}
        assert _bboxes_overlap(a, b) is False


# ---------------------------------------------------------------------------
# _flatten_nodes
# ---------------------------------------------------------------------------


class TestFlattenNodes:
    def test_flat(self):
        tree = {"id": "root", "children": [{"id": "child1", "children": []}]}
        result = _flatten_nodes(tree)
        assert len(result) == 2

    def test_empty(self):
        assert _flatten_nodes({}) == []
        assert _flatten_nodes("not a dict") == []


# ---------------------------------------------------------------------------
# _detect_border_issues
# ---------------------------------------------------------------------------


class TestDetectBorderIssues:
    def test_missing_border(self):
        drawn = [{"type": "line", "bbox": [10, 10, 90, 90], "color": "#333", "width": 1}]
        nodes = [{"id": "n1", "properties": {"x": 10, "y": 10, "width": 80, "height": 80}}]
        suggestions: list[Any] = []
        _detect_border_issues(drawn, nodes, suggestions, 0)
        assert len(suggestions) == 1
        assert suggestions[0].type == "border-refine"

    def test_existing_border_no_suggestion(self):
        drawn = [{"type": "rect", "bbox": [10, 10, 90, 90], "color": "#333", "width": 1}]
        nodes = [
            {
                "id": "n1",
                "properties": {
                    "x": 10,
                    "y": 10,
                    "width": 80,
                    "height": 80,
                    "border_top_width": 1,
                },
            }
        ]
        suggestions: list[Any] = []
        _detect_border_issues(drawn, nodes, suggestions, 0)
        assert len(suggestions) == 0

    def test_ignores_non_line_rect(self):
        drawn = [{"type": "text", "bbox": [0, 0, 100, 100]}]
        nodes = [{"id": "n1", "properties": {"x": 0, "y": 0, "width": 100, "height": 100}}]
        suggestions: list[Any] = []
        _detect_border_issues(drawn, nodes, suggestions, 0)
        assert len(suggestions) == 0


# ---------------------------------------------------------------------------
# _detect_background_issues
# ---------------------------------------------------------------------------


class TestDetectBackgroundIssues:
    def test_missing_background(self):
        rects = [{"fill_color": "#ff0000", "bbox": [0, 0, 100, 100]}]
        nodes = [{"id": "n1", "properties": {"x": 0, "y": 0, "width": 100, "height": 100}}]
        suggestions: list[Any] = []
        _detect_background_issues(rects, nodes, suggestions, 0)
        assert len(suggestions) == 1
        assert suggestions[0].type == "background-refine"
        assert suggestions[0].suggested_value == "#ff0000"

    def test_matching_background(self):
        rects = [{"fill_color": "#ff0000", "bbox": [0, 0, 100, 100]}]
        nodes = [
            {
                "id": "n1",
                "properties": {
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "background_color": "#ff0000",
                },
            }
        ]
        suggestions: list[Any] = []
        _detect_background_issues(rects, nodes, suggestions, 0)
        assert len(suggestions) == 0


# ---------------------------------------------------------------------------
# _detect_text_align_issues
# ---------------------------------------------------------------------------


class TestDetectTextAlignIssues:
    def test_right_aligned_text(self):
        positions = [{"element_id": "n1", "x": 180, "text_width": 20, "container_width": 200}]
        nodes = [{"id": "n1", "properties": {"text_align": "left"}}]
        suggestions: list[Any] = []
        _detect_text_align_issues(positions, nodes, suggestions, 0)
        assert len(suggestions) == 1
        assert suggestions[0].suggested_value == "right"

    def test_center_aligned_text(self):
        positions = [{"element_id": "n1", "x": 90, "text_width": 20, "container_width": 200}]
        nodes = [{"id": "n1", "properties": {"text_align": "left"}}]
        suggestions: list[Any] = []
        _detect_text_align_issues(positions, nodes, suggestions, 0)
        assert len(suggestions) == 1
        assert suggestions[0].suggested_value == "center"

    def test_already_correct(self):
        positions = [{"element_id": "n1", "x": 0, "text_width": 50, "container_width": 200}]
        nodes = [{"id": "n1", "properties": {"text_align": "left"}}]
        suggestions: list[Any] = []
        _detect_text_align_issues(positions, nodes, suggestions, 0)
        assert len(suggestions) == 0


# ---------------------------------------------------------------------------
# _detect_zorder_issues
# ---------------------------------------------------------------------------


class TestDetectZorderIssues:
    def test_overlapping_without_zindex(self):
        nodes = [
            {"id": "a", "properties": {"x": 0, "y": 0, "width": 100, "height": 100}},
            {"id": "b", "properties": {"x": 50, "y": 50, "width": 100, "height": 100}},
        ]
        suggestions: list[Any] = []
        _detect_zorder_issues(nodes, suggestions, 0)
        assert len(suggestions) >= 1
        assert all(s.type == "z-order" for s in suggestions)

    def test_no_overlap(self):
        nodes = [
            {"id": "a", "properties": {"x": 0, "y": 0, "width": 50, "height": 50}},
            {"id": "b", "properties": {"x": 200, "y": 200, "width": 50, "height": 50}},
        ]
        suggestions: list[Any] = []
        _detect_zorder_issues(nodes, suggestions, 0)
        assert len(suggestions) == 0

    def test_with_zindex_already_set(self):
        nodes = [
            {"id": "a", "properties": {"x": 0, "y": 0, "width": 100, "height": 100, "zIndex": 1}},
            {"id": "b", "properties": {"x": 50, "y": 50, "width": 100, "height": 100, "zIndex": 2}},
        ]
        suggestions: list[Any] = []
        _detect_zorder_issues(nodes, suggestions, 0)
        assert len(suggestions) == 0
