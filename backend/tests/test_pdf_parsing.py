"""Tests for Story 5.5 — Bloco 2: PDF Parsing.

Covers:
- Text reconstruction (span merging)
- Font normalisation
- Grid detection
- Encrypted PDF detection
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_text_block(
    text: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    page_number: int = 0,
    pdf_index: int = 0,
):
    from models.parsed_document import TextBlock

    return TextBlock(
        text=text,
        bbox=(x0, y0, x1, y1),
        font_name=font_name,
        font_size=font_size,
        page_number=page_number,
        pdf_index=pdf_index,
    )


# ---------------------------------------------------------------------------
# Test 1 — Text Reconstruction
# ---------------------------------------------------------------------------


def test_text_reconstruction_merges_fragments():
    """Fragmented spans on the same line with same font should merge."""
    from services.stages.text_reconstruction import _reconstruct_page_blocks

    # Simulate "Cl" + "iente" on the same Y position, adjacent X
    # Each char is ~6px wide, so "Cl" spans x=0..12, "iente" x=12..42
    blocks = [
        _make_text_block("Cl",     x0=0,  y0=100, x1=12, y1=112),
        _make_text_block("iente",  x0=12, y0=100, x1=42, y1=112),
    ]

    result = _reconstruct_page_blocks(blocks)

    assert len(result) == 1, f"Expected 1 merged block, got {len(result)}: {[b.text for b in result]}"
    assert result[0].text == "Cliente"


def test_text_reconstruction_keeps_separate_columns():
    """Blocks in different columns (large X gap) must NOT be merged."""
    from services.stages.text_reconstruction import _reconstruct_page_blocks

    blocks = [
        _make_text_block("Nome",    x0=0,   y0=50, x1=40,  y1=62),
        _make_text_block("Empresa", x0=300, y0=50, x1=356, y1=62),
    ]

    result = _reconstruct_page_blocks(blocks)

    assert len(result) == 2, f"Expected 2 separate blocks, got {len(result)}"


def test_text_reconstruction_different_lines():
    """Blocks on different Y lines must not be merged together."""
    from services.stages.text_reconstruction import _reconstruct_page_blocks

    blocks = [
        _make_text_block("Line1", x0=10, y0=0,  x1=50, y1=12),
        _make_text_block("Line2", x0=10, y0=20, x1=50, y1=32),
    ]

    result = _reconstruct_page_blocks(blocks)

    assert len(result) == 2


def test_text_reconstruction_currency_tokens():
    """R$ and amount separated by small gap should merge into one block."""
    from services.stages.text_reconstruction import _reconstruct_page_blocks

    # "R$" ends at x=24, "1.234,56" starts at x=28 — gap of 4px, avg char ~8px
    blocks = [
        _make_text_block("R$",       x0=0,  y0=80, x1=24, y1=92),
        _make_text_block("1.234,56", x0=28, y0=80, x1=88, y1=92),
    ]

    result = _reconstruct_page_blocks(blocks)

    assert len(result) == 1
    assert "R$" in result[0].text
    assert "1.234,56" in result[0].text


def test_text_reconstruction_font_mismatch_blocks_merge():
    """Blocks with different font families on same Y must NOT be merged (AC #3)."""
    from services.stages.text_reconstruction import _reconstruct_page_blocks

    # Arial "Nome" and Times "Empresa" on the same Y, small X gap — font differs
    blocks = [
        _make_text_block("Nome",    x0=0,  y0=50, x1=40, y1=62, font_name="Arial"),
        _make_text_block("Empresa", x0=42, y0=50, x1=98, y1=62, font_name="Times"),
    ]

    result = _reconstruct_page_blocks(blocks)

    assert len(result) == 2, (
        f"Expected 2 separate blocks (font mismatch), got {len(result)}: {[b.text for b in result]}"
    )


@pytest.mark.asyncio
async def test_text_reconstruction_executor_contract():
    """Stage 3 execute() must return blocks_before, blocks_after, merged and update context (AC #4)."""
    from services.stages.text_reconstruction import execute
    from models.parsed_document import ParsedDocument, ParsedPage, TextBlock

    # Build a minimal parsed_document with 2 fragments that will merge
    block1 = TextBlock(text="Cl",    bbox=(0, 100, 12, 112), font_name="Helvetica",
                       font_size=12.0, page_number=0, pdf_index=0)
    block2 = TextBlock(text="iente", bbox=(12, 100, 42, 112), font_name="Helvetica",
                       font_size=12.0, page_number=0, pdf_index=0)
    page = ParsedPage(page_number=0, text_blocks=[block1, block2])
    doc = ParsedDocument(job_id="job-test", pdf_index=0, pdf_name="test.pdf", pages=[page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc.to_context_dict()],
    }

    result = await execute(context)

    # Verify return contract (AC #4)
    assert "blocks_before" in result, "Missing blocks_before in result"
    assert "blocks_after" in result, "Missing blocks_after in result"
    assert "merged" in result, "Missing merged in result"
    assert result["blocks_before"] == 2
    assert result["blocks_after"] == 1
    assert result["merged"] == 1

    # Verify context was updated in-place (AC #4)
    updated_docs = context["parsed_documents"]
    assert len(updated_docs) == 1
    updated_blocks = updated_docs[0]["pages"][0]["text_blocks"]
    assert len(updated_blocks) == 1, "Expected 1 merged block in context"
    assert updated_blocks[0]["text"] == "Cliente", (
        f"Expected merged text 'Cliente', got '{updated_blocks[0]['text']}'"
    )


# ---------------------------------------------------------------------------
# Test 2 — Font Normalisation
# ---------------------------------------------------------------------------


def test_font_normalisation_helvetica_to_arial():
    from services.stages.font_extraction import normalise_font

    css = normalise_font("Helvetica", 12.0)
    assert css.font_family == "Arial"
    assert css.font_weight == "normal"
    assert css.font_style == "normal"


def test_font_normalisation_helvetica_bold():
    from services.stages.font_extraction import normalise_font

    css = normalise_font("Helvetica-Bold", 14.0)
    assert css.font_family == "Arial"
    assert css.font_weight == "bold"


def test_font_normalisation_times_roman():
    from services.stages.font_extraction import normalise_font

    css = normalise_font("Times-Roman", 10.0)
    assert css.font_family == "Times New Roman"
    assert css.font_style == "normal"


def test_font_normalisation_courier():
    from services.stages.font_extraction import normalise_font

    css = normalise_font("Courier", 12.0)
    assert css.font_family == "Courier New"


def test_font_normalisation_subset_prefix():
    """Fonts with subset prefix like 'ABCDEF+Helvetica' should still normalise."""
    from services.stages.font_extraction import normalise_font

    css = normalise_font("ABCDEF+Helvetica-Bold", 10.0)
    assert css.font_family == "Arial"
    assert css.font_weight == "bold"


def test_font_normalisation_unknown_font_passthrough():
    """Unknown fonts should be returned as-is (preserve document intent)."""
    from services.stages.font_extraction import normalise_font

    css = normalise_font("CustomBrandFont", 11.0)
    assert css.font_family == "CustomBrandFont"


# ---------------------------------------------------------------------------
# Test 3 — Grid Detection
# ---------------------------------------------------------------------------


def test_grid_detection_two_columns():
    """Two clusters of X coordinates → 2 columns."""
    from services.stages.grid_detection import detect_grid

    # Left column ~x=50, right column ~x=300
    blocks = [
        _make_text_block("A", x0=48,  y0=10, x1=100, y1=22),
        _make_text_block("B", x0=50,  y0=30, x1=102, y1=42),
        _make_text_block("C", x0=298, y0=10, x1=350, y1=22),
        _make_text_block("D", x0=302, y0=30, x1=354, y1=42),
        _make_text_block("E", x0=51,  y0=50, x1=103, y1=62),
        _make_text_block("F", x0=299, y0=50, x1=351, y1=62),
    ]

    grid = detect_grid(blocks)

    assert grid.columns == 2, f"Expected 2 columns, got {grid.columns}"
    assert len(grid.column_positions) == 2


def test_grid_detection_single_column():
    """All blocks in one column → 1 column."""
    from services.stages.grid_detection import detect_grid

    blocks = [
        _make_text_block("A", x0=50, y0=10, x1=200, y1=22),
        _make_text_block("B", x0=52, y0=30, x1=202, y1=42),
        _make_text_block("C", x0=49, y0=50, x1=201, y1=62),
    ]

    grid = detect_grid(blocks)

    assert grid.columns == 1


def test_grid_detection_too_few_blocks():
    """Fewer than MIN_BLOCKS_FOR_CLUSTERING blocks → fallback 1x1 grid."""
    from services.stages.grid_detection import detect_grid

    blocks = [
        _make_text_block("A", x0=0, y0=0, x1=100, y1=12),
    ]

    grid = detect_grid(blocks)

    assert grid.columns == 1
    assert grid.rows == 1


def test_grid_detection_output_shape():
    """GridInfo must contain column_positions and row_positions lists."""
    from services.stages.grid_detection import detect_grid

    blocks = [_make_text_block(str(i), x0=i * 50, y0=i * 20, x1=i * 50 + 40, y1=i * 20 + 12)
              for i in range(5)]

    grid = detect_grid(blocks)

    assert isinstance(grid.column_positions, list)
    assert isinstance(grid.row_positions, list)
    assert grid.columns == len(grid.column_positions)
    assert grid.rows == len(grid.row_positions)


# ---------------------------------------------------------------------------
# Test 4 — Encrypted PDF Detection
# ---------------------------------------------------------------------------


def test_encrypted_pdf_raises_value_error():
    """_extract_text_from_pdf must raise ValueError for encrypted PDFs."""
    from pathlib import Path
    from services.stages.text_extraction import _extract_text_from_pdf

    fitz_mock = MagicMock()
    doc_mock = MagicMock()
    doc_mock.is_encrypted = True
    fitz_mock.open.return_value = doc_mock

    # Patch fitz inside the text_extraction module namespace
    with patch("services.stages.text_extraction.fitz", fitz_mock, create=True):
        # Temporarily inject fitz into the module
        import services.stages.text_extraction as te_mod
        original_import = __builtins__  # noqa: F841
        with patch.dict("sys.modules", {"fitz": fitz_mock}):
            # Force the function to use our mock by patching builtins.__import__
            import builtins
            real_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "fitz":
                    return fitz_mock
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(ValueError, match="PDF protegido por senha"):
                    _extract_text_from_pdf(
                        pdf_path=Path("/fake/protected.pdf"),
                        job_id="job-test",
                        pdf_index=0,
                    )


@pytest.mark.asyncio
async def test_encrypted_pdf_stage_records_error():
    """Stage 2 execute() must record the error and not crash the pipeline."""
    import tempfile
    from pathlib import Path

    fitz_mock = MagicMock()
    doc_mock = MagicMock()
    doc_mock.is_encrypted = True
    fitz_mock.open.return_value = doc_mock

    with tempfile.TemporaryDirectory() as tmpdir:
        job_id = "test-encrypted"
        job_dir = Path(tmpdir) / "jobs" / job_id
        job_dir.mkdir(parents=True)

        # Create a fake PDF file
        fake_pdf = job_dir / "protected.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake encrypted content")

        with patch.dict("sys.modules", {"fitz": fitz_mock}):
            import importlib
            import services.stages.text_extraction as te_mod
            importlib.reload(te_mod)

            context: Dict[str, Any] = {
                "job_id": job_id,
                "tmp_base": str(Path(tmpdir) / "jobs"),
            }
            result = await te_mod.execute(context)

        assert result["pdf_count"] == 1
        assert result["parsed_count"] == 0
        assert len(result["errors"]) == 1
        assert "protegido" in result["errors"][0].lower()

        import importlib
        import services.stages.text_extraction as te_mod
        importlib.reload(te_mod)


# ---------------------------------------------------------------------------
# Test 5 — Screenshot sampling for large PDFs
# ---------------------------------------------------------------------------


def test_screenshot_sampling_large_pdf():
    """PDFs with > 500 pages should sample ~50 evenly-distributed pages."""
    from services.stages.screenshot_generator import _select_sample_pages

    pages = _select_sample_pages(total_pages=600)
    assert len(pages) == 50
    assert pages[0] == 0
    assert pages[-1] < 600


def test_screenshot_sampling_small_pdf():
    """PDFs with <= 50 pages should return all page indices."""
    from services.stages.screenshot_generator import _select_sample_pages

    pages = _select_sample_pages(total_pages=30)
    assert pages == list(range(30))


# ---------------------------------------------------------------------------
# Test 6 — ParsedDocument serialisation
# ---------------------------------------------------------------------------


def test_parsed_document_serialisation():
    """ParsedDocument.to_context_dict() must produce a JSON-serialisable dict."""
    import json
    from models.parsed_document import (
        CSSFont, GridInfo, ParsedDocument, ParsedImage, ParsedPage, TextBlock
    )

    block = TextBlock(text="Hello", bbox=(0, 0, 100, 12), font_name="Arial",
                      font_size=12.0, page_number=0, pdf_index=0)
    font = CSSFont(font_family="Arial", font_size=12.0)
    image = ParsedImage(path="/tmp/img.png", format="png", bbox=(0, 0, 50, 50), page_number=0)
    grid = GridInfo(columns=2, rows=3, column_positions=[50.0, 300.0], row_positions=[10.0, 30.0, 50.0])
    page = ParsedPage(page_number=0, text_blocks=[block], images=[image], fonts=[font], grid_info=grid)
    doc = ParsedDocument(job_id="job-1", pdf_index=0, pdf_name="test.pdf", pages=[page])

    d = doc.to_context_dict()
    serialised = json.dumps(d)  # must not raise
    assert '"Hello"' in serialised
    assert '"Arial"' in serialised
