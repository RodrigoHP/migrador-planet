"""Stage 2 — Text Extraction sub-module.

Responsibilities:
  - Span extraction from PDF pages (2.1)
  - Text block reconstruction from spans (2.2)
  - Font CSS mapping (2.3)

Story 41.3 — extracted from stage2_deep_extraction.py
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import fitz  # PyMuPDF

from models.pipeline_context import FontInfo, TextBlock

# ---------------------------------------------------------------------------
# FONT_MAP — Expanded ~50 fonts PDF -> CSS (2.3)
# ---------------------------------------------------------------------------

FONT_MAP: dict[str, str] = {
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

# Span flag bits (PyMuPDF)
_FLAG_SUPERSCRIPT = 1 << 0
_FLAG_ITALIC = 1 << 1
_FLAG_SERIF = 1 << 2
_FLAG_MONO = 1 << 3
_FLAG_BOLD = 1 << 4


def _normalize_pdf_font_name(raw_name: str) -> str:
    """Strip subset prefix (ABCDEF+FontName -> FontName)."""
    return _SUBSET_PREFIX_RE.sub("", raw_name)


# ---------------------------------------------------------------------------
# 2.1 — Full Text + Metadata
# ---------------------------------------------------------------------------


def _extract_spans_from_page(page: fitz.Page) -> tuple[list[dict[str, Any]], float, float]:
    """Extract all text spans with metadata from a page.

    Returns (spans_list, width, height).
    """
    raw = page.get_text("dict")
    width = float(page.rect.width)
    height = float(page.rect.height)

    spans: list[dict[str, Any]] = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:  # text blocks only
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                flags = span.get("flags", 0)
                spans.append(
                    {
                        "text": text,
                        "bbox": list(span["bbox"]),
                        "font_name": span.get("font", ""),
                        "font_size": float(span.get("size", 0.0)),
                        "is_bold": bool(flags & _FLAG_BOLD),
                        "is_italic": bool(flags & _FLAG_ITALIC),
                        "is_mono": bool(flags & _FLAG_MONO),
                        "color": int(span.get("color", 0)),
                        "flags": flags,
                    }
                )

    return spans, width, height


# ---------------------------------------------------------------------------
# 2.2 — Text Reconstruction
# ---------------------------------------------------------------------------


def _build_block_from_spans(spans: list[dict[str, Any]]) -> TextBlock:
    """Build a TextBlock from a group of merged spans."""
    # Combine text with space where needed
    parts: list[str] = []
    sub_spans: list[dict[str, Any]] = []
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

        sub_spans.append(
            {
                "text": text,
                "offset": offset,
                "length": len(text),
                "font_name": sp["font_name"],
                "font_size": sp["font_size"],
                "is_bold": sp["is_bold"],
                "is_italic": sp["is_italic"],
                "color": sp["color"],
            }
        )
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

    return TextBlock(
        id=str(uuid.uuid4()),
        text=full_text,
        bbox=[x0, y0, x1, y1],
        font_name=dominant["font_name"],
        font_size=dominant["font_size"],
        is_bold=dominant["is_bold"],
        is_italic=dominant["is_italic"],
        is_mono=dominant.get("is_mono", False),
        color=dominant["color"],
        sub_spans=None if is_uniform else sub_spans,
    )


def _merge_spans_to_blocks(spans: list[dict[str, Any]]) -> list[TextBlock]:
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
    lines: list[list[dict[str, Any]]] = []
    current_line: list[dict[str, Any]] = [sorted_spans[0]]

    for sp in sorted_spans[1:]:
        prev = current_line[-1]
        y_threshold = max(prev["font_size"], sp["font_size"]) * 0.3
        if abs(sp["bbox"][1] - prev["bbox"][1]) <= max(y_threshold, 2.0):
            current_line.append(sp)
        else:
            lines.append(current_line)
            current_line = [sp]
    lines.append(current_line)

    blocks: list[TextBlock] = []

    for line in lines:
        line.sort(key=lambda s: s["bbox"][0])
        if not line:
            continue

        # Merge spans in line
        merged_groups: list[list[dict[str, Any]]] = [[line[0]]]

        for nxt in line[1:]:
            acc_last = merged_groups[-1][-1]
            x_gap = nxt["bbox"][0] - acc_last["bbox"][2]
            avg_fs = (acc_last["font_size"] + nxt["font_size"]) / 2
            _merge_threshold = avg_fs * 0.3  # noqa: F841 — kept for documentation

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


# ---------------------------------------------------------------------------
# 2.3 — Font -> CSS
# ---------------------------------------------------------------------------


def _font_to_css(
    font_name: str,
    font_size: float,
    is_bold: bool,
    is_italic: bool,
) -> dict[str, Any]:
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


def _collect_page_fonts(text_blocks: list[TextBlock]) -> list[FontInfo]:
    """Collect unique CSS fonts from text blocks on a page."""
    seen: dict[str, FontInfo] = {}
    for block in text_blocks:
        key = f"{block.font_name}|{block.font_size}|{block.is_bold}|{block.is_italic}"
        if key not in seen:
            css = _font_to_css(block.font_name, block.font_size, block.is_bold, block.is_italic)
            seen[key] = FontInfo(
                name=block.font_name,
                css_family=css["font_family"],
                size=block.font_size,
                is_bold=block.is_bold,
                is_italic=block.is_italic,
            )
    return list(seen.values())
