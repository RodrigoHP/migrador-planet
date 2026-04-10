"""Stage 2 Extraction package.

Re-exports all public symbols for backward-compatible access.

Story 41.3 — stage2_deep_extraction.py decomposed into sub-modules.
"""

from services.stages.stage2_extraction.drawn_quality import (
    _color_to_int,
    _extract_drawn_elements,
    _line_orientation,
    _quality_check,
)
from services.stages.stage2_extraction.grid_table_extraction import (
    _check_ruling_lines,
    _detect_grid_jenks,
    _detect_header_rows,
    _detect_tables,
    _fallback_gap_groups,
    _jenks_1d,
    _structure_tables,
)
from services.stages.stage2_extraction.media_extraction import (
    _extract_images,
    _take_screenshot,
)
from services.stages.stage2_extraction.text_extraction import (
    FONT_MAP,
    _build_block_from_spans,
    _collect_page_fonts,
    _extract_spans_from_page,
    _font_to_css,
    _merge_spans_to_blocks,
    _normalize_pdf_font_name,
)

__all__ = [
    # text_extraction
    "FONT_MAP",
    "_build_block_from_spans",
    "_collect_page_fonts",
    "_extract_spans_from_page",
    "_font_to_css",
    "_merge_spans_to_blocks",
    "_normalize_pdf_font_name",
    # media_extraction
    "_extract_images",
    "_take_screenshot",
    # grid_table_extraction
    "_check_ruling_lines",
    "_color_to_int",
    "_detect_grid_jenks",
    "_detect_header_rows",
    "_detect_tables",
    "_extract_drawn_elements",
    "_fallback_gap_groups",
    "_jenks_1d",
    "_line_orientation",
    "_quality_check",
    "_structure_tables",
]
