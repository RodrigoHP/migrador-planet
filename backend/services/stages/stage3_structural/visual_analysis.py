"""Stage 3 — Visual Analysis sub-module (Step 3.2).

Responsibilities:
  - Mistral OCR (unconditional) for raster table extraction + zone detection
  - PyMuPDF for raster image bbox (replaces GPT-4o Vision bbox)
  - Response parsing and validation
  - Fallback analysis using adaptive thresholds

Story 41.3 — extracted from stage3_structural_analysis.py
Story 46.2 — GPT-4o Vision eliminated; replaced by Mistral + PyMuPDF
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

EmitProgressFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Visual Analysis Prompt
# ---------------------------------------------------------------------------

_VISUAL_ANALYSIS_PROMPT = """\
Analyze this document page image. Return ONLY valid JSON with:

1. "regions": visual regions with bbox and type
2. For each region: "html_suggestion" (representative HTML snippet)
3. For chart_area: identify "chart_type" (bar|line|pie|doughnut|polarArea) and "confidence" (0-100)
4. For barcode_area: identify "barcode_format" (CODE128|CODE39|EAN13|EAN8|UPC|ITF|MSI) and "confidence" (0-100)
5. For svg_area: identify vector graphics (logos, icons, decorative shapes) and "confidence" (0-100)
6. Compare your visual analysis against this programmatic extraction:
   {extraction_summary}

   Provide a "consistency_score" (0-100).

JSON structure:
{{
  "regions": [
    {{
      "type": "header|body|footer|sidebar|table_area|chart_area|barcode_area|image_area|svg_area",
      "bbox": [x0, y0, x1, y1],
      "description": "brief description of content",
      "html_suggestion": "<suggested HTML for this region>",
      "chart_type": "bar",
      "barcode_format": "CODE128",
      "confidence": 85
    }}
  ],
  "consistency_score": 85,
  "consistency_notes": "brief notes on discrepancies"
}}
"""

VALID_REGION_TYPES = {
    "header",
    "body",
    "footer",
    "sidebar",
    "table_area",
    "chart_area",
    "barcode_area",
    "image_area",
    "svg_area",
}

# ---------------------------------------------------------------------------
# PIL Color Sampling for Raster Tables (Story 43.5)
# ---------------------------------------------------------------------------


def sample_table_colors(
    image_path: str,
    row_heights_pct: list[float] | None = None,
    header_height_frac: float = 0.12,
) -> dict[str, Any]:
    """Sample background colors from a raster table crop image.

    Args:
        image_path: Path to PNG/JPEG crop of the full table.
        row_heights_pct: Fractional height of each data row (from Mistral layout).
            If provided, returns row_bg_colors (one hex per row) in addition to header.
            If None, only header_bg_color is returned (legacy behavior).
        header_height_frac: Fraction of image height for header strip (default 12%).

    Returns:
        dict with:
          - header_bg_color: str hex (#RRGGBB) — median of top strip
          - border_color: str hex — 5th-percentile darkest edge pixel
          - row_bg_colors: list[str] hex — per-row background (only when row_heights_pct given)
        Any field is None if PIL unavailable or sampling fails.
    """
    try:
        import statistics

        from PIL import Image
    except ImportError:
        result: dict[str, Any] = {"header_bg_color": None, "border_color": None}
        if row_heights_pct is not None:
            result["row_bg_colors"] = [None] * len(row_heights_pct)
        return result

    try:
        img = Image.open(image_path).convert("RGB")
    except OSError:
        result = {"header_bg_color": None, "border_color": None}
        if row_heights_pct is not None:
            result["row_bg_colors"] = [None] * len(row_heights_pct)
        return result

    w, h = img.size
    inset = min(5, w // 4)

    # Header strip: top header_height_frac of image
    header_h = max(1, int(h * header_height_frac))
    header_pixels = list(img.crop((inset, inset, w - inset, header_h)).getdata())
    if header_pixels:
        r_med = int(statistics.median(p[0] for p in header_pixels))
        g_med = int(statistics.median(p[1] for p in header_pixels))
        b_med = int(statistics.median(p[2] for p in header_pixels))
        header_bg_color: str | None = f"#{r_med:02X}{g_med:02X}{b_med:02X}"
    else:
        header_bg_color = None

    # Border color: 5th-percentile darkest pixel from top+left edge band
    edge_band = min(6, h // 4, w // 4)
    edge_pixels: list[tuple[int, int, int]] = []
    for strip in [img.crop((0, 0, w, edge_band)), img.crop((0, 0, edge_band, h))]:
        edge_pixels.extend(strip.getdata())  # type: ignore[arg-type]
    if edge_pixels:
        edge_pixels.sort(key=lambda p: p[0] + p[1] + p[2])
        idx_5pct = max(0, int(len(edge_pixels) * 0.05) - 1)
        rp, gp, bp = edge_pixels[idx_5pct]
        border_color: str | None = f"#{rp:02X}{gp:02X}{bp:02X}"
    else:
        border_color = None

    result = {"header_bg_color": header_bg_color, "border_color": border_color}

    # Per-row background sampling (AC1 — Story 43.5)
    if row_heights_pct:
        row_bg_colors: list[str | None] = []
        y = 0
        for pct in row_heights_pct:
            row_h = max(1, int(h * pct))
            cy = y + row_h // 2  # vertical center of row
            strip_top = max(0, cy - 2)
            strip_bot = min(h, cy + 2)
            strip = img.crop((inset, strip_top, w - inset, strip_bot))
            strip_pixels = list(strip.getdata())
            if strip_pixels:
                rs = int(statistics.median(p[0] for p in strip_pixels))
                gs = int(statistics.median(p[1] for p in strip_pixels))
                bs = int(statistics.median(p[2] for p in strip_pixels))
                row_bg_colors.append(f"#{rs:02X}{gs:02X}{bs:02X}")
            else:
                row_bg_colors.append(None)
            y += row_h
        result["row_bg_colors"] = row_bg_colors

    return result


# ---------------------------------------------------------------------------
# Font & Style Enrichment for Raster Tables (Story 43.6)
# ---------------------------------------------------------------------------

_SCREENSHOT_SCALE = 150 / 72  # DPI ratio: stage2 renders at 150dpi, PDF points at 72dpi


def extract_dominant_font(
    text_blocks: list[Any],
    bbox: list[float],
) -> dict[str, Any]:
    """Find dominant font in text blocks overlapping with a bbox region.

    Uses Stage 2 extracted text_blocks (already have font_name, font_size, is_bold,
    font_color) — no need to re-open the PDF.

    Args:
        text_blocks: list of TextBlock objects or dicts from page_data["text_blocks"]
        bbox: [x0, y0, x1, y1] in PDF point coordinates

    Returns:
        dict with font_family, font_size_pt, font_weight, text_color; empty if no overlap.
    """
    from collections import Counter

    def _get(block: Any, attr: str) -> Any:
        return block.get(attr) if isinstance(block, dict) else getattr(block, attr, None)

    def _overlaps(block_bbox: list[float], region: list[float]) -> bool:
        bx0, by0, bx1, by1 = block_bbox
        rx0, ry0, rx1, ry1 = region
        return not (bx1 < rx0 or bx0 > rx1 or by1 < ry0 or by0 > ry1)

    matching = [b for b in text_blocks if (bb := _get(b, "bbox")) is not None and _overlaps(bb, bbox)]
    if not matching:
        return {}

    fonts = Counter(_get(b, "font_name") for b in matching if _get(b, "font_name"))
    sizes = [s for b in matching if (s := _get(b, "font_size"))]
    bold_count = sum(1 for b in matching if _get(b, "is_bold"))
    colors = Counter(_get(b, "font_color") for b in matching if _get(b, "font_color"))

    raw_font = fonts.most_common(1)[0][0] if fonts else ""
    # Normalize: "ArialMT_feDefaultFont[0]" → "Arial"
    clean_font = raw_font.split("[")[0].split("_")[0] if raw_font else None
    avg_size = round(sum(sizes) / len(sizes), 1) if sizes else None
    is_bold = bold_count > len(matching) / 2
    dominant_color = colors.most_common(1)[0][0] if colors else None

    return {
        "font_family": clean_font,
        "font_size_pt": avg_size,
        "font_weight": "bold" if is_bold else "normal",
        "text_color": dominant_color,
    }


def _crop_table_image(screenshot_path: str, table_bbox_pdf: list[float]) -> str | None:
    """Crop page screenshot to table bbox and write to a temp PNG.

    Coordinates are in PDF points (72dpi); screenshot is at 150dpi.
    Returns path to temp PNG, or None on failure.
    """
    import tempfile

    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        img = Image.open(screenshot_path)
    except OSError:
        return None

    x0, y0, x1, y1 = table_bbox_pdf
    px0 = max(0, int(x0 * _SCREENSHOT_SCALE))
    py0 = max(0, int(y0 * _SCREENSHOT_SCALE))
    px1 = min(img.width, int(x1 * _SCREENSHOT_SCALE))
    py1 = min(img.height, int(y1 * _SCREENSHOT_SCALE))

    if px1 <= px0 or py1 <= py0:
        return None

    crop = img.crop((px0, py0, px1, py1))
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    crop.save(tmp.name)
    tmp.close()
    return tmp.name


def _enrich_raster_table_style(
    table: dict[str, Any],
    page_data: dict[str, Any],
    screenshot_path: str | None,
) -> None:
    """Enrich raster table dict with font and color style data. Modifies in-place.

    Story 43.6 — integrates PyMuPDF font data (via Stage 2 text_blocks)
    and PIL per-row color sampling into table["style"].
    """
    import os

    table_bbox = table.get("bbox", [0.0, 0.0, 0.0, 0.0])

    # Font: dominant font from Stage 2 text_blocks in the table bbox
    text_blocks = page_data.get("text_blocks", [])
    font_data = extract_dominant_font(text_blocks, table_bbox)

    # Colors: PIL sampling from page screenshot crop
    color_data: dict[str, Any] = {}
    crop_path: str | None = None
    if screenshot_path:
        crop_path = _crop_table_image(screenshot_path, table_bbox)
        if crop_path:
            row_heights_pct = table.get("layout", {}).get("row_heights_pct")
            color_data = sample_table_colors(crop_path, row_heights_pct=row_heights_pct)
            try:
                os.unlink(crop_path)
            except OSError:
                pass

    table["style"] = {
        "font_family": font_data.get("font_family"),
        "font_size_pt": font_data.get("font_size_pt"),
        "font_weight": font_data.get("font_weight"),
        "text_color": font_data.get("text_color"),
        "header_bg_color": color_data.get("header_bg_color"),
        "row_bg_colors": color_data.get("row_bg_colors"),
        "border_color": color_data.get("border_color"),
        "border_width_pt": 1.0,
    }


# ---------------------------------------------------------------------------
# Raster Table Extraction via Mistral OCR PDF (Story 43.2 rev — ADR 2026-04-13)
# Story 46.2 — GPT-4o Vision eliminated; Mistral called unconditionally
# ---------------------------------------------------------------------------

# Minimum image area in PDF points² to be considered a raster table
# (filters out logos/barcodes which are typically small)
_MIN_TABLE_AREA_PTS: float = 100.0 * 50.0  # 5 000 sq pts


def _get_raster_image_bboxes_pymupdf(pdf_path: str, page_index: int) -> list[list[float]]:
    """Return bboxes of raster images on the page sorted by area descending (PDF points).

    Only images with area >= _MIN_TABLE_AREA_PTS are returned.
    Used by _extract_raster_table_mistral to obtain accurate table bbox without GPT-4o.

    Story 46.2 — AC2: bbox via PyMuPDF (replaces GPT-4o region_bbox).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return []

    try:
        doc = fitz.open(pdf_path)
        page = doc[page_index]
        bboxes: list[list[float]] = []
        for img in page.get_images(full=True):
            try:
                rect = page.get_image_bbox(img)
                w = rect.x1 - rect.x0
                h = rect.y1 - rect.y0
                if w * h >= _MIN_TABLE_AREA_PTS:
                    bboxes.append([rect.x0, rect.y0, rect.x1, rect.y1])
            except Exception:
                continue
        doc.close()
        # Largest image first — most likely to be the raster table
        bboxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
        return bboxes
    except Exception as exc:
        logger.warning("PyMuPDF image bbox failed for %s page %d: %s", pdf_path, page_index, exc)
        return []


def _build_regions_from_mistral(
    extracted_table: dict[str, Any] | None,
    zones: dict[str, str | None],
    page_width: float,
    page_height: float,
) -> dict[str, Any]:
    """Build visual_analysis regions dict from Mistral results.

    Produces the same format as the legacy GPT-4o visual analysis response so that
    downstream consumers (section_utils, tree_builder) remain unchanged.

    Story 46.2 — AC3: header/footer zones from Mistral extract_header/extract_footer.
    """
    regions: list[dict[str, Any]] = []

    header_text = zones.get("header") or ""
    footer_text = zones.get("footer") or ""

    # Header region — from Mistral extract_header
    if header_text and header_text != "#":
        header_h = int(page_height * 0.15)
        regions.append(
            {
                "type": "header",
                "bbox": [0, 0, int(page_width), header_h],
                "description": f"Header: {header_text[:80]}",
                "html_suggestion": "<header></header>",
                "chart_type": None,
                "barcode_format": None,
                "confidence": 90,
            }
        )

    # Raster table_area region — from Mistral tables[] + PyMuPDF bbox
    if extracted_table is not None:
        bbox = extracted_table["bbox"]
        regions.append(
            {
                "type": "table_area",
                "bbox": [int(v) for v in bbox],
                "description": "Raster table — Mistral OCR + PyMuPDF bbox",
                "html_suggestion": "<table></table>",
                "chart_type": None,
                "barcode_format": None,
                "confidence": 95,
            }
        )

    # Body region — always present; bounds adjusted for header/footer
    body_y0 = int(page_height * 0.15) if (header_text and header_text != "#") else 0
    body_y1 = int(page_height * 0.90) if (footer_text and footer_text != "#") else int(page_height)
    regions.append(
        {
            "type": "body",
            "bbox": [0, body_y0, int(page_width), body_y1],
            "description": "Body content area",
            "html_suggestion": "<main></main>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": 80,
        }
    )

    # Footer region — from Mistral extract_footer
    if footer_text and footer_text != "#":
        footer_y = int(page_height * 0.90)
        regions.append(
            {
                "type": "footer",
                "bbox": [0, footer_y, int(page_width), int(page_height)],
                "description": f"Footer: {footer_text[:80]}",
                "html_suggestion": "<footer></footer>",
                "chart_type": None,
                "barcode_format": None,
                "confidence": 90,
            }
        )

    return {
        "regions": regions,
        "consistency_score": 85,
        "consistency_notes": "Mistral OCR + PyMuPDF (Story 46.2 — no GPT-4o Vision)",
        "consistency_level": "consistent",
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _summarize_extraction(page_data: dict[str, Any]) -> str:
    """Build a brief summary of programmatic extraction for the prompt."""
    blocks = page_data.get("text_blocks", [])
    tables = page_data.get("tables", [])
    images = page_data.get("images", [])
    drawn = page_data.get("drawn_elements")

    parts = [f"Text blocks: {len(blocks)}"]
    if tables:
        parts.append(f"Tables: {len(tables)}")
    if images:
        parts.append(f"Images: {len(images)}")
    # drawn_elements is list[dict] from _extract_drawn_elements (not a dict).
    # Count by orientation so GPT-4o has strong signals for barcode/table detection.
    if drawn and isinstance(drawn, list):
        h_lines = sum(1 for e in drawn if e.get("type") == "line" and e.get("orientation") == "horizontal")
        v_lines = sum(1 for e in drawn if e.get("type") == "line" and e.get("orientation") == "vertical")
        if h_lines:
            parts.append(f"Horizontal lines: {h_lines}")
        if v_lines:
            parts.append(f"Vertical lines: {v_lines} (possible barcode stripes or table grid)")
    return "; ".join(parts)


def _parse_visual_response(raw_json: str) -> dict[str, Any]:
    """Parse GPT-4o JSON response into validated structure."""
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:\w*)\s*\n?", "", raw_json.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return {"regions": [], "consistency_score": 0, "consistency_notes": "parse_error"}

    # Defensive: model returned array directly instead of object
    if isinstance(data, list):
        data = {"regions": data, "consistency_score": 0, "consistency_notes": "auto_wrapped"}

    regions = data.get("regions", [])
    validated_regions = []
    for r in regions:
        if not isinstance(r, dict):
            continue
        rtype = r.get("type", "body")
        if rtype not in VALID_REGION_TYPES:
            rtype = "body"
        bbox = r.get("bbox", [0, 0, 100, 100])
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0, 0, 100, 100]
        validated_regions.append(
            {
                "type": rtype,
                "bbox": [int(v) if isinstance(v, (int, float)) else 0 for v in bbox],
                "description": str(r.get("description", "")),
                "html_suggestion": str(r.get("html_suggestion", "")),
                "chart_type": r.get("chart_type"),
                "barcode_format": r.get("barcode_format"),
                "confidence": r.get("confidence"),
            }
        )

    score = data.get("consistency_score", 0)
    if not isinstance(score, (int, float)):
        score = 0

    return {
        "regions": validated_regions,
        "consistency_score": int(score),
        "consistency_notes": str(data.get("consistency_notes", "")),
    }


def _parse_html_table_mistral(html_content: str) -> dict[str, Any] | None:
    """Parse HTML table from Mistral OCR response into pipeline schema.

    Generic parser — works for any document type.
    Handles <br/> in cells (joins parts with " | ").
    Uses colspan attributes to compute col_widths_pct.

    Returns dict with headers, rows, layout (col_widths_pct, row_heights_pct).
    Returns None if parsing fails or table is empty.
    """
    from html.parser import HTMLParser

    class _TableParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.rows: list[list[list[str]]] = []
            self.colspans: list[list[int]] = []
            self._current_row: list[list[str]] = []
            self._current_row_colspans: list[int] = []
            self._current_parts: list[str] = []
            self._current_part: list[str] = []
            self._current_colspan: int = 1
            self._in_cell: bool = False

        def handle_starttag(self, tag: str, attrs: list) -> None:
            attr_dict = dict(attrs)
            if tag == "tr":
                self._current_row = []
                self._current_row_colspans = []
            elif tag in ("td", "th"):
                self._current_parts = []
                self._current_part = []
                self._in_cell = True
                self._current_colspan = int(attr_dict.get("colspan", 1))
            elif tag == "br" and self._in_cell:
                self._current_parts.append(" ".join("".join(self._current_part).split()).strip())
                self._current_part = []

        def handle_endtag(self, tag: str) -> None:
            if tag in ("td", "th"):
                self._in_cell = False
                self._current_parts.append(" ".join("".join(self._current_part).split()).strip())
                self._current_row.append(self._current_parts)
                self._current_row_colspans.append(self._current_colspan)
            elif tag == "tr" and self._current_row:
                self.rows.append(self._current_row)
                self.colspans.append(self._current_row_colspans)

        def handle_data(self, data: str) -> None:
            if self._in_cell:
                self._current_part.append(data)

    parser = _TableParser()
    parser.feed(html_content)

    if not parser.rows:
        return None

    # Flatten each cell's br-separated parts into single string
    flat_rows: list[list[str]] = []
    for row in parser.rows:
        flat_rows.append([" | ".join(p for p in cell if p.strip()) for cell in row])

    if not flat_rows:
        return None

    headers = flat_rows[0]
    rows = flat_rows[1:]

    # col_widths_pct from first row colspans
    first_cs = list(parser.colspans[0]) if parser.colspans else [1] * len(headers)
    # Pad if needed
    while len(first_cs) < len(headers):
        first_cs.append(1)
    first_cs = first_cs[: len(headers)]
    total_units = sum(first_cs) or len(first_cs)
    col_widths_pct = [cs / total_units for cs in first_cs]

    n_data_rows = len(rows) or 1
    row_heights_pct = [1.0 / n_data_rows] * n_data_rows

    return {
        "headers": headers,
        "rows": rows,
        "layout": {
            "col_widths_pct": col_widths_pct,
            "row_heights_pct": row_heights_pct,
        },
    }


async def _extract_raster_table_mistral(
    pdf_path: str | None,
    page_index: int,
    mistral_api_key: str,
    mistral_cache: dict[str, Any],
) -> tuple[dict[str, Any] | None, float, dict[str, str | None]]:
    """Extract raster table via Mistral OCR PDF + PyMuPDF bbox (Story 46.2).

    Calls Mistral OCR with extract_header=True, extract_footer=True, pages=[page_index].
    Uses PyMuPDF to obtain exact raster image bbox — NO GPT-4o region_bbox dependency.
    Caches response per (pdf_path, page_index) to avoid duplicate API calls.

    Returns:
        (table_dict, cost_usd, zones)
        - table_dict: extracted table with PyMuPDF bbox, source="mistral_ocr_raster"
          None when no raster table found (vector table or empty page)
        - cost_usd: API cost (0.0 on cache hit)
        - zones: {"header": str|None, "footer": str|None} from Mistral response
    """
    import base64
    from pathlib import Path

    import httpx

    _empty_zones: dict[str, str | None] = {"header": None, "footer": None}

    if pdf_path is None:
        logger.warning("Mistral raster extraction: pdf_path is None for page %d", page_index)
        return None, 0.0, _empty_zones

    # Per-page cache — cost charged only on first call per (pdf_path, page_index)
    cache_key = f"{pdf_path}:{page_index}"
    if cache_key in mistral_cache:
        pages_data: list[dict[str, Any]] = mistral_cache[cache_key]["pages"]
        cost = 0.0
    else:
        try:
            pdf_bytes = Path(pdf_path).read_bytes()
        except OSError as e:
            logger.warning("Mistral raster extraction: cannot read PDF %s: %s", pdf_path, e)
            return None, 0.0, _empty_zones

        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_b64}",
            },
            "table_format": "html",
            "extract_header": True,
            "extract_footer": True,
            "pages": [page_index],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/ocr",
                headers={
                    "Authorization": f"Bearer {mistral_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        data = resp.json()
        if "error" in data or data.get("object") == "error":
            raise RuntimeError(f"Mistral OCR error: {data.get('message', data)}")

        pages_data = data.get("pages", [])
        usage = data.get("usage_info", {})
        pages_count = usage.get("pages_processed", len(pages_data)) or 1
        cost = pages_count * 0.001
        mistral_cache[cache_key] = {"pages": pages_data}

    # With pages=[page_index], Mistral returns only the requested page at index 0.
    if not pages_data:
        return None, cost, _empty_zones

    page = pages_data[0]

    # Extract header/footer zones — AC3
    header_text: str | None = page.get("header") or None
    footer_text: str | None = page.get("footer") or None
    if footer_text == "#":
        footer_text = None  # Mistral sentinel for absent footer
    zones: dict[str, str | None] = {"header": header_text, "footer": footer_text}

    # Check for tables in Mistral response
    page_tables = page.get("tables", [])
    if not page_tables:
        # No table detected (vector page or empty) — AC4: continue without error
        return None, cost, zones

    # Get raster image bboxes via PyMuPDF — AC2
    raster_bboxes = _get_raster_image_bboxes_pymupdf(pdf_path, page_index)
    if not raster_bboxes:
        # Mistral found a table but no raster image → vector table (pdfplumber handles it)
        logger.debug(
            "Mistral detected table but no raster image for %s page %d — likely vector table",
            pdf_path,
            page_index,
        )
        return None, cost, zones

    # Parse first table HTML
    best_html = page_tables[0].get("content", "")
    parsed = _parse_html_table_mistral(best_html)
    if not parsed:
        logger.warning("Mistral raster: HTML parse failed for %s page %d", pdf_path, page_index)
        return None, cost, zones

    headers = parsed["headers"]
    rows = parsed["rows"]
    raw_cells = ([headers] if headers else []) + rows
    col_count = len(headers) if headers else (len(rows[0]) if rows else 0)

    # Use largest raster image as table bbox — precise, no GPT-4o needed
    bbox = raster_bboxes[0]

    table: dict[str, Any] = {
        "bbox": bbox,
        "raw_cells": raw_cells,
        "has_ruling_lines": False,
        "col_count": col_count,
        "row_count": len(raw_cells),
        "source": "mistral_ocr_raster",
        "layout": parsed.get("layout", {}),
    }
    return table, cost, zones


def _fallback_visual_analysis(
    page_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate fallback visual analysis using adaptive thresholds.

    Used when GPT-4o Vision is unavailable.
    Top 10% = header, bottom 10% = footer, rest = body.
    """
    page_height = page_data.get("height", 842.0)
    page_width = page_data.get("width", 595.0)

    header_end = int(page_height * 0.10)
    footer_start = int(page_height * 0.90)

    regions = [
        {
            "type": "header",
            "bbox": [0, 0, int(page_width), header_end],
            "description": "Header region (threshold-based)",
            "html_suggestion": "<header></header>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
        {
            "type": "body",
            "bbox": [0, header_end, int(page_width), footer_start],
            "description": "Body region (threshold-based)",
            "html_suggestion": "<main></main>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
        {
            "type": "footer",
            "bbox": [0, footer_start, int(page_width), int(page_height)],
            "description": "Footer region (threshold-based)",
            "html_suggestion": "<footer></footer>",
            "chart_type": None,
            "barcode_format": None,
            "confidence": None,
        },
    ]

    return {
        "regions": regions,
        "consistency_score": 50,
        "consistency_notes": "Fallback: threshold-based zones (no GPT-4o Vision)",
    }


# ---------------------------------------------------------------------------
# Sub-step 3.2 — Visual Analysis (Mistral OCR + PyMuPDF — Story 46.2)
# ---------------------------------------------------------------------------


async def _run_3_2(
    clusters: list[dict[str, Any]],
    enriched_documents: list[dict[str, Any]],
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, dict[str, Any]]:
    """Sub-step 3.2 — Visual Analysis.

    Story 46.2: GPT-4o Vision eliminated.
    Mistral OCR is called unconditionally per representative page.
    Raster table bbox comes from PyMuPDF (not GPT-4o).
    Header/footer zones come from Mistral extract_header/extract_footer.

    Fallback: threshold-based zones when MISTRAL_API_KEY is absent.
    """
    import os

    visual_analysis: dict[str, dict[str, Any]] = {}

    # Build page lookup: {pdf_id}:{page_index} -> page_data
    page_lookup: dict[str, dict[str, Any]] = {}
    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            pk = f"{pdf_id}:{page['page_index']}"
            page_lookup[pk] = page

    mistral_api_key: str | None = os.environ.get("MISTRAL_API_KEY")
    mistral_cache: dict[str, Any] = {}  # cache_key "(pdf_path:page_index)" -> {"pages": [...]}

    # Build pdf_id -> pdf_path map for Mistral calls
    pdf_docs_map: dict[str, str] = {
        str(doc["id"]): doc["path"] for doc in context.get("pdf_documents", []) if "id" in doc and "path" in doc
    }

    if not mistral_api_key:
        context.setdefault("_pipeline_warnings", []).append(
            "MISTRAL_API_KEY não configurado — análise visual usando thresholds adaptativos (~75% qualidade)."
        )

    api_cost_total = 0.0

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        if cluster_id.startswith("_"):
            continue

        rep = cluster["representative_page"]
        page_key = f"{rep['pdf_id']}:{rep['page_index']}"
        page_data = page_lookup.get(page_key)

        if page_data is None:
            visual_analysis[page_key] = _fallback_visual_analysis({"height": 842.0, "width": 595.0})
            continue

        if not mistral_api_key:
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            continue

        pdf_path: str | None = pdf_docs_map.get(str(rep.get("pdf_id", "")))
        page_index: int = rep.get("page_index", 0)
        screenshot_path: str | None = page_data.get("screenshot_path")

        try:
            extracted_table, call_cost, zones = await _extract_raster_table_mistral(
                pdf_path, page_index, mistral_api_key, mistral_cache
            )
            api_cost_total += call_cost

            page_h = float(page_data.get("height", 842.0))
            page_w = float(page_data.get("width", 595.0))
            result = _build_regions_from_mistral(extracted_table, zones, page_w, page_h)

            if extracted_table is not None:
                # Enrich with font (text_blocks) + colors (PIL crop) — Story 43.6
                _enrich_raster_table_style(
                    extracted_table,
                    page_data=page_data,
                    screenshot_path=screenshot_path,
                )
                # Attach to the table_area region for downstream consumers
                for region in result["regions"]:
                    if region["type"] == "table_area":
                        region["extracted_table"] = extracted_table
                        break

            visual_analysis[page_key] = result

        except Exception as exc:
            logger.warning("Mistral OCR call failed for %s: %s", page_key, exc)
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)

    if api_cost_total > 0:
        context["_vision_api_cost"] = context.get("_vision_api_cost", 0.0) + api_cost_total

    return visual_analysis
