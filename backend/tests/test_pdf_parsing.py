"""Residual tests for ParsedDocument serialisation (Story 5.5).

All v1 stage-level tests (text_reconstruction, font_extraction, grid_detection,
text_extraction, screenshot_generator) removed in Story 15.9 — helpers deleted.
Only the model serialisation test is preserved as it tests models.parsed_document
which is still active.
"""

from __future__ import annotations

from typing import Any, Dict


# ---------------------------------------------------------------------------
# Test — ParsedDocument serialisation
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
