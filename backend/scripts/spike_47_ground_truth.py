"""47.1/47.2/47.3 — Ground truth PyMuPDF para todos os samples (exceto certificado)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAMPLES = Path("tests/fixtures/samples")
REPORT_DIR = Path("../docs/reports/epic-47")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SKIP_TIPOS = {"certificado"}  # certificados vão na 47.5


def analyze_pdf(pdf_path: Path) -> dict:
    try:
        doc = fitz.open(pdf_path)
        result: dict = {
            "file": pdf_path.name,
            "tipo": pdf_path.parent.name,
            "pages": len(doc),
            "text_spans": 0,
            "images": 0,
            "raster_large": [],
            "tables_vectorial": 0,
            "fonts": set(),
            "sample_texts": [],
            "page_detail": [],
        }
        for page_num, page in enumerate(doc):
            pg = {"page": page_num, "spans": 0, "images": 0, "rasters": 0, "tables": 0}
            for b in page.get_text("dict").get("blocks", []):
                if b.get("type") == 0:
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            result["text_spans"] += 1
                            pg["spans"] += 1
                            if span.get("font"):
                                result["fonts"].add(span["font"])
                            t = span.get("text", "").strip()
                            if t and len(result["sample_texts"]) < 8:
                                result["sample_texts"].append(t[:60])
            imgs = page.get_image_info(xrefs=True)
            result["images"] += len(imgs)
            pg["images"] = len(imgs)
            for img in imgs:
                w, h = img.get("width", 0), img.get("height", 0)
                if w >= 500 and h >= 500:
                    result["raster_large"].append({"page": page_num, "w": w, "h": h, "bbox": list(img.get("bbox", []))})
                    pg["rasters"] += 1
            try:
                tbls = page.find_tables()
                result["tables_vectorial"] += len(tbls.tables)
                pg["tables"] = len(tbls.tables)
            except Exception:
                pass
            result["page_detail"].append(pg)
        result["fonts"] = sorted(result["fonts"])
        result["raster_count"] = len(result["raster_large"])
        doc.close()
        return result
    except Exception as e:
        return {"file": pdf_path.name, "tipo": pdf_path.parent.name, "error": str(e)}


print("=" * 70)
print("GROUND TRUTH — 47.1 (relatório/apólice) + 47.2 (boleto) + 47.3 (dirf)")
print("=" * 70)

all_results = []
for tipo_dir in sorted(SAMPLES.iterdir()):
    if not tipo_dir.is_dir() or tipo_dir.name in SKIP_TIPOS:
        continue
    pdfs = sorted(tipo_dir.glob("*.pdf"))
    if not pdfs:
        continue
    print(f"\n{'─' * 60}")
    print(f"TIPO: {tipo_dir.name.upper()}")
    for pdf_path in pdfs:
        r = analyze_pdf(pdf_path)
        all_results.append(r)
        if "error" in r:
            print(f"  ❌ {r['file']}: {r['error']}")
            continue
        raster_warn = f"⚠️  {r['raster_count']} rasters grandes" if r["raster_count"] else "✅ sem rasters"
        print(f"\n  {r['file']}")
        print(f"    Páginas: {r['pages']} | Spans: {r['text_spans']} | {raster_warn}")
        print(f"    Tabelas vetoriais: {r['tables_vectorial']} | Imagens: {r['images']}")
        print(f"    Fontes: {', '.join(r['fonts'])[:80]}")
        if r["sample_texts"]:
            print(f"    Sample: {r['sample_texts'][0]}")

# Sumário por tipo
print(f"\n{'=' * 70}")
print("SUMÁRIO POR TIPO")
print(f"{'─' * 70}")
by_tipo: dict = defaultdict(list)
for r in all_results:
    if "error" not in r:
        by_tipo[r["tipo"]].append(r)

for tipo, items in sorted(by_tipo.items()):
    total_rasters = sum(r["raster_count"] for r in items)
    total_tables = sum(r["tables_vectorial"] for r in items)
    print(f"  {tipo:15s} {len(items)} PDFs | rasters: {total_rasters} | tabelas vetoriais: {total_tables}")

# Salvar
report_path = REPORT_DIR / "ground-truth-47123.json"
# Serializar sets para JSON
for r in all_results:
    if isinstance(r.get("fonts"), set):
        r["fonts"] = sorted(r["fonts"])
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"\nRelatório salvo: {report_path}")
