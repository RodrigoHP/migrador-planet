"""Tests for Story 5.9 — Bloco 5: Table Detection + Semantic Intelligence.

Covers:
- Stage 17 — Table Detection (grid lines, alignment, combined, multi-page)
- Stage 18 — Table Structuring (headers, rows, multi-page merge)
- Stage 19 — Semantic Analysis (label, value, title, header, footer_text,
              page_number, table_header, table_cell)
- register_bloco5 and register_bloco6_semantic wire stages into registry
- table_header vs label: header de tabela não é campo de formulário
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import pytest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_text_block(
    text: str,
    bbox: Tuple[float, float, float, float],
    page_number: int = 0,
    pdf_index: int = 0,
    font_name: str = "Arial",
    font_size: float = 10.0,
) -> Dict[str, Any]:
    """Return a TextBlock as a plain dict (for embedding in ParsedPage/ParsedDocument)."""
    return {
        "text": text,
        "bbox": bbox,
        "page_number": page_number,
        "pdf_index": pdf_index,
        "font_name": font_name,
        "font_size": font_size,
        "semantic_label": "",
    }


def _make_parsed_doc(
    pages: List[Dict[str, Any]],
    pdf_index: int = 0,
    job_id: str = "test-job",
) -> Dict[str, Any]:
    """Build a ParsedDocument dict with the given pages."""
    return {
        "job_id": job_id,
        "pdf_index": pdf_index,
        "pdf_name": f"doc_{pdf_index}.pdf",
        "pages": pages,
    }


def _make_page(
    page_number: int,
    text_blocks: List[Dict[str, Any]],
    grid_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "page_number": page_number,
        "text_blocks": text_blocks,
        "images": [],
        "fonts": [],
        "grid_info": grid_info,
        "screenshot_path": None,
    }


def _make_grid_info(columns: int, rows: int) -> Dict[str, Any]:
    return {
        "columns": columns,
        "rows": rows,
        "column_positions": [],
        "row_positions": [],
    }


# ---------------------------------------------------------------------------
# Test 1 — Table Detection: grid_info with columns > 1 and rows > 2
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_detection_by_grid_lines():
    """Page with grid_info.columns=3, rows=5 should detect a table (score > 0.5)."""
    from services.stages.table_detection import execute

    # Build 9 blocks arranged in 3 columns × 3 rows
    blocks = []
    for row in range(3):
        for col in range(3):
            x0 = 50.0 + col * 150.0
            y0 = 100.0 + row * 30.0
            blocks.append(_make_text_block(
                f"cell_{row}_{col}",
                (x0, y0, x0 + 100.0, y0 + 20.0),
            ))

    grid = _make_grid_info(columns=3, rows=5)
    page = _make_page(0, blocks, grid_info=grid)
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc]}
    result = await execute(context)

    assert result["tables_detected"] >= 1
    assert len(context["tables"]) >= 1
    first_table = context["tables"][0]
    assert first_table["confidence"] >= 0.5


# ---------------------------------------------------------------------------
# Test 2 — Table Detection: alignment-based (no grid_info)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_detection_by_alignment_no_grid():
    """Blocks aligned in columns/rows without grid_info should still be detected."""
    from services.stages.table_detection import execute

    # 3 columns × 4 rows, very regular spacing
    blocks = []
    for row in range(4):
        for col in range(3):
            x0 = 50.0 + col * 150.0
            y0 = 200.0 + row * 25.0
            blocks.append(_make_text_block(
                f"data_{row}_{col}",
                (x0, y0, x0 + 100.0, y0 + 18.0),
            ))

    page = _make_page(0, blocks)  # no grid_info
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc]}
    result = await execute(context)

    assert result["tables_detected"] >= 1
    assert len(context["tables"]) >= 1


# ---------------------------------------------------------------------------
# Test 3 — Table Detection: single-column content → not a table
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_detection_single_column_not_detected():
    """A single column of text should NOT be detected as a table."""
    from services.stages.table_detection import execute

    # All blocks at the same x position (paragraph)
    blocks = [
        _make_text_block("Line 1", (50.0, 100.0 + i * 14.0, 400.0, 112.0 + i * 14.0))
        for i in range(6)
    ]
    page = _make_page(0, blocks)
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc]}
    result = await execute(context)

    assert result["tables_detected"] == 0
    assert len(context["tables"]) == 0


# ---------------------------------------------------------------------------
# Test 4 — Table Detection: multi-page table detected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_detection_multi_page():
    """Table ending near page bottom + similar table on next page → is_multi_page."""
    from services.stages.table_detection import execute

    def _table_blocks(page_num: int, y_start: float) -> List[Dict[str, Any]]:
        blocks = []
        for row in range(4):
            for col in range(3):
                x0 = 50.0 + col * 150.0
                y0 = y_start + row * 25.0
                blocks.append(_make_text_block(
                    f"val_{row}_{col}",
                    (x0, y0, x0 + 100.0, y0 + 18.0),
                    page_number=page_num,
                ))
        return blocks

    # Page 0: table ends near the bottom (y starts at ~700)
    page0_blocks = _table_blocks(0, y_start=700.0)
    grid = _make_grid_info(columns=3, rows=5)
    page0 = _make_page(0, page0_blocks, grid_info=grid)

    # Page 1: continuation at the top
    page1_blocks = _table_blocks(1, y_start=50.0)
    page1 = _make_page(1, page1_blocks, grid_info=grid)

    doc = _make_parsed_doc([page0, page1])

    context: Dict[str, Any] = {"parsed_documents": [doc]}
    result = await execute(context)

    multi_page = [t for t in context["tables"] if t["is_multi_page"]]
    assert len(multi_page) >= 1
    assert multi_page[0]["continuation_pages"] == [1]


# ---------------------------------------------------------------------------
# Test 5 — Table Structuring: headers identified from rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_structuring_headers_identified():
    """Stage 18 should preserve or identify header row in a simple table."""
    from services.stages.table_structuring import execute

    # Pre-built table from Stage 17 (as if already detected)
    import uuid
    table = {
        "table_id": str(uuid.uuid4()),
        "page_number": 0,
        "pdf_index": 0,
        "bbox": (50.0, 100.0, 500.0, 300.0),
        "headers": ["Nome", "Valor", "Data"],
        "rows": [
            ["João", "100,00", "01/01/2025"],
            ["Maria", "200,00", "02/01/2025"],
        ],
        "column_widths": [150.0, 150.0, 150.0],
        "is_multi_page": False,
        "continuation_pages": [],
        "confidence": 0.75,
        "detection_method": "combined",
    }

    blocks = [
        _make_text_block("Nome", (50.0, 100.0, 200.0, 115.0), font_name="Arial-Bold", font_size=11.0),
        _make_text_block("Valor", (200.0, 100.0, 350.0, 115.0), font_name="Arial-Bold", font_size=11.0),
        _make_text_block("João", (50.0, 130.0, 200.0, 145.0)),
        _make_text_block("100,00", (200.0, 130.0, 350.0, 145.0)),
    ]
    page = _make_page(0, blocks)
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {
        "tables": [table],
        "parsed_documents": [doc],
    }
    result = await execute(context)

    assert result["tables_structured"] >= 1
    structured = context["tables"][0]
    assert structured["headers"] == ["Nome", "Valor", "Data"]
    assert len(structured["rows"]) == 2


# ---------------------------------------------------------------------------
# Test 6 — Table Structuring: multi-page rows merged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_structuring_multi_page_merge():
    """Continuation table rows should be merged into the primary table."""
    from services.stages.table_structuring import execute
    import uuid

    primary_id = str(uuid.uuid4())
    cont_id = str(uuid.uuid4())

    primary = {
        "table_id": primary_id,
        "page_number": 0,
        "pdf_index": 0,
        "bbox": (50.0, 700.0, 500.0, 840.0),
        "headers": ["A", "B"],
        "rows": [["a1", "b1"]],
        "column_widths": [200.0, 200.0],
        "is_multi_page": True,
        "continuation_pages": [1],
        "confidence": 0.8,
        "detection_method": "combined",
    }
    continuation = {
        "table_id": cont_id,
        "page_number": 1,
        "pdf_index": 0,
        "bbox": (50.0, 50.0, 500.0, 200.0),
        "headers": [],
        "rows": [["a2", "b2"], ["a3", "b3"]],
        "column_widths": [200.0, 200.0],
        "is_multi_page": False,
        "continuation_pages": [],
        "confidence": 0.8,
        "detection_method": "combined",
    }

    context: Dict[str, Any] = {
        "tables": [primary, continuation],
        "parsed_documents": [],
    }
    result = await execute(context)

    # After merge, only the primary table should remain
    tables = context["tables"]
    # Primary table should have all rows
    primary_result = next((t for t in tables if t["table_id"] == primary_id), None)
    assert primary_result is not None
    assert len(primary_result["rows"]) == 3  # 1 original + 2 from continuation


# ---------------------------------------------------------------------------
# Test 7 — Semantic Analysis: "Nome:" → label
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_label_for_colon_text():
    """Text ending with ':' should be classified as 'label'."""
    from services.stages.semantic_analysis import execute

    block = _make_text_block("Nome:", (50.0, 400.0, 150.0, 412.0))
    page = _make_page(0, [block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": []}
    await execute(context)

    pages = context["parsed_documents"][0]["pages"]
    found_block = pages[0]["text_blocks"][0]
    assert found_block["semantic_label"] == "label"


# ---------------------------------------------------------------------------
# Test 8 — Semantic Analysis: numeric value → "value"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_value_for_numeric():
    """Pure numeric text should be classified as 'value'."""
    from services.stages.semantic_analysis import execute

    block = _make_text_block("12345.67", (200.0, 400.0, 350.0, 412.0))
    page = _make_page(0, [block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": []}
    await execute(context)

    found = context["parsed_documents"][0]["pages"][0]["text_blocks"][0]
    assert found["semantic_label"] == "value"


# ---------------------------------------------------------------------------
# Test 9 — Semantic Analysis: block in header zone → "header"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_header_zone():
    """Block in top 15% of page should be classified as 'header'."""
    from services.stages.semantic_analysis import execute

    # y in top 15% of 842pt page → y < 126
    block = _make_text_block("EMPRESA XYZ LTDA", (50.0, 50.0, 400.0, 65.0))
    page = _make_page(0, [block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": []}
    await execute(context)

    found = context["parsed_documents"][0]["pages"][0]["text_blocks"][0]
    assert found["semantic_label"] == "header"


# ---------------------------------------------------------------------------
# Test 10 — Semantic Analysis: page number in footer zone
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_page_number():
    """Numeric text in bottom 10% of page should be classified as 'page_number'."""
    from services.stages.semantic_analysis import execute

    # y in bottom 10% of 842pt page → y > 757
    block = _make_text_block("1", (280.0, 820.0, 315.0, 835.0))
    page = _make_page(0, [block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": []}
    await execute(context)

    found = context["parsed_documents"][0]["pages"][0]["text_blocks"][0]
    assert found["semantic_label"] == "page_number"


# ---------------------------------------------------------------------------
# Test 11 — Semantic Analysis: footer text (non-numeric in footer zone)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_footer_text():
    """Non-page-number text in bottom zone should be 'footer_text'."""
    from services.stages.semantic_analysis import execute

    block = _make_text_block("Confidencial — uso interno", (50.0, 815.0, 400.0, 827.0))
    page = _make_page(0, [block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": []}
    await execute(context)

    found = context["parsed_documents"][0]["pages"][0]["text_blocks"][0]
    assert found["semantic_label"] == "footer_text"


# ---------------------------------------------------------------------------
# Test 12 — Semantic Analysis: large bold text → "title"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_title_large_bold():
    """Large bold text in body zone should be classified as 'title'."""
    from services.stages.semantic_analysis import execute

    # Regular block (avg font ~10pt)
    regular = _make_text_block("Some text", (50.0, 300.0, 400.0, 312.0), font_size=10.0)
    # Title candidate: font 16pt bold, in the body zone (not header/footer)
    title_blk = _make_text_block(
        "RELATÓRIO FINANCEIRO",
        (50.0, 200.0, 500.0, 220.0),
        font_name="Arial-Bold",
        font_size=16.0,
    )

    page = _make_page(0, [regular, title_blk])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": []}
    await execute(context)

    blocks = context["parsed_documents"][0]["pages"][0]["text_blocks"]
    title_found = next(b for b in blocks if b["text"] == "RELATÓRIO FINANCEIRO")
    assert title_found["semantic_label"] == "title"


# ---------------------------------------------------------------------------
# Test 13 — Semantic Analysis: table_header ≠ label (key AC requirement)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_table_header_not_label():
    """A column header inside a table must be 'table_header', not 'label'.

    This is the key architectural decision: table headers like "Data", "Valor",
    "Descrição" should not be interpreted as form field labels.
    """
    from services.stages.semantic_analysis import execute
    import uuid

    # Place the table header block inside a DetectedTable bbox
    table_dict = {
        "table_id": str(uuid.uuid4()),
        "page_number": 0,
        "pdf_index": 0,
        "bbox": (50.0, 200.0, 500.0, 500.0),
        "headers": ["Data", "Valor", "Descrição"],
        "rows": [["01/01/2025", "100,00", "Pagamento"]],
        "column_widths": [150.0, 150.0, 150.0],
        "is_multi_page": False,
        "continuation_pages": [],
        "confidence": 0.8,
        "detection_method": "grid_lines",
    }

    # "Data" is in the header zone of the table (top ~15% of bbox y range = 200 to 248)
    header_block = _make_text_block("Data", (50.0, 205.0, 200.0, 218.0))
    page = _make_page(0, [header_block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": [table_dict]}
    await execute(context)

    found = context["parsed_documents"][0]["pages"][0]["text_blocks"][0]
    # Must NOT be classified as "label" even though "Data" doesn't end with ":"
    assert found["semantic_label"] != "label"
    # Must be a table-related label
    assert found["semantic_label"] in ("table_header", "table_cell")


# ---------------------------------------------------------------------------
# Test 14 — Semantic Analysis: table_cell for data block inside table
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_table_cell_for_data_block():
    """A data block inside a table region should be 'table_cell'."""
    from services.stages.semantic_analysis import execute
    import uuid

    table_dict = {
        "table_id": str(uuid.uuid4()),
        "page_number": 0,
        "pdf_index": 0,
        "bbox": (50.0, 200.0, 500.0, 500.0),
        "headers": ["Nome"],
        "rows": [["João Silva"]],
        "column_widths": [200.0],
        "is_multi_page": False,
        "continuation_pages": [],
        "confidence": 0.8,
        "detection_method": "alignment",
    }

    # "João Silva" is in the data zone of the table (below header zone)
    data_block = _make_text_block("João Silva", (50.0, 350.0, 200.0, 365.0))
    page = _make_page(0, [data_block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc], "tables": [table_dict]}
    await execute(context)

    found = context["parsed_documents"][0]["pages"][0]["text_blocks"][0]
    assert found["semantic_label"] == "table_cell"


# ---------------------------------------------------------------------------
# Test 15 — register_bloco5 wires stages 17-18 into registry
# ---------------------------------------------------------------------------


def test_register_bloco5_wires_stages():
    """register_bloco5 should replace stubs 17-18 with real implementations."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco5

    registry = build_default_registry()

    # Before registration, stubs have no execute_fn
    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[17]._execute_fn is None
    assert stages_before[18]._execute_fn is None

    register_bloco5(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}
    assert stages_after[17]._execute_fn is not None, "Stage 17 still stub after register_bloco5"
    assert stages_after[18]._execute_fn is not None, "Stage 18 still stub after register_bloco5"

    # Pipeline must remain intact — still 27 stages
    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 28


# ---------------------------------------------------------------------------
# Test 16 — register_bloco6_semantic wires stage 19 into registry
# ---------------------------------------------------------------------------


def test_register_bloco6_semantic_wires_stage19():
    """register_bloco6_semantic should replace stub 19 with real implementation."""
    from models.pipeline import build_default_registry
    from services.stages.register_all import register_bloco6_semantic

    registry = build_default_registry()

    stages_before = {s.stage_number: s for s in registry.all_stages()}
    assert stages_before[19]._execute_fn is None

    register_bloco6_semantic(registry)

    stages_after = {s.stage_number: s for s in registry.all_stages()}
    assert stages_after[19]._execute_fn is not None, "Stage 19 still stub after register_bloco6_semantic"

    pipeline = registry.build_pipeline()
    assert pipeline.total_stages == 28


# ---------------------------------------------------------------------------
# Test 17 — SSE progress emitted by stages 17, 18, 19
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_progress_emitted_stages_17_18_19():
    """All three stages should emit SSE events when emit_progress is provided."""
    from services.stages.table_detection import execute as s17
    from services.stages.table_structuring import execute as s18
    from services.stages.semantic_analysis import execute as s19

    events = []

    def capture(event):
        events.append(event)

    # Minimal valid context
    block = _make_text_block("Nome:", (50.0, 400.0, 150.0, 412.0))
    page = _make_page(0, [block])
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {
        "parsed_documents": [doc],
        "tables": [],
        "emit_progress": capture,
    }

    await s17(context)
    await s18(context)
    await s19(context)

    stage_nums = [e["stage"] for e in events]
    assert 17 in stage_nums
    assert 18 in stage_nums
    assert 19 in stage_nums
    for e in events:
        assert e["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 18 — End-to-end: stages 17→18→19 on a document with a table
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_bloco5_table_plus_semantic():
    """Stages 17→18→19 should run without errors and produce labelled blocks."""
    from services.stages.table_detection import execute as s17
    from services.stages.table_structuring import execute as s18
    from services.stages.semantic_analysis import execute as s19

    # Create a page with a 3-column table + a label block outside it
    table_blocks = []
    col_xs = [50.0, 200.0, 350.0]
    for row in range(4):
        for ci, x0 in enumerate(col_xs):
            y0 = 200.0 + row * 30.0
            table_blocks.append(_make_text_block(
                f"r{row}c{ci}",
                (x0, y0, x0 + 100.0, y0 + 20.0),
            ))

    label_block = _make_text_block("CPF:", (50.0, 400.0, 150.0, 412.0))

    grid = _make_grid_info(columns=3, rows=4)
    page = _make_page(0, table_blocks + [label_block], grid_info=grid)
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {"parsed_documents": [doc]}

    await s17(context)
    assert len(context["tables"]) >= 1

    await s18(context)
    assert len(context["tables"]) >= 1

    await s19(context)

    # All blocks should have a semantic_label set
    for blk in context["parsed_documents"][0]["pages"][0]["text_blocks"]:
        assert blk["semantic_label"] != "", f"Block '{blk['text']}' has no semantic_label"

    # The "CPF:" block (outside table) should be a "label"
    labelled_blocks = context["parsed_documents"][0]["pages"][0]["text_blocks"]
    cpf_block = next((b for b in labelled_blocks if b["text"] == "CPF:"), None)
    assert cpf_block is not None
    assert cpf_block["semantic_label"] == "label"


# ---------------------------------------------------------------------------
# Test 19 — TextBlock has semantic_label field
# ---------------------------------------------------------------------------


def test_text_block_has_semantic_label_field():
    """TextBlock model must have a semantic_label field defaulting to empty string."""
    from models.parsed_document import TextBlock

    blk = TextBlock(text="test", bbox=(0.0, 0.0, 10.0, 10.0), page_number=0)
    assert hasattr(blk, "semantic_label")
    assert blk.semantic_label == ""

    blk2 = TextBlock(text="Nome:", bbox=(0.0, 0.0, 80.0, 12.0), page_number=0, semantic_label="label")
    assert blk2.semantic_label == "label"


# ---------------------------------------------------------------------------
# Test 20 — DetectedTable model fields
# ---------------------------------------------------------------------------


def test_detected_table_model_fields():
    """DetectedTable must expose all required fields from the story spec."""
    from models.detected_table import DetectedTable

    t = DetectedTable(
        table_id="t-001",
        page_number=1,
        pdf_index=0,
        bbox=(10.0, 20.0, 400.0, 300.0),
        headers=["Col A", "Col B"],
        rows=[["val1", "val2"]],
        column_widths=[190.0, 190.0],
        is_multi_page=True,
        continuation_pages=[2],
    )
    assert t.table_id == "t-001"
    assert t.headers == ["Col A", "Col B"]
    assert t.is_multi_page is True
    assert t.continuation_pages == [2]
    assert t.confidence == 0.0  # default


# ---------------------------------------------------------------------------
# Story 10.12 — Test 21: Stage 18 preserves rows when no bold header detected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_structuring_rows_preserved_no_bold():
    """AC#2 — Stage 18 must NOT erase existing rows when no header is detected.

    Given a DetectedTable with rows=[["Col A", "Col B"], ["val1", "val2"]] and
    no pre-existing headers, when the page blocks are regular (not bold, not
    large font), Stage 18 must leave both rows intact and headers empty.
    """
    from services.stages.table_structuring import execute
    import uuid

    table = {
        "table_id": str(uuid.uuid4()),
        "page_number": 0,
        "pdf_index": 0,
        "bbox": (50.0, 100.0, 500.0, 300.0),
        "headers": [],
        "rows": [["Col A", "Col B"], ["val1", "val2"]],
        "column_widths": [200.0, 200.0],
        "is_multi_page": False,
        "continuation_pages": [],
        "confidence": 0.8,
        "detection_method": "alignment",
    }

    # Regular non-bold blocks at normal font size — no header heuristic trigger
    blocks = [
        _make_text_block("Col A", (50.0, 100.0, 200.0, 115.0), font_name="Arial", font_size=10.0),
        _make_text_block("Col B", (250.0, 100.0, 400.0, 115.0), font_name="Arial", font_size=10.0),
        _make_text_block("val1", (50.0, 130.0, 200.0, 145.0), font_name="Arial", font_size=10.0),
        _make_text_block("val2", (250.0, 130.0, 400.0, 145.0), font_name="Arial", font_size=10.0),
    ]
    page = _make_page(0, blocks)
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {
        "tables": [table],
        "parsed_documents": [doc],
    }
    result = await execute(context)

    assert result["tables_structured"] == 1
    structured = context["tables"][0]
    # Both rows must still be present — Stage 18 must not delete them
    assert len(structured["rows"]) == 2, (
        f"Expected 2 rows but got {len(structured['rows'])}: {structured['rows']}"
    )
    assert structured["rows"][0] == ["Col A", "Col B"]
    assert structured["rows"][1] == ["val1", "val2"]


# ---------------------------------------------------------------------------
# Story 10.12 — Test 22: Stage 18 promotes rows[0] to headers when bold block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_structuring_bold_block_promotes_header():
    """AC#3 — Stage 18 must promote rows[0] to headers when bold block is in top 15%.

    Given a DetectedTable with rows=[["Nome", "Valor"], ["João", "100"]] and
    no pre-existing headers, when a TextBlock with font_name="Arial-Bold" exists
    in the top 15% of the table bbox, Stage 18 must:
    - Set table.headers = ["Nome", "Valor"]
    - Remove that row from table.rows (so rows = [["João", "100"]])
    """
    from services.stages.table_structuring import execute
    import uuid

    bbox = (50.0, 100.0, 500.0, 400.0)  # height = 300; top 15% = y <= 145
    table = {
        "table_id": str(uuid.uuid4()),
        "page_number": 0,
        "pdf_index": 0,
        "bbox": bbox,
        "headers": [],
        "rows": [["Nome", "Valor"], ["João", "100"]],
        "column_widths": [200.0, 200.0],
        "is_multi_page": False,
        "continuation_pages": [],
        "confidence": 0.8,
        "detection_method": "alignment",
    }

    # Bold block in top 15% zone (y=105, within y0=100 to y0+height*0.15=145)
    blocks = [
        _make_text_block("Nome", (50.0, 105.0, 200.0, 118.0), font_name="Arial-Bold", font_size=10.0),
        _make_text_block("Valor", (250.0, 105.0, 400.0, 118.0), font_name="Arial-Bold", font_size=10.0),
        _make_text_block("João", (50.0, 160.0, 200.0, 175.0), font_name="Arial", font_size=10.0),
        _make_text_block("100", (250.0, 160.0, 400.0, 175.0), font_name="Arial", font_size=10.0),
    ]
    page = _make_page(0, blocks)
    doc = _make_parsed_doc([page])

    context: Dict[str, Any] = {
        "tables": [table],
        "parsed_documents": [doc],
    }
    result = await execute(context)

    assert result["tables_structured"] == 1
    structured = context["tables"][0]
    # rows[0] must be promoted to headers
    assert structured["headers"] == ["Nome", "Valor"], (
        f"Expected headers=['Nome','Valor'] but got {structured['headers']}"
    )
    # rows[0] must be removed from rows
    assert len(structured["rows"]) == 1, (
        f"Expected 1 data row but got {len(structured['rows'])}: {structured['rows']}"
    )
    assert structured["rows"][0] == ["João", "100"]


# ---------------------------------------------------------------------------
# Story 10.12 — Test 23: Stage 18 multi-page merge — single merged table result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_structuring_multi_page_single_result():
    """AC#4 — After Stage 18, two tables (primary + continuation) become one.

    Given primary table with is_multi_page=True, continuation_pages=[2] and a
    continuation table on page 2, Stage 18 must produce exactly 1 table with
    rows from both. The continuation table record must be removed.
    """
    from services.stages.table_structuring import execute
    import uuid

    primary_id = str(uuid.uuid4())
    cont_id = str(uuid.uuid4())

    primary = {
        "table_id": primary_id,
        "page_number": 1,
        "pdf_index": 0,
        "bbox": (50.0, 700.0, 500.0, 840.0),
        "headers": ["Col1", "Col2"],
        "rows": [["r1c1", "r1c2"]],
        "column_widths": [200.0, 200.0],
        "is_multi_page": True,
        "continuation_pages": [2],
        "confidence": 0.8,
        "detection_method": "combined",
    }
    continuation = {
        "table_id": cont_id,
        "page_number": 2,
        "pdf_index": 0,
        "bbox": (50.0, 50.0, 500.0, 200.0),
        "headers": [],
        "rows": [["r2c1", "r2c2"], ["r3c1", "r3c2"]],
        "column_widths": [200.0, 200.0],
        "is_multi_page": False,
        "continuation_pages": [],
        "confidence": 0.8,
        "detection_method": "combined",
    }

    context: Dict[str, Any] = {
        "tables": [primary, continuation],
        "parsed_documents": [],
    }
    result = await execute(context)

    tables = context["tables"]
    # Only 1 table should remain after merge
    assert len(tables) == 1, f"Expected 1 table after merge but got {len(tables)}"

    merged = tables[0]
    assert merged["table_id"] == primary_id, "Merged table must be the primary table"
    # 1 original row + 2 from continuation = 3 rows total
    assert len(merged["rows"]) == 3, (
        f"Expected 3 rows after merge but got {len(merged['rows'])}: {merged['rows']}"
    )
    # Continuation table id must not appear in results
    assert not any(t["table_id"] == cont_id for t in tables), (
        "Continuation table must be removed after merge"
    )
