"""Tests for Stage 23 — field_matching.py (Story 12.2 AC6).

Tests that:
- When flat_paths is empty (field_tree None), a warning SSE event is emitted
- context["field_matching_skipped"] = True when no XSD schema available
"""

from __future__ import annotations

import asyncio
import pytest
from typing import Any, Dict


def _make_context(field_tree=None, blocks=None):
    """Build minimal pipeline context for field_matching tests."""
    pages = []
    if blocks:
        pages = [{"page_number": 0, "text_blocks": blocks}]
    return {
        "parsed_documents": [{"pdf_name": "test.pdf", "pdf_index": 0, "pages": pages}],
        "field_tree": field_tree,
        "_sse_events": [],
    }


def _make_block(text, semantic_label="value"):
    return {
        "id": "b1",
        "text": text,
        "semantic_label": semantic_label,
        "bbox": [10, 700, 200, 720],
        "page_number": 0,
        "pdf_index": 0,
    }


class TestFieldMatchingWarnings:
    """Story 12.2 AC5/AC6: field_matching warns when flat_paths is empty."""

    def _run(self, ctx):
        from services.stages.field_matching import execute
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(execute(ctx))
        finally:
            loop.close()

    def test_field_tree_none_sets_field_matching_skipped(self):
        """AC5: field_matching_skipped=True when field_tree is None."""
        ctx = _make_context(field_tree=None, blocks=[_make_block("João Silva")])
        self._run(ctx)
        assert ctx.get("field_matching_skipped") is True

    def test_field_tree_none_emits_warning_sse_event(self):
        """AC5: SSE warning event emitted with stage='field_matching' and status='warning'."""
        ctx = _make_context(field_tree=None, blocks=[_make_block("João Silva")])
        self._run(ctx)
        events = ctx.get("_sse_events", [])
        warning_events = [e for e in events if e.get("stage") == "field_matching" and e.get("status") == "warning"]
        assert len(warning_events) >= 1, f"Expected warning event, got: {events}"

    def test_field_tree_empty_flat_paths_also_warns(self):
        """AC5: field_tree with empty flat_paths also triggers warning."""
        ctx = _make_context(field_tree={"flat_paths": []}, blocks=[_make_block("Value")])
        self._run(ctx)
        assert ctx.get("field_matching_skipped") is True

    def test_with_valid_flat_paths_no_skipped_flag(self):
        """AC6: When field_tree has paths, field_matching_skipped is NOT set."""
        field_tree = {"flat_paths": ["doc.nome", "doc.valor"]}
        ctx = _make_context(field_tree=field_tree, blocks=[_make_block("João")])
        self._run(ctx)
        assert not ctx.get("field_matching_skipped")

    def test_field_tree_none_still_generates_minimal_mappings(self):
        """Backward compat: minimal mappings (xsd_field_path='') still produced."""
        ctx = _make_context(field_tree=None, blocks=[_make_block("ABC")])
        self._run(ctx)
        mappings = ctx.get("field_mappings", [])
        assert len(mappings) >= 1
        assert mappings[0]["xsd_field_path"] == ""
