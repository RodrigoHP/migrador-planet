"""Pilar A Audit — Boleto Corporate.Boleto.Convenio.pdf

Compara o que PyMuPDF consegue extrair direto do PDF (ground truth)
vs o que o pipeline extraiu (tmp_baseline_boleto.json).

Dimensoes auditadas:
- Text blocks / spans
- Linhas e retangulos (drawings)
- Imagens raster
- Tabelas (find_tables)
- Fonts unicas
- Cores unicas
- Page metadata
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

# Forca UTF-8 no stdout (Windows console)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PDF_PATH = Path("D:/Downloads/Corporate.Boleto.Convenio.pdf")
BASELINE_PATH = Path("C:/CohortAios/migrador-planet/backend/tmp_baseline_boleto.json")


def audit_pdf_ground_truth(pdf_path: Path) -> dict:
    """Extrai tudo que o PyMuPDF consegue ver (baseline de deteccao possivel)."""
    doc = fitz.open(pdf_path)
    result = {
        "pages": [],
        "total": {
            "text_blocks": 0,
            "text_spans": 0,
            "text_chars": 0,
            "drawings_lines": 0,
            "drawings_rects": 0,
            "drawings_other": 0,
            "images": 0,
            "tables_find_tables": 0,
            "xref_images": 0,
        },
        "fonts_unique": set(),
        "colors_unique": set(),
    }

    for page_index, page in enumerate(doc):
        page_data = {
            "index": page_index,
            "width": page.rect.width,
            "height": page.rect.height,
            "rotation": page.rotation,
            "text_blocks": 0,
            "text_spans": 0,
            "drawings_lines": 0,
            "drawings_rects": 0,
            "drawings_other": 0,
            "images": 0,
            "tables": [],
            "fonts": set(),
            "sample_texts": [],
        }

        # Text blocks
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                page_data["text_blocks"] += 1
                result["total"]["text_blocks"] += 1
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        page_data["text_spans"] += 1
                        result["total"]["text_spans"] += 1
                        result["total"]["text_chars"] += len(span.get("text", ""))
                        font = span.get("font", "")
                        if font:
                            page_data["fonts"].add(font)
                            result["fonts_unique"].add(font)
                        color = span.get("color")
                        if color is not None:
                            result["colors_unique"].add(color)
                        text = span.get("text", "").strip()
                        if text and len(page_data["sample_texts"]) < 10:
                            page_data["sample_texts"].append(text)

        # Drawings
        try:
            drawings = page.get_drawings()
            for d in drawings:
                for item in d.get("items", []):
                    kind = item[0]
                    if kind == "l":
                        page_data["drawings_lines"] += 1
                        result["total"]["drawings_lines"] += 1
                    elif kind == "re":
                        page_data["drawings_rects"] += 1
                        result["total"]["drawings_rects"] += 1
                    else:
                        page_data["drawings_other"] += 1
                        result["total"]["drawings_other"] += 1
        except Exception as e:
            page_data["drawings_error"] = str(e)

        # Images (get_images xref + get_image_info renderizadas)
        try:
            xref_images = page.get_images(full=True)
            page_data["xref_images"] = len(xref_images)
            result["total"]["xref_images"] += len(xref_images)
        except Exception:
            page_data["xref_images"] = 0

        try:
            img_info = page.get_image_info(xrefs=True)
            page_data["images"] = len(img_info)
            result["total"]["images"] += len(img_info)
            page_data["image_details"] = [
                {
                    "bbox": list(img.get("bbox", [])),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                    "xref": img.get("xref", 0),
                }
                for img in img_info
            ]
        except Exception as e:
            page_data["images_error"] = str(e)

        # Tables via find_tables
        try:
            tables = page.find_tables()
            for table in tables.tables:
                cells = table.extract()
                page_data["tables"].append(
                    {
                        "bbox": list(table.bbox),
                        "rows": len(cells),
                        "cols": len(cells[0]) if cells else 0,
                    }
                )
                result["total"]["tables_find_tables"] += 1
        except Exception as e:
            page_data["tables_error"] = str(e)

        page_data["fonts"] = sorted(page_data["fonts"])
        result["pages"].append(page_data)

    result["fonts_unique"] = sorted(result["fonts_unique"])
    result["colors_unique"] = sorted(result["colors_unique"])
    result["page_count"] = len(doc)
    doc.close()
    return result


def _walk_tree(node: dict, counter: Counter, fonts: set, sample_text: list) -> None:
    """Conta todos os node.type de uma documentTree, recursivo."""
    if not isinstance(node, dict):
        return
    t = node.get("type")
    if t:
        counter[t] += 1
    fn = node.get("font_name")
    if fn:
        fonts.add(fn)
    text = (node.get("text") or node.get("value") or "").strip()
    if text and len(sample_text) < 20 and t in ("label", "value", "dynamic", "likely_dynamic", "field"):
        sample_text.append(f"[{t}] {text[:60]}")
    for c in node.get("children", []) or []:
        _walk_tree(c, counter, fonts, sample_text)


def audit_pipeline_output(baseline_path: Path) -> dict:
    """Extrai o que o pipeline produziu (navegando layout_types[].documentTree)."""
    raw = baseline_path.read_bytes().decode("utf-8", errors="replace")
    data = json.loads(raw)
    result = data.get("result_json", data)

    summary = {
        "layouts": [],
        "total_field_mappings": len(result.get("field_mappings", [])),
        "fonts_found": set(),
        "totals": Counter(),
    }

    layout_types = result.get("layout_types", [])
    for lt in layout_types if isinstance(layout_types, list) else []:
        tree_root = (lt.get("documentTree") or {}).get("root")
        counter = Counter()
        fonts: set = set()
        samples: list = []
        if tree_root:
            _walk_tree(tree_root, counter, fonts, samples)

        summary["layouts"].append(
            {
                "id": lt.get("id", "?"),
                "page_count": lt.get("page_count"),
                "confidence": lt.get("confidence"),
                "node_counts": dict(counter),
                "fonts": sorted(fonts),
                "samples": samples,
            }
        )
        summary["totals"] += counter
        summary["fonts_found"] |= fonts

    summary["totals"] = dict(summary["totals"])
    summary["fonts_found"] = sorted(summary["fonts_found"])
    return summary


def main():
    print("=" * 80)
    print("PILAR A AUDIT — Boleto Corporate.Boleto.Convenio.pdf")
    print("=" * 80)

    print("\n[1] Ground Truth (PyMuPDF direto)")
    print("-" * 80)
    gt = audit_pdf_ground_truth(PDF_PATH)
    print(f"Paginas: {gt['page_count']}")
    for page in gt["pages"]:
        print(f"\nPage {page['index']} — {page['width']:.0f}x{page['height']:.0f}pts (rot={page['rotation']})")
        print(f"  Text blocks: {page['text_blocks']}")
        print(f"  Text spans:  {page['text_spans']}")
        print(f"  Linhas:      {page['drawings_lines']}")
        print(f"  Retangulos:  {page['drawings_rects']}")
        print(f"  Other draw:  {page['drawings_other']}")
        print(f"  Images:      {page['images']} (xref={page['xref_images']})")
        print(f"  Tables:      {len(page['tables'])}")
        if page.get("image_details"):
            for i, img in enumerate(page["image_details"]):
                print(f"    Img {i}: {img['width']}x{img['height']}px bbox={img['bbox']}")
        if page.get("tables"):
            for i, t in enumerate(page["tables"]):
                print(f"    Tbl {i}: {t['rows']}rows x {t['cols']}cols bbox={t['bbox']}")
        print(f"  Fonts:       {', '.join(page['fonts'][:3])}{'...' if len(page['fonts']) > 3 else ''}")
        print(f"  Sample text: {' | '.join(page['sample_texts'][:3])}")

    print("\nTOTAIS (PyMuPDF ground truth):")
    for k, v in gt["total"].items():
        print(f"  {k:30s} = {v}")
    print(f"  fonts_unique (count)         = {len(gt['fonts_unique'])}")
    print(f"  fonts: {', '.join(gt['fonts_unique'][:8])}")
    print(f"  colors_unique (count)        = {len(gt['colors_unique'])}")

    print("\n[2] Pipeline Output (tmp_baseline_boleto.json)")
    print("-" * 80)
    po = audit_pipeline_output(BASELINE_PATH)
    print(f"Layouts detectados: {len(po['layouts'])}")
    for lt in po["layouts"]:
        print(f"\nLayout {lt['id']}: conf={lt['confidence']}, pages={lt['page_count']}")
        for t, n in sorted(lt["node_counts"].items(), key=lambda x: -x[1]):
            print(f"    {t:20s} = {n}")
        print(f"    fonts: {', '.join(lt['fonts'])}")
        if lt["samples"]:
            print("    samples:")
            for s in lt["samples"][:10]:
                print(f"      {s}")

    print(f"\nTotal field_mappings: {po['total_field_mappings']}")
    print(f"Fonts encontradas no pipeline: {len(po['fonts_found'])}")

    print("\n[3] GAP ANALYSIS — Ground Truth vs Pipeline")
    print("-" * 80)

    # Ground truth aggregates
    gt_text_spans = gt["total"]["text_spans"]
    gt_text_blocks = gt["total"]["text_blocks"]
    gt_lines = gt["total"]["drawings_lines"]
    gt_rects = gt["total"]["drawings_rects"]
    gt_images = gt["total"]["images"]
    gt_tables = gt["total"]["tables_find_tables"]

    # Pipeline aggregates (soma de Layout A + B)
    totals = po["totals"]
    po_text_leaves = (
        totals.get("label", 0)
        + totals.get("value", 0)
        + totals.get("dynamic", 0)
        + totals.get("likely_dynamic", 0)
        + totals.get("field", 0)
    )
    po_lines = totals.get("line", 0)
    po_images = totals.get("image", 0)
    po_tables = totals.get("table", 0)

    print(f"{'Dimensao':28s} {'PyMuPDF':>12s} {'Pipeline':>12s} {'Status':>10s}")
    print("-" * 68)

    def row(name, gt_v, po_v):
        status = "OK" if po_v >= gt_v else f"GAP-{gt_v - po_v}"
        print(f"  {name:26s} {gt_v:12d} {po_v:12d} {status:>10s}")

    row("text spans/leaves", gt_text_spans, po_text_leaves)
    row("text blocks", gt_text_blocks, po_text_leaves)
    row("lines", gt_lines, po_lines)
    row("rectangles", gt_rects, 0)  # pipeline nao separa rects
    row("images", gt_images, po_images)
    row("tables (find_tables)", gt_tables, po_tables)

    # Fonts
    gt_fonts = set(gt["fonts_unique"])
    po_fonts = set(po["fonts_found"])
    missing_fonts = gt_fonts - po_fonts
    if missing_fonts:
        print(f"\nFontes perdidas pelo pipeline: {sorted(missing_fonts)}")
    else:
        print(f"\nFontes: OK (pipeline tem {len(po_fonts)} / gt tem {len(gt_fonts)})")

    # Conteudo raster: tabela JPEG 2174x1337
    print("\n[4] CONTEUDO INVISIVEL (raster)")
    print("-" * 80)
    for page in gt["pages"]:
        for img in page.get("image_details", []):
            w, h = img["width"], img["height"]
            if w >= 500 and h >= 500:  # imagem grande = provavel tabela/conteudo
                print(f"  Page {page['index']}: imagem {w}x{h}px bbox={img['bbox']}")
                print("    → PyMuPDF nao consegue ler texto/celulas internos")
                print(f"    → Pipeline detectou {po_tables} 'table' node(s) para a regiao")

    print("\n" + "=" * 80)
    print("OBSERVACAO CRITICA:")
    print("O ground truth 'PyMuPDF direto' NAO inclui:")
    print("  - Conteudo dentro de imagens raster (JPEG tabela, logos c/ texto)")
    print("  - Texto visivel que PyMuPDF nao consegue extrair (raster puro)")
    print("Para capturar esses, precisaria OCR + Vision API.")
    print("=" * 80)


if __name__ == "__main__":
    main()
