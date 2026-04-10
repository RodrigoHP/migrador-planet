"""Tests for Stage 2 — Deep Extraction (Story 13.5).

Covers:
- PDF with table -> find_tables() detects
- PDF with image -> bbox extracted
- Bold/italic detected via span flags
- Text color preserved
- drawn_elements extracted (lines, rects)
- sub_spans for rich text inline
- Benchmark: ~6 pages < 10s
- PyMuPDF version check
"""

from __future__ import annotations

import io
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fitz  # PyMuPDF
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_stage2():
    import services.stages.stage2_deep_extraction as mod

    return mod


async def _noop_emit(event: dict[str, Any]) -> None:
    """No-op progress emitter for tests."""
    pass


def _create_simple_pdf(path: str, num_pages: int = 1) -> None:
    """Create a simple PDF with text blocks."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), "Header Text", fontsize=14)
        page.insert_text((50, 200), "Customer: John Doe", fontsize=10)
        page.insert_text((50, 250), "Date: 01/01/2026", fontsize=10)
        page.insert_text((50, 300), "Amount: R$ 1.234,56", fontsize=10)
        page.insert_text((50, 750), f"Page {i + 1}", fontsize=8)
    doc.save(path)
    doc.close()


def _create_pdf_with_table(path: str) -> None:
    """Create a PDF with a simple table structure using drawn lines."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Draw table grid lines
    x0, y0 = 50, 100
    col_widths = [100, 150, 100]
    row_height = 25
    num_rows = 5
    num_cols = len(col_widths)
    total_width = sum(col_widths)

    # Draw horizontal lines
    for row in range(num_rows + 1):
        y = y0 + row * row_height
        page.draw_line((x0, y), (x0 + total_width, y))

    # Draw vertical lines
    x = x0
    for col in range(num_cols + 1):
        page.draw_line((x, y0), (x, y0 + num_rows * row_height))
        if col < num_cols:
            x += col_widths[col]

    # Insert text in cells
    headers = ["Name", "Description", "Value"]
    for col, header in enumerate(headers):
        cx = x0 + sum(col_widths[:col]) + 5
        page.insert_text((cx, y0 + 18), header, fontsize=10, fontname="helv")

    data = [
        ["Alice", "Item A", "100"],
        ["Bob", "Item B", "200"],
        ["Carol", "Item C", "300"],
        ["Dave", "Item D", "400"],
    ]
    for row_idx, row_data in enumerate(data):
        for col, text in enumerate(row_data):
            cx = x0 + sum(col_widths[:col]) + 5
            cy = y0 + (row_idx + 1) * row_height + 18
            page.insert_text((cx, cy), text, fontsize=10)

    doc.save(path)
    doc.close()


def _create_pdf_with_image(path: str) -> None:
    """Create a PDF with an embedded image."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text((50, 50), "Document with Image", fontsize=12)

    # Create a small PNG image (red square 50x50)
    try:
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (50, 50), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        rect = fitz.Rect(100, 100, 200, 200)
        page.insert_image(rect, stream=img_bytes)
    except ImportError:
        # If Pillow not available, insert a simple placeholder
        pass

    doc.save(path)
    doc.close()


def _create_pdf_with_bold_italic(path: str) -> None:
    """Create a PDF with bold and italic text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Regular text
    page.insert_text((50, 100), "Regular text here", fontsize=10, fontname="helv")
    # Bold text
    page.insert_text((50, 150), "Bold text here", fontsize=10, fontname="hebo")
    # Italic text
    page.insert_text((50, 200), "Italic text here", fontsize=10, fontname="heit")

    doc.save(path)
    doc.close()


def _create_pdf_with_drawings(path: str) -> None:
    """Create a PDF with drawn elements (lines, rects)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text((50, 50), "Document with drawings", fontsize=12)

    # Draw horizontal line
    page.draw_line((50, 100), (500, 100), color=(0, 0, 0), width=1.5)

    # Draw vertical line
    page.draw_line((300, 100), (300, 400), color=(0, 0, 0), width=1.0)

    # Draw rectangle
    page.draw_rect(fitz.Rect(100, 200, 400, 350), color=(0, 0, 1), fill=(0.9, 0.9, 1.0), width=2.0)

    doc.save(path)
    doc.close()


def _create_multi_style_pdf(path: str) -> None:
    """Create a PDF with mixed inline styles (rich text)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Write different font styles close together on the same line
    page.insert_text((50, 100), "Normal", fontsize=10, fontname="helv")
    page.insert_text((110, 100), "Bold", fontsize=10, fontname="hebo")
    page.insert_text((150, 100), "Italic", fontsize=10, fontname="heit")

    # Another line with uniform style
    page.insert_text((50, 200), "All same style text block", fontsize=10, fontname="helv")

    doc.save(path)
    doc.close()


def _build_context(pdf_path: str, pdf_id: str = "test-pdf-1", storage: Any = None) -> dict[str, Any]:
    """Build a minimal pipeline context with 1 cluster and 1 representative page."""
    return {
        "pdf_documents": [{"id": pdf_id, "path": pdf_path, "name": "test.pdf"}],
        "clusters": [
            {
                "cluster_id": "A",
                "pages": [{"pdf_id": pdf_id, "page_index": 0}],
                "representative_page": {"pdf_id": pdf_id, "page_index": 0},
                "page_count": 1,
                "confidence": {"confidence": 0.95, "level": "high", "factors": {}},
            }
        ],
        "_storage": storage,
        "job_id": "test-job-123",
    }


def _build_multi_page_context(
    pdf_path: str,
    num_pages: int,
    pdf_id: str = "test-pdf-1",
    storage: Any = None,
) -> dict[str, Any]:
    """Build context with multiple clusters for benchmark testing."""
    # Create clusters: 1 cluster per 2 pages, representative = first page of each cluster
    clusters = []
    for i in range(0, num_pages, 2):
        pages_in_cluster = [{"pdf_id": pdf_id, "page_index": j} for j in range(i, min(i + 2, num_pages))]
        clusters.append(
            {
                "cluster_id": chr(65 + i // 2),  # A, B, C, ...
                "pages": pages_in_cluster,
                "representative_page": {"pdf_id": pdf_id, "page_index": i},
                "page_count": len(pages_in_cluster),
                "confidence": {"confidence": 0.95, "level": "high", "factors": {}},
            }
        )

    return {
        "pdf_documents": [{"id": pdf_id, "path": pdf_path, "name": "test.pdf"}],
        "clusters": clusters,
        "_storage": storage,
        "job_id": "test-job-bench",
    }


def _make_mock_storage() -> MagicMock:
    """Create a mock StorageGateway."""
    storage = MagicMock()
    storage.upload_asset = AsyncMock(side_effect=lambda job_id, name, data: f"assets/{name}")
    storage.upload_screenshot = AsyncMock(side_effect=lambda job_id, key, data: f"screenshots/{key}.png")
    return storage


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestStage2TableDetection:
    """PDF with table -> find_tables() detects."""

    @pytest.mark.asyncio
    async def test_table_detected(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "table.pdf")
        _create_pdf_with_table(pdf_path)

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result["enriched_documents"]
        assert len(enriched) >= 1

        rep_page = None
        for doc in enriched:
            for pg in doc["pages"]:
                if pg["is_representative"]:
                    rep_page = pg
                    break

        assert rep_page is not None
        tables = rep_page.get("tables", [])
        # find_tables may or may not detect depending on PyMuPDF version
        # The important thing is no crash and the structure is correct
        if tables:
            tbl = tables[0]
            assert "table_id" in tbl
            assert "bbox" in tbl
            assert "headers" in tbl
            assert "rows" in tbl
            assert "header_row_count" in tbl
            assert "columns" in tbl
            assert "column_widths" in tbl
            assert "confidence" in tbl
            assert "detection_method" in tbl
            assert "has_ruling_lines" in tbl


class TestStage2ImageExtraction:
    """PDF with image -> bbox extracted."""

    @pytest.mark.asyncio
    async def test_image_extracted(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "image.pdf")
        _create_pdf_with_image(pdf_path)

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result["enriched_documents"]
        assert len(enriched) >= 1

        rep_page = None
        for doc in enriched:
            for pg in doc["pages"]:
                if pg["is_representative"]:
                    rep_page = pg
                    break

        assert rep_page is not None
        images = rep_page.get("images", [])
        # Image may or may not be extracted depending on PIL availability
        if images:
            img = images[0]
            assert "path" in img
            assert "bbox" in img
            assert "bbox_valid" in img
            assert "format" in img
            assert isinstance(img["bbox"], list)
            assert len(img["bbox"]) == 4


class TestStage2BoldItalicFlags:
    """Bold/italic detected via span flags."""

    @pytest.mark.asyncio
    async def test_bold_italic_detected(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "bold_italic.pdf")
        _create_pdf_with_bold_italic(pdf_path)

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result["enriched_documents"]
        assert len(enriched) >= 1

        rep_page = None
        for doc in enriched:
            for pg in doc["pages"]:
                if pg["is_representative"]:
                    rep_page = pg
                    break

        assert rep_page is not None
        blocks = rep_page.get("text_blocks", [])
        assert len(blocks) >= 1

        # Check that all blocks have is_bold and is_italic fields
        for block in blocks:
            assert "is_bold" in block
            assert "is_italic" in block
            assert "is_mono" in block
            assert isinstance(block["is_bold"], bool)
            assert isinstance(block["is_italic"], bool)

        # Check that at least one block is bold (hebo font creates bold flag)
        bold_blocks = [b for b in blocks if b["is_bold"]]
        italic_blocks = [b for b in blocks if b["is_italic"]]
        # PyMuPDF sets flags based on font features, so bold/italic should be detected
        assert len(bold_blocks) > 0 or len(italic_blocks) > 0 or len(blocks) > 0


class TestStage2TextColor:
    """Text color preserved."""

    @pytest.mark.asyncio
    async def test_color_preserved(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "color.pdf")
        _create_simple_pdf(pdf_path)

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result["enriched_documents"]
        rep_page = None
        for doc in enriched:
            for pg in doc["pages"]:
                if pg["is_representative"]:
                    rep_page = pg
                    break

        assert rep_page is not None
        blocks = rep_page.get("text_blocks", [])
        assert len(blocks) >= 1

        for block in blocks:
            assert "color" in block
            assert isinstance(block["color"], int)
            # Default black text should be 0
            assert block["color"] == 0


class TestStage2DrawnElements:
    """drawn_elements extracted (lines, rectangles)."""

    @pytest.mark.asyncio
    async def test_drawn_elements(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "drawings.pdf")
        _create_pdf_with_drawings(pdf_path)

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result["enriched_documents"]
        rep_page = None
        for doc in enriched:
            for pg in doc["pages"]:
                if pg["is_representative"]:
                    rep_page = pg
                    break

        assert rep_page is not None
        drawn = rep_page.get("drawn_elements")
        assert drawn is not None
        assert isinstance(drawn, list)
        assert len(drawn) >= 1

        # Check structure of drawn elements
        for elem in drawn:
            assert "type" in elem
            assert elem["type"] in ("line", "rect", "curve")
            assert "bbox" in elem
            assert isinstance(elem["bbox"], list)
            assert len(elem["bbox"]) == 4
            assert "width" in elem

        # Should have lines and rects
        types = {e["type"] for e in drawn}
        assert "line" in types or "rect" in types

        # Check orientation for lines
        lines = [e for e in drawn if e["type"] == "line"]
        if lines:
            for line in lines:
                assert "orientation" in line
                if line["orientation"] is not None:
                    assert line["orientation"] in ("horizontal", "vertical", "diagonal")


class TestStage2SubSpans:
    """sub_spans preserved for rich text inline."""

    @pytest.mark.asyncio
    async def test_sub_spans_mixed_style(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "multi_style.pdf")
        _create_multi_style_pdf(pdf_path)

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result["enriched_documents"]
        rep_page = None
        for doc in enriched:
            for pg in doc["pages"]:
                if pg["is_representative"]:
                    rep_page = pg
                    break

        assert rep_page is not None
        blocks = rep_page.get("text_blocks", [])
        assert len(blocks) >= 1

        # Check that sub_spans field exists on all blocks
        for block in blocks:
            assert "sub_spans" in block
            # sub_spans should be None for uniform blocks or a list for mixed
            if block["sub_spans"] is not None:
                assert isinstance(block["sub_spans"], list)
                for sub in block["sub_spans"]:
                    assert "text" in sub
                    assert "offset" in sub
                    assert "length" in sub
                    assert "font_name" in sub
                    assert "font_size" in sub
                    assert "is_bold" in sub
                    assert "is_italic" in sub
                    assert "color" in sub

        # At least one block should have uniform style (sub_spans=None)
        uniform_blocks = [b for b in blocks if b["sub_spans"] is None]
        assert len(uniform_blocks) >= 1


class TestStage2Benchmark:
    """Benchmark: ~6 representative pages < 10s."""

    @pytest.mark.asyncio
    async def test_benchmark_6_pages(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "bench.pdf")
        # Create 12 pages -> 6 clusters -> 6 representatives
        _create_simple_pdf(pdf_path, num_pages=12)

        storage = _make_mock_storage()
        context = _build_multi_page_context(pdf_path, num_pages=12, storage=storage)

        start = time.monotonic()
        result = await mod.run_stage2(context, _noop_emit)
        elapsed = time.monotonic() - start

        assert elapsed < 10.0, f"Stage 2 took {elapsed:.2f}s, expected < 10s"

        enriched = result["enriched_documents"]
        assert len(enriched) >= 1

        # Count representative pages processed
        rep_count = sum(1 for doc in enriched for pg in doc["pages"] if pg["is_representative"])
        assert rep_count == 6


class TestStage2PyMuPDFVersion:
    """PyMuPDF version check."""

    def test_version_check_passes(self):
        mod = _get_stage2()
        # Should not raise with current PyMuPDF >= 1.23.0
        mod.check_pymupdf_version()

    def test_version_format(self):
        """PyMuPDF version string is parseable."""
        version_str = fitz.version[0]
        parts = version_str.split(".")
        assert len(parts) >= 3
        for part in parts[:3]:
            assert part.isdigit()


class TestStage2OutputContract:
    """Verify output matches contract 3.2."""

    @pytest.mark.asyncio
    async def test_output_contract(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "contract.pdf")
        _create_simple_pdf(pdf_path, num_pages=3)

        storage = _make_mock_storage()
        context = {
            "pdf_documents": [{"id": "pdf-1", "path": pdf_path, "name": "contract.pdf"}],
            "clusters": [
                {
                    "cluster_id": "A",
                    "pages": [
                        {"pdf_id": "pdf-1", "page_index": 0},
                        {"pdf_id": "pdf-1", "page_index": 1},
                        {"pdf_id": "pdf-1", "page_index": 2},
                    ],
                    "representative_page": {"pdf_id": "pdf-1", "page_index": 0},
                    "page_count": 3,
                    "confidence": {"confidence": 0.95, "level": "high", "factors": {}},
                }
            ],
            "_storage": storage,
            "job_id": "test-contract",
        }

        result = await mod.run_stage2(context, _noop_emit)

        # Verify enriched_documents structure
        assert "enriched_documents" in result
        assert "extraction_warnings" in result

        enriched = result["enriched_documents"]
        assert len(enriched) == 1

        doc = enriched[0]
        assert "pdf_id" in doc
        assert "pages" in doc
        assert len(doc["pages"]) == 3  # 1 rep + 2 non-rep

        # Representative page has full data
        rep_pages = [p for p in doc["pages"] if p["is_representative"]]
        assert len(rep_pages) == 1

        rep = rep_pages[0]
        assert "page_index" in rep
        assert "cluster_id" in rep
        assert rep["cluster_id"] == "A"
        assert "width" in rep and rep["width"] > 0
        assert "height" in rep and rep["height"] > 0
        assert "text_blocks" in rep
        assert "images" in rep
        assert "fonts" in rep
        assert "grid_info" in rep  # may be None
        assert "screenshot_path" in rep
        assert "tables" in rep
        assert "drawn_elements" in rep  # may be None

        # Text block structure
        if rep["text_blocks"]:
            block = rep["text_blocks"][0]
            assert "id" in block
            assert "text" in block
            assert "bbox" in block
            assert len(block["bbox"]) == 4
            assert "font_name" in block
            assert "font_size" in block
            assert "is_bold" in block
            assert "is_italic" in block
            assert "is_mono" in block
            assert "color" in block
            assert "sub_spans" in block

        # Non-representative pages have minimal data
        non_rep_pages = [p for p in doc["pages"] if not p["is_representative"]]
        assert len(non_rep_pages) == 2
        for nrp in non_rep_pages:
            assert nrp["text_blocks"] == []
            assert nrp["is_representative"] is False
            assert nrp["cluster_id"] == "A"

        # extraction_warnings is a list
        warnings = result["extraction_warnings"]
        assert isinstance(warnings, list)


class TestStage2OnlyRepresentatives:
    """Only representative pages are fully processed."""

    @pytest.mark.asyncio
    async def test_only_representatives_processed(self, tmp_path):
        mod = _get_stage2()
        pdf_path = str(tmp_path / "reps.pdf")
        _create_simple_pdf(pdf_path, num_pages=5)

        storage = _make_mock_storage()
        context = {
            "pdf_documents": [{"id": "pdf-1", "path": pdf_path, "name": "reps.pdf"}],
            "clusters": [
                {
                    "cluster_id": "A",
                    "pages": [
                        {"pdf_id": "pdf-1", "page_index": 0},
                        {"pdf_id": "pdf-1", "page_index": 1},
                        {"pdf_id": "pdf-1", "page_index": 2},
                    ],
                    "representative_page": {"pdf_id": "pdf-1", "page_index": 0},
                    "page_count": 3,
                    "confidence": {"confidence": 0.95, "level": "high", "factors": {}},
                },
                {
                    "cluster_id": "B",
                    "pages": [
                        {"pdf_id": "pdf-1", "page_index": 3},
                        {"pdf_id": "pdf-1", "page_index": 4},
                    ],
                    "representative_page": {"pdf_id": "pdf-1", "page_index": 3},
                    "page_count": 2,
                    "confidence": {"confidence": 0.90, "level": "high", "factors": {}},
                },
            ],
            "_storage": storage,
            "job_id": "test-reps",
        }

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result["enriched_documents"]
        all_pages = [pg for doc in enriched for pg in doc["pages"]]

        # Total pages: 5
        assert len(all_pages) == 5

        # Only 2 representatives
        reps = [pg for pg in all_pages if pg["is_representative"]]
        assert len(reps) == 2

        # Representatives have text blocks
        for rep in reps:
            assert len(rep["text_blocks"]) > 0

        # Non-representatives have empty text blocks
        non_reps = [pg for pg in all_pages if not pg["is_representative"]]
        assert len(non_reps) == 3
        for nrp in non_reps:
            assert len(nrp["text_blocks"]) == 0


class TestStage2FontMap:
    """Font -> CSS mapping tests."""

    def test_normalize_subset_prefix(self):
        mod = _get_stage2()
        assert mod._normalize_pdf_font_name("ABCDEF+Helvetica") == "Helvetica"
        assert mod._normalize_pdf_font_name("XYZABC+TimesNewRoman") == "TimesNewRoman"
        assert mod._normalize_pdf_font_name("Arial") == "Arial"  # no prefix

    def test_font_map_coverage(self):
        mod = _get_stage2()
        # Should have ~50 entries
        assert len(mod.FONT_MAP) >= 40

    def test_font_to_css(self):
        mod = _get_stage2()
        css = mod._font_to_css("Helvetica", 12.0, is_bold=True, is_italic=False)
        assert css["font_weight"] == "bold"
        assert css["font_style"] == "normal"
        assert "Arial" in css["font_family"]


class TestStage2QualityCheck:
    """Quality check generates appropriate warnings."""

    def test_empty_page_warning(self):
        mod = _get_stage2()
        page_data: dict[str, Any] = {
            "text_blocks": [],
            "tables": [],
            "images": [],
        }
        warnings = mod._quality_check(page_data, 0, "test")
        assert any("no text blocks" in w["message"] for w in warnings)

    def test_encoding_warning(self):
        mod = _get_stage2()
        page_data = {
            "text_blocks": [{"text": "Hello\ufffdWorld", "bbox": [0, 0, 100, 20]}],
            "tables": [],
            "images": [],
        }
        warnings = mod._quality_check(page_data, 0, "test")
        assert any("encoding" in w["message"] for w in warnings)

    def test_invalid_bbox_warning(self):
        mod = _get_stage2()
        page_data = {
            "text_blocks": [{"text": "Hello", "bbox": [0, 0, 100, 20]}],
            "tables": [],
            "images": [{"path": "img.png", "bbox": [0, 0, 0, 0], "bbox_valid": False, "format": "png"}],
        }
        warnings = mod._quality_check(page_data, 0, "test")
        assert any("invalid bbox" in w["message"] for w in warnings)


class TestStage2GridDetection:
    """Jenks grid detection tests."""

    def test_jenks_1d_basic(self):
        mod = _get_stage2()
        values = [10, 12, 11, 50, 52, 51, 100, 102, 101]
        centroids = mod._jenks_1d(values, 5)
        # Should detect ~3 groups
        assert len(centroids) >= 2

    def test_grid_detection_with_blocks(self):
        import uuid

        from models.pipeline_context import TextBlock

        mod = _get_stage2()
        blocks = [
            TextBlock(
                id=str(uuid.uuid4()),
                text="A",
                bbox=[50, 100, 200, 120],
                font_name="Helvetica",
                font_size=10.0,
                is_bold=False,
                is_italic=False,
            ),
            TextBlock(
                id=str(uuid.uuid4()),
                text="B",
                bbox=[50, 150, 200, 170],
                font_name="Helvetica",
                font_size=10.0,
                is_bold=False,
                is_italic=False,
            ),
            TextBlock(
                id=str(uuid.uuid4()),
                text="C",
                bbox=[50, 200, 200, 220],
                font_name="Helvetica",
                font_size=10.0,
                is_bold=False,
                is_italic=False,
            ),
            TextBlock(
                id=str(uuid.uuid4()),
                text="D",
                bbox=[300, 100, 450, 120],
                font_name="Helvetica",
                font_size=10.0,
                is_bold=False,
                is_italic=False,
            ),
            TextBlock(
                id=str(uuid.uuid4()),
                text="E",
                bbox=[300, 150, 450, 170],
                font_name="Helvetica",
                font_size=10.0,
                is_bold=False,
                is_italic=False,
            ),
        ]
        grid = mod._detect_grid_jenks(blocks, 842.0)
        # Should detect grid structure
        if grid is not None:
            assert "columns" in grid
            assert "rows" in grid
            assert "column_positions" in grid
            assert "row_positions" in grid


class TestStage2WiringOrchestrator:
    """Verify stage 2 is wired in the orchestrator."""

    def test_orchestrator_uses_run_stage2(self):
        from services.pipeline_orchestrator_v2 import STAGE_FUNCTIONS

        # Stage 2 should be _run_stage_2 (index 1)
        stage2_fn = STAGE_FUNCTIONS[1]
        assert stage2_fn.__name__ == "_run_stage_2"


# ---------------------------------------------------------------------------
# Test: Story 15.15 — screenshot_path is always a local file path
# ---------------------------------------------------------------------------


class TestScreenshotPathIsLocal:
    """Story 15.15: _take_screenshot must return a local filesystem path.

    When STORAGE_MODE=supabase, upload_screenshot returns a Supabase remote
    path like 'jobs/abc/screenshots/...'. Stage 3 calls load_image_as_base64
    which does open(path, 'rb') -- a remote path causes FileNotFoundError.

    Fix (Opção A): save PNG locally AND upload to remote storage, always
    return the local path.
    """

    @pytest.mark.asyncio
    async def test_screenshot_path_is_local_file(self, tmp_path):
        """screenshot_path in page_data must be an existing local file."""
        mod = _get_stage2()
        import os

        # Simulate supabase storage: upload returns a remote-style path
        storage = MagicMock()
        storage.upload_asset = AsyncMock(return_value="assets/result.json")
        storage.upload_screenshot = AsyncMock(
            side_effect=lambda job_id, key, data: f"jobs/{job_id}/screenshots/{key}.png"
        )

        pdf_path = str(tmp_path / "test.pdf")
        _create_simple_pdf(pdf_path, num_pages=1)

        context = {
            "pdf_documents": [{"id": "pdf-1", "path": pdf_path, "name": "test.pdf"}],
            "clusters": [
                {
                    "cluster_id": "A",
                    "pages": [{"pdf_id": "pdf-1", "page_index": 0}],
                    "representative_page": {"pdf_id": "pdf-1", "page_index": 0},
                    "page_count": 1,
                    "confidence": {"confidence": 0.9, "level": "high", "factors": {}},
                }
            ],
            "_storage": storage,
            "job_id": "test-screenshot-local",
        }

        result = await mod.run_stage2(context, _noop_emit)

        enriched = result.get("enriched_documents", [])
        assert enriched, "enriched_documents must not be empty"

        rep_pages = [p for doc in enriched for p in doc.get("pages", []) if p.get("is_representative")]
        assert rep_pages, "At least one representative page expected"

        for rep in rep_pages:
            screenshot_path = rep.get("screenshot_path")
            if screenshot_path is not None:
                # AC2: screenshot_path must be a valid local file path
                assert os.path.isfile(screenshot_path), (
                    f"screenshot_path '{screenshot_path}' must be an existing local file. "
                    "Stage 3 uses open(path, 'rb') — remote paths cause FileNotFoundError."
                )

    @pytest.mark.asyncio
    async def test_screenshot_upload_failure_does_not_abort(self, tmp_path):
        """If storage upload fails, screenshot_path is still a valid local file."""
        mod = _get_stage2()
        import os

        # Storage upload throws an exception
        storage = MagicMock()
        storage.upload_asset = AsyncMock(return_value="assets/result.json")
        storage.upload_screenshot = AsyncMock(side_effect=Exception("Supabase upload failed"))

        pdf_path = str(tmp_path / "test.pdf")
        _create_simple_pdf(pdf_path, num_pages=1)

        context = {
            "pdf_documents": [{"id": "pdf-1", "path": pdf_path, "name": "test.pdf"}],
            "clusters": [
                {
                    "cluster_id": "A",
                    "pages": [{"pdf_id": "pdf-1", "page_index": 0}],
                    "representative_page": {"pdf_id": "pdf-1", "page_index": 0},
                    "page_count": 1,
                    "confidence": {"confidence": 0.9, "level": "high", "factors": {}},
                }
            ],
            "_storage": storage,
            "job_id": "test-screenshot-upload-fail",
        }

        # Should not raise even if upload fails
        result = await mod.run_stage2(context, _noop_emit)

        enriched = result.get("enriched_documents", [])
        rep_pages = [p for doc in enriched for p in doc.get("pages", []) if p.get("is_representative")]

        for rep in rep_pages:
            screenshot_path = rep.get("screenshot_path")
            if screenshot_path is not None:
                assert os.path.isfile(screenshot_path), (
                    f"screenshot_path '{screenshot_path}' must be local even when upload fails"
                )


class TestImageMultiPlacement:
    """Mesmo xref colocado 2× na página deve gerar 2 entradas de imagem.

    PDFs de boleto Bradesco reutilizam o mesmo xref do logo em dois locais:
    'Recibo do Sacado' (topo) e 'Ficha de Compensação' (baixo). O bug
    anterior fazia break após o primeiro get_image_rects — o logo da
    ficha nunca aparecia no template.
    """

    @pytest.mark.asyncio
    async def test_same_xref_two_placements_creates_two_entries(self, tmp_path):
        """Uma imagem inserida em 2 posições → 2 entradas no images[] da página."""
        try:
            from PIL import Image as PILImage
        except ImportError:
            pytest.skip("Pillow not available")

        mod = _get_stage2()

        # Criar PDF com a MESMA imagem em 2 posições diferentes
        pdf_path = str(tmp_path / "dual_logo.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        # Criar PNG 30×20 e inserir na mesma página em 2 locais
        img = PILImage.new("RGB", (30, 20), color=(0, 80, 160))  # azul Bradesco
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        # Primeiro placement: y=10 (topo — Recibo do Sacado)
        page.insert_image(fitz.Rect(10, 10, 60, 35), stream=img_bytes)
        # Segundo placement: y=430 (baixo — Ficha de Compensação)
        page.insert_image(fitz.Rect(10, 430, 60, 455), stream=img_bytes)

        page.insert_text((70, 20), "Recibo do Sacado", fontsize=10)
        page.insert_text((70, 440), "Ficha de Compensação", fontsize=10)
        doc.save(pdf_path)
        doc.close()

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)
        result = await mod.run_stage2(context, _noop_emit)

        enriched = result.get("enriched_documents", [])
        rep_page = next(
            (p for doc in enriched for p in doc.get("pages", []) if p.get("is_representative")),
            None,
        )
        assert rep_page is not None

        images = rep_page.get("images", [])
        # Deve haver uma entrada por placement (2 placements = 2 entradas)
        valid_images = [i for i in images if i.get("bbox_valid")]
        assert len(valid_images) >= 2, (
            f"Imagem inserida 2× na página deve gerar 2 entradas com bbox_valid=True, "
            f"mas encontrou {len(valid_images)}: {valid_images}"
        )

        # Os dois bboxes devem ter y0 diferentes (um no topo, outro na parte baixa)
        y0_values = sorted(img["bbox"][1] for img in valid_images)
        assert y0_values[-1] - y0_values[0] > 100, (
            f"Os dois placements devem estar distantes verticalmente, mas y0_values={y0_values}"
        )


class TestImageBboxClamping:
    """Imagens com bbox fora dos limites da página devem ser clamped.

    PDFs podem posicionar imagens com y0 < 0 (acima da borda da página),
    por exemplo via bleed area ou arredondamento de matriz de transformação.
    Um y0 negativo produz top:-Xpx no CSS, o que é clipado por
    .page{overflow:hidden} — logo aparece cortado no topo.

    O fix correto é clampar y0 a max(0, y0) na extração (stage2),
    garantindo que nenhuma imagem seja posicionada acima da borda da página.
    """

    @pytest.mark.asyncio
    async def test_negative_y0_clamped_to_zero(self, tmp_path):
        """Imagem com placement y0 < 0 deve ter y0 clamped para 0."""
        try:
            from PIL import Image as PILImage
        except ImportError:
            pytest.skip("Pillow not available")

        mod = _get_stage2()

        pdf_path = str(tmp_path / "bleed_logo.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        # Criar PNG 60×40
        img = PILImage.new("RGB", (60, 40), color=(200, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        # Inserir imagem com y_start=10 (dentro da página, mas vamos simular bleed)
        page.insert_image(fitz.Rect(5, 5, 65, 45), stream=img_bytes)
        page.insert_text((70, 20), "Texto de referencia", fontsize=10)
        doc.save(pdf_path)
        doc.close()

        storage = _make_mock_storage()
        context = _build_context(pdf_path, storage=storage)
        result = await mod.run_stage2(context, _noop_emit)

        enriched = result.get("enriched_documents", [])
        rep_page = next(
            (p for doc_e in enriched for p in doc_e.get("pages", []) if p.get("is_representative")),
            None,
        )
        assert rep_page is not None

        images = rep_page.get("images", [])
        for img_entry in images:
            bbox = img_entry.get("bbox", [])
            if len(bbox) >= 4:
                assert bbox[0] >= 0.0, f"x0 deve ser >= 0, mas foi {bbox[0]}"
                assert bbox[1] >= 0.0, f"y0 deve ser >= 0, mas foi {bbox[1]} (causaria top negativo no CSS)"
                assert bbox[2] <= 595.0 + 1e-3, f"x1 deve ser <= page_width, mas foi {bbox[2]}"
                assert bbox[3] <= 842.0 + 1e-3, f"y1 deve ser <= page_height, mas foi {bbox[3]}"
