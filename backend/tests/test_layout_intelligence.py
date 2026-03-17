"""Tests for Story 5.8 — Bloco 4: Layout Intelligence.

Covers:
- Stage 12 — Layout Alignment (single-doc trivial, multi-doc offset)
- Stage 13 — Multi-Example Analysis (label vs dynamic, heuristics)
- Stage 14 — Stability Classification (stable/variable/absent, scores)
- Stage 15 — Variant Detection (optional_field, conditional_section, dynamic_table)
- Stage 16 — Intelligence Normalization (consolidation, re-serialisation)
- register_bloco4 wires stages into registry
- Single-document fallback (reduced accuracy flag)
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------


def _make_skeleton(
    page_number: int = 0,
    pdf_index: int = 0,
    text_blocks: List[tuple] = None,
    table_count: int = 0,
):
    """Create a LayoutSkeleton with controllable text_blocks."""
    from models.layout_type import LayoutSkeleton, LayoutZones

    blocks = text_blocks or []
    table_candidates = []
    for i in range(table_count):
        table_candidates.append((10.0, 300.0 + i * 50, 500.0, 340.0 + i * 50))

    return LayoutSkeleton(
        page_number=page_number,
        pdf_index=pdf_index,
        text_blocks=blocks,
        table_candidates=table_candidates,
        zones=LayoutZones(),
        grid_info=None,
        page_width=595.0,
        page_height=842.0,
    )


def _make_layout_type(
    cluster_id: int = 0,
    pages: List[Dict[str, int]] = None,
):
    from models.layout_type import LayoutFingerprint, LayoutType

    p = pages or [{"pdf_index": 0, "page_number": 0}]
    return LayoutType(
        cluster_id=cluster_id,
        name=f"Layout {cluster_id}",
        representative_page=p[0],
        fingerprint=LayoutFingerprint(),
        page_count=len(p),
        pages=p,
    )


# ---------------------------------------------------------------------------
# Test 1 — Layout Alignment: single document is trivial
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alignment_single_document_trivial():
    """With 1 PDF, all offsets should be (0, 0) and single_document flag set."""
    from services.stages.layout_alignment import execute

    skel = _make_skeleton(0, 0, [("Hello", (10.0, 10.0, 100.0, 22.0))])
    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}])

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel],
    }
    result = await execute(context)

    assert result["single_document"] is True
    assert result["pdf_count"] == 1
    offsets = context["alignment_offsets"]
    assert 0 in offsets
    assert offsets[0][0] == (0.0, 0.0)
    assert context.get("intelligence_metadata", {}).get("single_document") is True
    assert context["intelligence_metadata"]["reduced_accuracy"] is True


# ---------------------------------------------------------------------------
# Test 2 — Layout Alignment: multi-PDF computes non-trivial offsets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alignment_multi_pdf_computes_offsets():
    """With 2 PDFs, offsets should be computed (reference pdf=0 has 0 offset)."""
    from services.stages.layout_alignment import execute

    # PDF 0 starts at x=10, PDF 1 starts at x=20 → offset for pdf 1 = -10
    skel0 = _make_skeleton(0, 0, [("A", (10.0, 50.0, 100.0, 62.0))])
    skel1 = _make_skeleton(0, 1, [("A", (20.0, 50.0, 110.0, 62.0))])
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel0, skel1],
    }
    result = await execute(context)

    assert result["single_document"] is False
    assert result["pdf_count"] == 2
    offsets = context["alignment_offsets"][0]
    # PDF 0 is reference → offset (0, 0)
    assert offsets[0] == (0.0, 0.0)
    # PDF 1 should have non-zero x offset
    dx, dy = offsets[1]
    assert dx == pytest.approx(-10.0)


# ---------------------------------------------------------------------------
# Test 3 — Multi-Example Analysis: identical text → label (multi-PDF)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_example_label_identical_text():
    """Text identical across PDFs at same position → classified as label."""
    from services.stages.multi_example_analysis import execute

    bbox = (10.0, 50.0, 100.0, 62.0)
    skel0 = _make_skeleton(0, 0, [("Cliente:", bbox)])
    skel1 = _make_skeleton(0, 1, [("Cliente:", bbox)])
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel0, skel1],
        "alignment_offsets": {0: {0: (0.0, 0.0), 1: (0.0, 0.0)}},
        "intelligence_metadata": {},
    }
    result = await execute(context)

    labels = context["_element_labels"][0]
    label_entries = [e for e in labels if e["classification"] == "label"]
    assert len(label_entries) >= 1
    assert label_entries[0]["confidence"] == "confirmed"
    assert result["total_labels"] >= 1


# ---------------------------------------------------------------------------
# Test 4 — Multi-Example Analysis: varying text → dynamic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_example_dynamic_varying_text():
    """Text that differs across PDFs at the same position → classified as dynamic."""
    from services.stages.multi_example_analysis import execute

    bbox = (10.0, 80.0, 200.0, 92.0)
    skel0 = _make_skeleton(0, 0, [("João Silva", bbox)])
    skel1 = _make_skeleton(0, 1, [("Maria Oliveira", bbox)])
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel0, skel1],
        "alignment_offsets": {0: {0: (0.0, 0.0), 1: (0.0, 0.0)}},
        "intelligence_metadata": {},
    }
    result = await execute(context)

    labels = context["_element_labels"][0]
    dynamic_entries = [e for e in labels if e["classification"] == "dynamic"]
    assert len(dynamic_entries) >= 1
    assert dynamic_entries[0]["confidence"] == "confirmed"
    assert result["total_dynamic"] >= 1


# ---------------------------------------------------------------------------
# Test 5 — Multi-Example Analysis: single PDF heuristics (colon → label)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_example_single_pdf_colon_is_label():
    """Single-PDF mode: text ending with ':' → inferred label."""
    from services.stages.multi_example_analysis import execute

    skel = _make_skeleton(0, 0, [("Nome:", (10.0, 50.0, 80.0, 62.0))])
    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}])

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel],
        "alignment_offsets": {},
        "intelligence_metadata": {"single_document": True, "reduced_accuracy": True},
    }
    result = await execute(context)

    labels = context["_element_labels"][0]
    label_entries = [e for e in labels if e["classification"] == "label"]
    assert any("Nome:" in str(e["text_samples"]) for e in label_entries)
    assert all(e["confidence"] == "inferred" for e in labels)
    assert result["confidence_mode"] == "inferred"


# ---------------------------------------------------------------------------
# Test 6 — Multi-Example Analysis: single PDF — numeric text → dynamic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_example_single_pdf_numeric_is_dynamic():
    """Single-PDF mode: numeric text → inferred dynamic."""
    from services.stages.multi_example_analysis import execute

    skel = _make_skeleton(0, 0, [("12345.67", (10.0, 50.0, 80.0, 62.0))])
    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}])

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel],
        "alignment_offsets": {},
        "intelligence_metadata": {"single_document": True},
    }
    await execute(context)

    labels = context["_element_labels"][0]
    dynamic_entries = [e for e in labels if e["classification"] == "dynamic"]
    assert any("12345.67" in str(e["text_samples"]) for e in dynamic_entries)


# ---------------------------------------------------------------------------
# Test 7 — Stability Classification: stable element
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stability_stable_label():
    """Element classified as 'label' with confirmed confidence → stable."""
    from services.stages.stability_classification import execute

    element_labels = {
        0: [
            {
                "bbox_key": "10.0,50.0,100.0,62.0",
                "text_samples": ["Cliente:"],
                "classification": "label",
                "confidence": "confirmed",
            }
        ]
    }
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )
    context = {
        "_element_labels": element_labels,
        "_layout_type_objects": [lt],
        "_skeleton_objects": [],
        "intelligence_metadata": {},
    }
    result = await execute(context)

    smap = context["_stability_map"][0]
    key = "10.0,50.0,100.0,62.0"
    assert key in smap
    assert smap[key]["classification"] == "stable"
    assert smap[key]["stability_score"] == pytest.approx(1.0)
    assert result["total_stable"] == 1


# ---------------------------------------------------------------------------
# Test 8 — Stability Classification: variable element
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stability_variable_dynamic():
    """Element classified as 'dynamic' with confirmed confidence → variable."""
    from services.stages.stability_classification import execute

    element_labels = {
        0: [
            {
                "bbox_key": "10.0,80.0,200.0,92.0",
                "text_samples": ["João", "Maria"],
                "classification": "dynamic",
                "confidence": "confirmed",
            }
        ]
    }
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )
    context = {
        "_element_labels": element_labels,
        "_layout_type_objects": [lt],
        "_skeleton_objects": [],
        "intelligence_metadata": {},
    }
    result = await execute(context)

    smap = context["_stability_map"][0]
    key = "10.0,80.0,200.0,92.0"
    assert smap[key]["classification"] == "variable"
    assert result["total_variable"] == 1


# ---------------------------------------------------------------------------
# Test 9 — Stability Classification: absent element (partial presence)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stability_absent_partial_docs():
    """Element with fewer samples than total docs → absent classification."""
    from services.stages.stability_classification import execute

    # 3 docs but element appeared in only 1 (not confirmed → doc_count based on samples)
    element_labels = {
        0: [
            {
                "bbox_key": "50.0,200.0,300.0,212.0",
                "text_samples": ["Avalista:"],   # only 1 unique sample (seen in 1 doc)
                "classification": "label",
                "confidence": "partial",  # not "confirmed" → doc_count = len(samples)
            }
        ]
    }
    # 3 PDFs in cluster
    lt = _make_layout_type(
        0,
        [
            {"pdf_index": 0, "page_number": 0},
            {"pdf_index": 1, "page_number": 0},
            {"pdf_index": 2, "page_number": 0},
        ],
    )
    context = {
        "_element_labels": element_labels,
        "_layout_type_objects": [lt],
        "_skeleton_objects": [],
        "intelligence_metadata": {},
    }
    result = await execute(context)

    smap = context["_stability_map"][0]
    key = "50.0,200.0,300.0,212.0"
    assert smap[key]["classification"] == "absent"
    assert smap[key]["stability_score"] < 1.0
    assert result["total_absent"] == 1


# ---------------------------------------------------------------------------
# Test 10 — Stability Classification: single-document → unknown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stability_single_doc_unknown():
    """In single-document mode, all elements are classified as 'unknown'."""
    from services.stages.stability_classification import execute

    element_labels = {
        0: [
            {
                "bbox_key": "10.0,50.0,100.0,62.0",
                "text_samples": ["Nome:"],
                "classification": "label",
                "confidence": "inferred",
            }
        ]
    }
    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}])
    context = {
        "_element_labels": element_labels,
        "_layout_type_objects": [lt],
        "_skeleton_objects": [],
        "intelligence_metadata": {"single_document": True},
    }
    result = await execute(context)

    smap = context["_stability_map"][0]
    key = "10.0,50.0,100.0,62.0"
    assert smap[key]["classification"] == "unknown"
    assert result["total_unknown"] == 1


# ---------------------------------------------------------------------------
# Test 11 — Variant Detection: optional_field for absent element
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_variant_optional_field():
    """Absent element should generate an optional_field variant."""
    from services.stages.variant_detection import execute

    smap = {
        0: {
            "10.0,50.0,100.0,62.0": {
                "classification": "absent",
                "stability_score": 0.5,
                "doc_count": 1,
                "total_docs": 2,
                "confidence": "confirmed",
            }
        }
    }
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )
    context = {
        "_stability_map": smap,
        "_layout_type_objects": [lt],
        "_skeleton_objects": [],
        "intelligence_metadata": {},
        "_element_labels": {0: []},
    }
    result = await execute(context)

    variants = context["_variants"][0]
    opt_fields = [v for v in variants if v["type"] == "optional_field"]
    assert len(opt_fields) == 1
    assert "10.0,50.0,100.0,62.0" in opt_fields[0]["elements"]
    assert "1/2 docs" in opt_fields[0]["presence_pattern"]
    assert result["total_optional_fields"] == 1


# ---------------------------------------------------------------------------
# Test 12 — Variant Detection: conditional_section for adjacent absent fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_variant_conditional_section_adjacent():
    """Adjacent absent elements should form a conditional section."""
    from services.stages.variant_detection import execute

    # Two adjacent absent elements (y-close)
    smap = {
        0: {
            "10.0,100.0,200.0,112.0": {
                "classification": "absent",
                "stability_score": 0.5,
                "doc_count": 1,
                "total_docs": 2,
                "confidence": "confirmed",
            },
            "10.0,120.0,200.0,132.0": {
                "classification": "absent",
                "stability_score": 0.5,
                "doc_count": 1,
                "total_docs": 2,
                "confidence": "confirmed",
            },
        }
    }
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )
    context = {
        "_stability_map": smap,
        "_layout_type_objects": [lt],
        "_skeleton_objects": [],
        "intelligence_metadata": {},
        "_element_labels": {0: []},
    }
    result = await execute(context)

    sections = context["_conditional_sections"][0]
    assert len(sections) >= 1
    assert len(sections[0]["elements"]) == 2
    assert result["total_conditional_sections"] >= 1


# ---------------------------------------------------------------------------
# Test 13 — Variant Detection: dynamic_table when table count varies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_variant_dynamic_table():
    """Table count varying across PDFs → dynamic_table variant."""
    from services.stages.variant_detection import execute

    # PDF 0: 0 tables, PDF 1: 2 tables → variation > 0.5
    skel0 = _make_skeleton(0, 0, table_count=0)
    skel1 = _make_skeleton(0, 1, table_count=2)
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )
    context = {
        "_stability_map": {0: {}},
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel0, skel1],
        "intelligence_metadata": {},
        "_element_labels": {0: []},
    }
    result = await execute(context)

    variants = context["_variants"][0]
    dyn_tables = [v for v in variants if v["type"] == "dynamic_table"]
    assert len(dyn_tables) >= 1
    assert result["total_dynamic_tables"] >= 1


# ---------------------------------------------------------------------------
# Test 14 — Variant Detection: single document → no variants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_variant_single_doc_no_variants():
    """In single-document mode, variant detection yields empty results."""
    from services.stages.variant_detection import execute

    smap = {
        0: {
            "10.0,50.0,100.0,62.0": {
                "classification": "unknown",
                "stability_score": 1.0,
                "doc_count": 1,
                "total_docs": 1,
                "confidence": "inferred",
            }
        }
    }
    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}])
    context = {
        "_stability_map": smap,
        "_layout_type_objects": [lt],
        "_skeleton_objects": [],
        "intelligence_metadata": {"single_document": True},
        "_element_labels": {0: []},
    }
    result = await execute(context)

    assert context["_variants"][0] == []
    assert result["total_optional_fields"] == 0
    assert result["total_conditional_sections"] == 0
    assert result["single_document"] is True


# ---------------------------------------------------------------------------
# Test 15 — Intelligence Normalization: consolidates all data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_normalization_consolidates_all():
    """Stage 16 should consolidate labels, dynamic_fields, stability, variants."""
    from services.stages.intelligence_normalization import execute

    element_labels = {
        0: [
            {
                "bbox_key": "10.0,50.0,100.0,62.0",
                "text_samples": ["Cliente:"],
                "classification": "label",
                "confidence": "confirmed",
            },
            {
                "bbox_key": "10.0,80.0,200.0,92.0",
                "text_samples": ["João", "Maria"],
                "classification": "dynamic",
                "confidence": "confirmed",
            },
        ]
    }
    stability_map = {
        0: {
            "10.0,50.0,100.0,62.0": {
                "classification": "stable",
                "stability_score": 1.0,
                "doc_count": 2,
                "total_docs": 2,
            },
            "10.0,80.0,200.0,92.0": {
                "classification": "variable",
                "stability_score": 1.0,
                "doc_count": 2,
                "total_docs": 2,
            },
        }
    }
    variants = {
        0: [
            {
                "type": "optional_field",
                "elements": ["50.0,200.0,300.0,212.0"],
                "presence_pattern": "1/2 docs",
            }
        ]
    }
    cond_sections = {0: []}
    lt = _make_layout_type(
        0,
        [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 1, "page_number": 0}],
    )

    context = {
        "_layout_type_objects": [lt],
        "_element_labels": element_labels,
        "_stability_map": stability_map,
        "_variants": variants,
        "_conditional_sections": cond_sections,
        "intelligence_metadata": {},
    }
    result = await execute(context)

    intel = context["intelligence"][0]
    assert len(intel["labels"]) == 1
    assert intel["labels"][0]["text_samples"] == ["Cliente:"]
    assert len(intel["dynamic_fields"]) == 1
    assert intel["dynamic_fields"][0]["text_samples"] == ["João", "Maria"]
    assert "10.0,50.0,100.0,62.0" in intel["stability_map"]
    assert len(intel["variants"]) == 1
    assert intel["metadata"]["label_count"] == 1
    assert intel["metadata"]["dynamic_count"] == 1
    assert result["total_labels"] == 1
    assert result["total_dynamic_fields"] == 1
    assert result["total_variants"] == 1
    # layout_types should be re-serialised
    assert "layout_types" in context
    assert len(context["layout_types"]) == 1


# ---------------------------------------------------------------------------
# Test 16 — Normalization: single_document flag propagated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_normalization_single_doc_flag():
    """Normalization should propagate single_document and reduced_accuracy flags."""
    from services.stages.intelligence_normalization import execute

    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}])
    context = {
        "_layout_type_objects": [lt],
        "_element_labels": {0: []},
        "_stability_map": {0: {}},
        "_variants": {0: []},
        "_conditional_sections": {0: []},
        "intelligence_metadata": {"single_document": True, "reduced_accuracy": True},
    }
    result = await execute(context)

    intel = context["intelligence"][0]
    assert intel["metadata"]["single_document"] is True
    assert intel["metadata"]["reduced_accuracy"] is True
    assert result["single_document"] is True
    assert result["reduced_accuracy"] is True


# ---------------------------------------------------------------------------
# Test 17 — register_bloco4 wires stages 12-16 into registry
# ---------------------------------------------------------------------------


def test_register_bloco4_wires_stages():
    """register_bloco4 should replace stubs 12-16 with real implementations."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco4

    registry = build_default_registry()

    # Before registration, stubs execute nothing interesting
    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[12]._execute_fn is None  # stub

    register_bloco4(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}

    for stage_num in (12, 13, 14, 15, 16):
        assert stages_after[stage_num]._execute_fn is not None, (
            f"Stage {stage_num} still has a stub executor after register_bloco4"
        )

    # Pipeline shape must remain intact — still 27 stages
    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 28


# ---------------------------------------------------------------------------
# Test 18 — End-to-end: stages 12-16 run in sequence (single PDF)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_bloco4_single_pdf():
    """Stages 12-16 should run in sequence without errors on a single PDF."""
    from services.stages.layout_alignment import execute as s12
    from services.stages.multi_example_analysis import execute as s13
    from services.stages.stability_classification import execute as s14
    from services.stages.variant_detection import execute as s15
    from services.stages.intelligence_normalization import execute as s16

    skels = [
        _make_skeleton(0, 0, [("Nome:", (10.0, 50.0, 80.0, 62.0)), ("123.456", (10.0, 80.0, 80.0, 92.0))]),
        _make_skeleton(1, 0, [("Data:", (10.0, 100.0, 80.0, 112.0))]),
    ]
    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}, {"pdf_index": 0, "page_number": 1}])

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": skels,
        "parsed_documents": [],
    }

    await s12(context)
    await s13(context)
    await s14(context)
    await s15(context)
    await s16(context)

    # Intelligence should be present and correct
    assert "intelligence" in context
    intel = context["intelligence"][0]
    assert "labels" in intel
    assert "dynamic_fields" in intel
    assert "stability_map" in intel
    assert "variants" in intel
    assert intel["metadata"]["single_document"] is True
    assert intel["metadata"]["reduced_accuracy"] is True
    # All elements should be "inferred" confidence
    for entry in intel["labels"] + intel["dynamic_fields"]:
        assert entry["confidence"] == "inferred"


# ---------------------------------------------------------------------------
# Test 19 — SSE progress events are emitted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_progress_emitted_by_all_stages():
    """All 5 stages should emit exactly one SSE event when emit_progress is set."""
    from services.stages.layout_alignment import execute as s12
    from services.stages.multi_example_analysis import execute as s13
    from services.stages.stability_classification import execute as s14
    from services.stages.variant_detection import execute as s15
    from services.stages.intelligence_normalization import execute as s16

    events = []

    def capture(event):
        events.append(event)

    skel = _make_skeleton(0, 0, [("A:", (10.0, 50.0, 80.0, 62.0))])
    lt = _make_layout_type(0, [{"pdf_index": 0, "page_number": 0}])

    context = {
        "_layout_type_objects": [lt],
        "_skeleton_objects": [skel],
        "_element_labels": {0: []},
        "_stability_map": {0: {}},
        "_variants": {0: []},
        "_conditional_sections": {0: []},
        "intelligence_metadata": {"single_document": True},
        "emit_progress": capture,
    }

    await s12(context)
    await s13(context)
    await s14(context)
    await s15(context)
    await s16(context)

    stage_nums = [e["stage"] for e in events]
    assert 12 in stage_nums
    assert 13 in stage_nums
    assert 14 in stage_nums
    assert 15 in stage_nums
    assert 16 in stage_nums
    for e in events:
        assert e["status"] == "completed"
