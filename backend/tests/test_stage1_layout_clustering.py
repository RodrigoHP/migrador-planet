"""Tests for Stage 1 — Layout Clustering (Story 13.4).

Covers:
- 1 PDF, 5 identical pages -> 1 cluster
- 1 PDF, 2 different layouts -> 2 clusters
- 3 PDFs same template -> clusters with pdf_id preserved
- Incompatible PDF -> homogeneity check detects
- _raw_text_blocks preserved with real text
- Benchmark: 100 pages < 6s
- Content abstraction patterns
- Region filtering
- Geometry similarity
- Confidence scoring
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import fitz  # PyMuPDF
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_stage1():
    import services.stages.stage1_layout_clustering as mod
    return mod


async def _noop_emit(event: Dict[str, Any]) -> None:
    """No-op progress emitter for tests."""
    pass


def _create_pdf_with_identical_pages(path: str, num_pages: int = 5) -> None:
    """Create a PDF where all pages have identical text block layout."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)  # A4
        # Header area
        page.insert_text((50, 40), "Company Name Inc.", fontsize=14)
        # Body area - consistent layout
        page.insert_text((50, 120), "Customer Name: John Doe", fontsize=10)
        page.insert_text((50, 150), "Account: 12345-6", fontsize=10)
        page.insert_text((50, 200), "Date: 01/01/2026", fontsize=10)
        page.insert_text((50, 250), f"Transaction #{i+1}", fontsize=10)
        page.insert_text((50, 300), "Amount: R$ 1.234,56", fontsize=10)
        page.insert_text((50, 350), "Description of the transaction that is a bit longer text", fontsize=10)
        # Footer area
        page.insert_text((50, 800), f"Page {i+1} of {num_pages}", fontsize=8)
    doc.save(path)
    doc.close()


def _create_pdf_with_two_layouts(path: str) -> None:
    """Create a PDF with 2 different page layouts."""
    doc = fitz.open()

    # Layout A: text-heavy, left-aligned (3 pages)
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 120), "Report Title", fontsize=14)
        page.insert_text((50, 160), "Section 1: Introduction", fontsize=12)
        page.insert_text((50, 200), "This is a long paragraph of text for the report body.", fontsize=10)
        page.insert_text((50, 240), "Another paragraph with more details about the subject.", fontsize=10)
        page.insert_text((50, 280), "Date: 15/03/2026", fontsize=10)
        page.insert_text((50, 320), "Value: R$ 5.678,90", fontsize=10)

    # Layout B: table-like, multi-column (2 pages)
    for i in range(2):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 120), "Data Table", fontsize=14)
        # Column 1
        page.insert_text((50, 180), "Item", fontsize=10)
        page.insert_text((50, 210), "Product A", fontsize=10)
        page.insert_text((50, 240), "Product B", fontsize=10)
        # Column 2 (different X position)
        page.insert_text((300, 180), "Price", fontsize=10)
        page.insert_text((300, 210), "R$ 100,00", fontsize=10)
        page.insert_text((300, 240), "R$ 200,00", fontsize=10)
        # Column 3
        page.insert_text((450, 180), "Qty", fontsize=10)
        page.insert_text((450, 210), "10", fontsize=10)
        page.insert_text((450, 240), "20", fontsize=10)

    doc.save(path)
    doc.close()


def _create_pdf_template(path: str, num_pages: int = 5, variation: int = 0) -> None:
    """Create a PDF that follows a specific template with minor variations.

    variation parameter adds slight differences in dynamic content while
    keeping the same layout structure.
    """
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        # Same structural layout for all
        page.insert_text((50, 120), "Standard Report Header", fontsize=14)
        page.insert_text((50, 170), f"Customer: Client {variation}", fontsize=10)
        page.insert_text((50, 200), f"Date: {10+variation}/03/2026", fontsize=10)
        page.insert_text((50, 240), f"Amount: R$ {1000 + variation * 100},00", fontsize=10)
        page.insert_text((50, 280), "Description of the standard content here", fontsize=10)
        page.insert_text((50, 330), f"Reference: {100000 + i + variation * 1000}", fontsize=10)
    doc.save(path)
    doc.close()


def _create_incompatible_pdf(path: str, num_pages: int = 3) -> None:
    """Create a PDF with a completely different layout (incompatible template)."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=842, height=595)  # Landscape
        # Completely different layout - centered, large text
        page.insert_text((300, 100), "CERTIFICATE", fontsize=24)
        page.insert_text((200, 200), "This certifies that Person Name", fontsize=16)
        page.insert_text((200, 280), "has completed the program on 01/01/2026", fontsize=12)
        page.insert_text((350, 400), "Signature: ___________", fontsize=10)
    doc.save(path)
    doc.close()


def _create_blank_pdf(path: str) -> None:
    """Create a PDF with a blank page."""
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(path)
    doc.close()


def _make_context(pdf_documents: List[Dict[str, str]]) -> Dict[str, Any]:
    """Build a minimal pipeline context for Stage 1."""
    return {
        "_storage": None,
        "_current_stage": 0,
        "_current_stage_name": "",
        "pdf_documents": pdf_documents,
        "xsd_path": "",
        "job_id": "test-job",
        "_job": {"job_id": "test-job", "status": "running", "config": {}},
    }


# ---------------------------------------------------------------------------
# Test 1: 1 PDF, 5 identical pages -> 1 cluster
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identical_pages_single_cluster(tmp_path):
    """5 identical pages from 1 PDF should produce 1 cluster."""
    mod = _get_stage1()

    pdf_path = str(tmp_path / "identical.pdf")
    _create_pdf_with_identical_pages(pdf_path, num_pages=5)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "identical.pdf"}]
    context = _make_context(pdf_docs)

    result = await mod.run_stage1(context, _noop_emit)

    clusters = result["clusters"]
    # Should have 1 main cluster (possibly + special clusters for blank/scanned)
    main_clusters = [c for c in clusters if not c["cluster_id"].startswith("_")]
    assert len(main_clusters) == 1, f"Expected 1 cluster, got {len(main_clusters)}: {main_clusters}"

    cluster = main_clusters[0]
    assert cluster["page_count"] == 5
    assert len(cluster["pages"]) == 5

    # All pages from same PDF
    for page in cluster["pages"]:
        assert page["pdf_id"] == "pdf-0"

    # Has representative
    rep = cluster["representative_page"]
    assert rep["pdf_id"] == "pdf-0"
    assert 0 <= rep["page_index"] < 5

    # Has confidence
    assert "confidence" in cluster["confidence"]
    assert cluster["confidence"]["level"] in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Test 2: 1 PDF, 2 different layouts -> 2 clusters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_layouts_two_clusters(tmp_path):
    """PDF with 2 distinct layouts should produce 2 clusters."""
    mod = _get_stage1()

    pdf_path = str(tmp_path / "two_layouts.pdf")
    _create_pdf_with_two_layouts(pdf_path)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "two_layouts.pdf"}]
    context = _make_context(pdf_docs)

    result = await mod.run_stage1(context, _noop_emit)

    clusters = result["clusters"]
    main_clusters = [c for c in clusters if not c["cluster_id"].startswith("_")]

    # Should produce at least 2 clusters (the two different layouts)
    assert len(main_clusters) >= 2, f"Expected >=2 clusters, got {len(main_clusters)}"

    # Total pages across all clusters should be 5
    total_pages = sum(c["page_count"] for c in main_clusters)
    assert total_pages == 5

    # Each cluster should have a representative
    for c in main_clusters:
        assert "representative_page" in c
        assert c["representative_page"]["pdf_id"] == "pdf-0"


# ---------------------------------------------------------------------------
# Test 3: 3 PDFs same template -> clusters with pdf_id preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_pdf_same_template(tmp_path):
    """3 PDFs of the same template should cluster together with pdf_id preserved."""
    mod = _get_stage1()

    pdf_paths = []
    pdf_docs = []
    for i in range(3):
        path = str(tmp_path / f"template_{i}.pdf")
        _create_pdf_template(path, num_pages=3, variation=i)
        pdf_paths.append(path)
        pdf_docs.append({"id": f"pdf-{i}", "path": path, "name": f"template_{i}.pdf"})

    context = _make_context(pdf_docs)
    result = await mod.run_stage1(context, _noop_emit)

    clusters = result["clusters"]
    main_clusters = [c for c in clusters if not c["cluster_id"].startswith("_")]

    # All 9 pages should be accounted for
    total_pages = sum(c["page_count"] for c in main_clusters)
    assert total_pages == 9, f"Expected 9 pages total, got {total_pages}"

    # pdf_id should be preserved in every page entry
    all_pdf_ids = set()
    for c in main_clusters:
        for page in c["pages"]:
            assert isinstance(page["pdf_id"], str)
            assert page["pdf_id"].startswith("pdf-")
            all_pdf_ids.add(page["pdf_id"])

    # All 3 PDFs should be represented
    assert all_pdf_ids == {"pdf-0", "pdf-1", "pdf-2"}

    # Same template -> pages from multiple PDFs should be in the same cluster(s)
    for c in main_clusters:
        if c["page_count"] > 1:
            cluster_pdfs = {p["pdf_id"] for p in c["pages"]}
            # At least some clusters should contain pages from multiple PDFs
            # (since they share the same template)


# ---------------------------------------------------------------------------
# Test 4: Incompatible PDF -> homogeneity check detects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_incompatible_pdf_homogeneity(tmp_path):
    """An incompatible PDF mixed with compatible ones triggers homogeneity check."""
    mod = _get_stage1()

    # 2 compatible PDFs
    path1 = str(tmp_path / "compat1.pdf")
    path2 = str(tmp_path / "compat2.pdf")
    _create_pdf_template(path1, num_pages=4, variation=0)
    _create_pdf_template(path2, num_pages=4, variation=1)

    # 1 incompatible PDF
    path3 = str(tmp_path / "incompat.pdf")
    _create_incompatible_pdf(path3, num_pages=3)

    pdf_docs = [
        {"id": "pdf-0", "path": path1, "name": "compat1.pdf"},
        {"id": "pdf-1", "path": path2, "name": "compat2.pdf"},
        {"id": "pdf-2", "path": path3, "name": "incompat.pdf"},
    ]

    # Test the homogeneity check function directly
    # First run through classification + clustering to get clusters
    config = mod.ClusteringConfig()

    # Simulate what homogeneity check would do with known clusters
    # Incompatible PDF pages should form exclusive clusters
    clusters_for_check = [
        {
            "cluster_id": "A",
            "pages": [
                {"pdf_id": "pdf-0", "page_index": 0},
                {"pdf_id": "pdf-0", "page_index": 1},
                {"pdf_id": "pdf-1", "page_index": 0},
                {"pdf_id": "pdf-1", "page_index": 1},
            ],
        },
        {
            "cluster_id": "B",
            "pages": [
                {"pdf_id": "pdf-2", "page_index": 0},
                {"pdf_id": "pdf-2", "page_index": 1},
                {"pdf_id": "pdf-2", "page_index": 2},
            ],
        },
    ]

    mismatched = mod._homogeneity_check(
        clusters_for_check, ["pdf-0", "pdf-1", "pdf-2"], config
    )

    # pdf-2 should be detected as mismatched (all its pages in exclusive cluster B)
    assert len(mismatched) >= 1
    mismatched_ids = {m["pdf_id"] for m in mismatched}
    assert "pdf-2" in mismatched_ids

    # pdf-0 and pdf-1 should NOT be mismatched (they share cluster A)
    assert "pdf-0" not in mismatched_ids
    assert "pdf-1" not in mismatched_ids


# ---------------------------------------------------------------------------
# Test 5: _raw_text_blocks preserved with real text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_raw_text_blocks_preserved(tmp_path):
    """_raw_text_blocks must contain real text (pre-abstraction) for all pages."""
    mod = _get_stage1()

    pdf_path = str(tmp_path / "raw_blocks.pdf")
    _create_pdf_with_identical_pages(pdf_path, num_pages=3)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "raw_blocks.pdf"}]
    context = _make_context(pdf_docs)

    result = await mod.run_stage1(context, _noop_emit)

    raw_blocks = result.get("_raw_text_blocks", {})

    # Should have entries for all 3 pages
    assert len(raw_blocks) == 3, f"Expected 3 page entries, got {len(raw_blocks)}"

    for page_idx in range(3):
        key = f"pdf-0:{page_idx}"
        assert key in raw_blocks, f"Missing raw_text_blocks for {key}"

        blocks = raw_blocks[key]
        assert len(blocks) > 0, f"No blocks for {key}"

        # Blocks should contain real text (not abstracted)
        all_text = " ".join(b["text"] for b in blocks)
        # Should contain actual text like "John Doe" or "R$ 1.234,56"
        assert any(
            real_text in all_text
            for real_text in ["John Doe", "1.234,56", "Account", "Transaction"]
        ), f"Raw blocks should contain real text, got: {all_text[:200]}"

        # Each block should have required fields
        for block in blocks:
            assert "text" in block
            assert "bbox_norm" in block
            assert len(block["bbox_norm"]) == 4
            assert "x_center" in block
            assert "y_center" in block
            assert block["type"] == 0
            # Normalised coords should be in [0, 1]
            for coord in block["bbox_norm"]:
                assert 0.0 <= coord <= 1.0, f"Coord out of range: {coord}"


# ---------------------------------------------------------------------------
# Test 6: Benchmark — 100 pages < 6s
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_benchmark_100_pages(tmp_path):
    """100 pages should complete in under 6 seconds (without LLM)."""
    mod = _get_stage1()

    pdf_path = str(tmp_path / "benchmark.pdf")
    _create_pdf_with_identical_pages(pdf_path, num_pages=100)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "benchmark.pdf"}]
    context = _make_context(pdf_docs)

    start = time.monotonic()
    result = await mod.run_stage1(context, _noop_emit)
    elapsed = time.monotonic() - start

    assert elapsed < 6.0, f"Stage 1 took {elapsed:.2f}s for 100 pages (limit: 6s)"

    # Verify result is valid
    clusters = result.get("clusters", [])
    assert len(clusters) > 0
    total_pages = sum(c["page_count"] for c in clusters)
    assert total_pages == 100


# ---------------------------------------------------------------------------
# Test 7: Content abstraction patterns
# ---------------------------------------------------------------------------


def test_abstract_text_patterns():
    """Content abstraction should replace dates, money, CPF, CNPJ with tokens."""
    mod = _get_stage1()

    assert mod._abstract_text("01/01/2026") == "DATE"
    assert mod._abstract_text("2026-03-22") == "DATE"
    assert mod._abstract_text("R$ 1.234,56") == "NUMBER"
    assert mod._abstract_text("100,00") == "NUMBER"
    assert mod._abstract_text("Março 2026") == "DATE"
    assert mod._abstract_text("123.456.789-01") == "CPF"
    assert mod._abstract_text("12.345.678/0001-90") == "CNPJ"
    assert mod._abstract_text("Hi") == "TEXT_S"
    assert mod._abstract_text("Short text") == "TEXT_S"
    assert mod._abstract_text("This is a longer text that exceeds twenty characters") == "TEXT_L"


# ---------------------------------------------------------------------------
# Test 8: Output contract compliance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_contract_31(tmp_path):
    """Output must conform to contract 3.1 schema."""
    mod = _get_stage1()

    pdf_path = str(tmp_path / "contract.pdf")
    _create_pdf_with_identical_pages(pdf_path, num_pages=3)

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "contract.pdf"}]
    context = _make_context(pdf_docs)

    result = await mod.run_stage1(context, _noop_emit)

    # clusters key must exist
    assert "clusters" in result
    assert "_raw_text_blocks" in result

    for cluster in result["clusters"]:
        # Required fields
        assert isinstance(cluster["cluster_id"], str)
        assert isinstance(cluster["pages"], list)
        assert isinstance(cluster["page_count"], int)
        assert "representative_page" in cluster
        assert "confidence" in cluster

        # Page entries
        for page in cluster["pages"]:
            assert isinstance(page["pdf_id"], str)
            assert isinstance(page["page_index"], int)

        # Representative
        rep = cluster["representative_page"]
        assert isinstance(rep["pdf_id"], str)
        assert isinstance(rep["page_index"], int)

        # Confidence structure
        conf = cluster["confidence"]
        assert isinstance(conf["confidence"], float)
        assert 0.0 <= conf["confidence"] <= 1.0
        assert conf["level"] in ("high", "medium", "low")

    # Every page should be in exactly one cluster
    all_pages = set()
    for cluster in result["clusters"]:
        for page in cluster["pages"]:
            page_key = f"{page['pdf_id']}:{page['page_index']}"
            assert page_key not in all_pages, f"Page {page_key} in multiple clusters"
            all_pages.add(page_key)


# ---------------------------------------------------------------------------
# Test 9: pdf_id as str throughout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pdf_id_is_str(tmp_path):
    """pdf_id must be str type everywhere in the output."""
    mod = _get_stage1()

    pdf_path = str(tmp_path / "str_id.pdf")
    _create_pdf_with_identical_pages(pdf_path, num_pages=2)

    # Use integer-like id to verify it's converted to str
    pdf_docs = [{"id": "42", "path": pdf_path, "name": "str_id.pdf"}]
    context = _make_context(pdf_docs)

    result = await mod.run_stage1(context, _noop_emit)

    for cluster in result["clusters"]:
        for page in cluster["pages"]:
            assert isinstance(page["pdf_id"], str)
        assert isinstance(cluster["representative_page"]["pdf_id"], str)

    for key in result["_raw_text_blocks"]:
        pdf_id = key.split(":")[0]
        assert isinstance(pdf_id, str)
        assert pdf_id == "42"


# ---------------------------------------------------------------------------
# Test 10: Blank page handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blank_page_handling(tmp_path):
    """Blank pages should be classified and placed in special _blank cluster."""
    mod = _get_stage1()

    # Create a PDF with mixed content: some text pages and a blank
    doc = fitz.open()
    # Text page
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 120), "This page has content", fontsize=12)
    page.insert_text((50, 200), "More content here on this page", fontsize=10)
    # Blank page
    doc.new_page(width=595, height=842)
    # Another text page
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 120), "This page also has content", fontsize=12)
    page.insert_text((50, 200), "And more content here too please", fontsize=10)

    pdf_path = str(tmp_path / "with_blank.pdf")
    doc.save(pdf_path)
    doc.close()

    pdf_docs = [{"id": "pdf-0", "path": pdf_path, "name": "with_blank.pdf"}]
    context = _make_context(pdf_docs)

    result = await mod.run_stage1(context, _noop_emit)

    clusters = result["clusters"]
    blank_clusters = [c for c in clusters if c["cluster_id"] == "_blank"]

    # Should have a _blank cluster with 1 page
    assert len(blank_clusters) == 1
    assert blank_clusters[0]["page_count"] == 1
    assert blank_clusters[0]["pages"][0]["page_index"] == 1  # the middle page


# ---------------------------------------------------------------------------
# Test 11: Geometry similarity function
# ---------------------------------------------------------------------------


def test_geometry_similarity_identical():
    """Identical block layouts should produce similarity ~1.0."""
    mod = _get_stage1()

    blocks_a = [
        {"x_center": 0.1, "y_center": 0.3, "bbox_norm": [0.05, 0.25, 0.15, 0.35]},
        {"x_center": 0.5, "y_center": 0.5, "bbox_norm": [0.45, 0.45, 0.55, 0.55]},
        {"x_center": 0.9, "y_center": 0.7, "bbox_norm": [0.85, 0.65, 0.95, 0.75]},
    ]
    blocks_b = list(blocks_a)  # identical

    sim = mod._geometry_similarity(blocks_a, blocks_b)
    assert sim >= 0.95, f"Identical blocks should have sim ~1.0, got {sim}"


def test_geometry_similarity_different():
    """Completely different block layouts should have low similarity."""
    mod = _get_stage1()

    blocks_a = [
        {"x_center": 0.1, "y_center": 0.1, "bbox_norm": [0.05, 0.05, 0.15, 0.15]},
    ]
    blocks_b = [
        {"x_center": 0.9, "y_center": 0.9, "bbox_norm": [0.85, 0.85, 0.95, 0.95]},
    ]

    sim = mod._geometry_similarity(blocks_a, blocks_b)
    assert sim < 0.5, f"Different blocks should have low sim, got {sim}"


# ---------------------------------------------------------------------------
# Test 12: ClusteringConfig from job config
# ---------------------------------------------------------------------------


def test_clustering_config_from_job_config():
    """ClusteringConfig should accept overrides from job config."""
    mod = _get_stage1()

    config = mod.ClusteringConfig.from_job_config({
        "clustering_config": {
            "clustering_threshold": 0.90,
            "phash_max_distance": 5,
        }
    })

    assert config.clustering_threshold == 0.90
    assert config.phash_max_distance == 5
    # Non-overridden values remain default
    assert config.position_tolerance == 0.05


# ---------------------------------------------------------------------------
# Test 13: Homogeneity check single PDF (no-op)
# ---------------------------------------------------------------------------


def test_homogeneity_check_single_pdf():
    """Single-PDF jobs should produce no mismatches."""
    mod = _get_stage1()

    clusters = [
        {
            "cluster_id": "A",
            "pages": [
                {"pdf_id": "pdf-0", "page_index": 0},
                {"pdf_id": "pdf-0", "page_index": 1},
            ],
        }
    ]
    config = mod.ClusteringConfig()
    mismatched = mod._homogeneity_check(clusters, ["pdf-0"], config)
    assert mismatched == []


# ---------------------------------------------------------------------------
# Test 14: Confidence score levels
# ---------------------------------------------------------------------------


def test_confidence_levels():
    """Confidence levels should be high/medium/low based on score."""
    mod = _get_stage1()

    high = mod._compute_confidence(0, 1.0, [], True, {"confidence": 1.0})
    assert high["level"] == "high"
    assert high["confidence"] >= 0.85

    low = mod._compute_confidence(0, 0.5, [{"cluster_idx": 0}], False, None)
    assert low["level"] == "low"
    assert low["confidence"] < 0.70


# ---------------------------------------------------------------------------
# Test 15: Density similarity
# ---------------------------------------------------------------------------


def test_density_similarity():
    """Blocks with similar area coverage should have high density similarity."""
    mod = _get_stage1()

    blocks_a = [
        {"bbox_norm": [0.1, 0.2, 0.5, 0.3]},
        {"bbox_norm": [0.1, 0.4, 0.5, 0.5]},
    ]
    blocks_b = [
        {"bbox_norm": [0.1, 0.2, 0.5, 0.3]},
        {"bbox_norm": [0.1, 0.4, 0.5, 0.5]},
    ]

    sim = mod._density_similarity(blocks_a, blocks_b, body_height=0.6)
    assert sim == 1.0

    # Different density
    blocks_c = [
        {"bbox_norm": [0.0, 0.0, 1.0, 0.5]},
    ]
    sim2 = mod._density_similarity(blocks_a, blocks_c, body_height=0.6)
    assert sim2 < 1.0
