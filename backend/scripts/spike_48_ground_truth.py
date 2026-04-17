"""48.3 — Ground truth multi-sample: dynamic/static + repeated sections.

Analisa 3+ PDFs do mesmo template PosicaoConsolidada e produz:
1. dynamic_fields  — blocos que mudam entre instâncias
2. static_fields   — blocos idênticos em todas as instâncias
3. repeated_sections — blocos que aparecem N>=2 vezes na mesma página
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAMPLES = Path("tests/fixtures/samples/relatorio")
REPORT_DIR = Path("../docs/reports/epic-48")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE_PDFS = [
    SAMPLES / "PosicaoConsolidada.pdf",
    SAMPLES / "PosicaoConsolidada2.pdf",
    SAMPLES / "PosicaoConsolidada3.pdf",
]

BBOX_TOLERANCE = 8.0  # pt — tolerância para considerar bloco "na mesma posição"
MIN_OCCURRENCES = 2  # mínimo de ocorrências para seção repetida


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def bbox_key(bbox: list | tuple, tol: float = BBOX_TOLERANCE) -> tuple:
    """Bucket bbox em grade de `tol` pt para comparação fuzzy."""
    return tuple(round(v / tol) for v in bbox)


def extract_blocks(pdf_path: Path) -> dict[int, list[dict]]:
    """Extrai blocos de texto por página."""
    doc = fitz.open(pdf_path)
    pages: dict[int, list[dict]] = {}
    for page_num, page in enumerate(doc):
        blocks = []
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") != 0:
                continue
            text = " ".join(
                span.get("text", "").strip() for line in b.get("lines", []) for span in line.get("spans", [])
            ).strip()
            if not text:
                continue
            blocks.append({"bbox": b["bbox"], "text": text, "bbox_key": bbox_key(b["bbox"])})
        pages[page_num] = blocks
        doc.close() if False else None  # keep linter happy
    doc.close()
    return pages


# ---------------------------------------------------------------------------
# 1. Cross-instance: dynamic vs static
# ---------------------------------------------------------------------------


def analyze_cross_instance(pdf_pages_list: list[dict[int, list[dict]]]) -> dict:
    """Compara blocos entre instâncias do mesmo template."""
    dynamic: list[dict] = []
    static: list[dict] = []

    # Usar primeira instância como referência
    ref_pages = pdf_pages_list[0]

    for page_num, ref_blocks in ref_pages.items():
        for ref_block in ref_blocks:
            key = ref_block["bbox_key"]
            texts_by_instance: list[str] = [ref_block["text"]]

            for other_pages in pdf_pages_list[1:]:
                other_blocks = other_pages.get(page_num, [])
                match = next((b for b in other_blocks if b["bbox_key"] == key), None)
                if match:
                    texts_by_instance.append(match["text"])

            if len(texts_by_instance) < 2:
                # Bloco só aparece em 1 instância — considerar dinâmico
                dynamic.append(
                    {
                        "page": page_num,
                        "bbox": list(ref_block["bbox"]),
                        "texts": texts_by_instance,
                        "note": "only_in_one_instance",
                    }
                )
                continue

            unique_texts = set(texts_by_instance)
            if len(unique_texts) > 1:
                dynamic.append(
                    {
                        "page": page_num,
                        "bbox": list(ref_block["bbox"]),
                        "texts": texts_by_instance,
                        "sample": texts_by_instance[0][:60],
                    }
                )
            else:
                static.append(
                    {
                        "page": page_num,
                        "bbox": list(ref_block["bbox"]),
                        "text": texts_by_instance[0],
                        "sample": texts_by_instance[0][:60],
                    }
                )

    return {"dynamic_fields": dynamic, "static_fields": static}


# ---------------------------------------------------------------------------
# 2. Intra-page: repeated sections
# ---------------------------------------------------------------------------


def detect_repeated_sections(pages: dict[int, list[dict]]) -> list[dict]:
    """Detecta blocos que se repetem N>=2 vezes na mesma página."""
    all_repeated: list[dict] = []

    for page_num, blocks in pages.items():
        # Fingerprint: (x0_bucket, width_bucket, n_words)
        fp_groups: dict[tuple, list[dict]] = defaultdict(list)
        for block in blocks:
            x0 = round(block["bbox"][0] / 20) * 20  # múltiplo de 20pt
            w = round((block["bbox"][2] - block["bbox"][0]) / 20) * 20
            n_words = len(block["text"].split())
            n_words_bucket = round(n_words / 3) * 3  # múltiplo de 3 palavras
            fp = (x0, w, n_words_bucket)
            fp_groups[fp].append(block)

        for fp, group in fp_groups.items():
            if len(group) < MIN_OCCURRENCES:
                continue

            # Verificar que estão em posições y progressivas (não sobrepostos)
            y_positions = sorted(b["bbox"][1] for b in group)
            if len(y_positions) < 2:
                continue
            y_span = y_positions[-1] - y_positions[0]
            avg_height = sum(b["bbox"][3] - b["bbox"][1] for b in group) / len(group)

            # Filtro: y_span deve ser pelo menos avg_height * (N-1) * 0.5
            min_span = avg_height * (len(group) - 1) * 0.5
            if y_span < min_span:
                continue

            all_repeated.append(
                {
                    "page": page_num,
                    "fingerprint": {"x0": fp[0], "width": fp[1], "n_words": fp[2]},
                    "occurrences": len(group),
                    "avg_height_pt": round(avg_height, 1),
                    "y_range": [round(y_positions[0], 1), round(y_positions[-1], 1)],
                    "bboxes": [list(b["bbox"]) for b in group],
                    "sample_texts": [b["text"][:80] for b in group[:4]],
                    "xsd_candidate": "(análise manual necessária)",
                }
            )

    return all_repeated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> None:
    print("=" * 70)
    print("SPIKE 48.3 — Ground Truth Multi-Sample: PosicaoConsolidada x3")
    print("=" * 70)

    # Verificar PDFs
    missing = [p for p in TEMPLATE_PDFS if not p.exists()]
    if missing:
        print(f"\n❌ PDFs não encontrados: {[str(p) for p in missing]}")
        sys.exit(1)

    print(f"\n✅ {len(TEMPLATE_PDFS)} instâncias encontradas:")
    for p in TEMPLATE_PDFS:
        print(f"   {p.name}")

    # Extrair blocos de todos os PDFs
    print("\n📄 Extraindo blocos...")
    all_pages = [extract_blocks(p) for p in TEMPLATE_PDFS]

    page_counts = [len(pages) for pages in all_pages]
    print(f"   Páginas: {page_counts}")

    # 1. Cross-instance analysis
    print("\n🔄 Análise cross-instance (dynamic vs static)...")
    cross = analyze_cross_instance(all_pages)
    n_dynamic = len(cross["dynamic_fields"])
    n_static = len(cross["static_fields"])
    print(f"   Dinâmicos: {n_dynamic} | Estáticos: {n_static}")

    if cross["dynamic_fields"]:
        print("\n   Exemplos DINÂMICOS (primeiros 5):")
        for f in cross["dynamic_fields"][:5]:
            print(f"   p{f['page']} bbox≈{[round(v) for v in f['bbox'][:2]]}: {f.get('sample', f['texts'][0])[:50]!r}")
            if len(f["texts"]) > 1:
                print(f"          → outros: {f['texts'][1][:50]!r}")

    # 2. Intra-page repeated sections (usando primeira instância como referência)
    print("\n🔁 Detecção de seções repetidas (intra-page)...")
    repeated = detect_repeated_sections(all_pages[0])

    if repeated:
        print(f"   {len(repeated)} padrão(ões) repetido(s) encontrado(s):\n")
        for r in repeated:
            print(f"   Página {r['page']}: {r['occurrences']}x | y=[{r['y_range'][0]:.0f}..{r['y_range'][1]:.0f}]pt")
            print(
                f"   Fingerprint: x0={r['fingerprint']['x0']}pt, w={r['fingerprint']['width']}pt, ~{r['fingerprint']['n_words']} palavras"
            )
            print(f"   Amostras: {r['sample_texts'][:2]}")
            print()
    else:
        print("   Nenhum padrão repetido detectado com os critérios atuais.")

    # Salvar relatório
    report = {
        "template": "PosicaoConsolidada",
        "pdfs_analyzed": [p.name for p in TEMPLATE_PDFS],
        "page_counts": page_counts,
        "cross_instance": {
            "dynamic_count": n_dynamic,
            "static_count": n_static,
            "dynamic_fields": cross["dynamic_fields"],
            "static_fields": cross["static_fields"][:30],  # limitar output
        },
        "repeated_sections": repeated,
    }

    out_path = REPORT_DIR / "ground-truth-posicaoconsolidada.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Relatório salvo: {out_path}")
    print(f"   Dinâmicos: {n_dynamic} | Estáticos: {n_static} | Repetidos: {len(repeated)}")


if __name__ == "__main__":
    run()
