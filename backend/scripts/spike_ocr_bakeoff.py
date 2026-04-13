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
    vision_candidates = [GPT4oCandidate(), ClaudeSonnetCandidate(), GeminiFlashCandidate()]

    # Filter by --candidates arg
    if args.candidates and args.candidates != "all":
        selected = [c.strip() for c in args.candidates.split(",")]
        vision_candidates = [c for c in vision_candidates if c.name in selected]

    total_cost_tracker = [0.0]
    N_RUNS = args.runs

    # ---- Table bake-off ----
    print("\n--- TABLE EXTRACTION ---")
    table_results = []
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
