"""Stage 2 — Deep Extraction (So Representativas).

Story 13.5 — Extracts complete data (text, fonts, images, tables, drawn elements)
from representative pages only, reducing extraction time from ~20min (100 pages)
to ~10s (~6 representatives).

Architecture reference: docs/architecture/pipeline-redesign-v3.md Section 6 (Stage 2)
Output contract: Section 3.2
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EmitProgressFn = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# PyMuPDF version check
# ---------------------------------------------------------------------------

_MINIMUM_PYMUPDF_VERSION = (1, 23, 0)


def check_pymupdf_version() -> None:
    """Verify PyMuPDF >= 1.23.0 (find_tables, get_drawings support)."""
    version_str = fitz.version[0]  # e.g. "1.24.0"
    parts = tuple(int(x) for x in version_str.split(".")[:3])
    if parts < _MINIMUM_PYMUPDF_VERSION:
        raise RuntimeError(
            f"PyMuPDF >= {'.'.join(str(v) for v in _MINIMUM_PYMUPDF_VERSION)} required, "
            f"found {version_str}"
        )


# ---------------------------------------------------------------------------
# FONT_MAP — Expanded ~50 fonts PDF -> CSS (2.3)
# ---------------------------------------------------------------------------

FONT_MAP: Dict[str, str] = {
    # Helvetica family
    "Helvetica": "Arial, Helvetica, sans-serif",
    "Helvetica-Bold": "Arial, Helvetica, sans-serif",
    "Helvetica-Oblique": "Arial, Helvetica, sans-serif",
    "Helvetica-BoldOblique": "Arial, Helvetica, sans-serif",
    "HelveticaNeue": "Arial, Helvetica, sans-serif",
    "HelveticaNeue-Bold": "Arial, Helvetica, sans-serif",
    "HelveticaNeue-Italic": "Arial, Helvetica, sans-serif",
    "HelveticaNeue-BoldItalic": "Arial, Helvetica, sans-serif",
    "HelveticaNeue-Light": "Arial, Helvetica, sans-serif",
    "HelveticaNeue-Medium": "Arial, Helvetica, sans-serif",
    # Arial family
    "Arial": "Arial, Helvetica, sans-serif",
    "Arial-Bold": "Arial, Helvetica, sans-serif",
    "Arial-BoldMT": "Arial, Helvetica, sans-serif",
    "Arial-ItalicMT": "Arial, Helvetica, sans-serif",
    "ArialMT": "Arial, Helvetica, sans-serif",
    "ArialNarrow": "Arial Narrow, Arial, sans-serif",
    "ArialNarrow-Bold": "Arial Narrow, Arial, sans-serif",
    # Times family
    "Times-Roman": "Times New Roman, Times, serif",
    "Times-Bold": "Times New Roman, Times, serif",
    "Times-Italic": "Times New Roman, Times, serif",
    "Times-BoldItalic": "Times New Roman, Times, serif",
    "TimesNewRoman": "Times New Roman, Times, serif",
    "TimesNewRomanPS": "Times New Roman, Times, serif",
    "TimesNewRomanPSMT": "Times New Roman, Times, serif",
    "TimesNewRomanPS-Bold": "Times New Roman, Times, serif",
    "TimesNewRomanPS-BoldMT": "Times New Roman, Times, serif",
    "TimesNewRomanPS-Italic": "Times New Roman, Times, serif",
    "TimesNewRomanPS-ItalicMT": "Times New Roman, Times, serif",
    # Courier family
    "Courier": "Courier New, Courier, monospace",
    "Courier-Bold": "Courier New, Courier, monospace",
    "Courier-Oblique": "Courier New, Courier, monospace",
    "Courier-BoldOblique": "Courier New, Courier, monospace",
    "CourierNew": "Courier New, Courier, monospace",
    "CourierNewPS": "Courier New, Courier, monospace",
    "CourierNewPSMT": "Courier New, Courier, monospace",
    # Verdana
    "Verdana": "Verdana, Geneva, sans-serif",
    "Verdana-Bold": "Verdana, Geneva, sans-serif",
    "Verdana-Italic": "Verdana, Geneva, sans-serif",
    # Georgia
    "Georgia": "Georgia, serif",
    "Georgia-Bold": "Georgia, serif",
    "Georgia-Italic": "Georgia, serif",
    # Tahoma
    "Tahoma": "Tahoma, Geneva, sans-serif",
    "Tahoma-Bold": "Tahoma, Geneva, sans-serif",
    # Calibri
    "Calibri": "Calibri, sans-serif",
    "Calibri-Bold": "Calibri, sans-serif",
    "Calibri-Italic": "Calibri, sans-serif",
    "Calibri-BoldItalic": "Calibri, sans-serif",
    # Cambria
    "Cambria": "Cambria, serif",
    "Cambria-Bold": "Cambria, serif",
    # Garamond
    "Garamond": "Garamond, serif",
    "Garamond-Bold": "Garamond, serif",
    # Symbol / Dingbats
    "Symbol": "Symbol",
    "ZapfDingbats": "ZapfDingbats",
    # Segoe UI
    "SegoeUI": "Segoe UI, sans-serif",
    "SegoeUI-Bold": "Segoe UI, sans-serif",
    # Trebuchet
    "TrebuchetMS": "Trebuchet MS, sans-serif",
    "TrebuchetMS-Bold": "Trebuchet MS, sans-serif",
}

# Subset prefix pattern: ABCDEF+FontName -> FontName
_SUBSET_PREFIX_RE = re.compile(r"^[A-Z]{6}\+")


def _normalize_pdf_font_name(raw_name: str) -> str:
    """Strip subset prefix (ABCDEF+FontName -> FontName)."""
    return _SUBSET_PREFIX_RE.sub("", raw_name)


# ---------------------------------------------------------------------------
# Sub-progress helper
# ---------------------------------------------------------------------------


async def _emit_sub(
    emit: EmitProgressFn,
    sub_step: str,
    sub_pct: float,
) -> None:
    """Emit a Stage 2 sub-progress event."""
    from services.pipeline_orchestrator_v2 import (
        compute_overall_progress,
        make_sub_progress_event,
    )

    event = make_sub_progress_event(
        stage=2,
        stage_name="Deep Extraction",
        status="running",
        progress_pct=compute_overall_progress(2, sub_pct),
        sub_step=sub_step,
        sub_progress_pct=sub_pct,
    )
    await emit(event)


# ═══════════════════════════════════════════════════════════════════════════
# 2.1 — Full Text + Metadata
# ═══════════════════════════════════════════════════════════════════════════

# Span flag bits (PyMuPDF)
_FLAG_SUPERSCRIPT = 1 << 0
_FLAG_ITALIC = 1 << 1
_FLAG_SERIF = 1 << 2
_FLAG_MONO = 1 << 3
_FLAG_BOLD = 1 << 4


def _extract_spans_from_page(page: fitz.Page) -> Tuple[List[Dict[str, Any]], float, float]:
    """Extract all text spans with metadata from a page.

    Returns (spans_list, width, height).
    """
    raw = page.get_text("dict")
    width = float(page.rect.width)
    height = float(page.rect.height)

    spans: List[Dict[str, Any]] = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:  # text blocks only
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                flags = span.get("flags", 0)
                spans.append({
                    "text": text,
                    "bbox": list(span["bbox"]),
                    "font_name": span.get("font", ""),
                    "font_size": float(span.get("size", 0.0)),
                    "is_bold": bool(flags & _FLAG_BOLD),
                    "is_italic": bool(flags & _FLAG_ITALIC),
                    "is_mono": bool(flags & _FLAG_MONO),
                    "color": int(span.get("color", 0)),
                    "flags": flags,
                })

    return spans, width, height


# ═══════════════════════════════════════════════════════════════════════════
# 2.2 — Text Reconstruction
# ═══════════════════════════════════════════════════════════════════════════


def _merge_spans_to_blocks(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge fragmented spans into text blocks.

    Threshold = font_size * 0.3 (proportional, not fixed).
    Preserves sub_spans[] when block has mixed inline styles.
    sub_spans=None if block is uniform (single span style).
    """
    if not spans:
        return []

    # Sort by Y then X
    sorted_spans = sorted(spans, key=lambda s: (s["bbox"][1], s["bbox"][0]))

    # Group into lines by Y proximity (threshold = font_size * 0.3)
    lines: List[List[Dict[str, Any]]] = []
    current_line: List[Dict[str, Any]] = [sorted_spans[0]]

    for sp in sorted_spans[1:]:
        prev = current_line[-1]
        y_threshold = max(prev["font_size"], sp["font_size"]) * 0.3
        if abs(sp["bbox"][1] - prev["bbox"][1]) <= max(y_threshold, 2.0):
            current_line.append(sp)
        else:
            lines.append(current_line)
            current_line = [sp]
    lines.append(current_line)

    blocks: List[Dict[str, Any]] = []

    for line in lines:
        line.sort(key=lambda s: s["bbox"][0])
        if not line:
            continue

        # Merge spans in line
        merged_groups: List[List[Dict[str, Any]]] = [[line[0]]]

        for nxt in line[1:]:
            acc_last = merged_groups[-1][-1]
            x_gap = nxt["bbox"][0] - acc_last["bbox"][2]
            avg_fs = (acc_last["font_size"] + nxt["font_size"]) / 2
            merge_threshold = avg_fs * 0.3

            # Merge if close enough horizontally
            if x_gap < max(avg_fs * 1.2, 5.0):
                merged_groups[-1].append(nxt)
            else:
                merged_groups.append([nxt])

        # Build blocks from merged groups
        for group in merged_groups:
            block = _build_block_from_spans(group)
            blocks.append(block)

    return blocks


def _build_block_from_spans(spans: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a single text block from a group of merged spans."""
    # Combine text with space where needed
    parts: List[str] = []
    sub_spans: List[Dict[str, Any]] = []
    offset = 0

    # Compute merged bbox
    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)

    for i, sp in enumerate(spans):
        text = sp["text"]
        # Add space between spans if gap > threshold
        if i > 0:
            prev = spans[i - 1]
            x_gap = sp["bbox"][0] - prev["bbox"][2]
            avg_fs = (prev["font_size"] + sp["font_size"]) / 2
            if x_gap > avg_fs * 0.3:
                parts.append(" ")
                offset += 1

        sub_spans.append({
            "text": text,
            "offset": offset,
            "length": len(text),
            "font_name": sp["font_name"],
            "font_size": sp["font_size"],
            "is_bold": sp["is_bold"],
            "is_italic": sp["is_italic"],
            "color": sp["color"],
        })
        parts.append(text)
        offset += len(text)

    full_text = "".join(parts)

    # Determine dominant style (most frequent by text length)
    dominant = max(spans, key=lambda s: len(s["text"]))

    # Check if uniform: all spans have same style
    is_uniform = all(
        s["font_name"] == spans[0]["font_name"]
        and s["font_size"] == spans[0]["font_size"]
        and s["is_bold"] == spans[0]["is_bold"]
        and s["is_italic"] == spans[0]["is_italic"]
        and s["color"] == spans[0]["color"]
        for s in spans
    )

    return {
        "id": str(uuid.uuid4()),
        "text": full_text,
        "bbox": [x0, y0, x1, y1],
        "font_name": dominant["font_name"],
        "font_size": dominant["font_size"],
        "is_bold": dominant["is_bold"],
        "is_italic": dominant["is_italic"],
        "is_mono": dominant.get("is_mono", False),
        "color": dominant["color"],
        "sub_spans": None if is_uniform else sub_spans,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2.3 — Font -> CSS
# ═══════════════════════════════════════════════════════════════════════════


def _font_to_css(
    font_name: str,
    font_size: float,
    is_bold: bool,
    is_italic: bool,
) -> Dict[str, Any]:
    """Convert PDF font to CSS font descriptor using FONT_MAP + span flags."""
    normalized = _normalize_pdf_font_name(font_name)

    css_family = FONT_MAP.get(normalized)
    if css_family is None:
        # Try base name without style suffix
        base = normalized.split("-")[0]
        css_family = FONT_MAP.get(base)
        if css_family is None:
            css_family = normalized or font_name

    # Bold/italic from span flags, NOT from font name
    weight = "bold" if is_bold else "normal"
    style = "italic" if is_italic else "normal"

    return {
        "font_family": css_family,
        "font_size": round(font_size, 2),
        "font_weight": weight,
        "font_style": style,
    }


def _collect_page_fonts(text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collect unique CSS fonts from text blocks on a page."""
    seen: Dict[str, Dict[str, Any]] = {}
    for block in text_blocks:
        key = f"{block['font_name']}|{block['font_size']}|{block['is_bold']}|{block['is_italic']}"
        if key not in seen:
            seen[key] = _font_to_css(
                block["font_name"],
                block["font_size"],
                block["is_bold"],
                block["is_italic"],
            )
    return list(seen.values())


# ═══════════════════════════════════════════════════════════════════════════
# 2.4 — Image Extraction
# ═══════════════════════════════════════════════════════════════════════════

# Minimum image dimensions to avoid masks/artifacts
_MIN_IMG_DIMENSION = 10  # pixels


async def _extract_images(
    page: fitz.Page,
    doc: fitz.Document,
    page_index: int,
    pdf_id: str,
    storage: Any,
    job_id: str,
) -> List[Dict[str, Any]]:
    """Extract embedded images from a page, filter masks, validate bbox."""
    image_list = page.get_images(full=True)
    images: List[Dict[str, Any]] = []

    for img_index, img_info in enumerate(image_list):
        xref = img_info[0]
        try:
            img_data = doc.extract_image(xref)
        except Exception:
            continue

        ext = img_data.get("ext", "png")
        img_bytes = img_data.get("image", b"")
        width = img_data.get("width", 0)
        height = img_data.get("height", 0)

        if not img_bytes:
            continue

        # Filter masks (tiny images)
        if width < _MIN_IMG_DIMENSION or height < _MIN_IMG_DIMENSION:
            continue

        # Collect ALL placements of this xref on the page.
        # PDFs reuse the same image xref in multiple positions (e.g. the Bradesco
        # logo appears twice on a boleto: once in "Recibo do Sacado" and once in
        # "Ficha de Compensação"). Breaking after the first rect caused the second
        # placement to be silently dropped — that logo never appeared in the template.
        placements: List[List[float]] = []
        try:
            for rect in page.get_image_rects(xref):
                placements.append([float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)])
        except Exception:
            pass

        # Fallback: zero bbox (will be marked invalid below)
        if not placements:
            placements = [[0.0, 0.0, 0.0, 0.0]]

        # Upload image bytes once; share the data-URI across all placements.
        filename = f"img_{pdf_id}_{page_index}_{img_index}.{ext}"
        try:
            asset_url = await storage.upload_asset(job_id, filename, img_bytes)
        except Exception as exc:
            logger.warning("Failed to upload image %s: %s", filename, exc)
            asset_url = filename  # fallback to filename

        for placement_bbox in placements:
            bbox_valid = not (
                placement_bbox[0] == 0.0
                and placement_bbox[1] == 0.0
                and placement_bbox[2] == 0.0
                and placement_bbox[3] == 0.0
            )
            images.append({
                "path": asset_url,
                "bbox": placement_bbox,
                "bbox_valid": bbox_valid,
                "format": ext,
            })

    return images


# ═══════════════════════════════════════════════════════════════════════════
# 2.5 — Screenshot (ONLY representatives)
# ═══════════════════════════════════════════════════════════════════════════

_SCREENSHOT_DPI = 150


async def _take_screenshot(
    page: fitz.Page,
    page_index: int,
    pdf_id: str,
    storage: Any,
    job_id: str,
) -> Optional[str]:
    """Render page at 150 DPI, save locally AND upload via storage.

    Always returns a local filesystem path so that Stage 3's
    load_image_as_base64() can open the file with open(path, 'rb'),
    regardless of STORAGE_MODE.  Opção A (Story 15.15).
    """
    try:
        matrix = fitz.Matrix(_SCREENSHOT_DPI / 72, _SCREENSHOT_DPI / 72)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")

        page_key = f"page_{pdf_id}_{page_index}"

        # Save PNG locally so Stage 3 can open it (works for any storage mode)
        local_dir = Path("/tmp/jobs") / job_id / "screenshots"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / f"{page_key}.png"
        local_path.write_bytes(png_bytes)

        # Also upload to remote storage (Supabase or local gateway)
        try:
            await storage.upload_screenshot(job_id, page_key, png_bytes)
        except Exception as upload_exc:
            logger.warning(
                "Storage upload failed for screenshot %s:%d (local copy retained): %s",
                pdf_id, page_index, upload_exc,
            )

        return str(local_path)
    except Exception as exc:
        logger.warning("Failed to take screenshot for page %s:%d: %s", pdf_id, page_index, exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 2.6 — Grid Detection (Jenks Natural Breaks)
# ═══════════════════════════════════════════════════════════════════════════

# Header/footer exclusion zones (normalised Y fractions)
_HEADER_ZONE_END = 0.10
_FOOTER_ZONE_START = 0.90

_MIN_BLOCKS_FOR_GRID = 3
_MAX_BREAKS = 10


def _detect_grid_jenks(
    text_blocks: List[Dict[str, Any]],
    page_height: float,
) -> Optional[Dict[str, Any]]:
    """Detect grid using jenkspy Jenks Natural Breaks, excluding header/footer zones."""
    if len(text_blocks) < _MIN_BLOCKS_FOR_GRID:
        return None

    # Filter out header/footer zones
    body_blocks = [
        b for b in text_blocks
        if page_height > 0 and _HEADER_ZONE_END <= b["bbox"][1] / page_height <= _FOOTER_ZONE_START
    ]

    if len(body_blocks) < _MIN_BLOCKS_FOR_GRID:
        return None

    x_coords = [b["bbox"][0] for b in body_blocks]
    y_coords = [b["bbox"][1] for b in body_blocks]

    col_positions = _jenks_1d(x_coords, _MAX_BREAKS)
    row_positions = _jenks_1d(y_coords, _MAX_BREAKS)

    if not col_positions and not row_positions:
        return None

    return {
        "columns": len(col_positions),
        "rows": len(row_positions),
        "column_positions": [round(p, 2) for p in col_positions],
        "row_positions": [round(p, 2) for p in row_positions],
    }


def _jenks_1d(values: List[float], max_breaks: int) -> List[float]:
    """Cluster 1D values using Jenks Natural Breaks.

    Falls back to simple gap-based grouping if jenkspy is not available.
    """
    if not values or len(set(values)) < 2:
        return [sum(values) / len(values)] if values else []

    unique_vals = sorted(set(values))
    n_unique = len(unique_vals)

    if n_unique <= 2:
        return unique_vals

    # Number of classes = min(unique values, max_breaks)
    n_classes = min(n_unique, max_breaks)

    try:
        import jenkspy

        breaks = jenkspy.jenks_breaks(values, n_classes=n_classes)
        # Compute centroids for each class
        centroids: List[float] = []
        sorted_vals = sorted(values)
        for i in range(len(breaks) - 1):
            low = breaks[i]
            high = breaks[i + 1]
            group = [v for v in sorted_vals if low <= v <= high]
            if group:
                centroids.append(sum(group) / len(group))
        return centroids

    except ImportError:
        logger.warning("jenkspy not available, using gap-based grid detection")
        return _fallback_gap_groups(values, max_breaks)


def _fallback_gap_groups(values: List[float], max_groups: int) -> List[float]:
    """Fallback gap-based grouping when jenkspy is unavailable."""
    sorted_vals = sorted(set(round(v, 1) for v in values))
    if len(sorted_vals) <= 1:
        return [sum(values) / len(values)]

    gaps = [(sorted_vals[i + 1] - sorted_vals[i], i) for i in range(len(sorted_vals) - 1)]
    if not gaps:
        return [sum(values) / len(values)]

    median_gap = sorted(g[0] for g in gaps)[len(gaps) // 2]
    threshold = max(median_gap * 3, 5.0)

    groups: List[List[float]] = [[sorted_vals[0]]]
    for i in range(len(sorted_vals) - 1):
        if sorted_vals[i + 1] - sorted_vals[i] > threshold:
            groups.append([])
        groups[-1].append(sorted_vals[i + 1])

    groups = groups[:max_groups]
    return [sum(g) / len(g) for g in groups if g]


# ═══════════════════════════════════════════════════════════════════════════
# 2.7 — Table Detection (PyMuPDF find_tables)
# ═══════════════════════════════════════════════════════════════════════════


def _detect_tables(page: fitz.Page) -> List[Dict[str, Any]]:
    """Detect tables using PyMuPDF find_tables() (ruling lines + clustering built-in).

    Returns list of raw table dicts with cells.
    """
    try:
        tables_finder = page.find_tables()
    except Exception as exc:
        logger.warning("find_tables() failed: %s", exc)
        return []

    results: List[Dict[str, Any]] = []
    for table in tables_finder.tables:
        bbox = list(table.bbox)
        cells = table.extract()  # List[List[str | None]]
        header = table.header

        # Determine if table has ruling lines
        has_ruling = _check_ruling_lines(page, bbox)

        results.append({
            "raw_cells": cells,
            "bbox": bbox,
            "header": header,
            "has_ruling_lines": has_ruling,
            "col_count": table.col_count if hasattr(table, "col_count") else (len(cells[0]) if cells else 0),
            "row_count": table.row_count if hasattr(table, "row_count") else len(cells),
        })

    return results


def _check_ruling_lines(page: fitz.Page, table_bbox: List[float]) -> bool:
    """Check if there are drawn lines within the table bbox (ruling lines)."""
    try:
        drawings = page.get_drawings()
        x0, y0, x1, y1 = table_bbox
        for d in drawings:
            for item in d.get("items", []):
                if item[0] in ("l", "re"):  # line or rect
                    # Check if any drawing item intersects table bbox
                    return True
        return False
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# 2.8 — Table Structuring
# ═══════════════════════════════════════════════════════════════════════════


def _structure_tables(
    raw_tables: List[Dict[str, Any]],
    text_blocks: List[Dict[str, Any]],
    page_height: float,
) -> List[Dict[str, Any]]:
    """Structure detected tables: cells with bbox, header detection, multi-page continuation."""
    structured: List[Dict[str, Any]] = []

    for raw in raw_tables:
        cells = raw["raw_cells"]
        bbox = raw["bbox"]

        if not cells:
            continue

        col_count = len(cells[0]) if cells else 0
        if col_count == 0:
            continue

        # Detect header rows via style comparison
        header_row_count = _detect_header_rows(cells, text_blocks, bbox)

        # Build headers and rows with cell objects
        headers: List[List[Dict[str, Any]]] = []
        rows: List[List[Dict[str, Any]]] = []

        # Compute approximate cell bboxes
        table_x0, table_y0, table_x1, table_y1 = bbox
        table_width = table_x1 - table_x0
        table_height = table_y1 - table_y0
        row_count = len(cells)

        col_width = table_width / max(col_count, 1)
        row_height = table_height / max(row_count, 1)

        column_widths = [round(col_width, 2)] * col_count

        for row_idx, row_cells in enumerate(cells):
            row_data: List[Dict[str, Any]] = []
            for col_idx, cell_text in enumerate(row_cells):
                cell_x0 = table_x0 + col_idx * col_width
                cell_y0 = table_y0 + row_idx * row_height
                cell_x1 = cell_x0 + col_width
                cell_y1 = cell_y0 + row_height
                row_data.append({
                    "text": cell_text or "",
                    "bbox": [round(cell_x0, 2), round(cell_y0, 2), round(cell_x1, 2), round(cell_y1, 2)],
                    "column_index": col_idx,
                })

            if row_idx < header_row_count:
                headers.append(row_data)
            else:
                rows.append(row_data)

        # Multi-page continuation: table occupies >80% of page height
        is_multi_page = (table_height / max(page_height, 1.0)) > 0.80

        confidence = 0.9 if raw["has_ruling_lines"] else 0.7
        method = "ruling_lines" if raw["has_ruling_lines"] else "clustering"

        structured.append({
            "table_id": str(uuid.uuid4()),
            "bbox": bbox,
            "headers": headers,
            "rows": rows,
            "header_row_count": header_row_count,
            "columns": col_count,
            "column_widths": column_widths,
            "confidence": confidence,
            "detection_method": method,
            "has_ruling_lines": raw["has_ruling_lines"],
            "is_multi_page": is_multi_page,
        })

    return structured


def _detect_header_rows(
    cells: List[List[Optional[str]]],
    text_blocks: List[Dict[str, Any]],
    table_bbox: List[float],
) -> int:
    """Detect header rows by comparing style (bold, font_size) with data rows.

    Returns header_row_count (0, 1, or 2+).
    """
    if not cells or len(cells) < 2:
        return 0

    # Find text blocks within the table bbox top region
    tx0, ty0, tx1, ty1 = table_bbox
    table_height = ty1 - ty0
    row_count = len(cells)
    approx_row_height = table_height / max(row_count, 1)

    # Blocks in first row zone
    first_row_y_max = ty0 + approx_row_height * 1.5
    first_row_blocks = [
        b for b in text_blocks
        if tx0 <= b["bbox"][0] <= tx1 and ty0 <= b["bbox"][1] <= first_row_y_max
    ]

    # Blocks in data zone (after first 2 rows)
    data_y_min = ty0 + approx_row_height * 2
    data_blocks = [
        b for b in text_blocks
        if tx0 <= b["bbox"][0] <= tx1 and b["bbox"][1] >= data_y_min
    ]

    if not first_row_blocks or not data_blocks:
        # Default: assume 1 header if first row text looks different from data
        first_row_text = cells[0]
        data_text = cells[1] if len(cells) > 1 else []
        if first_row_text and data_text:
            # Simple heuristic: if first row has no numbers but data has, it's a header
            return 1
        return 0

    # Compare average font sizes
    first_avg_size = sum(b["font_size"] for b in first_row_blocks) / len(first_row_blocks)
    data_avg_size = sum(b["font_size"] for b in data_blocks) / len(data_blocks)

    # Compare bold ratio
    first_bold_ratio = sum(1 for b in first_row_blocks if b["is_bold"]) / len(first_row_blocks)
    data_bold_ratio = sum(1 for b in data_blocks if b["is_bold"]) / max(len(data_blocks), 1)

    if first_bold_ratio > data_bold_ratio + 0.3 or first_avg_size > data_avg_size * 1.1:
        # Check if second row is also header-like
        if row_count > 2:
            second_row_y_min = ty0 + approx_row_height
            second_row_y_max = ty0 + approx_row_height * 2.5
            second_row_blocks = [
                b for b in text_blocks
                if tx0 <= b["bbox"][0] <= tx1 and second_row_y_min <= b["bbox"][1] <= second_row_y_max
            ]
            if second_row_blocks:
                second_bold_ratio = sum(1 for b in second_row_blocks if b["is_bold"]) / len(second_row_blocks)
                if second_bold_ratio > data_bold_ratio + 0.3:
                    return 2
        return 1

    return 0


# ═══════════════════════════════════════════════════════════════════════════
# 2.9 — Quality Check + Drawn Elements
# ═══════════════════════════════════════════════════════════════════════════


def _extract_drawn_elements(page: fitz.Page) -> Optional[List[Dict[str, Any]]]:
    """Extract drawn elements (lines, rects, curves) via get_drawings()."""
    try:
        drawings = page.get_drawings()
    except Exception:
        return None

    if not drawings:
        return None

    elements: List[Dict[str, Any]] = []
    for d in drawings:
        fill_color = d.get("fill")
        stroke_color = d.get("color")
        width = d.get("width", 0.0)

        fill_int = _color_to_int(fill_color) if fill_color else None
        stroke_int = _color_to_int(stroke_color) if stroke_color else None
        # width may be None for filled shapes without explicit stroke width
        safe_width = round(float(width or 0.0), 2)

        for item in d.get("items", []):
            kind = item[0]  # "l" = line, "re" = rect, "c" = curve, "qu" = quad
            if kind == "l":
                p1, p2 = item[1], item[2]
                bbox = [
                    min(p1.x, p2.x), min(p1.y, p2.y),
                    max(p1.x, p2.x), max(p1.y, p2.y),
                ]
                orientation = _line_orientation(p1, p2)
                elements.append({
                    "type": "line",
                    "bbox": [round(v, 2) for v in bbox],
                    "orientation": orientation,
                    "fill_color": fill_int,
                    "stroke_color": stroke_int,
                    "width": safe_width,
                })
            elif kind == "re":
                rect = item[1]
                elements.append({
                    "type": "rect",
                    "bbox": [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)],
                    "orientation": None,
                    "fill_color": fill_int,
                    "stroke_color": stroke_int,
                    "width": safe_width,
                })
            elif kind == "c":
                # Curve: use bounding points
                points = item[1:]
                if points:
                    xs = [p.x for p in points if hasattr(p, "x")]
                    ys = [p.y for p in points if hasattr(p, "y")]
                    if xs and ys:
                        elements.append({
                            "type": "curve",
                            "bbox": [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)],
                            "orientation": None,
                            "fill_color": fill_int,
                            "stroke_color": stroke_int,
                            "width": safe_width,
                        })

    return elements if elements else None


def _color_to_int(color: Any) -> Optional[int]:
    """Convert PyMuPDF color (tuple of 0-1 floats) to RGB int."""
    if color is None:
        return None
    if isinstance(color, (int, float)):
        # Grayscale
        v = int(round(float(color) * 255))
        return (v << 16) | (v << 8) | v
    if isinstance(color, (tuple, list)):
        if len(color) == 1:
            v = int(round(color[0] * 255))
            return (v << 16) | (v << 8) | v
        if len(color) >= 3:
            r = int(round(color[0] * 255))
            g = int(round(color[1] * 255))
            b = int(round(color[2] * 255))
            return (r << 16) | (g << 8) | b
    return None


def _line_orientation(p1: Any, p2: Any) -> Optional[str]:
    """Determine line orientation: horizontal, vertical, or diagonal."""
    threshold = 2.0  # points
    dx = abs(p1.x - p2.x)
    dy = abs(p1.y - p2.y)

    if dy < threshold and dx > threshold:
        return "horizontal"
    if dx < threshold and dy > threshold:
        return "vertical"
    if dx > threshold and dy > threshold:
        return "diagonal"
    return None


def _quality_check(
    page_data: Dict[str, Any],
    page_index: int,
    pdf_id: str,
) -> List[Dict[str, Any]]:
    """Run 5 quality validations on extracted page data.

    1. text_blocks not empty
    2. encoding OK (no replacement chars)
    3. no duplicate text blocks
    4. tables valid (if any)
    5. images have bbox (if any)
    """
    warnings: List[Dict[str, Any]] = []
    page_key = f"{pdf_id}:{page_index}"

    # 1. text_blocks not empty
    text_blocks = page_data.get("text_blocks", [])
    if not text_blocks:
        warnings.append({
            "page_key": page_key,
            "page_index": page_index,
            "type": "empty_page",
            "severity": "warning",
            "message": f"Page {page_index}: no text blocks extracted",
        })

    # 2. encoding check
    for block in text_blocks:
        text = block.get("text", "")
        if "\ufffd" in text or "\x00" in text:
            warnings.append({
                "page_key": page_key,
                "page_index": page_index,
                "type": "encoding_issue",
                "severity": "warning",
                "message": f"Page {page_index}: encoding issues detected in text block",
            })
            break

    # 3. duplicate detection
    texts = [b["text"].strip() for b in text_blocks if b.get("text")]
    if texts:
        unique = set(texts)
        dup_ratio = 1.0 - len(unique) / len(texts)
        if dup_ratio > 0.5 and len(texts) > 3:
            warnings.append({
                "page_key": page_key,
                "page_index": page_index,
                "type": "duplicate_text",
                "severity": "warning",
                "message": f"Page {page_index}: {dup_ratio:.0%} duplicate text blocks detected",
            })

    # 4. tables validation
    tables = page_data.get("tables", [])
    for tbl in tables:
        if not tbl.get("rows") and not tbl.get("headers"):
            warnings.append({
                "page_key": page_key,
                "page_index": page_index,
                "type": "invalid_table",
                "severity": "warning",
                "message": f"Page {page_index}: table {tbl.get('table_id', '?')} has no rows or headers",
            })

    # 5. images bbox validation
    images = page_data.get("images", [])
    invalid_bbox_count = sum(1 for img in images if not img.get("bbox_valid", True))
    if invalid_bbox_count > 0:
        warnings.append({
            "page_key": page_key,
            "page_index": page_index,
            "type": "invalid_image_bbox",
            "severity": "warning",
            "message": f"Page {page_index}: {invalid_bbox_count} image(s) with invalid bbox",
        })

    return warnings


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════


async def run_stage2(
    context: Dict[str, Any],
    emit_progress: EmitProgressFn,
) -> Dict[str, Any]:
    """Stage 2: Deep Extraction — ONLY representative pages.

    Args:
        context: Pipeline context with clusters, pdf_documents, _storage, job_id.
        emit_progress: Async callback for SSE events.

    Returns:
        Updated context with enriched_documents, extraction_warnings.
    """
    context["_current_stage"] = 2
    context["_current_stage_name"] = "Deep Extraction"

    # Check PyMuPDF version
    check_pymupdf_version()

    clusters: List[Dict[str, Any]] = context.get("clusters", [])
    pdf_documents: List[Dict[str, str]] = context.get("pdf_documents", [])
    storage = context.get("_storage")
    job_id = context.get("job_id", "")

    if not clusters or not pdf_documents:
        context["enriched_documents"] = []
        context["extraction_warnings"] = []
        from services.pipeline_orchestrator_v2 import make_sub_progress_event, compute_overall_progress
        await emit_progress(make_sub_progress_event(
            stage=2, stage_name="Deep Extraction", status="running",
            progress_pct=compute_overall_progress(2, 1.0), sub_step="2.0 Complete",
            sub_progress_pct=1.0,
            summary={"pages_processed": 0, "warnings": 0},
        ))
        return context

    # Build pdf_id -> path map
    pdf_docs_map: Dict[str, str] = {}
    pdf_names_map: Dict[str, str] = {}
    for doc in pdf_documents:
        pid = str(doc["id"])
        pdf_docs_map[pid] = doc["path"]
        pdf_names_map[pid] = doc.get("name", "")

    # Identify representative pages and build cluster membership
    representative_pages: List[Dict[str, Any]] = []
    page_cluster_map: Dict[str, str] = {}  # "pdf_id:page_index" -> cluster_id
    page_representative_map: Dict[str, bool] = {}  # "pdf_id:page_index" -> is_representative

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        rep = cluster.get("representative_page", {})
        rep_key = f"{rep['pdf_id']}:{rep['page_index']}"

        for page_info in cluster.get("pages", []):
            pk = f"{page_info['pdf_id']}:{page_info['page_index']}"
            page_cluster_map[pk] = cluster_id
            page_representative_map[pk] = (pk == rep_key)

        representative_pages.append({
            "pdf_id": rep["pdf_id"],
            "page_index": rep["page_index"],
            "cluster_id": cluster_id,
        })

    # ═══════════════════════════════════════════
    # Process ONLY representative pages
    # ═══════════════════════════════════════════

    # Group by pdf_id for efficient PDF opening
    reps_by_pdf: Dict[str, List[Dict[str, Any]]] = {}
    for rp in representative_pages:
        reps_by_pdf.setdefault(rp["pdf_id"], []).append(rp)

    # Result containers
    enriched_by_pdf: Dict[str, Dict[str, Any]] = {}
    all_warnings: List[Dict[str, Any]] = []

    total_reps = len(representative_pages)
    processed = 0

    for pdf_id, reps in reps_by_pdf.items():
        pdf_path = pdf_docs_map.get(pdf_id)
        if not pdf_path:
            continue

        doc = fitz.open(pdf_path)
        pdf_name = pdf_names_map.get(pdf_id, "")

        if pdf_id not in enriched_by_pdf:
            enriched_by_pdf[pdf_id] = {
                "pdf_id": pdf_id,
                "pdf_name": pdf_name,
                "pages": [],
            }

        for rp in reps:
            page_index = rp["page_index"]
            cluster_id = rp["cluster_id"]

            if page_index >= len(doc):
                continue

            page = doc[page_index]

            # --- 2.1 Full Text + Metadata ---
            await _emit_sub(emit_progress, "2.1 Text Extraction", processed / max(total_reps, 1) * 0.15)
            spans, width, height = _extract_spans_from_page(page)

            # --- 2.2 Text Reconstruction ---
            await _emit_sub(emit_progress, "2.2 Text Reconstruction", processed / max(total_reps, 1) * 0.25)
            text_blocks = _merge_spans_to_blocks(spans)

            # --- 2.3 Font -> CSS ---
            fonts = _collect_page_fonts(text_blocks)

            # --- 2.4 Image Extraction ---
            await _emit_sub(emit_progress, "2.4 Image Extraction", 0.30 + processed / max(total_reps, 1) * 0.15)
            if storage is not None:
                images = await _extract_images(page, doc, page_index, pdf_id, storage, job_id)
            else:
                images = []

            # --- 2.5 Screenshot ---
            await _emit_sub(emit_progress, "2.5 Screenshot", 0.45 + processed / max(total_reps, 1) * 0.10)
            if storage is not None:
                screenshot_path = await _take_screenshot(page, page_index, pdf_id, storage, job_id)
            else:
                screenshot_path = None

            # --- 2.6 Grid Detection ---
            await _emit_sub(emit_progress, "2.6 Grid Detection", 0.55 + processed / max(total_reps, 1) * 0.10)
            grid_info = _detect_grid_jenks(text_blocks, height)

            # --- 2.7 Table Detection ---
            await _emit_sub(emit_progress, "2.7 Table Detection", 0.65 + processed / max(total_reps, 1) * 0.10)
            raw_tables = _detect_tables(page)

            # --- 2.8 Table Structuring ---
            await _emit_sub(emit_progress, "2.8 Table Structuring", 0.75 + processed / max(total_reps, 1) * 0.10)
            tables = _structure_tables(raw_tables, text_blocks, height)

            # --- 2.9 Quality Check + Drawn Elements ---
            await _emit_sub(emit_progress, "2.9 Quality Check", 0.85 + processed / max(total_reps, 1) * 0.15)
            drawn_elements = _extract_drawn_elements(page)

            page_data: Dict[str, Any] = {
                "page_index": page_index,
                "cluster_id": cluster_id,
                "is_representative": True,
                "width": width,
                "height": height,
                "text_blocks": text_blocks,
                "images": images,
                "fonts": fonts,
                "grid_info": grid_info,
                "screenshot_path": screenshot_path,
                "tables": tables,
                "drawn_elements": drawn_elements,
            }

            # Quality check
            page_warnings = _quality_check(page_data, page_index, pdf_id)
            all_warnings.extend(page_warnings)

            enriched_by_pdf[pdf_id]["pages"].append(page_data)
            processed += 1

        doc.close()

    # Also add non-representative pages with minimal data (cluster_id, is_representative=False)
    # Group by pdf_id to avoid reopening PDFs for each page
    non_rep_by_pdf: Dict[str, List[Tuple[int, str]]] = {}  # pdf_id -> [(page_index, cluster_id)]
    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        rep = cluster.get("representative_page", {})
        rep_key = f"{rep['pdf_id']}:{rep['page_index']}"

        for page_info in cluster.get("pages", []):
            pk = f"{page_info['pdf_id']}:{page_info['page_index']}"
            if pk == rep_key:
                continue  # already processed

            pdf_id = page_info["pdf_id"]
            page_index = page_info["page_index"]
            non_rep_by_pdf.setdefault(pdf_id, []).append((page_index, cluster_id))

    for pdf_id, pages_info in non_rep_by_pdf.items():
        if pdf_id not in enriched_by_pdf:
            enriched_by_pdf[pdf_id] = {
                "pdf_id": pdf_id,
                "pdf_name": pdf_names_map.get(pdf_id, ""),
                "pages": [],
            }

        pdf_path = pdf_docs_map.get(pdf_id)
        _doc = None
        if pdf_path:
            try:
                _doc = fitz.open(pdf_path)
            except Exception:
                pass

        for page_index, cluster_id in pages_info:
            w, h = 0.0, 0.0
            if _doc is not None and page_index < len(_doc):
                _page = _doc[page_index]
                w = float(_page.rect.width)
                h = float(_page.rect.height)

            enriched_by_pdf[pdf_id]["pages"].append({
                "page_index": page_index,
                "cluster_id": cluster_id,
                "is_representative": False,
                "width": w,
                "height": h,
                "text_blocks": [],
                "images": [],
                "fonts": [],
                "grid_info": None,
                "screenshot_path": None,
                "tables": [],
                "drawn_elements": None,
            })

        if _doc is not None:
            _doc.close()

    # Build final output
    enriched_documents = list(enriched_by_pdf.values())

    # Sort pages within each document
    for doc_data in enriched_documents:
        doc_data["pages"].sort(key=lambda p: p["page_index"])

    context["enriched_documents"] = enriched_documents
    context["extraction_warnings"] = all_warnings

    await _emit_sub(emit_progress, "2.9 Complete", 1.0)

    logger.info(
        "Stage 2 complete: %d representative pages processed, %d warnings",
        processed,
        len(all_warnings),
    )

    # Emit final summary for the accordion
    from services.pipeline_orchestrator_v2 import make_sub_progress_event, compute_overall_progress
    rep_pages = [
        p
        for doc_data in enriched_documents
        for p in doc_data.get("pages", [])
        if p.get("is_representative")
    ]
    total_blocks = sum(len(p.get("text_blocks", [])) for p in rep_pages)
    total_images = sum(len(p.get("images", [])) for p in rep_pages)
    total_tables = sum(len(p.get("tables", [])) for p in rep_pages)
    total_fonts = sum(len(p.get("fonts", [])) for p in rep_pages)
    await emit_progress(make_sub_progress_event(
        stage=2, stage_name="Deep Extraction", status="running",
        progress_pct=compute_overall_progress(2, 1.0), sub_step="2.9 Complete",
        sub_progress_pct=1.0,
        summary={
            "pages_processed": processed,
            "blocks_extracted": total_blocks,
            "warnings": len(all_warnings),
            "images_extracted": total_images,
            "tables_detected": total_tables,
            "fonts_identified": total_fonts,
        },
    ))

    return context
