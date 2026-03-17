"""Stage 19 — Semantic Analysis.

Classifies each TextBlock in every ParsedDocument into one of the following
semantic labels:

    label         — static field identifier, e.g. "Nome:", "CPF:"
    value         — dynamic field content, e.g. "João Silva", "123.456-7"
    title         — large/bold text heading at the top of a section
    header        — text in the page-header zone (top 15% of page)
    footer_text   — text in the page-footer zone (bottom 10% of page)
    page_number   — numeric / "Página N de M" text in the footer zone
    table_header  — text that is the header row of a detected table
    table_cell    — text that is a data cell inside a detected table

Classification relies on four heuristics (applied in priority order):
    1. Table context   — block intersects a detected table region → table_header or table_cell
    2. Zone            — y-position relative to page height → header / footer_text / page_number
    3. Formatting      — font size > average * 1.2 and bold → title
    4. Text content    — ends with ":" → label; purely numeric → value; otherwise value

Reads:  context["parsed_documents"]  — List[Dict] (ParsedDocument serialised)
        context["tables"]            — List[Dict] (DetectedTable serialised, optional)
Writes: context["parsed_documents"]  — updated with semantic_label on every TextBlock

Registers itself as Stage 19 (Block 6).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from models.detected_table import DetectedTable
from models.parsed_document import ParsedDocument, ParsedPage, TextBlock


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADER_ZONE_FRACTION = 0.15   # top 15% of page height
FOOTER_ZONE_FRACTION = 0.10   # bottom 10% of page height
DEFAULT_PAGE_HEIGHT = 842.0   # A4 fallback

_PAGE_NUMBER_RE = re.compile(
    r"^(p[áa]gina\s+\d+(\s+de\s+\d+)?|\d+\s*/\s*\d+|\d+)$",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(r"^[\d\s.,/$%\-+()]+$")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _bbox_overlap(
    b1: Tuple[float, float, float, float],
    b2: Tuple[float, float, float, float],
) -> bool:
    """Return True if two bboxes overlap (inclusive)."""
    x0a, y0a, x1a, y1a = b1
    x0b, y0b, x1b, y1b = b2
    return x0a <= x1b and x1a >= x0b and y0a <= y1b and y1a >= y0b


def _point_in_bbox(
    x: float,
    y: float,
    bbox: Tuple[float, float, float, float],
) -> bool:
    x0, y0, x1, y1 = bbox
    return x0 <= x <= x1 and y0 <= y <= y1


# ---------------------------------------------------------------------------
# Table context index
# ---------------------------------------------------------------------------


class _TableIndex:
    """Fast spatial lookup for table regions and header zones."""

    def __init__(self, tables: List[DetectedTable]) -> None:
        self._tables = tables

    def _table_for_block(self, block: TextBlock) -> Optional[DetectedTable]:
        bx = (block.bbox[0] + block.bbox[2]) / 2
        by = (block.bbox[1] + block.bbox[3]) / 2
        for tbl in self._tables:
            if tbl.page_number == block.page_number and tbl.pdf_index == block.pdf_index:
                if _point_in_bbox(bx, by, tbl.bbox):
                    return tbl
        return None

    def semantic_label_from_table(self, block: TextBlock) -> Optional[str]:
        """Return 'table_header' or 'table_cell' if block is inside a table."""
        tbl = self._table_for_block(block)
        if tbl is None:
            return None

        # Check if the block's text matches a header value
        if tbl.headers:
            # Header zone: upper ~(header_row_height) of the table bbox
            header_height_est = (tbl.bbox[3] - tbl.bbox[1]) * 0.15 + tbl.bbox[1]
            if block.bbox[1] <= header_height_est:
                if block.text.strip() in tbl.headers:
                    return "table_header"
        return "table_cell"


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------


def _zone_label(
    block: TextBlock,
    page_height: float,
) -> Optional[str]:
    """Classify block by vertical zone on the page."""
    y_mid = (block.bbox[1] + block.bbox[3]) / 2
    relative = y_mid / page_height if page_height > 0 else 0.5

    if relative <= HEADER_ZONE_FRACTION:
        return "header"
    if relative >= (1.0 - FOOTER_ZONE_FRACTION):
        text = block.text.strip()
        if _PAGE_NUMBER_RE.match(text):
            return "page_number"
        return "footer_text"
    return None


# ---------------------------------------------------------------------------
# Formatting classification
# ---------------------------------------------------------------------------


def _is_bold(font_name: str) -> bool:
    n = font_name.lower()
    return "bold" in n or "black" in n or "heavy" in n


def _format_label(
    block: TextBlock,
    avg_font_size: float,
) -> Optional[str]:
    """Return 'title' if block looks like a section title."""
    if block.font_size > 0 and block.font_size > avg_font_size * 1.2:
        if _is_bold(block.font_name) or block.font_size > avg_font_size * 1.5:
            return "title"
    return None


# ---------------------------------------------------------------------------
# Content-based classification
# ---------------------------------------------------------------------------


def _content_label(text: str) -> str:
    """Classify by text content heuristics."""
    stripped = text.strip()
    if stripped.endswith(":"):
        return "label"
    if _NUMERIC_RE.match(stripped) and len(stripped) >= 1:
        return "value"
    # Default: treat as value (dynamic content)
    return "value"


# ---------------------------------------------------------------------------
# Per-page classification
# ---------------------------------------------------------------------------


def _classify_page(
    page: ParsedPage,
    table_index: _TableIndex,
) -> ParsedPage:
    """Return a new ParsedPage with semantic_label set on every TextBlock."""
    if not page.text_blocks:
        return page

    # Estimate page height: prefer DEFAULT_PAGE_HEIGHT (A4 = 842pts).
    # Only use block extent when blocks clearly exceed the default (i.e. the PDF
    # is larger than A4).  Never use a small multiplier that would push A4-range
    # blocks out of the footer zone.
    max_y1 = max((b.bbox[3] for b in page.text_blocks), default=0.0)
    if max_y1 > DEFAULT_PAGE_HEIGHT:
        page_height = max_y1 * 1.05  # slightly larger than the tallest block
    else:
        page_height = DEFAULT_PAGE_HEIGHT

    # Average font size for formatting heuristics
    font_sizes = [b.font_size for b in page.text_blocks if b.font_size > 0]
    avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else 10.0

    new_blocks: List[TextBlock] = []
    for block in page.text_blocks:
        label: Optional[str] = None

        # Priority 1: table context
        label = table_index.semantic_label_from_table(block)

        # Priority 2: zone
        if label is None:
            label = _zone_label(block, page_height)

        # Priority 3: formatting → title
        if label is None:
            label = _format_label(block, avg_font)

        # Priority 4: content heuristics
        if label is None:
            label = _content_label(block.text)

        # Build updated block (Pydantic model, so create new)
        new_blocks.append(
            TextBlock(
                text=block.text,
                bbox=block.bbox,
                font_name=block.font_name,
                font_size=block.font_size,
                page_number=block.page_number,
                pdf_index=block.pdf_index,
                semantic_label=label or "value",
            )
        )

    return ParsedPage(
        page_number=page.page_number,
        text_blocks=new_blocks,
        images=page.images,
        fonts=page.fonts,
        grid_info=page.grid_info,
        screenshot_path=page.screenshot_path,
    )


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 19 executor — Semantic Analysis."""
    emit = context.get("emit_progress")

    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])
    raw_tables: List[Dict[str, Any]] = context.get("tables", [])

    tables = [DetectedTable(**t) for t in raw_tables]
    table_index = _TableIndex(tables)

    label_counts: Dict[str, int] = {}
    updated_docs: List[Dict[str, Any]] = []

    for doc_dict in parsed_documents:
        parsed = ParsedDocument(**doc_dict)
        new_pages = []
        for page in parsed.pages:
            classified_page = _classify_page(page, table_index)
            new_pages.append(classified_page)
            for blk in classified_page.text_blocks:
                label_counts[blk.semantic_label] = label_counts.get(blk.semantic_label, 0) + 1
        parsed.pages = new_pages
        updated_docs.append(parsed.to_context_dict())

    context["parsed_documents"] = updated_docs

    total_blocks = sum(label_counts.values())
    summary = {
        "total_blocks_classified": total_blocks,
        "label_distribution": label_counts,
    }

    if emit:
        try:
            emit(
                {
                    "stage": 19,
                    "stage_name": "Semantic Analysis",
                    "status": "completed",
                    "summary": summary,
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return summary


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace stub Stage 19 with this implementation."""
    registry.remove_stage(19)
    registry.register_stage(
        stage_number=19,
        name="Semantic Analysis",
        block_id=6,
        estimated_duration=2.5,
        execute_fn=execute,
    )
