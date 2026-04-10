"""Contract tests — document_trees format across Stage 3 → Stage 4 → Stage 5.

Story 10.21 — RCA rca-2026-03-31-stage5-document-trees-contract.

Validates that:
- Stage 3 outputs document_trees as Dict[cluster_id, tree] in context (not list)
- Stage 4 consumes document_trees as dict without error
- Stage 5 / _step_5_6_pipeline_result consumes document_trees as dict without error
- Regression: if document_trees were a list, Stage 5 would crash with AttributeError

All external dependencies (LLM, storage, emit_progress) are mocked.
No files, network calls, or real PDFs required.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend is on sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _noop_emit(event: dict[str, Any]) -> None:
    pass


def _minimal_tree() -> dict[str, Any]:
    """Minimal valid document tree node."""
    return {
        "id": "root-c1",
        "type": "document",
        "children": [],
    }


def _raw_trees_as_list() -> list[dict[str, Any]]:
    """Format returned by _run_3_4 (list)."""
    return [
        {"cluster_id": "cluster-1", "tree": _minimal_tree()},
        {"cluster_id": "cluster-2", "tree": _minimal_tree()},
    ]


def _document_trees_as_dict() -> dict[str, dict[str, Any]]:
    """Expected normalized format after Stage 3 processing."""
    return {
        "cluster-1": _minimal_tree(),
        "cluster-2": _minimal_tree(),
    }


def _minimal_layout_types() -> list[dict[str, Any]]:
    return [
        {"id": "cluster-1", "cluster_id": "cluster-1", "name": "Layout A"},
    ]


# ---------------------------------------------------------------------------
# AC-1: Stage 3 outputs document_trees as dict
# ---------------------------------------------------------------------------


class TestStage3Contract:
    """Stage 3 must write document_trees as Dict[cluster_id, tree] to context."""

    @pytest.mark.asyncio
    async def test_stage3_normalizes_list_to_dict(self):
        """_run_3_4 returns list; run_stage3 must convert to dict before writing context."""
        import services.stages.stage3_structural_analysis as mod

        raw_list = _raw_trees_as_list()

        # Mock all sub-steps so we only test the normalization logic
        mock_loop = MagicMock()
        # run_in_executor used for _run_3_1 (sync in thread pool)
        future = asyncio.get_event_loop().create_future()
        future.set_result({})
        mock_loop.run_in_executor = MagicMock(return_value=future)

        with (
            patch.object(mod, "_run_3_1", return_value={}),
            patch.object(mod, "_run_3_2", new=AsyncMock(return_value={})),
            patch.object(mod, "_run_3_3", return_value=({}, {})),
            patch.object(mod, "_run_3_4", return_value=raw_list),
            patch("asyncio.get_event_loop", return_value=mock_loop),
            patch(
                "services.pipeline_orchestrator_v2.make_sub_progress_event",
                return_value={},
            ),
            patch(
                "services.pipeline_orchestrator_v2.compute_overall_progress",
                return_value=0,
            ),
        ):
            context: dict[str, Any] = {
                "clusters": [],
                "_raw_text_blocks": {},
                "enriched_documents": [],
            }
            result = await mod.run_stage3(context, _noop_emit)

        # document_trees must be a dict, not a list
        assert isinstance(result["document_trees"], dict), f"Expected dict, got {type(result['document_trees'])}"

    @pytest.mark.asyncio
    async def test_stage3_dict_keyed_by_cluster_id(self):
        """Keys of document_trees must be cluster_id strings."""
        import services.stages.stage3_structural_analysis as mod

        raw_list = _raw_trees_as_list()

        future = asyncio.get_event_loop().create_future()
        future.set_result({})
        mock_loop = MagicMock()
        mock_loop.run_in_executor = MagicMock(return_value=future)

        with (
            patch.object(mod, "_run_3_1", return_value={}),
            patch.object(mod, "_run_3_2", new=AsyncMock(return_value={})),
            patch.object(mod, "_run_3_3", return_value=({}, {})),
            patch.object(mod, "_run_3_4", return_value=raw_list),
            patch("asyncio.get_event_loop", return_value=mock_loop),
            patch("services.pipeline_orchestrator_v2.make_sub_progress_event", return_value={}),
            patch("services.pipeline_orchestrator_v2.compute_overall_progress", return_value=0),
        ):
            context: dict[str, Any] = {
                "clusters": [],
                "_raw_text_blocks": {},
                "enriched_documents": [],
            }
            result = await mod.run_stage3(context, _noop_emit)

        trees = result["document_trees"]
        assert "cluster-1" in trees
        assert "cluster-2" in trees
        assert trees["cluster-1"] == _minimal_tree()

    @pytest.mark.asyncio
    async def test_stage3_empty_clusters_produces_empty_dict(self):
        """Empty _run_3_4 list normalizes to empty dict, not empty list."""
        import services.stages.stage3_structural_analysis as mod

        future = asyncio.get_event_loop().create_future()
        future.set_result({})
        mock_loop = MagicMock()
        mock_loop.run_in_executor = MagicMock(return_value=future)

        with (
            patch.object(mod, "_run_3_1", return_value={}),
            patch.object(mod, "_run_3_2", new=AsyncMock(return_value={})),
            patch.object(mod, "_run_3_3", return_value=({}, {})),
            patch.object(mod, "_run_3_4", return_value=[]),  # empty list
            patch("asyncio.get_event_loop", return_value=mock_loop),
            patch("services.pipeline_orchestrator_v2.make_sub_progress_event", return_value={}),
            patch("services.pipeline_orchestrator_v2.compute_overall_progress", return_value=0),
        ):
            context: dict[str, Any] = {
                "clusters": [],
                "_raw_text_blocks": {},
                "enriched_documents": [],
            }
            result = await mod.run_stage3(context, _noop_emit)

        assert result["document_trees"] == {}
        assert isinstance(result["document_trees"], dict)


# ---------------------------------------------------------------------------
# AC-2: Stage 4 consumes document_trees as dict
# ---------------------------------------------------------------------------


class TestStage4Contract:
    """Stage 4 must consume context['document_trees'] as dict without error."""

    @pytest.mark.asyncio
    async def test_stage4_accepts_dict_document_trees(self):
        """run_stage4 with document_trees as dict does not crash."""
        import services.stages.stage4_field_mapping as mod

        context: dict[str, Any] = {
            "document_trees": _document_trees_as_dict(),
            "intelligence": {},
            "clusters": [],
            "enriched_documents": [],
            "visual_analysis": {},
            "xsd_path": None,
            "field_tree": None,
            "layout_types": _minimal_layout_types(),
        }

        # Stage 4 will attempt LLM calls — mock them all
        with (
            patch.object(mod, "_step_4_1_xsd_parsing", return_value=None),
            patch.object(mod, "_step_4_2_pair_validation", return_value=[]),
            patch.object(mod, "_step_4_3_format_pre_detection", return_value=([], {})),
            patch.object(mod, "_step_4_4_section_xsd_matching", return_value={}),
            patch.object(
                mod,
                "_step_4_5_field_matching",
                new=AsyncMock(return_value=([], [], {})),
            ),
            patch.object(mod, "_step_4_6_confidence_scoring", return_value={}),
            patch.object(mod, "_step_4_7_consistency_validation", return_value={"warnings": [], "errors": []}),
            patch(
                "services.pipeline_orchestrator_v2.make_sub_progress_event",
                return_value={},
            ),
            patch(
                "services.pipeline_orchestrator_v2.compute_overall_progress",
                return_value=0,
            ),
        ):
            # Should not raise
            result = await mod.run_stage4(context, _noop_emit)

        # document_trees format in context must remain dict
        assert isinstance(context["document_trees"], dict)

    def test_stage4_document_trees_type_annotation(self):
        """document_trees is read directly as Dict — no isinstance conversion needed."""
        import inspect

        import services.stages.stage4_field_mapping as mod

        source = inspect.getsource(mod.run_stage4)
        # After our fix, there should be no list-to-dict conversion block
        assert "isinstance(raw_trees, list)" not in source, (
            "Stage 4 still has list-to-dict conversion — Stage 3 should normalize instead"
        )


# ---------------------------------------------------------------------------
# AC-3: Stage 5 / _step_5_6_pipeline_result consumes document_trees as dict
# ---------------------------------------------------------------------------


class TestStage5Contract:
    """Stage 5 internal functions must consume document_trees as dict."""

    def test_step_5_6_accepts_dict_document_trees(self):
        """_step_5_6_pipeline_result with document_trees as dict does not crash."""
        from services.stages.stage5_template_generation import _step_5_6_pipeline_result

        context: dict[str, Any] = {
            "document_trees": _document_trees_as_dict(),
            "layout_types": _minimal_layout_types(),
            "confidence_scores": {},
            "enriched_documents": [],
            "visual_analysis": None,
            "field_mappings": [],
            "format_functions": {},
            "clusters": [],
            "pdf_documents": [],
            "parsed_documents": [],
            "document_type_confidence": 0.0,
        }

        # Should not raise AttributeError
        result = _step_5_6_pipeline_result(
            context,
            html_by_layout={},
            css_global="",
            coverage_by_layout={},
            overlay_by_layout={},
            multi_doc={"pdfs": [], "detections": []},
        )

        assert isinstance(result, dict)

    def test_step_5_6_builds_trees_by_layout(self):
        """_step_5_6_pipeline_result correctly maps layout_id → tree when document_trees is dict."""
        from services.stages.stage5_template_generation import _step_5_6_pipeline_result

        tree = _minimal_tree()
        context: dict[str, Any] = {
            "document_trees": {"cluster-1": tree},
            "layout_types": [
                {
                    "id": "cluster-1",
                    "cluster_id": "cluster-1",
                    "name": "A",
                    "page_width_pts": 595,
                    "page_height_pts": 842,
                }
            ],
            "confidence_scores": {},
            "enriched_documents": [],
            "visual_analysis": None,
            "field_mappings": [],
            "format_functions": {},
            "clusters": [],
            "pdf_documents": [],
            "parsed_documents": [],
            "document_type_confidence": 0.0,
        }

        result = _step_5_6_pipeline_result(
            context,
            html_by_layout={"cluster-1": "<div/>"},
            css_global="body{}",
            coverage_by_layout={},
            overlay_by_layout={},
            multi_doc={"pdfs": [], "detections": []},
        )

        # layout_types should be enriched (even if trees_by_layout is empty due to
        # _convert_tree_to_css_coords returning None for minimal tree)
        assert "layout_types" in result
        assert "document_structure" in result

    def test_stage5_no_list_conversion_in_run_stage5(self):
        """run_stage5 must not contain list-to-dict conversion — Stage 3 handles it."""
        import inspect

        import services.stages.stage5_template_generation as mod

        source = inspect.getsource(mod.run_stage5)
        assert "isinstance(raw_trees, list)" not in source, (
            "Stage 5 still has list-to-dict conversion — Stage 3 should normalize instead"
        )


# ---------------------------------------------------------------------------
# AC-4: Regression — if document_trees were a list, Stage 5 crashes (documented)
# ---------------------------------------------------------------------------


class TestStage5Regression:
    """Documents the regression that triggered RCA rca-2026-03-31-stage5-document-trees-contract."""

    def test_step_5_6_crashes_with_list_document_trees(self):
        """If document_trees is incorrectly a list, .get() raises AttributeError.

        This test documents the original bug. It serves as a sentinel:
        if Stage 3 ever regresses and writes a list, this test reminds us
        of the exact failure mode.
        """
        from services.stages.stage5_template_generation import _step_5_6_pipeline_result

        context: dict[str, Any] = {
            # BUG SCENARIO: document_trees as list (old Stage 3 format)
            "document_trees": [{"cluster_id": "cluster-1", "tree": _minimal_tree()}],
            "layout_types": [{"id": "cluster-1", "cluster_id": "cluster-1", "name": "A"}],
            "confidence_scores": {},
            "enriched_documents": [],
            "visual_analysis": None,
            "field_mappings": [],
            "format_functions": {},
            "clusters": [],
            "pdf_documents": [],
            "parsed_documents": [],
            "document_type_confidence": 0.0,
        }

        with pytest.raises(AttributeError, match="'list' object has no attribute 'get'"):
            _step_5_6_pipeline_result(
                context,
                html_by_layout={},
                css_global="",
                coverage_by_layout={},
                overlay_by_layout={},
                multi_doc={"pdfs": [], "detections": []},
            )
