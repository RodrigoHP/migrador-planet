"""Stage 3 — Visual Analysis sub-module (Step 3.2).

Responsibilities:
  - GPT-4o Vision API calls for page region detection
  - Response parsing and validation
  - Fallback analysis using adaptive thresholds

Story 41.3 — extracted from stage3_structural_analysis.py
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
# ---------------------------------------------------------------------------


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
    pdf_path: str,
    page_index: int,
    region_bbox: list[float],
    mistral_api_key: str,
    mistral_cache: dict[str, Any],
) -> tuple[dict[str, Any] | None, float]:
    """Extract raster table via Mistral OCR PDF (Story 43.2 rev — ADR 2026-04-13).

    Sends the full PDF to Mistral OCR endpoint with table_format='html'.
    Caches response per pdf_path to avoid duplicate API calls.
    Returns (table_dict, cost_usd). table_dict has source="mistral_ocr_raster".
    Returns (None, 0.0) on failure or no tables found.
    """
    import base64
    from pathlib import Path

    import httpx

    # Per-PDF cache — cost charged only on first call
    if pdf_path in mistral_cache:
        pages_data: list[dict[str, Any]] = mistral_cache[pdf_path]["pages"]
        cost = 0.0  # already charged on first call
    else:
        try:
            pdf_bytes = Path(pdf_path).read_bytes()
        except OSError as e:
            logger.warning("Mistral raster extraction: cannot read PDF %s: %s", pdf_path, e)
            return None, 0.0

        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_b64}",
            },
            "table_format": "html",
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
        mistral_cache[pdf_path] = {"pages": pages_data}

    if page_index >= len(pages_data):
        return None, cost

    page_tables = pages_data[page_index].get("tables", [])
    if not page_tables:
        return None, cost

    # Use first table (single-table assumption for boleto; extend later if needed)
    best_html = page_tables[0].get("content", "")
    parsed = _parse_html_table_mistral(best_html)
    if not parsed:
        logger.warning("Mistral raster: HTML parse failed for %s page %d", pdf_path, page_index)
        return None, cost

    headers = parsed["headers"]
    rows = parsed["rows"]
    raw_cells = ([headers] if headers else []) + rows
    col_count = len(headers) if headers else (len(rows[0]) if rows else 0)

    table: dict[str, Any] = {
        "bbox": list(region_bbox),
        "raw_cells": raw_cells,
        "has_ruling_lines": False,
        "col_count": col_count,
        "row_count": len(raw_cells),
        "source": "mistral_ocr_raster",
        "layout": parsed.get("layout", {}),
    }
    return table, cost


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
# Sub-step 3.2 — Visual Analysis (GPT-4o Vision)
# ---------------------------------------------------------------------------


async def _run_3_2(
    clusters: list[dict[str, Any]],
    enriched_documents: list[dict[str, Any]],
    context: dict[str, Any],
    emit_progress: EmitProgressFn,
) -> dict[str, dict[str, Any]]:
    """Sub-step 3.2 — Visual Analysis.

    1 combined GPT-4o Vision call per representative page.
    MANDATORY but with fallback via handle_service_failure().
    """
    visual_analysis: dict[str, dict[str, Any]] = {}

    # Build page lookup: {pdf_id}:{page_index} -> page_data
    page_lookup: dict[str, dict[str, Any]] = {}
    for doc in enriched_documents:
        pdf_id = doc.get("pdf_id", "")
        for page in doc.get("pages", []):
            pk = f"{pdf_id}:{page['page_index']}"
            page_lookup[pk] = page

    # Get or create vision client
    vision_client = context.get("vision_client")
    vision_available = vision_client is not None

    if not vision_available:
        import os

        vision_enabled = os.environ.get("VISION_AI_ENABLED", "true").lower() not in ("false", "0", "no", "off")
        if not vision_enabled:
            context.setdefault("_pipeline_warnings", []).append(
                "Vision AI desabilitado via configuração (VISION_AI_ENABLED=false)."
            )
        else:
            try:
                from services.openrouter_client import get_client

                vision_client = get_client()
                vision_available = True
            except (ValueError, ImportError) as e:
                vision_available = False
                context.setdefault("_pipeline_warnings", []).append(
                    f"Vision AI desabilitado: {e}. Análise estrutural rodando em modo fallback (~75% qualidade)."
                )

    api_calls = 0
    api_cost_total = 0.0

    # Mistral OCR setup for raster table extraction
    import os

    mistral_api_key: str | None = os.environ.get("MISTRAL_API_KEY")
    mistral_cache: dict[str, Any] = {}  # pdf_path -> {"pages": [...]}
    # Build pdf_id -> pdf_path map for Mistral calls
    pdf_docs_map: dict[str, str] = {
        str(doc["id"]): doc["path"] for doc in context.get("pdf_documents", []) if "id" in doc and "path" in doc
    }

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

        if not vision_available:
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            continue

        screenshot_path = page_data.get("screenshot_path")
        if not screenshot_path:
            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            continue

        # Try GPT-4o Vision call
        image_b64 = None
        try:
            from services.openrouter_client import chat_with_vision, load_image_as_base64

            image_b64 = load_image_as_base64(screenshot_path)
            extraction_summary = _summarize_extraction(page_data)
            prompt = _VISUAL_ANALYSIS_PROMPT.replace("{extraction_summary}", extraction_summary)

            raw_response, call_cost = await chat_with_vision(
                vision_client,
                image_b64=image_b64,
                prompt=prompt,
            )
            result = _parse_visual_response(raw_response)
            api_calls += 1
            api_cost_total += call_cost

            # Determine consistency level
            score = result["consistency_score"]
            if score >= 80:
                result["consistency_level"] = "consistent"
            elif score >= 50:
                result["consistency_level"] = "partial"
            else:
                result["consistency_level"] = "inconsistent"

            visual_analysis[page_key] = result

            # Raster table extraction via Mistral OCR (Story 43.2 rev — ADR 2026-04-13).
            # PyMuPDF/pdfplumber fail on JPEG-embedded tables (no vector text).
            # Pre-extract here so section_utils consumes synchronously. (Opção C pattern)
            if mistral_api_key:
                pdf_path = pdf_docs_map.get(str(rep.get("pdf_id", "")))
                page_index = rep.get("page_index", 0)
                for region in result.get("regions", []):
                    if region.get("type") == "table_area":
                        if pdf_path is None:
                            logger.warning("Mistral raster: pdf_path not found for %s", page_key)
                            continue
                        try:
                            extracted_table, table_cost = await _extract_raster_table_mistral(
                                pdf_path, page_index, region["bbox"], mistral_api_key, mistral_cache
                            )
                            if extracted_table is not None:
                                # Enrich with font (PyMuPDF text_blocks) + colors (PIL) — Story 43.6
                                _enrich_raster_table_style(
                                    extracted_table,
                                    page_data=page_data,
                                    screenshot_path=screenshot_path,
                                )
                                region["extracted_table"] = extracted_table
                            api_cost_total += table_cost
                        except Exception as raster_exc:
                            logger.warning(
                                "Mistral raster extraction failed for %s bbox %s: %s",
                                page_key,
                                region.get("bbox"),
                                raster_exc,
                            )
            else:
                logger.debug("MISTRAL_API_KEY not set — raster table extraction skipped for %s", page_key)

        except Exception as exc:
            logger.warning("Vision API call failed for %s: %s", page_key, exc)

            # Try handle_service_failure if job is available
            job = context.get("_job")
            if job is not None:
                try:
                    from services.pipeline_orchestrator_v2 import handle_service_failure

                    decision = await handle_service_failure(
                        context=context,
                        service_name="GPT-4o Vision",
                        stage_name="Stage 3.2 Visual Analysis",
                        error=exc,
                        fallback_description="Usar thresholds adaptativos (header 10%, footer 90%)",
                        impact_description="Qualidade reduzida (~75% vs ~95%)",
                        job=job,
                        emit_progress=emit_progress,
                    )
                    if decision == "retry" and image_b64 is not None:
                        # One retry
                        try:
                            from services.openrouter_client import chat_with_vision

                            extraction_summary = _summarize_extraction(page_data)
                            prompt = _VISUAL_ANALYSIS_PROMPT.replace("{extraction_summary}", extraction_summary)
                            raw_response, call_cost = await chat_with_vision(
                                vision_client,
                                image_b64=image_b64,
                                prompt=prompt,
                            )
                            result = _parse_visual_response(raw_response)
                            api_calls += 1
                            api_cost_total += call_cost
                            visual_analysis[page_key] = result
                        except Exception:
                            visual_analysis[page_key] = _fallback_visual_analysis(page_data)
                    else:
                        visual_analysis[page_key] = _fallback_visual_analysis(page_data)
                except Exception:
                    visual_analysis[page_key] = _fallback_visual_analysis(page_data)
            else:
                visual_analysis[page_key] = _fallback_visual_analysis(page_data)

    # Update context with API usage stats
    context["_vision_api_calls"] = context.get("_vision_api_calls", 0) + api_calls
    if api_cost_total > 0:
        context["_vision_api_cost"] = context.get("_vision_api_cost", 0.0) + api_cost_total

    return visual_analysis
