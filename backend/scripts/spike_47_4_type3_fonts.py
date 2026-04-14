"""47.4 — Investigar Type3 fonts e fontes customizadas nos certificados."""

import json
import sys
from pathlib import Path

import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAMPLES = Path("tests/fixtures/samples/certificado")
REPORT_DIR = Path("../docs/reports/epic-47")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def check_font(doc, font_name, xref):
    """Tenta extrair dados da fonte via xref."""
    try:
        font_data = doc.extract_font(xref)
        has_tounicode = font_data and len(font_data[3]) > 0
        return has_tounicode
    except Exception:
        return None


def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    result = {
        "file": pdf_path.name,
        "pages": len(doc),
        "fonts": [],
        "type3_found": False,
        "custom_font_found": False,
        "text_extraction_test": [],
        "rawdict_comparison": [],
    }

    # Analisar fontes
    for page_num in range(len(doc)):
        page = doc[page_num]
        font_list = doc.get_page_fonts(page_num, full=True)
        for font in font_list:
            xref, ext, font_type, basefont, name, enc, referencer = font[:7]
            is_type3 = font_type == "Type3"
            is_custom = any(x in basefont for x in ["Sentico", "Humnst", "Type3"])
            has_tounicode = check_font(doc, basefont, xref)

            font_entry = {
                "xref": xref,
                "type": font_type,
                "basefont": basefont,
                "encoding": enc,
                "is_type3": is_type3,
                "has_tounicode": has_tounicode,
            }
            if font_entry not in result["fonts"]:
                result["fonts"].append(font_entry)
            if is_type3:
                result["type3_found"] = True
            if is_custom:
                result["custom_font_found"] = True

    # Teste de extração de texto — standard vs rawdict
    for page_num in range(min(2, len(doc))):
        page = doc[page_num]

        # Método 1: standard dict
        std_spans = []
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        t = span.get("text", "").strip()
                        if t:
                            std_spans.append(t[:50])

        # Método 2: rawdict (tenta recuperar glifos sem ToUnicode)
        raw_spans = []
        try:
            for b in page.get_text("rawdict").get("blocks", []):
                if b.get("type") == 0:
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            t = span.get("text", "").strip()
                            if t:
                                raw_spans.append(t[:50])
        except Exception as e:
            raw_spans = [f"ERRO: {e}"]

        legible_std = sum(1 for t in std_spans if any(c.isalpha() for c in t))
        legible_raw = sum(1 for t in raw_spans if any(c.isalpha() for c in t))

        result["text_extraction_test"].append(
            {
                "page": page_num,
                "std_spans": len(std_spans),
                "std_legible": legible_std,
                "raw_spans": len(raw_spans),
                "raw_legible": legible_raw,
                "std_samples": std_spans[:5],
                "raw_samples": raw_spans[:5],
            }
        )

    doc.close()
    return result


# Executar análise
print("=" * 70)
print("SPIKE 47.4 — Type3 Fonts e Fontes Customizadas nos Certificados")
print("=" * 70)

all_results = []
for pdf_path in sorted(SAMPLES.glob("*.pdf")):
    print(f"\n{'─' * 60}")
    print(f"Analisando: {pdf_path.name}")
    r = analyze_pdf(pdf_path)
    all_results.append(r)

    print(f"  Páginas: {r['pages']}")
    print(f"  Type3 found: {'⚠️  SIM' if r['type3_found'] else '✅ não'}")
    print(f"  Fonte customizada: {'⚠️  SIM' if r['custom_font_found'] else '✅ não'}")
    print("  Fontes detectadas:")
    for f in r["fonts"][:5]:
        tc = "✅ ToUnicode" if f["has_tounicode"] else "❌ sem ToUnicode"
        print(f"    [{f['type']}] {f['basefont']} — {tc}")
    for t in r["text_extraction_test"]:
        std_pct = round(t["std_legible"] / max(t["std_spans"], 1) * 100)
        raw_pct = round(t["raw_legible"] / max(t["raw_spans"], 1) * 100)
        print(
            f"  Pág {t['page']}: std={t['std_spans']} spans ({std_pct}% legíveis) | raw={t['raw_spans']} ({raw_pct}% legíveis)"
        )
        if t["std_samples"]:
            print(f"    std sample: {t['std_samples'][0]}")

# Salvar relatório
report_path = REPORT_DIR / "type3-fonts-report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 70}")
print(f"Relatório salvo: {report_path}")
print("\nRECOMENDAÇÃO:")
has_type3 = any(r["type3_found"] for r in all_results)
has_custom = any(r["custom_font_found"] for r in all_results)
if has_type3:
    print("  ⚠️  Type3 fonts detectadas — avaliar Mistral OCR como fallback de texto")
if has_custom:
    print("  ⚠️  Fontes customizadas — verificar se ToUnicode map está presente")
if not has_type3 and not has_custom:
    print("  ✅ Nenhum problema crítico de fonte detectado")
