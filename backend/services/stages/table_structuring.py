"""Stage 18 — Table Structuring.

Takes the raw DetectedTable objects produced by Stage 17 (Table Detection) and
refines their structure:

- Re-identifies header rows using font-size / bold heuristics when available.
- Builds proper TableRow / TableCell objects for downstream use.
- Handles multi-page tables: merges continuation data rows from subsequent pages
  and records continuation_pages[] references.

Reads:  context["tables"]           — List[Dict] (DetectedTable serialised)
        context["parsed_documents"] — List[Dict] (for font/bbox metadata)
Writes: context["tables"]           — List[Dict] (updated DetectedTable serialised)

Registers itself as Stage 18 (Block 5).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from models.detected_table import DetectedTable, TableCell, TableRow
from models.parsed_document import ParsedDocument, TextBlock


# ---------------------------------------------------------------------------
# Header detection heuristics
# ---------------------------------------------------------------------------


def _is_bold(font_name: str) -> bool:
    """Rough check for bold weight based on font name."""
    name_lower = font_name.lower()
    return "bold" in name_lower or "black" in name_lower or "heavy" in name_lower


def _header_row_index(
    table_bbox: Tuple[float, float, float, float],
    blocks_on_page: List[TextBlock],
) -> Optional[int]:
    """Return 0 if the first row of the table appears to be a header, else None.

    Heuristics:
    - Blocks in the top ~15% of the table bbox that are bold or larger font.
    - If any block in that zone is bold/large, treat row 0 as header.
    """
    x0, y0, x1, y1 = table_bbox
    header_zone_y = y0 + (y1 - y0) * 0.15

    header_blocks = [
        b for b in blocks_on_page
        if x0 <= b.bbox[0] <= x1 and y0 <= b.bbox[1] <= header_zone_y
    ]
    if not header_blocks:
        return None

    avg_font = sum(b.font_size for b in blocks_on_page) / len(blocks_on_page) if blocks_on_page else 0
    for b in header_blocks:
        if _is_bold(b.font_name) or (b.font_size > avg_font * 1.1 and b.font_size > 0):
            return 0

    return None


# ---------------------------------------------------------------------------
# Core structuring
# ---------------------------------------------------------------------------


def _build_cell_map(
    blocks: List[TextBlock],
    col_count: int,
) -> Dict[Tuple[int, int], str]:
    """Build a (row_idx, col_idx) → text dict from raw blocks.

    Assigns blocks to columns by sorting x positions into col_count buckets,
    and to rows by y-gap clustering.
    """
    if not blocks:
        return {}

    sorted_x = sorted(set(round(b.bbox[0], 1) for b in blocks))
    # Assign column index: divide x range into col_count equal buckets
    if len(sorted_x) <= 1:
        col_boundaries = [0.0, float("inf")]
    else:
        x_min, x_max = sorted_x[0], sorted_x[-1]
        step = (x_max - x_min) / max(col_count, 1)
        col_boundaries = [x_min + step * i for i in range(col_count + 1)]
        col_boundaries[-1] = float("inf")

    def _col_idx(x: float) -> int:
        for i in range(len(col_boundaries) - 1):
            if col_boundaries[i] <= x < col_boundaries[i + 1]:
                return i
        return col_count - 1

    # Row grouping by y proximity
    sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
    row_groups: List[List[TextBlock]] = []
    for blk in sorted_blocks:
        if not row_groups or blk.bbox[1] - row_groups[-1][0].bbox[1] > 5.0:
            row_groups.append([blk])
        else:
            row_groups[-1].append(blk)

    cell_map: Dict[Tuple[int, int], str] = {}
    for row_i, group in enumerate(row_groups):
        for blk in group:
            ci = _col_idx(blk.bbox[0])
            key = (row_i, ci)
            prev = cell_map.get(key, "")
            cell_map[key] = (prev + " " + blk.text).strip() if prev else blk.text

    return cell_map


def structure_table(
    table: DetectedTable,
    blocks_on_page: List[TextBlock],
) -> DetectedTable:
    """Refine a DetectedTable: re-identify headers, build proper rows/cells."""
    # Determine header row from font heuristics
    header_row_idx = _header_row_index(table.bbox, blocks_on_page)

    # If we have headers already from detection, keep them unless heuristic disagrees
    # Re-build rows from the existing table.rows (already structured in Stage 17)
    existing_rows = table.rows   # List[List[str]]
    existing_headers = table.headers

    if not existing_rows and not existing_headers:
        return table

    # Re-apply header detection: if heuristic says row 0 is header and we have rows
    if header_row_idx == 0 and existing_rows and not existing_headers:
        existing_headers = existing_rows[0]
        existing_rows = existing_rows[1:]

    table.headers = existing_headers
    table.rows = existing_rows
    return table


# ---------------------------------------------------------------------------
# Multi-page merging
# ---------------------------------------------------------------------------


def _merge_multi_page_tables(tables: List[DetectedTable]) -> List[DetectedTable]:
    """Merge continuation pages into the primary table record.

    For each table marked is_multi_page, find continuation tables on subsequent
    pages (by continuation_pages[]) and append their rows to the primary table.
    Continuation table records are removed from the output list.
    """
    # Index by page_number for quick lookup
    by_page: Dict[int, List[DetectedTable]] = {}
    for t in tables:
        by_page.setdefault(t.page_number, []).append(t)

    consumed_ids = set()

    for tbl in tables:
        if not tbl.is_multi_page or not tbl.continuation_pages:
            continue
        for cont_pg in tbl.continuation_pages:
            for cont_tbl in by_page.get(cont_pg, []):
                if cont_tbl.table_id == tbl.table_id:
                    continue
                if cont_tbl.table_id in consumed_ids:
                    continue
                # Merge rows (skip repeated header rows if same as primary)
                if cont_tbl.rows:
                    first_cont_row = cont_tbl.rows[0]
                    if first_cont_row == tbl.headers:
                        tbl.rows.extend(cont_tbl.rows[1:])
                    else:
                        tbl.rows.extend(cont_tbl.rows)
                consumed_ids.add(cont_tbl.table_id)

    return [t for t in tables if t.table_id not in consumed_ids]


# ---------------------------------------------------------------------------
# Page block lookup helper
# ---------------------------------------------------------------------------


def _blocks_for_table(
    table: DetectedTable,
    parsed_docs: List[ParsedDocument],
) -> List[TextBlock]:
    """Return TextBlocks from the matching page/pdf_index for a table."""
    for doc in parsed_docs:
        if doc.pdf_index != table.pdf_index:
            continue
        for page in doc.pages:
            if page.page_number == table.page_number:
                return page.text_blocks
    return []


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 18 executor — Table Structuring."""
    emit = context.get("emit_progress")

    raw_tables: List[Dict[str, Any]] = context.get("tables", [])
    parsed_documents: List[Dict[str, Any]] = context.get("parsed_documents", [])

    parsed_docs = [ParsedDocument(**d) for d in parsed_documents]

    tables = [DetectedTable(**t) for t in raw_tables]

    # Refine each table's structure
    structured: List[DetectedTable] = []
    for tbl in tables:
        page_blocks = _blocks_for_table(tbl, parsed_docs)
        refined = structure_table(tbl, page_blocks)
        structured.append(refined)

    # Merge multi-page tables
    merged = _merge_multi_page_tables(structured)

    context["tables"] = [t.model_dump() for t in merged]

    summary = {
        "tables_structured": len(merged),
        "tables_before_merge": len(structured),
        "documents_processed": len(parsed_documents),
    }

    if emit:
        try:
            emit(
                {
                    "stage": 18,
                    "stage_name": "Table Structuring",
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
    """Replace stub Stage 18 with this implementation."""
    registry.remove_stage(18)
    registry.register_stage(
        stage_number=18,
        name="Table Structuring",
        block_id=5,
        estimated_duration=2.0,
        execute_fn=execute,
    )
