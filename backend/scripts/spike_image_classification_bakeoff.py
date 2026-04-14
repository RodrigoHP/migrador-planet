#!/usr/bin/env python3
"""
Spike 43.7 — Bake-off de Classificação de Tipo de Conteúdo Raster (image_area)

Avalia candidatos para classificar o tipo de conteúdo de regiões image_area:
  - barcode → handler: decode (zxing-cpp)
  - logo / image → handler: preserve_as_image_crop

Candidatos:
  A) GPT-4o Vision  (via OpenRouter, ~$0.02/call)
  B) Gemini 2.0 Flash (via OpenRouter, ~$0.0003/call)
  C) Heurística PIL  (aspect ratio + histograma B&W, $0)

Usage:
    python spike_image_classification_bakeoff.py
    python spike_image_classification_bakeoff.py --candidates heuristic
    python spike_image_classification_bakeoff.py --candidates gpt4o,gemini,heuristic

Credenciais:
    OPENROUTER_API_KEY — GPT-4o e Gemini Flash

Orçamento máximo: $1 por execução completa (3 samples × 2 LLMs × ~$0.02).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import time
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv
from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "backend" / ".env", override=False)

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "ocr_bakeoff"
REPORTS_DIR = _ROOT / "docs" / "reports" / "epic-43-ocr-bakeoff"
GT_FILE = FIXTURES_DIR / "image_classification_ground_truth.json"

BUDGET_USD = 1.0

# ---------------------------------------------------------------------------
# Ground Truth
# ---------------------------------------------------------------------------


def load_ground_truth() -> list[dict]:
    with open(GT_FILE) as f:
        data = json.load(f)
    return data["samples"]


# ---------------------------------------------------------------------------
# Candidato C — Heurística PIL (sem LLM, $0)
# ---------------------------------------------------------------------------


def classify_heuristic(crop_path: Path) -> dict:
    """Classifica usando aspect ratio + % pixels preto/branco."""
    start = time.time()
    img = Image.open(crop_path).convert("RGB")
    arr = np.array(img)
    w, h = img.size
    aspect = w / h

    gray = np.mean(arr, axis=2)
    pct_bw = (np.mean(gray < 50) + np.mean(gray > 200)) * 100

    flat = arr.reshape(-1, 3)
    sample = flat[:: max(1, len(flat) // 1000)]
    unique_colors = len(set(map(tuple, sample)))

    # Regra: barcode tem aspect alto E maioria B&W E poucas cores
    if aspect > 3.0 and pct_bw > 85:
        predicted = "barcode"
        confidence = min(99, int(pct_bw))
    elif pct_bw > 70 and unique_colors < 20:
        predicted = "barcode"
        confidence = 70
    else:
        predicted = "logo"
        confidence = 80

    return {
        "predicted_type": predicted,
        "confidence": confidence,
        "latency_ms": int((time.time() - start) * 1000),
        "cost_usd": 0.0,
        "details": {
            "aspect_ratio": round(aspect, 2),
            "pct_bw": round(pct_bw, 1),
            "unique_colors": unique_colors,
        },
    }


# ---------------------------------------------------------------------------
# Candidatos A/B — LLM Vision (GPT-4o e Gemini Flash)
# ---------------------------------------------------------------------------

CLASSIFICATION_PROMPT = """You are analyzing a raster image extracted from a Brazilian financial PDF document (boleto bancário or convênio).

Classify this image into ONE of these types:
- "barcode": linear barcode (ITF, Code128) or QR code — black/white stripes or matrix pattern
- "logo": company logo, bank logo, institutional symbol — usually colorful or branded
- "chart": graph, diagram, pie chart, bar chart — data visualization
- "table": table with data cells (only if it's a raster/image table, not vector)
- "image": generic photo, illustration, or unrecognized visual element

Respond ONLY with valid JSON:
{"type": "<type>", "confidence": <0-100>, "reasoning": "<one sentence>"}"""


def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


async def classify_llm(
    crop_path: Path,
    model: str,
    model_label: str,
    cost_per_call: float,
    client: httpx.AsyncClient,
) -> dict:
    """Classifica usando LLM Vision via OpenRouter."""
    if not OPENROUTER_KEY or OPENROUTER_KEY == "test-key":
        return {
            "predicted_type": "SKIPPED",
            "confidence": 0,
            "latency_ms": 0,
            "cost_usd": 0.0,
            "error": "OPENROUTER_API_KEY não configurada ou é test-key",
        }

    start = time.time()
    b64 = image_to_base64(crop_path)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": CLASSIFICATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 150,
        "temperature": 0,
    }

    try:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Parse JSON response
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        result = json.loads(content)
        return {
            "predicted_type": result.get("type", "unknown"),
            "confidence": result.get("confidence", 0),
            "latency_ms": int((time.time() - start) * 1000),
            "cost_usd": cost_per_call,
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        return {
            "predicted_type": "ERROR",
            "confidence": 0,
            "latency_ms": int((time.time() - start) * 1000),
            "cost_usd": 0.0,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Runner principal
# ---------------------------------------------------------------------------


async def run_bakeoff(candidates: list[str]) -> dict:
    samples = load_ground_truth()
    results = {}

    async with httpx.AsyncClient() as client:
        for sample in samples:
            crop_path = FIXTURES_DIR / sample["crop_file"]
            if not crop_path.exists():
                print(f"  [SKIP] {sample['id']} — crop não encontrado: {crop_path}")
                continue

            print(f"\n-> Sample: {sample['id']} (expected={sample['expected_type']})")
            sample_results = {}

            if "heuristic" in candidates:
                res = classify_heuristic(crop_path)
                correct = res["predicted_type"] == sample["expected_type"]
                res["correct"] = correct
                sample_results["heuristic_pil"] = res
                status = "✅" if correct else "❌"
                print(f"  {status} heuristic: {res['predicted_type']} ({res['latency_ms']}ms, $0)")

            if "gpt4o" in candidates:
                res = await classify_llm(
                    crop_path,
                    "openai/gpt-4o",
                    "GPT-4o",
                    0.02,
                    client,
                )
                if res.get("predicted_type") not in ("SKIPPED", "ERROR"):
                    res["correct"] = res["predicted_type"] == sample["expected_type"]
                sample_results["gpt4o_vision"] = res
                status = "✅" if res.get("correct") else "⚠️"
                print(f"  {status} gpt4o: {res['predicted_type']} ({res['latency_ms']}ms, ${res['cost_usd']:.4f})")

            if "gemini" in candidates:
                res = await classify_llm(
                    crop_path,
                    "google/gemini-2.0-flash-001",
                    "Gemini Flash",
                    0.0003,
                    client,
                )
                if res.get("predicted_type") not in ("SKIPPED", "ERROR"):
                    res["correct"] = res["predicted_type"] == sample["expected_type"]
                sample_results["gemini_flash"] = res
                status = "✅" if res.get("correct") else "⚠️"
                print(f"  {status} gemini: {res['predicted_type']} ({res['latency_ms']}ms, ${res['cost_usd']:.4f})")

            results[sample["id"]] = {
                "expected_type": sample["expected_type"],
                "candidates": sample_results,
            }

    return results


def compute_summary(results: dict) -> dict:
    candidates = set()
    for sample_data in results.values():
        candidates.update(sample_data["candidates"].keys())

    summary = {}
    for cand in candidates:
        total = 0
        correct = 0
        total_cost = 0.0
        latencies = []
        for sample_data in results.values():
            r = sample_data["candidates"].get(cand, {})
            if r.get("predicted_type") not in ("SKIPPED", "ERROR", None):
                total += 1
                if r.get("correct"):
                    correct += 1
                total_cost += r.get("cost_usd", 0)
                latencies.append(r.get("latency_ms", 0))
        summary[cand] = {
            "accuracy": f"{correct}/{total}" if total > 0 else "N/A",
            "accuracy_pct": round(correct / total * 100, 1) if total > 0 else 0,
            "total_cost_usd": round(total_cost, 4),
            "latency_p50_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
        }
    return summary


def save_report(results: dict, summary: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "image-classification-bakeoff-results.json"
    with open(report_path, "w") as f:
        json.dump({"summary": summary, "detail": results}, f, indent=2, ensure_ascii=False)
    print(f"\nResultados salvos em: {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Spike 43.7 — Image Classification Bakeoff")
    parser.add_argument(
        "--candidates",
        default="heuristic,gpt4o,gemini",
        help="Candidatos a testar (heuristic, gpt4o, gemini)",
    )
    args = parser.parse_args()
    candidates = [c.strip() for c in args.candidates.split(",")]

    print("[SPIKE 43.7] Image Classification Bakeoff")
    print(f"   Candidatos: {candidates}")
    print(f"   Fixtures: {FIXTURES_DIR}")
    print()

    results = asyncio.run(run_bakeoff(candidates))
    summary = compute_summary(results)

    print("\n\n=== SUMARIO ===")
    for cand, s in summary.items():
        print(
            f"  {cand}: accuracy={s['accuracy']} ({s['accuracy_pct']}%) | "
            f"cost=${s['total_cost_usd']:.4f} | latency_p50={s['latency_p50_ms']}ms"
        )

    save_report(results, summary)


if __name__ == "__main__":
    main()
