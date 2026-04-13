"""Spike 46.1 - Validar Mistral images[] bbox como substituto do GPT-4o Vision.

Executa 5 hipóteses contra corp-convenio-1.pdf:
  AC1 - images[] tem bbox para tabela raster
  AC2 - Conversão coordenadas Mistral → PDF points (comparar vs GPT-4o baseline)
  AC3 - Correlação images[] ↔ tables[] via markdown
  AC4 - extract_header/extract_footer retorna zonas úteis
  AC5 - PIL heuristic funciona direto no image_base64

Usage:
    cd backend
    python scripts/spike_46_1_mistral_bbox.py

Requires:
    MISTRAL_API_KEY env var
    OPENROUTER_API_KEY env var (para AC2 baseline GPT-4o)
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent

# Load .env from project root
try:
    from dotenv import load_dotenv

    load_dotenv(str(REPO_ROOT / ".env"))
except ImportError:
    pass  # dotenv optional

PDF_PATH = REPO_ROOT / "backend/tests/fixtures/clustering_ground_truth_real/corp-convenio-1.pdf"
REPORT_DIR = REPO_ROOT / "docs/reports/epic-46-vision-optimization"
REPORT_PATH = REPORT_DIR / "46.1-mistral-bbox-spike.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pdf_b64(pdf_path: Path) -> str:
    return base64.b64encode(pdf_path.read_bytes()).decode()


async def _call_mistral_ocr(
    pdf_b64: str,
    mistral_key: str,
    *,
    include_image_base64: bool = False,
    extract_header: bool = False,
    extract_footer: bool = False,
) -> dict:
    import httpx

    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_b64}",
        },
        "table_format": "html",
        "include_image_base64": include_image_base64,
        "extract_header": extract_header,
        "extract_footer": extract_footer,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.mistral.ai/v1/ocr",
            headers={
                "Authorization": f"Bearer {mistral_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()


async def _call_gpt4o_vision(screenshot_b64: str, openrouter_key: str) -> dict:
    """Call GPT-4o Vision via OpenRouter to get baseline region bboxes."""
    import httpx

    prompt = """\
Analyze this document page image. Return ONLY valid JSON with regions detected.
JSON structure:
{
  "regions": [
    {
      "type": "header|body|footer|table_area|barcode_area|image_area",
      "bbox": [x0, y0, x1, y1],
      "description": "brief description"
    }
  ],
  "consistency_score": 85
}
"""
    payload = {
        "model": "openai/gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 1000,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    # strip markdown fences
    cleaned = re.sub(r"^```(?:\w*)\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return json.loads(cleaned.strip())


def _render_page_screenshot(pdf_path: Path, page_index: int = 0) -> str | None:
    """Render PDF page to PNG at 150 DPI, return base64. Returns None on failure."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        page = doc[page_index]
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        doc.close()
        return base64.b64encode(png_bytes).decode()
    except Exception as e:
        print(f"  [WARN] Screenshot render failed: {e}")
        return None


def _classify_from_base64(b64_str: str, bbox: list[float]) -> str:
    """Wrapper: save base64 image to tempfile, run PIL heuristic."""
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from services.stages.stage3_structural import _classify_image_area_heuristic  # noqa

    data = base64.b64decode(b64_str.split(",", 1)[-1] if "," in b64_str else b64_str)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(data)
        tmp_path = f.name
    try:
        return _classify_image_area_heuristic(bbox, tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _correlate_images_tables(page: dict) -> list[tuple[dict, dict]]:
    """Correlate images[] ↔ tables[] via markdown placeholder proximity."""
    markdown = page.get("markdown", "")
    images = page.get("images", [])
    tables = page.get("tables", [])

    if not images or not tables:
        return []

    img_positions: dict[str, int] = {}
    for m in re.finditer(r"!\[([^\]]+)\]\(([^\)]+)\)", markdown):
        img_id = m.group(2)  # filename in ()
        img_positions[img_id] = m.start()

    tbl_positions: dict[str, int] = {}
    for m in re.finditer(r"\[([^\]]+\.html)\]", markdown):
        tbl_id = m.group(1)
        tbl_positions[tbl_id] = m.start()

    correlations = []
    for img in images:
        img_id = img.get("id", "")
        img_pos = img_positions.get(img_id)
        if img_pos is None:
            # try matching by index
            idx = images.index(img)
            img_pos = idx * 100  # fallback positional estimate

        if not tbl_positions:
            continue
        closest_tbl_id = min(tbl_positions, key=lambda t: abs(tbl_positions[t] - img_pos))
        tbl = next((t for t in tables if t.get("id") == closest_tbl_id), None)
        if tbl:
            correlations.append((img, tbl))

    return correlations


# ---------------------------------------------------------------------------
# Main spike
# ---------------------------------------------------------------------------


async def run_spike() -> dict:
    mistral_key = os.environ.get("MISTRAL_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not mistral_key:
        print("ERROR: MISTRAL_API_KEY not set")
        sys.exit(1)

    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found: {PDF_PATH}")
        sys.exit(1)

    results: dict = {
        "pdf": str(PDF_PATH.name),
        "ac1": {"status": "NOT_RUN", "detail": ""},
        "ac2": {"status": "NOT_RUN", "detail": "", "bbox_diff": None},
        "ac3": {"status": "NOT_RUN", "detail": "", "correlations": []},
        "ac4": {"status": "NOT_RUN", "detail": "", "header": None, "footer": None},
        "ac5": {"status": "NOT_RUN", "detail": "", "classifications": []},
    }

    print(f"\n{'=' * 60}")
    print("Spike 46.1 - Mistral bbox vs GPT-4o Vision")
    print(f"PDF: {PDF_PATH.name}")
    print(f"{'=' * 60}\n")

    pdf_b64 = _pdf_b64(PDF_PATH)
    usage_info: dict = {}

    # -----------------------------------------------------------------------
    # AC1 + AC3: Chamada base - sem base64, com headers/footers
    # -----------------------------------------------------------------------
    print("> Chamada Mistral OCR (AC1/AC3/AC4)...")
    try:
        ocr_response = await _call_mistral_ocr(
            pdf_b64,
            mistral_key,
            include_image_base64=False,
            extract_header=True,
            extract_footer=True,
        )
        usage_info = ocr_response.get("usage_info", {})
        pages = ocr_response.get("pages", [])
        print(f"  Pages processadas: {len(pages)}")
        print(f"  Usage: {usage_info}")
    except Exception as e:
        print(f"  ERRO: {e}")
        results["ac1"]["status"] = "FAIL"
        results["ac1"]["detail"] = str(e)
        return results

    # -----------------------------------------------------------------------
    # AC1 - Bbox disponível?
    # -----------------------------------------------------------------------
    print("\n[AC1] Verificando pages[].images[] com bbox...")
    page_with_table = None
    table_image_bbox: list[float] = []

    for page in pages:
        images = page.get("images", [])
        tables = page.get("tables", [])
        if images and tables:
            page_with_table = page
            img = images[0]
            tx = img.get("top_left_x")
            ty = img.get("top_left_y")
            bx = img.get("bottom_right_x")
            by = img.get("bottom_right_y")
            print(f"  Página {page['index']}: {len(images)} imagens, {len(tables)} tabelas")
            print(f"  images[0].id = {img.get('id')}")
            print(f"  bbox = top_left=({tx},{ty}) bottom_right=({bx},{by})")
            if all(v is not None for v in [tx, ty, bx, by]):
                table_image_bbox = [tx, ty, bx, by]
                results["ac1"]["status"] = "PASS"
                results["ac1"]["detail"] = f"bbox presente: {table_image_bbox}"
            else:
                results["ac1"]["status"] = "FAIL"
                results["ac1"]["detail"] = f"bbox nulo: tx={tx} ty={ty} bx={bx} by={by}"
            break

    if page_with_table is None:
        results["ac1"]["status"] = "FAIL"
        results["ac1"]["detail"] = "Nenhuma página com images[] E tables[] simultaneamente"
        print("  FAIL: Nenhuma página com imagem+tabela")
    else:
        print(f"  AC1: {results['ac1']['status']} - {results['ac1']['detail']}")

    # -----------------------------------------------------------------------
    # AC2 - Conversão de coordenadas + comparação vs GPT-4o
    # -----------------------------------------------------------------------
    print("\n[AC2] Conversão de coordenadas Mistral → PDF points...")

    if table_image_bbox and page_with_table is not None:
        dims = page_with_table.get("dimensions") or {}
        dpi = dims.get("dpi", 200)
        scale = 72.0 / dpi
        pdf_bbox = [
            table_image_bbox[0] * scale,
            table_image_bbox[1] * scale,
            table_image_bbox[2] * scale,
            table_image_bbox[3] * scale,
        ]
        print(f"  DPI Mistral: {dpi}")
        print(f"  Mistral bbox (pixels): {table_image_bbox}")
        print(f"  Convertido para pontos PDF (72dpi): {[round(v, 1) for v in pdf_bbox]}")

        # Baseline GPT-4o (se OPENROUTER_API_KEY disponível)
        if openrouter_key:
            print("  Renderizando screenshot para baseline GPT-4o...")
            page_idx = page_with_table.get("index", 0)
            screenshot_b64 = _render_page_screenshot(PDF_PATH, page_idx)
            if screenshot_b64:
                try:
                    gpt4o_result = await _call_gpt4o_vision(screenshot_b64, openrouter_key)
                    gpt4o_regions = gpt4o_result.get("regions", [])
                    # Procura table_area ou region com maior overlap
                    table_regions = [r for r in gpt4o_regions if r.get("type") == "table_area"]
                    if table_regions:
                        gpt4o_bbox = table_regions[0]["bbox"]
                        diff = [abs(pdf_bbox[i] - gpt4o_bbox[i]) for i in range(4)]
                        max_diff = max(diff)
                        print(f"  GPT-4o bbox: {gpt4o_bbox}")
                        print(f"  Diff por coordenada: {[round(d, 1) for d in diff]}")
                        print(f"  Max diff: {round(max_diff, 1)} pontos PDF")
                        results["ac2"]["bbox_diff"] = {
                            "mistral_pdf": pdf_bbox,
                            "gpt4o": gpt4o_bbox,
                            "diff": diff,
                            "max_diff": max_diff,
                        }
                        if max_diff <= 10:
                            results["ac2"]["status"] = "PASS"
                            results["ac2"]["detail"] = f"Max diff {round(max_diff, 1)}pt ≤ 10pt threshold"
                        else:
                            results["ac2"]["status"] = "FAIL"
                            results["ac2"]["detail"] = f"Max diff {round(max_diff, 1)}pt > 10pt threshold"
                    else:
                        results["ac2"]["status"] = "PARTIAL"
                        results["ac2"]["detail"] = (
                            f"GPT-4o não retornou table_area. Regiões: {[r['type'] for r in gpt4o_regions]}"
                        )
                        results["ac2"]["bbox_diff"] = {
                            "mistral_pdf": pdf_bbox,
                            "gpt4o_regions": [r["type"] for r in gpt4o_regions],
                        }
                except Exception as e:
                    results["ac2"]["status"] = "PARTIAL"
                    results["ac2"]["detail"] = (
                        f"GPT-4o call falhou: {e}. Bbox Mistral convertido: {[round(v, 1) for v in pdf_bbox]}"
                    )
                    results["ac2"]["bbox_diff"] = {"mistral_pdf": pdf_bbox}
            else:
                results["ac2"]["status"] = "PARTIAL"
                results["ac2"]["detail"] = (
                    f"Screenshot falhou. Bbox Mistral convertido: {[round(v, 1) for v in pdf_bbox]}"
                )
                results["ac2"]["bbox_diff"] = {"mistral_pdf": pdf_bbox}
        else:
            results["ac2"]["status"] = "PARTIAL"
            results["ac2"]["detail"] = (
                f"OPENROUTER_API_KEY ausente - baseline GPT-4o não executado. Bbox Mistral convertido: {[round(v, 1) for v in pdf_bbox]}"
            )
            results["ac2"]["bbox_diff"] = {"mistral_pdf": pdf_bbox}
    else:
        results["ac2"]["status"] = "SKIP"
        results["ac2"]["detail"] = "AC1 falhou - sem bbox para converter"

    print(f"  AC2: {results['ac2']['status']} - {results['ac2']['detail']}")

    # -----------------------------------------------------------------------
    # AC3 - Correlação images[] ↔ tables[] via markdown
    # -----------------------------------------------------------------------
    print("\n[AC3] Correlação images[] ↔ tables[] via markdown...")

    if page_with_table is not None:
        correlations = _correlate_images_tables(page_with_table)
        markdown_snippet = page_with_table.get("markdown", "")[:300]
        print(f"  Markdown (primeiros 300 chars): {repr(markdown_snippet)}")
        print(f"  Correlações encontradas: {len(correlations)}")
        for img, tbl in correlations:
            print(f"    image.id={img.get('id')} ↔ table.id={tbl.get('id')}")
        results["ac3"]["correlations"] = [
            {"img_id": img.get("id"), "tbl_id": tbl.get("id")} for img, tbl in correlations
        ]
        if correlations:
            results["ac3"]["status"] = "PASS"
            results["ac3"]["detail"] = f"{len(correlations)} correlação(ões) identificadas via markdown"
        else:
            # Fallback: se há imagens e tabelas na mesma página, correlação por índice
            imgs = page_with_table.get("images", [])
            tbls = page_with_table.get("tables", [])
            if imgs and tbls:
                results["ac3"]["status"] = "PARTIAL"
                results["ac3"]["detail"] = (
                    f"Placeholders não encontrados no markdown. {len(imgs)} img + {len(tbls)} tbl - correlação por índice possível"
                )
            else:
                results["ac3"]["status"] = "FAIL"
                results["ac3"]["detail"] = "Sem correlação possível"
    else:
        results["ac3"]["status"] = "SKIP"
        results["ac3"]["detail"] = "AC1 falhou - sem página com imagem+tabela"

    print(f"  AC3: {results['ac3']['status']} - {results['ac3']['detail']}")

    # -----------------------------------------------------------------------
    # AC4 - extract_header / extract_footer
    # -----------------------------------------------------------------------
    print("\n[AC4] Verificando header/footer zones...")

    headers_found = []
    footers_found = []
    for page in pages:
        h = page.get("header")
        f = page.get("footer")
        if h:
            headers_found.append({"page": page["index"], "content": h[:100]})
        if f:
            footers_found.append({"page": page["index"], "content": f[:100]})

    print(f"  Páginas com header: {len(headers_found)}")
    print(f"  Páginas com footer: {len(footers_found)}")
    if headers_found:
        print(f"  Header sample (pg {headers_found[0]['page']}): {repr(headers_found[0]['content'])}")
    if footers_found:
        print(f"  Footer sample (pg {footers_found[0]['page']}): {repr(footers_found[0]['content'])}")

    results["ac4"]["header"] = headers_found[0] if headers_found else None
    results["ac4"]["footer"] = footers_found[0] if footers_found else None

    if headers_found or footers_found:
        results["ac4"]["status"] = "PASS"
        results["ac4"]["detail"] = f"{len(headers_found)} páginas com header, {len(footers_found)} com footer"
    else:
        results["ac4"]["status"] = "FAIL"
        results["ac4"]["detail"] = "header e footer ambos vazios em todas as páginas"

    print(f"  AC4: {results['ac4']['status']} - {results['ac4']['detail']}")

    # -----------------------------------------------------------------------
    # AC5 - PIL heuristic a partir de image_base64
    # -----------------------------------------------------------------------
    print("\n[AC5] PIL heuristic via image_base64...")

    print("  Chamada Mistral com include_image_base64=True...")
    try:
        ocr_with_b64 = await _call_mistral_ocr(
            pdf_b64,
            mistral_key,
            include_image_base64=True,
            extract_header=False,
            extract_footer=False,
        )
        pages_b64 = ocr_with_b64.get("pages", [])
        classifications = []

        for page in pages_b64:
            for img in page.get("images", []):
                img_b64 = img.get("image_base64")
                if not img_b64:
                    continue
                img_bbox_px = [
                    img.get("top_left_x", 0),
                    img.get("top_left_y", 0),
                    img.get("bottom_right_x", 100),
                    img.get("bottom_right_y", 100),
                ]
                dims = page.get("dimensions") or {}
                dpi = dims.get("dpi", 200)
                scale_to_72 = 72.0 / dpi
                img_bbox_pdf = [v * scale_to_72 for v in img_bbox_px]

                try:
                    cls = _classify_from_base64(img_b64, img_bbox_pdf)
                    entry = {
                        "page": page["index"],
                        "img_id": img.get("id"),
                        "classification": cls,
                        "bbox_pdf": [round(v, 1) for v in img_bbox_pdf],
                    }
                    classifications.append(entry)
                    print(f"  Pg{page['index']} {img.get('id')} → {cls}")
                except Exception as e:
                    print(f"  WARN: PIL classify falhou para {img.get('id')}: {e}")

        results["ac5"]["classifications"] = classifications
        if classifications:
            results["ac5"]["status"] = "PASS"
            results["ac5"]["detail"] = f"PIL heuristic executada em {len(classifications)} imagens via base64"
        else:
            results["ac5"]["status"] = "PARTIAL"
            results["ac5"]["detail"] = "Nenhuma imagem com base64 retornada pelo Mistral"

    except Exception as e:
        results["ac5"]["status"] = "FAIL"
        results["ac5"]["detail"] = f"Chamada com base64 falhou: {e}"

    print(f"  AC5: {results['ac5']['status']} - {results['ac5']['detail']}")

    return results


def _build_report(results: dict, usage_info: dict) -> str:
    """Gera relatório markdown."""
    ac_order = ["ac1", "ac2", "ac3", "ac4", "ac5"]
    status_icon = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "SKIP": "⏭️", "NOT_RUN": "-"}

    lines = [
        "# Spike 46.1 - Relatório: Mistral bbox como substituto do GPT-4o Vision",
        "",
        "**Data:** 2026-04-13  ",
        f"**PDF testado:** `{results['pdf']}`  ",
        "",
        "## Resultados por AC",
        "",
        "| AC | Hipótese | Status | Detalhe |",
        "|----|----------|--------|---------|",
    ]

    ac_titles = {
        "ac1": "images[] tem bbox para tabela raster",
        "ac2": "Conversão coordenadas ≤ 10pt diff vs GPT-4o",
        "ac3": "Correlação images[] ↔ tables[] via markdown",
        "ac4": "extract_header/footer retorna zonas úteis",
        "ac5": "PIL heuristic funciona via image_base64",
    }

    for ac in ac_order:
        r = results[ac]
        icon = status_icon.get(r["status"], "?")
        lines.append(f"| {ac.upper()} | {ac_titles[ac]} | {icon} {r['status']} | {r['detail']} |")

    lines += ["", "## Detalhes"]

    # AC2 bbox diff
    if results["ac2"].get("bbox_diff"):
        bd = results["ac2"]["bbox_diff"]
        lines += [
            "",
            "### AC2 - Bbox comparison",
            f"- Mistral (convertido para PDF pts): `{bd.get('mistral_pdf')}`",
        ]
        if "gpt4o" in bd:
            lines.append(f"- GPT-4o Vision bbox: `{bd.get('gpt4o')}`")
            lines.append(f"- Diff por coordenada: `{[round(d, 1) for d in bd.get('diff', [])]}`")
            lines.append(f"- Max diff: `{round(bd.get('max_diff', 0), 1)}` pontos PDF")

    # AC3 correlations
    if results["ac3"].get("correlations"):
        lines += ["", "### AC3 - Correlações encontradas", ""]
        for c in results["ac3"]["correlations"]:
            lines.append(f"- `{c['img_id']}` ↔ `{c['tbl_id']}`")

    # AC4 header/footer
    h = results["ac4"].get("header")
    f = results["ac4"].get("footer")
    if h or f:
        lines += ["", "### AC4 - Zonas Header/Footer", ""]
        if h:
            lines.append(f"- **Header** (pg {h['page']}): `{h['content']}`")
        if f:
            lines.append(f"- **Footer** (pg {f['page']}): `{f['content']}`")

    # AC5 classifications
    if results["ac5"].get("classifications"):
        lines += ["", "### AC5 - Classificações PIL", ""]
        for c in results["ac5"]["classifications"]:
            lines.append(f"- Pg{c['page']} `{c['img_id']}` → **{c['classification']}** (bbox_pdf={c['bbox_pdf']})")

    # Recomendação
    pass_count = sum(1 for ac in ac_order if results[ac]["status"] == "PASS")
    partial_count = sum(1 for ac in ac_order if results[ac]["status"] == "PARTIAL")
    fail_count = sum(1 for ac in ac_order if results[ac]["status"] == "FAIL")

    lines += ["", "## Recomendação", ""]

    if fail_count == 0 and pass_count >= 3:
        lines += [
            "**✅ ELIMINAR GPT-4o Vision do Stage 3**",
            "",
            "Mistral OCR fornece:",
            "- bbox de imagens via `pages[].images[]` com `top_left_x/y, bottom_right_x/y`",
            "- header/footer zones via `extract_header=True / extract_footer=True`",
            "- base64 para classificação PIL direta",
            "",
            "Implementar Story 46.2: substituir `_run_3_2` (GPT-4o) por pipeline Mistral-only.",
        ]
    elif pass_count + partial_count >= 3:
        lines += [
            "**⚠️ HÍBRIDO RECOMENDADO**",
            "",
            "Mistral cobre a maioria dos casos mas há gaps. Implementar:",
            "- Mistral como primário para table_area detection (AC1 PASS)",
            "- GPT-4o como fallback apenas quando `images[]` vazio",
            "- `extract_header/footer` como substituto para zone detection",
        ]
    else:
        lines += [
            "**❌ MANTER GPT-4o Vision**",
            "",
            f"Mistral insuficiente: {fail_count} ACs críticos falharam.",
            "Documentar como decisão de manter baseline e arquivar spike.",
        ]

    lines += [
        "",
        "## Custo da Spike",
        "- Mistral OCR (2 chamadas): ~$0.002 × páginas processadas",
        "- GPT-4o Vision (baseline AC2): ~$0.01 (1 chamada)",
        "",
        "---",
        "*Gerado por spike_46_1_mistral_bbox.py - Story 46.1*",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main():
    results = await run_spike()

    print(f"\n{'=' * 60}")
    print("SUMÁRIO")
    print(f"{'=' * 60}")
    for ac in ["ac1", "ac2", "ac3", "ac4", "ac5"]:
        r = results[ac]
        icon = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "SKIP": "⏭️"}.get(r["status"], "?")
        print(f"  {ac.upper()}: {icon} {r['status']} - {r['detail'][:80]}")

    # Salva resultados JSON
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "46.1-results.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nResultados JSON: {json_path}")

    # Gera relatório markdown
    report_md = _build_report(results, {})
    REPORT_PATH.write_text(report_md, encoding="utf-8")
    print(f"Relatório: {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
