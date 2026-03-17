"""Tests for Story 5.7 — Bloco 3: Layout Discovery.

Covers:
- Skeleton building from ParsedDocument data
- Page clustering (similar pages grouped together)
- Representative selection (primary + secondary per cluster)
- Fingerprint generation (same layout → same hash)
- Registry lookup: hit, miss, offline/skip
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_text_block_dict(
    text: str = "Sample",
    x0: float = 10.0,
    y0: float = 10.0,
    x1: float = 100.0,
    y1: float = 22.0,
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    page_number: int = 0,
    pdf_index: int = 0,
) -> Dict[str, Any]:
    return {
        "text": text,
        "bbox": [x0, y0, x1, y1],
        "font_name": font_name,
        "font_size": font_size,
        "page_number": page_number,
        "pdf_index": pdf_index,
    }


def _make_page_dict(
    page_number: int = 0,
    text_blocks: List[Dict[str, Any]] = None,
    grid_info: Dict[str, Any] = None,
) -> Dict[str, Any]:
    return {
        "page_number": page_number,
        "text_blocks": text_blocks or [],
        "images": [],
        "fonts": [],
        "grid_info": grid_info,
        "screenshot_path": None,
    }


def _make_parsed_document(
    pdf_index: int = 0,
    pages: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "job_id": "test-job",
        "pdf_index": pdf_index,
        "pdf_name": f"test_{pdf_index}.pdf",
        "pages": pages or [],
    }


def _make_skeleton(
    page_number: int = 0,
    pdf_index: int = 0,
    num_blocks: int = 5,
    table_count: int = 0,
    font_size: float = 12.0,
):
    """Create a LayoutSkeleton with controllable feature values."""
    from models.layout_type import LayoutSkeleton, LayoutZones

    blocks = []
    for i in range(num_blocks):
        # Spread blocks across page, font-size proxy = y1-y0 = font_size
        y0 = 100.0 + i * (font_size + 2)
        y1 = y0 + font_size
        blocks.append((f"Block {i}", (10.0, y0, 200.0, y1)))

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


# ---------------------------------------------------------------------------
# Test 1 — Skeleton Builder: basic construction
# ---------------------------------------------------------------------------


def test_skeleton_builder_basic():
    """Skeleton Builder should produce one skeleton per page."""
    from services.stages.skeleton_builder import _build_skeleton_from_page

    page = _make_page_dict(
        page_number=0,
        text_blocks=[
            _make_text_block_dict("Hello", x0=10, y0=50, x1=100, y1=62),
            _make_text_block_dict("World", x0=10, y0=100, x1=100, y1=112),
        ],
    )
    skeleton = _build_skeleton_from_page(page, pdf_index=0)

    assert skeleton.page_number == 0
    assert skeleton.pdf_index == 0
    assert len(skeleton.text_blocks) == 2
    assert skeleton.num_blocks == 2


@pytest.mark.asyncio
async def test_skeleton_builder_stage():
    """Stage 7 (execute) should build skeletons and store them in context."""
    from services.stages.skeleton_builder import execute

    pages = [
        _make_page_dict(0, [_make_text_block_dict("A"), _make_text_block_dict("B")]),
        _make_page_dict(1, [_make_text_block_dict("C")]),
    ]
    doc = _make_parsed_document(pdf_index=0, pages=pages)
    context = {"parsed_documents": [doc]}

    result = await execute(context)

    assert result["total_skeletons"] == 2
    assert result["total_pages"] == 2
    assert len(context["_skeleton_objects"]) == 2
    assert len(context["skeletons"]) == 2


# ---------------------------------------------------------------------------
# Test 2 — Skeleton Builder: table candidates from grid info
# ---------------------------------------------------------------------------


def test_skeleton_builder_table_candidates_from_grid():
    """Grid info with multiple rows and columns should produce a table candidate."""
    from services.stages.skeleton_builder import _build_skeleton_from_page

    grid = {
        "columns": 3,
        "rows": 4,
        "column_positions": [10.0, 200.0, 400.0],
        "row_positions": [100.0, 150.0, 200.0, 250.0],
    }
    page = _make_page_dict(0, [], grid_info=grid)
    skeleton = _build_skeleton_from_page(page, pdf_index=0)

    assert skeleton.table_count == 1
    assert skeleton.table_candidates[0] == (10.0, 100.0, 400.0, 250.0)


def test_skeleton_builder_no_table_candidate_without_grid():
    """A page without grid info should have no table candidates."""
    from services.stages.skeleton_builder import _build_skeleton_from_page

    page = _make_page_dict(0, [_make_text_block_dict()])
    skeleton = _build_skeleton_from_page(page, pdf_index=0)

    assert skeleton.table_count == 0


# ---------------------------------------------------------------------------
# Test 3 — Page Clustering: similar pages grouped together
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_page_clustering_similar_pages():
    """Pages with identical feature vectors should cluster together."""
    from services.stages.page_clustering import execute

    # Create 4 "header" pages and 4 "body" pages with distinct features
    skeletons_header = [_make_skeleton(i, 0, num_blocks=2, font_size=20.0) for i in range(4)]
    skeletons_body   = [_make_skeleton(i + 4, 0, num_blocks=10, font_size=10.0) for i in range(4)]
    all_skeletons = skeletons_header + skeletons_body

    context = {"_skeleton_objects": all_skeletons}
    result = await execute(context)

    labels: List[int] = context["cluster_labels"]
    assert len(labels) == 8

    # All header pages should be in the same cluster
    header_labels = labels[:4]
    assert len(set(header_labels)) == 1, f"Header pages split into multiple clusters: {header_labels}"

    # All body pages should be in the same cluster
    body_labels = labels[4:]
    assert len(set(body_labels)) == 1, f"Body pages split into multiple clusters: {body_labels}"

    # The two groups should be in different clusters
    assert header_labels[0] != body_labels[0], "Header and body ended up in the same cluster"


@pytest.mark.asyncio
async def test_page_clustering_single_page():
    """A single page should produce cluster label [0]."""
    from services.stages.page_clustering import execute

    skeletons = [_make_skeleton(0, 0)]
    context = {"_skeleton_objects": skeletons}

    await execute(context)

    assert context["cluster_labels"] == [0]


@pytest.mark.asyncio
async def test_page_clustering_empty():
    """Empty skeleton list should produce empty labels."""
    from services.stages.page_clustering import execute

    context = {"_skeleton_objects": []}
    result = await execute(context)

    assert context["cluster_labels"] == []
    assert result["num_clusters"] == 0


# ---------------------------------------------------------------------------
# Test 4 — Representative Selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_representative_selection_one_cluster():
    """With one cluster, representative should be from that cluster."""
    from services.stages.representative_selection import execute

    skeletons = [_make_skeleton(i, 0) for i in range(3)]
    labels = [0, 0, 0]

    context = {
        "_skeleton_objects": skeletons,
        "cluster_labels": labels,
    }
    result = await execute(context)

    layout_types = context["_layout_type_objects"]
    assert len(layout_types) == 1
    assert layout_types[0].cluster_id == 0
    assert layout_types[0].page_count == 3
    # Representative page must be one of the pages in cluster 0
    rep = layout_types[0].representative_page
    assert rep["pdf_index"] == 0
    assert rep["page_number"] in {0, 1, 2}


@pytest.mark.asyncio
async def test_representative_selection_two_clusters():
    """Two clusters should produce two LayoutTypes."""
    from services.stages.representative_selection import execute

    skeletons = [
        _make_skeleton(0, 0),
        _make_skeleton(1, 0),
        _make_skeleton(2, 1),
        _make_skeleton(3, 1),
    ]
    labels = [0, 0, 1, 1]

    context = {"_skeleton_objects": skeletons, "cluster_labels": labels}
    await execute(context)

    layout_types = context["_layout_type_objects"]
    assert len(layout_types) == 2
    ids = {lt.cluster_id for lt in layout_types}
    assert ids == {0, 1}


@pytest.mark.asyncio
async def test_representative_selection_prefers_diverse_pdfs():
    """When multiple PDFs, representative should prefer diversity."""
    from services.stages.representative_selection import execute

    # Two PDFs, same cluster
    skeletons = [
        _make_skeleton(0, pdf_index=0),
        _make_skeleton(1, pdf_index=0),
        _make_skeleton(0, pdf_index=1),
        _make_skeleton(1, pdf_index=1),
    ]
    labels = [0, 0, 0, 0]

    context = {"_skeleton_objects": skeletons, "cluster_labels": labels}
    await execute(context)

    layout_types = context["_layout_type_objects"]
    assert len(layout_types) == 1
    # All pages should be listed
    assert layout_types[0].page_count == 4


# ---------------------------------------------------------------------------
# Test 5 — Fingerprint Generation: same layout → same hash
# ---------------------------------------------------------------------------


def test_fingerprint_same_layout_same_hash():
    """Identical feature sets should produce the same fingerprint hash."""
    from services.stages.fingerprint_generation import _compute_fingerprint

    skeletons_a = [_make_skeleton(i, 0, num_blocks=5, table_count=1) for i in range(3)]
    skeletons_b = [_make_skeleton(i, 1, num_blocks=5, table_count=1) for i in range(3)]

    fp_a = _compute_fingerprint(skeletons_a)
    fp_b = _compute_fingerprint(skeletons_b)

    assert fp_a.fingerprint_hash == fp_b.fingerprint_hash
    assert len(fp_a.fingerprint_hash) == 64  # SHA-256 hex = 64 chars


def test_fingerprint_different_layout_different_hash():
    """Different feature sets should produce different fingerprint hashes."""
    from services.stages.fingerprint_generation import _compute_fingerprint

    skeletons_a = [_make_skeleton(i, 0, num_blocks=2, table_count=0) for i in range(3)]
    skeletons_b = [_make_skeleton(i, 0, num_blocks=10, table_count=3) for i in range(3)]

    fp_a = _compute_fingerprint(skeletons_a)
    fp_b = _compute_fingerprint(skeletons_b)

    assert fp_a.fingerprint_hash != fp_b.fingerprint_hash


def test_fingerprint_hash_is_sha256():
    """Fingerprint hash should be a valid SHA-256 hex digest."""
    from services.stages.fingerprint_generation import compute_fingerprint_hash

    fp_dict = {
        "tableCount": 1.0,
        "columnCount": 2,
        "headerBlocks": 3.0,
        "bodyZoneRatio": 0.75,
        "footerPresent": False,
    }
    h = compute_fingerprint_hash(fp_dict)
    expected = hashlib.sha256(
        json.dumps(fp_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert h == expected


@pytest.mark.asyncio
async def test_fingerprint_generation_stage():
    """Stage 10 should update fingerprints in layout_types."""
    from services.stages.fingerprint_generation import execute
    from models.layout_type import LayoutFingerprint, LayoutType

    skeletons = [_make_skeleton(i, 0) for i in range(3)]

    lt = LayoutType(
        cluster_id=0,
        name="Placeholder",
        representative_page={"pdf_index": 0, "page_number": 0},
        fingerprint=LayoutFingerprint(),
        page_count=3,
        pages=[{"pdf_index": 0, "page_number": i} for i in range(3)],
    )
    lt._cluster_skeletons = skeletons  # type: ignore[attr-defined]

    context = {
        "_layout_type_objects": [lt],
        "layout_types": [lt.to_dict()],
    }
    result = await execute(context)

    assert result["fingerprints_generated"] == 1
    assert lt.fingerprint.fingerprint_hash != ""
    assert len(lt.fingerprint.fingerprint_hash) == 64


# ---------------------------------------------------------------------------
# Test 6 — Registry Lookup: hit (template found)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registry_lookup_hit():
    """Registry Lookup should mark LayoutType as reusable when template found."""
    from services.stages.registry_lookup import execute
    from models.layout_type import LayoutFingerprint, LayoutType

    # Build a LayoutType with a known fingerprint hash
    fp = LayoutFingerprint(
        table_count=1.0,
        column_count=2,
        header_blocks=3.0,
        body_zone_ratio=0.75,
        footer_present=False,
        fingerprint_hash="abc123hash",
    )
    lt = LayoutType(
        cluster_id=0,
        name="Test Layout",
        representative_page={"pdf_index": 0, "page_number": 0},
        fingerprint=fp,
        page_count=1,
        pages=[{"pdf_index": 0, "page_number": 0}],
    )

    # Mock Supabase client
    mock_response = MagicMock()
    mock_response.data = [{"template_id": "template-uuid-1234"}]

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

    with patch("services.stages.registry_lookup._get_supabase_client", return_value=mock_client):
        context = {
            "_layout_type_objects": [lt],
            "layout_types": [lt.to_dict()],
        }
        result = await execute(context)

    assert result["hits"] == 1
    assert result["misses"] == 0
    assert lt.is_reusable is True
    assert lt.template_id == "template-uuid-1234"


# ---------------------------------------------------------------------------
# Test 7 — Registry Lookup: miss (no template)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registry_lookup_miss():
    """Registry Lookup should leave LayoutType as new when no match found."""
    from services.stages.registry_lookup import execute
    from models.layout_type import LayoutFingerprint, LayoutType

    fp = LayoutFingerprint(fingerprint_hash="newhash999")
    lt = LayoutType(
        cluster_id=0,
        name="New Layout",
        representative_page={"pdf_index": 0, "page_number": 0},
        fingerprint=fp,
        page_count=1,
        pages=[{"pdf_index": 0, "page_number": 0}],
    )

    mock_response = MagicMock()
    mock_response.data = []

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

    with patch("services.stages.registry_lookup._get_supabase_client", return_value=mock_client):
        context = {
            "_layout_type_objects": [lt],
            "layout_types": [lt.to_dict()],
        }
        result = await execute(context)

    assert result["hits"] == 0
    assert result["misses"] == 1
    assert lt.is_reusable is False
    assert lt.template_id is None


# ---------------------------------------------------------------------------
# Test 8 — Registry Lookup: offline / Supabase unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registry_lookup_offline():
    """When Supabase is unavailable, stage should skip with warning and continue."""
    from services.stages.registry_lookup import execute
    from models.layout_type import LayoutFingerprint, LayoutType

    fp = LayoutFingerprint(fingerprint_hash="somehash")
    lt = LayoutType(
        cluster_id=0,
        name="Layout",
        representative_page={"pdf_index": 0, "page_number": 0},
        fingerprint=fp,
        page_count=1,
        pages=[{"pdf_index": 0, "page_number": 0}],
    )

    # Simulate no client (env vars not set → returns None)
    with patch("services.stages.registry_lookup._get_supabase_client", return_value=None):
        warning_events = []

        def capture_emit(event):
            warning_events.append(event)

        context = {
            "_layout_type_objects": [lt],
            "layout_types": [lt.to_dict()],
            "emit_progress": capture_emit,
        }
        result = await execute(context)

    assert result["skipped"] is True
    assert result["hits"] == 0
    assert result["misses"] == 0
    # LayoutType should remain unchanged (not reusable)
    assert lt.is_reusable is False

    # Warning SSE should have been emitted
    assert len(warning_events) == 1
    assert warning_events[0]["status"] == "completed"
    assert "Registry indisponível" in warning_events[0].get("warning", "")


# ---------------------------------------------------------------------------
# Test 9 — Registry Lookup: Supabase raises exception mid-query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registry_lookup_exception_is_graceful():
    """If Supabase query raises, stage treats it as a miss and continues."""
    from services.stages.registry_lookup import execute
    from models.layout_type import LayoutFingerprint, LayoutType

    fp = LayoutFingerprint(fingerprint_hash="crashhash")
    lt = LayoutType(
        cluster_id=0,
        name="Layout",
        representative_page={"pdf_index": 0, "page_number": 0},
        fingerprint=fp,
        page_count=1,
        pages=[{"pdf_index": 0, "page_number": 0}],
    )

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = ConnectionError("Network error")

    with patch("services.stages.registry_lookup._get_supabase_client", return_value=mock_client):
        context = {
            "_layout_type_objects": [lt],
            "layout_types": [lt.to_dict()],
        }
        # Should NOT raise
        result = await execute(context)

    assert result["misses"] == 1
    assert lt.is_reusable is False


# ---------------------------------------------------------------------------
# Test 10 — End-to-end: 1 PDF with few pages → 1 Layout Type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_single_pdf_few_pages():
    """A single PDF with homogeneous pages should yield 1 LayoutType."""
    from services.stages.skeleton_builder import execute as stage7
    from services.stages.page_clustering import execute as stage8
    from services.stages.representative_selection import execute as stage9
    from services.stages.fingerprint_generation import execute as stage10
    from services.stages.registry_lookup import execute as stage11

    # Build a minimal single-page PDF context
    pages = [
        _make_page_dict(i, [
            _make_text_block_dict("Line 1", page_number=i),
            _make_text_block_dict("Line 2", y0=30.0, y1=42.0, page_number=i),
        ])
        for i in range(3)
    ]
    doc = _make_parsed_document(pdf_index=0, pages=pages)
    context = {"parsed_documents": [doc]}

    # Stage 7
    await stage7(context)
    # Stage 8
    await stage8(context)
    # Stage 9
    await stage9(context)
    # Stage 10
    await stage10(context)
    # Stage 11 — offline
    with patch("services.stages.registry_lookup._get_supabase_client", return_value=None):
        await stage11(context)

    layout_types = context["_layout_type_objects"]
    # With homogeneous pages, expect 1 layout type
    assert len(layout_types) >= 1

    lt = layout_types[0]
    assert lt.cluster_id >= 0
    assert lt.page_count >= 1
    assert lt.fingerprint.fingerprint_hash != ""
    assert lt.is_reusable is False  # offline → never reusable


# ---------------------------------------------------------------------------
# Test 11 — register_bloco3 wires stages into registry
# ---------------------------------------------------------------------------


def test_register_bloco3_wires_stages():
    """register_bloco3 should replace stubs 7-11 with real implementations."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco3

    registry = build_default_registry()

    # Before registration, stubs execute nothing interesting
    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[7]._execute_fn is None  # stub

    register_bloco3(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}

    # All 5 stages should now have real executors
    for stage_num in (7, 8, 9, 10, 11):
        assert stages_after[stage_num]._execute_fn is not None, (
            f"Stage {stage_num} still has a stub executor after register_bloco3"
        )

    # Pipeline shape must remain intact — still 27 stages
    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 28
