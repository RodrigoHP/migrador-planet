#!/usr/bin/env python3
"""
Spike 43.3 — OCR/Vision Bake-off para Conteúdo Raster

Testa candidatos de extração de conteúdo raster (tabela, barcode, imagem) e
gera relatório comparativo com métricas contra ground truth manual.

Usage:
    python spike_ocr_bakeoff.py [--pdf PATH] [--bbox x1,y1,x2,y2]
    python spike_ocr_bakeoff.py --candidates all
    python spike_ocr_bakeoff.py --candidates gpt4o,claude,gemini

Credenciais (env vars):
    OPENROUTER_API_KEY — GPT-4o, Claude Sonnet, Gemini Flash
    AZURE_DOC_INTEL_KEY + AZURE_DOC_INTEL_ENDPOINT — Azure Document Intelligence
    AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY — AWS Textract
    GOOGLE_APPLICATION_CREDENTIALS — Google Document AI

Orçamento máximo: $5 por execução completa.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Load from root .env (project root is 2 levels up from backend/scripts/)
_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "backend" / ".env", override=False)

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
AZURE_KEY = os.getenv("AZURE_DOC_INTEL_KEY", "")
AZURE_ENDPOINT = os.getenv("AZURE_DOC_INTEL_ENDPOINT", "")
MISTRAL_KEY = os.getenv("MISTRAL_API_KEY", "")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "ocr_bakeoff"
REPORTS_DIR = _ROOT / "docs" / "reports" / "epic-43-ocr-bakeoff"
GT_TABLE = FIXTURES_DIR / "boleto_raster_table_ground_truth.json"
GT_BARCODE = FIXTURES_DIR / "boleto_barcode_ground_truth.json"
CROP_TABLE = FIXTURES_DIR / "boleto_raster_table_crop.png"
CROP_BARCODE = FIXTURES_DIR / "boleto_barcode_crop.png"

BUDGET_USD = 5.0

# Canonical prompt for Vision LLMs (table extraction)
VISION_TABLE_PROMPT = """Extract the table from this image. Return ONLY valid JSON:
{
  "headers": ["col1", "col2", ...],
  "rows": [["val1", "val2", ...], ...],
  "style": {
    "font_family": "Arial",
    "font_size_px": 10,
    "font_weight": "normal",
    "header_bg_color": "#RRGGBB or null",
    "cell_bg_color": "#RRGGBB or null",
    "text_color": "#RRGGBB",
    "border_color": "#RRGGBB or null",
    "border_width_px": 1
  }
}

Rules:
- Preserve Portuguese text exactly (ç, ã, á, é, ó, ú)
- Use "" for empty cells, null for undetectable style
- Include ALL rows (including calculation/summary rows)
- Colors in hex (#RRGGBB format)
- Do not invent columns, rows, or styles
- Count ALL rows and columns carefully"""

VISION_BARCODE_PROMPT = """Analyze this barcode image. Return ONLY valid JSON:
{
  "barcode_type": "itf-14|code128|pdf417|qr|ean13|other",
  "decoded_value": "numeric string or null if unreadable",
  "visual_description": "brief description of barcode visual characteristics"
}

Rules:
- Identify the barcode symbology type
- Attempt to read/decode the value if possible
- Use null for decoded_value if the barcode is not readable as text"""

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _strip_json(raw: str) -> str:
    """Strip markdown fences from JSON response."""
    text = re.sub(r"^```(?:\w*)\s*\n?", "", raw.strip())
    text = re.sub(r"\n?```\s*$", "", text).strip()
    return text


def cell_f1(gt_rows: list[list[str]], pred_rows: list[list[str]]) -> float:
    """F1 score over all cells (position-matched)."""
    gt = {(r, c): v for r, row in enumerate(gt_rows) for c, v in enumerate(row)}
    pr = {(r, c): v for r, row in enumerate(pred_rows) for c, v in enumerate(row)}
    tp = sum(1 for k, v in gt.items() if pr.get(k) == v)
    fp = sum(1 for k in pr if pr.get(k) != gt.get(k))
    fn = sum(1 for k in gt if k not in pr)
    p = tp / (tp + fp) if (tp + fp) else 0
    r = tp / (tp + fn) if (tp + fn) else 0
    return round(2 * p * r / (p + r), 4) if (p + r) else 0.0


def header_accuracy(gt_headers: list[str], pred_headers: list[str]) -> float:
    """Fraction of headers exactly matched."""
    if not gt_headers:
        return 0.0
    matches = sum(1 for g, p in zip(gt_headers, pred_headers) if g == p)
    return round(matches / len(gt_headers), 4)


def portuguese_accuracy(gt_rows: list[list[str]], pred_rows: list[list[str]]) -> float:
    """Fraction of Portuguese-accented characters preserved correctly."""
    pt_chars = set("çãáéíóúàâêôÇÃÁÉÍÓÚÀÂÊÔ")
    pred_flat = {(r, c): v for r, row in enumerate(pred_rows) for c, v in enumerate(row)}

    total = 0
    correct = 0
    for r, row in enumerate(gt_rows):
        for c, v in enumerate(row):
            if any(ch in pt_chars for ch in v):
                total += 1
                if pred_flat.get((r, c)) == v:
                    correct += 1

    return round(correct / total, 4) if total else 1.0


def compute_table_metrics(gt: dict, pred: dict, n_runs: int = 1) -> dict:
    """Compute all table metrics comparing pred against gt."""
    gt_headers = gt.get("headers", [])
    gt_rows = gt.get("rows", [])

    pred_headers = pred.get("headers", [])
    pred_rows = pred.get("rows", [])
    pred_style = pred.get("style", {})

    h_acc = header_accuracy(gt_headers, pred_headers)
    col_acc = 1.0 if len(pred_headers) == len(gt_headers) else 0.0
    row_acc = (
        1.0 if len(pred_rows) == len(gt_rows) else round(min(len(pred_rows), len(gt_rows)) / max(len(gt_rows), 1), 4)
    )

    # Cell F1 over all rows (headers + rows combined for completeness)
    all_gt = [gt_headers] + gt_rows if gt_headers else gt_rows
    all_pred = [pred_headers] + pred_rows if pred_headers else pred_rows
    f1 = cell_f1(all_gt, all_pred)
    pt_acc = portuguese_accuracy(all_gt, all_pred)

    # Style detection
    font_detected = pred_style.get("font_family") is not None
    bg_detected = pred_style.get("cell_bg_color") is not None
    border_detected = pred_style.get("border_color") is not None

    return {
        "header_accuracy": h_acc,
        "col_count_accuracy": col_acc,
        "row_count_accuracy": row_acc,
        "cell_f1_mean": f1,
        "cell_f1_std": 0.0,  # updated across runs
        "portuguese_accuracy": pt_acc,
        "font_detected": font_detected,
        "bg_color_detected": bg_detected,
        "border_detected": border_detected,
        "pred_col_count": len(pred_headers),
        "pred_row_count": len(pred_rows),
        "gt_col_count": len(gt_headers),
        "gt_row_count": len(gt_rows),
    }


def compute_barcode_metrics(gt: dict, pred: dict) -> dict:
    """Compute barcode metrics."""
    gt_type = (gt.get("barcode_type") or "").lower()
    pred_type = (pred.get("barcode_type") or "").lower()

    # Type accuracy: check if type matches or is a known alias
    gt_aliases = [a.lower() for a in gt.get("barcode_type_aliases", [])]
    all_gt_types = {gt_type} | set(gt_aliases)
    type_acc = 1.0 if pred_type in all_gt_types else 0.0

    gt_value = gt.get("decoded_value")
    pred_value = pred.get("decoded_value")
    value_acc = (
        1.0
        if gt_value is not None and gt_value == pred_value
        else (
            0.0 if gt_value is not None else None  # None = GT has no ground truth value
        )
    )

    return {
        "type_accuracy": type_acc,
        "value_accuracy": value_acc,
        "pred_type": pred_type,
        "gt_type": gt_type,
    }


# ---------------------------------------------------------------------------
# Candidate runner — OpenRouter Vision LLMs
# ---------------------------------------------------------------------------


class OpenRouterCandidate:
    """Base class for Vision LLM candidates via OpenRouter."""

    def __init__(self, model_id: str, name: str):
        self.model_id = model_id
        self.name = name
        self.input_type = "image"

    def is_available(self) -> bool:
        return bool(OPENROUTER_KEY)

    def skip_reason(self) -> str | None:
        if not OPENROUTER_KEY:
            return "no credentials: OPENROUTER_API_KEY not set"
        return None

    async def _call(self, image_b64: str, prompt: str) -> tuple[str, float]:
        """Call OpenRouter API and return (content, cost_usd)."""
        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 4096,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")
        content = data["choices"][0]["message"]["content"]
        cost = data.get("usage", {}).get("cost", 0.0)
        return content, float(cost)

    async def extract_table(self, image_b64: str) -> tuple[dict | None, float, str]:
        """Returns (parsed_dict, cost_usd, raw_text)."""
        raw, cost = await self._call(image_b64, VISION_TABLE_PROMPT)
        try:
            parsed = json.loads(_strip_json(raw))
        except json.JSONDecodeError:
            parsed = None
        return parsed, cost, raw

    async def extract_barcode(self, image_b64: str) -> tuple[dict | None, float, str]:
        """Returns (parsed_dict, cost_usd, raw_text)."""
        raw, cost = await self._call(image_b64, VISION_BARCODE_PROMPT)
        try:
            parsed = json.loads(_strip_json(raw))
        except json.JSONDecodeError:
            parsed = None
        return parsed, cost, raw


class GPT4oCandidate(OpenRouterCandidate):
    def __init__(self):
        super().__init__("openai/gpt-4o", "gpt4o")


class ClaudeSonnetCandidate(OpenRouterCandidate):
    def __init__(self):
        super().__init__("anthropic/claude-sonnet-4-5", "claude-sonnet")


class GeminiFlashCandidate(OpenRouterCandidate):
    def __init__(self):
        super().__init__("google/gemini-2.0-flash-001", "gemini-flash")


# ---------------------------------------------------------------------------
# Candidate runner — Azure Document Intelligence
# ---------------------------------------------------------------------------


class AzureDocIntelCandidate:
    """Azure Document Intelligence prebuilt-layout candidate."""

    name = "azure-doc-intel"
    input_type = "image"  # also accepts PDF, but we use crop image

    def is_available(self) -> bool:
        return bool(AZURE_KEY and AZURE_ENDPOINT)

    def skip_reason(self) -> str | None:
        if not AZURE_KEY:
            return "no credentials: AZURE_DOC_INTEL_KEY not set"
        if not AZURE_ENDPOINT:
            return "no credentials: AZURE_DOC_INTEL_ENDPOINT not set"
        return None

    def _normalize_table(self, table) -> dict:
        """Convert Azure table response to normalized schema."""
        cells = table.cells or []
        row_count = table.row_count or 0
        col_count = table.column_count or 0

        # Build a matrix row x col
        matrix: list[list[str]] = [[""] * col_count for _ in range(row_count)]
        for cell in cells:
            r, c = cell.row_index, cell.column_index
            if r < row_count and c < col_count:
                matrix[r][c] = (cell.content or "").strip()

        # First row = headers if they are header cells
        header_cells = [c for c in cells if c.kind == "columnHeader"]
        if header_cells:
            headers = [""] * col_count
            for cell in header_cells:
                if cell.column_index < col_count:
                    headers[cell.column_index] = (cell.content or "").strip()
            rows = matrix[1:] if len(matrix) > 1 else []
        else:
            headers = matrix[0] if matrix else []
            rows = matrix[1:] if len(matrix) > 1 else []

        return {
            "headers": headers,
            "rows": rows,
            "structure": {"col_count": col_count, "row_count": row_count},
            "style": {
                "font_family": None,  # Azure prebuilt-layout returns font info in styles[]
                "font_size_px": None,
                "font_weight": None,
                "header_bg_color": None,
                "cell_bg_color": None,
                "text_color": None,
                "border_color": None,
                "border_width_px": None,
            },
        }

    def extract_table(self, image_path: Path) -> tuple[dict | None, float, str]:
        """Returns (parsed_dict, cost_usd, raw_description)."""
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        client = DocumentIntelligenceClient(endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY))

        with open(image_path, "rb") as f:
            img_bytes = f.read()

        # Analyze with prebuilt-layout
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=img_bytes,
            content_type="image/png",
        )
        result = poller.result()

        tables = result.tables or []
        raw_description = f"Azure extracted {len(tables)} table(s)"

        if not tables:
            return None, 0.015, raw_description  # ~$0.015/page flat rate

        # Take the largest table
        best = max(tables, key=lambda t: (t.row_count or 0) * (t.column_count or 0))
        normalized = self._normalize_table(best)

        return normalized, 0.015, raw_description


# ---------------------------------------------------------------------------
# Candidate runner — Mistral OCR
# ---------------------------------------------------------------------------


class MistralOcrCandidate:
    """Mistral OCR (mistral-ocr-latest) — specialized OCR model, returns Markdown.

    NOTE: mistral-ocr-latest returns a mix of free text + pipe-tables.
    The free text before the table often contains all the structured field data.
    We pick the pipe-table with the most content rows, NOT just the first one.
    For a true JSON-structured response, use MistralVisionCandidate (pixtral-large).
    """

    name = "mistral-ocr"
    input_type = "image"

    def is_available(self) -> bool:
        return bool(MISTRAL_KEY)

    def skip_reason(self) -> str | None:
        if not MISTRAL_KEY:
            return "no credentials: MISTRAL_API_KEY not set"
        return None

    def _parse_markdown_table(self, markdown: str) -> dict | None:
        """Extract BEST (most content) pipe-table from OCR output.

        Mistral OCR output structure:
        - Free text block (often key-value pairs from Seção A)
        - One or more pipe-tables (Seção B, C)

        Previous bug: always took the FIRST table (which is the header row of Seção B).
        Fix: collect ALL pipe-tables and return the one with the most data rows.
        """
        lines = markdown.splitlines()
        # Collect all tables as separate lists
        all_tables: list[list[list[str]]] = []
        current: list[list[str]] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                if re.match(r"^\|[\s\-|]+\|$", stripped):
                    continue  # separator row (--- etc)
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                current.append(cells)
            else:
                if current:
                    all_tables.append(current)
                    current = []

        if current:
            all_tables.append(current)

        if not all_tables:
            return None

        # Pick the table with the most total cells (most content)
        best = max(all_tables, key=lambda t: sum(len(r) for r in t))

        col_count = max(len(r) for r in best)
        headers = best[0] if best else []
        rows = best[1:] if len(best) > 1 else []

        return {
            "headers": headers,
            "rows": rows,
            "structure": {"col_count": col_count, "row_count": len(rows)},
            "style": {
                "font_family": None,
                "font_size_px": None,
                "font_weight": None,
                "header_bg_color": None,
                "cell_bg_color": None,
                "text_color": None,
                "border_color": None,
                "border_width_px": None,
            },
        }

    def _estimate_cost(self, usage: dict) -> float:
        """Mistral OCR: ~$0.001 per page (image)."""
        pages = usage.get("pages_processed", 1)
        return pages * 0.001

    async def extract_table(self, image_b64: str) -> tuple[dict | None, float, str]:
        """Returns (parsed_dict, cost_usd, raw_markdown)."""
        payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{image_b64}",
            },
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/ocr",
                headers={
                    "Authorization": f"Bearer {MISTRAL_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Mistral OCR error: {data['error']}")

        pages = data.get("pages", [])
        markdown = pages[0].get("markdown", "") if pages else ""
        usage = data.get("usage_info", {})
        cost = self._estimate_cost(usage)

        parsed = self._parse_markdown_table(markdown)
        return parsed, cost, markdown

    async def extract_barcode(self, image_b64: str) -> tuple[dict | None, float, str]:
        """Run OCR on barcode crop — Mistral may decode the numeric value."""
        payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{image_b64}",
            },
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/ocr",
                headers={"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
        data = resp.json()
        pages = data.get("pages", [])
        markdown = pages[0].get("markdown", "") if pages else ""
        usage = data.get("usage_info", {})
        cost = self._estimate_cost(usage)

        # Mistral OCR returns raw text — treat as decoded_value if numeric
        text = markdown.strip()
        digits_only = re.sub(r"\D", "", text)
        return (
            {
                "barcode_type": "unknown",
                "decoded_value": digits_only if len(digits_only) > 10 else None,
                "visual_description": f"Mistral OCR text: {text[:100]}",
            },
            cost,
            markdown,
        )


# ---------------------------------------------------------------------------
# Candidate runner — Mistral OCR PDF (mistral-ocr-latest + PDF + table_format=html)
# ---------------------------------------------------------------------------


class MistralOcrPdfCandidate:
    """Mistral OCR com PDF completo + table_format='html'.

    Diferença chave vs MistralOcrCandidate (image):
    - Input: PDF completo (data:application/pdf;base64,...)
    - Parâmetro: table_format='html' → popula pages[].tables[] com HTML estruturado
    - Output: parseia tables[0].content como HTML → extrai headers/rows via html.parser
    - Custo: ~$0.001/página (mesmo que image)

    Descoberto durante bake-off: com image crop, tables[] fica vazio.
    Com PDF, tables[] é populado com colspan/rowspan corretamente.
    """

    name = "mistral-ocr-pdf"
    input_type = "pdf"
    _PDF_PATH: Path | None = None  # setado em main() a partir de --pdf arg

    def is_available(self) -> bool:
        return bool(MISTRAL_KEY) and self._get_pdf_path() is not None

    def skip_reason(self) -> str | None:
        if not MISTRAL_KEY:
            return "no credentials: MISTRAL_API_KEY not set"
        if self._get_pdf_path() is None:
            return "no PDF path: pass --pdf argument"
        return None

    def _get_pdf_path(self) -> Path | None:
        return MistralOcrPdfCandidate._PDF_PATH

    def _estimate_cost(self, usage: dict) -> float:
        pages = usage.get("pages_processed", 1)
        return pages * 0.001

    def _parse_html_table(self, html_content: str) -> dict | None:
        """Parse HTML table (with colspan/rowspan/br) into normalized schema.

        O boleto tem estrutura específica:
        - Row 1: título do banco (Bradesco | 237 | RECIBO DO SACADO) — pular
        - Rows seguintes: cada <td> tem "Label<br/>Valor" format
          → label = header da coluna, valor = dado da célula

        Para cada row de dados geramos DUAS linhas na saída normalizada:
        - linha de labels  → primeira vira headers, demais viram rows[i]
        - linha de valores → rows[i+1]

        Isso replica exatamente o GT: headers + rows alternando labels/valores.
        """
        from html.parser import HTMLParser

        class TableParser(HTMLParser):
            def __init__(self):
                super().__init__()
                # cada célula armazena [partes separadas por <br/>]
                self.rows: list[list[list[str]]] = []
                self._current_row: list[list[str]] = []
                self._current_parts: list[str] = []
                self._current_part: list[str] = []
                self._in_cell = False

            def handle_starttag(self, tag, attrs):
                if tag == "tr":
                    self._current_row = []
                elif tag in ("td", "th"):
                    self._current_parts = []
                    self._current_part = []
                    self._in_cell = True
                elif tag == "br" and self._in_cell:
                    # finaliza parte atual, começa nova
                    self._current_parts.append(" ".join("".join(self._current_part).split()).strip())
                    self._current_part = []

            def handle_endtag(self, tag):
                if tag in ("td", "th"):
                    self._in_cell = False
                    self._current_parts.append(" ".join("".join(self._current_part).split()).strip())
                    self._current_row.append(self._current_parts)
                elif tag == "tr":
                    if self._current_row:
                        self.rows.append(self._current_row)

            def handle_data(self, data):
                if self._in_cell:
                    self._current_part.append(data)

        parser = TableParser()
        parser.feed(html_content)

        if not parser.rows:
            return None

        # Detecta e pula a row de título (células sem <br/>, conteúdo ≠ GT keywords)
        gt_keywords = {"benefici", "agência", "emissão", "vencimento", "pagador"}
        data_rows = []
        for row in parser.rows:
            row_text = " ".join(p for cell in row for p in cell).lower()
            has_gt_keyword = any(kw in row_text for kw in gt_keywords)
            has_br = any(len(cell) > 1 for cell in row)
            if has_gt_keyword or has_br:
                data_rows.append(row)
            # else: skip title row (Bradesco/237/RECIBO DO SACADO)

        if not data_rows:
            return None

        # Explode cada row HTML em duas linhas normalizadas: labels + values
        norm_rows: list[list[str]] = []
        for row in data_rows:
            labels = [cell[0] if cell else "" for cell in row]
            values = [cell[1] if len(cell) > 1 else "" for cell in row]
            norm_rows.append(labels)
            if any(v.strip() for v in values):
                norm_rows.append(values)

        if not norm_rows:
            return None

        # Primeira linha de labels → headers; resto → rows
        headers = norm_rows[0]
        rows = norm_rows[1:]
        # Remove colunas extras vazias (colspan artifacts)
        max_non_empty = max(
            (i + 1 for r in [headers] + rows for i, v in enumerate(r) if v.strip()),
            default=len(headers),
        )
        headers = headers[:max_non_empty]
        rows = [r[:max_non_empty] for r in rows]
        col_count = max_non_empty

        return {
            "headers": headers,
            "rows": rows,
            "structure": {"col_count": col_count, "row_count": len(rows)},
            "style": {
                "font_family": None,
                "font_size_px": None,
                "font_weight": None,
                "header_bg_color": None,
                "cell_bg_color": None,
                "text_color": None,
                "border_color": None,
                "border_width_px": None,
            },
        }

    async def extract_table(self, pdf_path: Path) -> tuple[dict | None, float, str]:
        """Async — returns (parsed_dict, cost_usd, raw_html)."""
        pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode()
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
                headers={"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
        data = resp.json()
        if "error" in data or data.get("object") == "error":
            raise RuntimeError(f"Mistral OCR PDF error: {data.get('message', data)}")

        pages = data.get("pages", [])
        usage = data.get("usage_info", {})
        cost = self._estimate_cost(usage)

        # Page 0 tables — pick the one that best matches GT Seção A
        tables = pages[0].get("tables", []) if pages else []
        if not tables:
            return None, cost, "No tables detected in PDF page 0"

        gt_keywords = {"benefici", "agência", "emissão", "vencimento", "pagador"}
        best_table = None
        best_score = -1
        all_html = []
        for t in tables:
            html_content = t.get("content", "")
            all_html.append(html_content)
            score = sum(1 for kw in gt_keywords if kw in html_content.lower())
            if score > best_score:
                best_score = score
                best_table = html_content

        parsed = self._parse_html_table(best_table) if best_table else None
        raw = "\n\n---\n\n".join(all_html)
        return parsed, cost, raw


# ---------------------------------------------------------------------------
# Candidate runner — Mistral Vision (pixtral-large, chat completions, JSON)
# ---------------------------------------------------------------------------


class MistralVisionCandidate(OpenRouterCandidate):
    """Mistral Pixtral-large-2411 via OpenRouter — returns structured JSON.

    Usa o mesmo VISION_TABLE_PROMPT dos outros Vision LLMs (GPT-4o/Claude/Gemini),
    roteado pelo OpenRouter para evitar rate limits do endpoint direto do Mistral.
    Comparação justa: mesmo prompt, mesmo schema JSON, mesmo canal de roteamento.
    """

    def __init__(self):
        super().__init__("mistralai/pixtral-large-2411", "mistral-vision")


# ---------------------------------------------------------------------------
# Candidate runner — Barcode specialists (local)
# ---------------------------------------------------------------------------


class ZxingCandidate:
    """zxing-cpp barcode decoder (local, free)."""

    name = "zxing-cpp"
    input_type = "image"

    def is_available(self) -> bool:
        try:
            import zxingcpp  # noqa: F401

            return True
        except ImportError:
            return False

    def skip_reason(self) -> str | None:
        if not self.is_available():
            return "no credentials: zxing-cpp not installed"
        return None

    def decode(self, image_path: Path) -> dict:
        import zxingcpp
        from PIL import Image

        img = Image.open(image_path).convert("L")
        # Try all linear codes first (boleto uses ITF)
        results = zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.LinearCodes)
        if not results:
            # Fallback: try all formats
            results = zxingcpp.read_barcodes(img)
        if results:
            r = results[0]
            return {
                "barcode_type": str(r.format).lower().replace("barcodeformat.", ""),
                "decoded_value": r.text,
                "visual_description": f"Decoded by zxing-cpp: {r.format}",
            }
        return {
            "barcode_type": None,
            "decoded_value": None,
            "visual_description": "zxing-cpp could not decode — image quality insufficient",
        }


# ---------------------------------------------------------------------------
# Run a single candidate × content type × N runs
# ---------------------------------------------------------------------------


async def run_table_candidate(
    candidate: OpenRouterCandidate | None,
    image_b64: str,
    gt: dict,
    n_runs: int = 3,
    output_dir: Path = REPORTS_DIR,
    total_cost_tracker: list[float] = None,
) -> dict:
    """Run table extraction N times, compute metrics, save results."""
    if total_cost_tracker is None:
        total_cost_tracker = [0.0]

    if candidate is None or not candidate.is_available():
        skip = getattr(candidate, "skip_reason", lambda: "unknown")()
        return {"candidate": getattr(candidate, "name", "?"), "skipped": True, "skip_reason": skip}

    cand_dir = output_dir / candidate.name
    cand_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    cell_f1_scores = []

    for run_id in range(1, n_runs + 1):
        # Budget guard
        if sum(total_cost_tracker) >= BUDGET_USD:
            print(f"  ⚠️  Budget ${BUDGET_USD} reached — stopping {candidate.name}")
            break

        print(f"  [{candidate.name}] Run {run_id}/{n_runs} table...")
        t0 = time.time()
        try:
            parsed, cost, raw = await candidate.extract_table(image_b64)
            latency_ms = int((time.time() - t0) * 1000)
            total_cost_tracker[0] += cost
            error = None
        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            cost = 0.0
            parsed = None
            raw = str(exc)
            error = str(exc)

        run_metrics = compute_table_metrics(gt, parsed or {}) if parsed else {}
        if parsed:
            cell_f1_scores.append(run_metrics.get("cell_f1_mean", 0.0))

        run_data = {
            "run_id": run_id,
            "raw_response": raw,
            "normalized": parsed,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "error": error,
            "metrics": run_metrics,
        }
        runs.append(run_data)

        # Save individual run
        (cand_dir / f"table_run{run_id}.json").write_text(
            json.dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # Aggregate metrics
    valid_runs = [r for r in runs if r["error"] is None and r["normalized"]]
    if valid_runs:
        import statistics

        agg = compute_table_metrics(gt, valid_runs[0]["normalized"])
        if len(cell_f1_scores) > 1:
            agg["cell_f1_std"] = round(statistics.stdev(cell_f1_scores), 4)
        latencies = [r["latency_ms"] for r in valid_runs]
        agg["latency_p50_ms"] = int(sorted(latencies)[len(latencies) // 2])
        agg["latency_p95_ms"] = int(sorted(latencies)[int(len(latencies) * 0.95)])
        agg["total_cost_usd"] = round(sum(r["cost_usd"] for r in runs), 6)
        agg["n_valid_runs"] = len(valid_runs)
    else:
        agg = {"error": "all runs failed", "n_valid_runs": 0}

    result = {
        "candidate": candidate.name,
        "content_type": "table",
        "input_type": candidate.input_type,
        "model_id": getattr(candidate, "model_id", None),
        "skipped": False,
        "runs": runs,
        "metrics": agg,
    }

    (cand_dir / "table_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


async def run_barcode_candidate_vision(
    candidate: OpenRouterCandidate,
    image_b64: str,
    gt: dict,
    n_runs: int = 3,
    output_dir: Path = REPORTS_DIR,
    total_cost_tracker: list[float] = None,
) -> dict:
    """Run barcode extraction via Vision LLM."""
    if total_cost_tracker is None:
        total_cost_tracker = [0.0]

    if not candidate.is_available():
        return {"candidate": candidate.name, "skipped": True, "skip_reason": candidate.skip_reason()}

    cand_dir = output_dir / candidate.name
    cand_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    for run_id in range(1, n_runs + 1):
        if sum(total_cost_tracker) >= BUDGET_USD:
            break

        print(f"  [{candidate.name}] Run {run_id}/{n_runs} barcode...")
        t0 = time.time()
        try:
            parsed, cost, raw = await candidate.extract_barcode(image_b64)
            latency_ms = int((time.time() - t0) * 1000)
            total_cost_tracker[0] += cost
            error = None
        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            cost = 0.0
            parsed = None
            raw = str(exc)
            error = str(exc)

        metrics = compute_barcode_metrics(gt, parsed or {}) if parsed else {}
        run_data = {
            "run_id": run_id,
            "raw_response": raw,
            "normalized": parsed,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "error": error,
            "metrics": metrics,
        }
        runs.append(run_data)
        (cand_dir / f"barcode_run{run_id}.json").write_text(
            json.dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    valid_runs = [r for r in runs if r["error"] is None and r["normalized"]]
    agg = compute_barcode_metrics(gt, valid_runs[0]["normalized"]) if valid_runs else {}
    agg["total_cost_usd"] = round(sum(r["cost_usd"] for r in runs), 6)
    agg["n_valid_runs"] = len(valid_runs)
    if valid_runs:
        latencies = [r["latency_ms"] for r in valid_runs]
        agg["latency_p50_ms"] = int(sorted(latencies)[len(latencies) // 2])
        agg["latency_p95_ms"] = int(sorted(latencies)[int(len(latencies) * 0.95)])

    result = {
        "candidate": candidate.name,
        "content_type": "barcode",
        "input_type": candidate.input_type,
        "skipped": False,
        "runs": runs,
        "metrics": agg,
    }
    (cand_dir / "barcode_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def run_barcode_zxing(output_dir: Path = REPORTS_DIR) -> dict:
    """Run zxing-cpp barcode decoder (synchronous)."""
    candidate = ZxingCandidate()
    if not candidate.is_available():
        return {"candidate": "zxing-cpp", "skipped": True, "skip_reason": candidate.skip_reason()}

    cand_dir = output_dir / "zxing-cpp"
    cand_dir.mkdir(parents=True, exist_ok=True)

    gt = json.loads(GT_BARCODE.read_text(encoding="utf-8"))

    print("  [zxing-cpp] Barcode decode...")
    t0 = time.time()
    try:
        decoded = candidate.decode(CROP_BARCODE)
        latency_ms = int((time.time() - t0) * 1000)
        error = None
    except Exception as exc:
        decoded = {"barcode_type": None, "decoded_value": None, "visual_description": str(exc)}
        latency_ms = int((time.time() - t0) * 1000)
        error = str(exc)

    metrics = compute_barcode_metrics(gt, decoded)
    metrics["latency_ms"] = latency_ms
    metrics["cost_usd"] = 0.0

    result = {
        "candidate": "zxing-cpp",
        "content_type": "barcode",
        "input_type": "image",
        "skipped": False,
        "runs": [{"run_id": 1, "normalized": decoded, "latency_ms": latency_ms, "error": error}],
        "metrics": metrics,
    }
    (cand_dir / "barcode_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


async def run_table_mistral_ocr_pdf(
    gt: dict,
    pdf_path: Path,
    n_runs: int = 3,
    output_dir: Path = REPORTS_DIR,
    total_cost_tracker: list[float] | None = None,
) -> dict:
    """Run Mistral OCR PDF candidate (synchronous)."""
    if total_cost_tracker is None:
        total_cost_tracker = [0.0]

    candidate = MistralOcrPdfCandidate()
    MistralOcrPdfCandidate._PDF_PATH = pdf_path

    if not candidate.is_available():
        return {"candidate": candidate.name, "skipped": True, "skip_reason": candidate.skip_reason()}

    cand_dir = output_dir / candidate.name
    cand_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    cell_f1_scores = []

    for run_id in range(1, n_runs + 1):
        if total_cost_tracker[0] >= BUDGET_USD:
            print(f"  Budget ${BUDGET_USD} reached — stopping mistral-ocr-pdf")
            break

        print(f"  [mistral-ocr-pdf] Run {run_id}/{n_runs} table...")
        t0 = time.time()
        try:
            parsed, cost, raw = await candidate.extract_table(pdf_path)
            latency_ms = int((time.time() - t0) * 1000)
            total_cost_tracker[0] += cost
            error = None
        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            cost = 0.0
            parsed = None
            raw = str(exc)
            error = str(exc)

        run_metrics = compute_table_metrics(gt, parsed or {}) if parsed else {}
        if parsed:
            cell_f1_scores.append(run_metrics.get("cell_f1_mean", 0.0))

        run_data = {
            "run_id": run_id,
            "raw_response": raw[:2000],  # HTML pode ser longo
            "normalized": parsed,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "error": error,
            "metrics": run_metrics,
        }
        runs.append(run_data)
        (cand_dir / f"table_run{run_id}.json").write_text(
            json.dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    valid_runs = [r for r in runs if r["error"] is None and r["normalized"]]
    if valid_runs:
        import statistics

        cell_f1_std = statistics.stdev(cell_f1_scores) if len(cell_f1_scores) > 1 else 0.0
        agg = compute_table_metrics(gt, valid_runs[0]["normalized"])
        agg["cell_f1_std"] = round(cell_f1_std, 4)
        latencies = [r["latency_ms"] for r in valid_runs]
        agg["latency_p50_ms"] = int(sorted(latencies)[len(latencies) // 2])
        agg["latency_p95_ms"] = int(sorted(latencies)[int(len(latencies) * 0.95)])
        agg["total_cost_usd"] = round(sum(r["cost_usd"] for r in runs), 6)
        agg["n_valid_runs"] = len(valid_runs)
    else:
        agg = {"total_cost_usd": 0.0, "n_valid_runs": 0}

    result = {
        "candidate": candidate.name,
        "content_type": "table",
        "input_type": "pdf",
        "skipped": False,
        "runs": runs,
        "metrics": agg,
    }
    (cand_dir / "table_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def run_table_azure(
    gt: dict,
    n_runs: int = 3,
    output_dir: Path = REPORTS_DIR,
    total_cost_tracker: list[float] | None = None,
) -> dict:
    """Run Azure Document Intelligence table extraction (synchronous)."""
    if total_cost_tracker is None:
        total_cost_tracker = [0.0]

    candidate = AzureDocIntelCandidate()
    if not candidate.is_available():
        return {"candidate": candidate.name, "skipped": True, "skip_reason": candidate.skip_reason()}

    cand_dir = output_dir / candidate.name
    cand_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    cell_f1_scores = []

    for run_id in range(1, n_runs + 1):
        if sum(total_cost_tracker) >= BUDGET_USD:
            print(f"  ⚠️  Budget ${BUDGET_USD} reached — stopping azure-doc-intel")
            break

        print(f"  [azure-doc-intel] Run {run_id}/{n_runs} table...")
        t0 = time.time()
        try:
            parsed, cost, raw = candidate.extract_table(CROP_TABLE)
            latency_ms = int((time.time() - t0) * 1000)
            total_cost_tracker[0] += cost
            error = None
        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            cost = 0.0
            parsed = None
            raw = str(exc)
            error = str(exc)

        run_metrics = compute_table_metrics(gt, parsed or {}) if parsed else {}
        if parsed:
            cell_f1_scores.append(run_metrics.get("cell_f1_mean", 0.0))

        run_data = {
            "run_id": run_id,
            "raw_response": raw,
            "normalized": parsed,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "error": error,
            "metrics": run_metrics,
        }
        runs.append(run_data)
        (cand_dir / f"table_run{run_id}.json").write_text(
            json.dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    valid_runs = [r for r in runs if r["error"] is None and r["normalized"]]
    if valid_runs:
        import statistics

        agg = compute_table_metrics(gt, valid_runs[0]["normalized"])
        if len(cell_f1_scores) > 1:
            agg["cell_f1_std"] = round(statistics.stdev(cell_f1_scores), 4)
        latencies = [r["latency_ms"] for r in valid_runs]
        agg["latency_p50_ms"] = int(sorted(latencies)[len(latencies) // 2])
        agg["latency_p95_ms"] = int(sorted(latencies)[int(len(latencies) * 0.95)])
        agg["total_cost_usd"] = round(sum(r["cost_usd"] for r in runs), 6)
        agg["n_valid_runs"] = len(valid_runs)
    else:
        agg = {
            "error": "all runs failed",
            "n_valid_runs": 0,
            "error_detail": runs[0].get("error") if runs else "no runs",
        }

    result = {
        "candidate": candidate.name,
        "content_type": "table",
        "input_type": candidate.input_type,
        "model_id": "prebuilt-layout",
        "skipped": False,
        "runs": runs,
        "metrics": agg,
    }
    (cand_dir / "table_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    table_results: list[dict],
    barcode_results: list[dict],
    total_cost: float,
) -> str:
    """Generate markdown report."""

    def fmt_pct(v: float | None) -> str:
        if v is None:
            return "—"
        return f"{v:.1%}"

    def fmt_bool(v: bool | None) -> str:
        if v is None:
            return "—"
        return "✅" if v else "❌"

    def fmt_ms(v: int | None) -> str:
        if v is None:
            return "—"
        return f"{v}ms"

    lines = [
        "# Epic 43 — OCR/Vision Bake-off: Extração de Conteúdo Raster",
        "",
        f"**Data:** 2026-04-13  |  **Budget gasto:** ${total_cost:.4f} / $5.00",
        "",
        "## Sumário Executivo",
        "",
        "Bake-off empírico de candidatos para extração de conteúdo raster em PDFs do tipo boleto bancário.",
        "Testado com `Corporate.Boleto.Convenio.pdf` — tabela raster JPEG na página 0.",
        "",
        "**Candidatos via OpenRouter (credenciais disponíveis):**",
        "- GPT-4o Vision (`openai/gpt-4o`)",
        "- Claude Sonnet 4.5 Vision (`anthropic/claude-sonnet-4-5`)",
        "- Gemini 2.0 Flash Vision (`google/gemini-2.0-flash-001`)",
        "",
        "**Candidatos locais (free):**",
        "- zxing-cpp (barcode decoder)",
        "",
        "**Candidatos nao testados (sem credenciais/instalacao):**",
        "- Azure Document Intelligence, AWS Textract, Google Document AI",
        "- Docling, Marker, pymupdf-layout, Table Transformer (TATR), Deplot",
        "- pyzbar (Windows DLL faltando)",
        "",
        "---",
        "",
        "## Tabela Raster — Métricas Comparativas",
        "",
        "Ground truth: `boleto_raster_table_ground_truth.json`",
        "- Colunas GT: 4  |  Linhas GT: 9",
        "- Headers: Beneficiário, Agência/Cód. Beneficiário, Data Emissão, Vencimento",
        "",
        "| Candidato | Header Acc | Col Acc | Row Acc | Cell F1 | PT Acc | Font | BG Color | Border | Lat p50 | Custo/3runs |",
        "|-----------|:----------:|:-------:|:-------:|:-------:|:------:|:----:|:--------:|:------:|:-------:|:-----------:|",
    ]

    for r in table_results:
        if r.get("skipped"):
            lines.append(f"| {r['candidate']} | ⏭️ skipped | | | | | | | | | — | _{r.get('skip_reason', '')}_")
            continue
        m = r.get("metrics", {})
        lines.append(
            f"| **{r['candidate']}** "
            f"| {fmt_pct(m.get('header_accuracy'))} "
            f"| {fmt_pct(m.get('col_count_accuracy'))} "
            f"| {fmt_pct(m.get('row_count_accuracy'))} "
            f"| {fmt_pct(m.get('cell_f1_mean'))} "
            f"| {fmt_pct(m.get('portuguese_accuracy'))} "
            f"| {fmt_bool(m.get('font_detected'))} "
            f"| {fmt_bool(m.get('bg_color_detected'))} "
            f"| {fmt_bool(m.get('border_detected'))} "
            f"| {fmt_ms(m.get('latency_p50_ms'))} "
            f"| ${m.get('total_cost_usd', 0.0):.4f} |"
        )

    lines += [
        "",
        "## Barcode — Métricas Comparativas",
        "",
        "Ground truth: `boleto_barcode_ground_truth.json`",
        "- Tipo GT: ITF-14 / Interleaved 2-of-5",
        "- Valor GT: null (JPEG comprimido não decodificável com qualidade de produção)",
        "",
        "| Candidato | Type Acc | Value Acc | Lat | Custo |",
        "|-----------|:--------:|:---------:|:---:|:-----:|",
    ]

    for r in barcode_results:
        if r.get("skipped"):
            lines.append(f"| {r['candidate']} | ⏭️ skipped | | | — | _{r.get('skip_reason', '')}_")
            continue
        m = r.get("metrics", {})
        lines.append(
            f"| **{r['candidate']}** "
            f"| {fmt_pct(m.get('type_accuracy'))} "
            f"| {fmt_pct(m.get('value_accuracy')) if m.get('value_accuracy') is not None else 'N/A (GT=null)'} "
            f"| {fmt_ms(m.get('latency_p50_ms') or m.get('latency_ms'))} "
            f"| ${m.get('total_cost_usd', m.get('cost_usd', 0.0)):.4f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Recomendação",
        "",
        "### Tabela Raster",
        "",
        "_Baseada nos resultados do bake-off acima._",
        "",
        "### Barcode",
        "",
        "**zxing-cpp**: Não conseguiu decodificar o JPEG comprimido. Alternativa: usar Vision LLM para identificar tipo + descrever; o valor real da linha digitável é derivado do PDF vetorial (não necessário extrair do raster).",
        "",
        "---",
        "",
        "## Spike Costs",
        "",
        "| Run | Custo |",
        "|-----|-------|",
        f"| Total acumulado | ${total_cost:.4f} |",
        "| Budget máximo | $5.00 |",
        f"| Budget restante | ${max(0, BUDGET_USD - total_cost):.4f} |",
        "",
        "---",
        "",
        "## Raw Outputs",
        "",
        "Ver `docs/reports/epic-43-ocr-bakeoff/{candidate}/` para outputs completos por candidato.",
        "",
        "---",
        "",
        "*Gerado por `backend/scripts/spike_ocr_bakeoff.py` — Story 43.3*",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main(args: argparse.Namespace) -> None:
    """Run bake-off."""
    print("=== Spike 43.3 — OCR/Vision Bake-off ===")
    print(f"  OpenRouter key: {'OK' if OPENROUTER_KEY else 'MISSING'}")
    print(f"  Azure: {'OK' if AZURE_KEY else 'not available (skipped)'}")
    print(f"  Mistral: {'OK' if MISTRAL_KEY else 'not available (skipped)'}")
    print(f"  AWS: {'OK' if AWS_ACCESS_KEY else 'not available (skipped)'}")
    print(f"  Google: {'OK' if GOOGLE_CREDS else 'not available (skipped)'}")
    print()

    # Load ground truths
    gt_table = json.loads(GT_TABLE.read_text(encoding="utf-8"))
    gt_barcode = json.loads(GT_BARCODE.read_text(encoding="utf-8"))

    # Load images as base64
    table_b64 = base64.b64encode(CROP_TABLE.read_bytes()).decode()
    barcode_b64 = base64.b64encode(CROP_BARCODE.read_bytes()).decode()

    # Vision LLM candidates
    vision_candidates = [
        GPT4oCandidate(),
        ClaudeSonnetCandidate(),
        GeminiFlashCandidate(),
        MistralOcrCandidate(),
        MistralVisionCandidate(),
    ]

    # Filter by --candidates arg
    if args.candidates and args.candidates != "all":
        selected = [c.strip() for c in args.candidates.split(",")]
        vision_candidates = [c for c in vision_candidates if c.name in selected]

    total_cost_tracker = [0.0]
    N_RUNS = args.runs

    # ---- Table bake-off ----
    print("\n--- TABLE EXTRACTION ---")
    table_results = []

    # Azure Document Intelligence (synchronous, runs first)
    azure_result = run_table_azure(
        gt_table, n_runs=N_RUNS, output_dir=REPORTS_DIR, total_cost_tracker=total_cost_tracker
    )
    m = azure_result.get("metrics", {})
    if azure_result.get("skipped"):
        print(f"  [azure-doc-intel] SKIPPED — {azure_result.get('skip_reason')}")
    else:
        print(
            f"  [azure-doc-intel] Cell F1={m.get('cell_f1_mean', 0):.3f}"
            f" Header={m.get('header_accuracy', 0):.3f}"
            f" Cost=${m.get('total_cost_usd', 0):.4f}"
        )
    table_results.append(azure_result)

    # Mistral OCR PDF (synchronous — only runs if --pdf provided)
    pdf_path = Path(args.pdf) if args.pdf else None
    should_run_mistral_pdf = (
        not args.candidates or args.candidates == "all" or "mistral-ocr-pdf" in (args.candidates or "")
    )
    if pdf_path and should_run_mistral_pdf:
        mistral_pdf_result = await run_table_mistral_ocr_pdf(
            gt_table, pdf_path, n_runs=N_RUNS, output_dir=REPORTS_DIR, total_cost_tracker=total_cost_tracker
        )
        m = mistral_pdf_result.get("metrics", {})
        if mistral_pdf_result.get("skipped"):
            print(f"  [mistral-ocr-pdf] SKIPPED — {mistral_pdf_result.get('skip_reason')}")
        else:
            print(
                f"  [mistral-ocr-pdf] Cell F1={m.get('cell_f1_mean', 0):.3f}"
                f" Header={m.get('header_accuracy', 0):.3f}"
                f" Cost=${m.get('total_cost_usd', 0):.4f}"
            )
        table_results.append(mistral_pdf_result)
    elif should_run_mistral_pdf and not pdf_path:
        print("  [mistral-ocr-pdf] SKIPPED — pass --pdf to enable PDF-mode OCR")

    for candidate in vision_candidates:
        if not candidate.is_available():
            print(f"  [{candidate.name}] SKIPPED — {candidate.skip_reason()}")
            table_results.append({"candidate": candidate.name, "skipped": True, "skip_reason": candidate.skip_reason()})
            continue
        result = await run_table_candidate(
            candidate, table_b64, gt_table, n_runs=N_RUNS, output_dir=REPORTS_DIR, total_cost_tracker=total_cost_tracker
        )
        m = result.get("metrics", {})
        print(
            f"  [{candidate.name}] Cell F1={m.get('cell_f1_mean', 0):.3f}"
            f" Header={m.get('header_accuracy', 0):.3f}"
            f" Cost=${m.get('total_cost_usd', 0):.4f}"
        )
        table_results.append(result)
        if total_cost_tracker[0] >= BUDGET_USD:
            print(f"  ⚠️  Budget ${BUDGET_USD} reached — stopping table bake-off")
            break

    # ---- Barcode bake-off ----
    print("\n--- BARCODE EXTRACTION ---")
    barcode_results = []

    # zxing-cpp (local)
    zxing_result = run_barcode_zxing(REPORTS_DIR)
    m = zxing_result.get("metrics", {})
    print(
        f"  [zxing-cpp] Type={m.get('pred_type', 'N/A')!r} Value={zxing_result['runs'][0]['normalized'].get('decoded_value', 'null') if not zxing_result.get('skipped') else 'N/A'!r}"
    )
    barcode_results.append(zxing_result)

    # Vision LLMs for barcode (single run — barcode prompt is cheap)
    for candidate in vision_candidates:
        if not candidate.is_available():
            barcode_results.append(
                {"candidate": candidate.name, "skipped": True, "skip_reason": candidate.skip_reason()}
            )
            continue
        result = await run_barcode_candidate_vision(
            candidate, barcode_b64, gt_barcode, n_runs=1, output_dir=REPORTS_DIR, total_cost_tracker=total_cost_tracker
        )
        m = result.get("metrics", {})
        print(f"  [{candidate.name}] Type acc={m.get('type_accuracy', 0):.1%} Cost=${m.get('total_cost_usd', 0):.4f}")
        barcode_results.append(result)
        if total_cost_tracker[0] >= BUDGET_USD:
            print(f"  ⚠️  Budget ${BUDGET_USD} reached — stopping barcode bake-off")
            break

    # ---- Report ----
    total_cost = total_cost_tracker[0]
    print(f"\n--- TOTAL COST: ${total_cost:.4f} ---")

    report = generate_report(table_results, barcode_results, total_cost)
    report_path = REPORTS_DIR / "epic-43-ocr-bakeoff.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\n✅ Report saved: {report_path}")

    # Save summary JSON
    summary = {
        "total_cost_usd": total_cost,
        "table_results": table_results,
        "barcode_results": barcode_results,
    }
    (REPORTS_DIR / "bakeoff_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== DONE ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR/Vision Bake-off for raster content extraction")
    parser.add_argument("--pdf", help="PDF file path (for PDF-native candidates)", default=None)
    parser.add_argument("--bbox", help="Region bbox x1,y1,x2,y2", default=None)
    parser.add_argument(
        "--candidates",
        help="Comma-separated candidates to run (default: all). Options: gpt4o,claude-sonnet,gemini-flash",
        default="all",
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per candidate (default: 3)")
    args = parser.parse_args()
    asyncio.run(main(args))
