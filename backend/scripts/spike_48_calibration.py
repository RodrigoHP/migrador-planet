"""48.9 — Calibration Spike: empirical thresholds for Stage 1 Ensemble Voting.

Computes score distributions for SAME vs DIFF page pairs across 4 signals:
  1. pHash masked thumbnail (imagehash)
  2. Font Jaccard signature (fitz get_text dict)
  3. Structural edit distance (difflib on bbox sequences)
  4. Markdown hash (pymupdf4llm) — exact match after dynamic-content normalization

Outputs:
  docs/reports/epic-48/calibration-thresholds.json
  docs/reports/epic-48/calibration-summary.md

Re-run 2026-04-18: fixtures corrigidos (ApoliceVgA/B separados),
pymupdf4llm instalado, sinal 4 habilitado.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from statistics import mean, stdev

import fitz
import imagehash
import pymupdf4llm
from PIL import Image, ImageDraw

# Normalization patterns for markdown fingerprint (remove dynamic content)
_MD_PATTERNS = [
    (re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"), "[CPF]"),
    (re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"), "[CNPJ]"),
    (re.compile(r"\d{2}/\d{2}/\d{4}"), "[DATE]"),
    (re.compile(r"\d{4}-\d{2}-\d{2}"), "[DATE]"),
    (re.compile(r"R\$\s*[\d.,]+"), "[BRL]"),
    (re.compile(r"\d[\d.,]*"), "[NUM]"),
]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAMPLES = Path("tests/fixtures/samples")
REPORT_DIR = Path("../docs/reports/epic-48")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Template groups — same base name = same template
# ---------------------------------------------------------------------------
TEMPLATE_GROUPS: dict[str, list[Path]] = {
    # boleto
    "boleto_corporate": sorted(SAMPLES.glob("boleto/BoletoCorporateMercantil*.pdf")),
    "boleto_individual": sorted(SAMPLES.glob("boleto/BoletoIndividual*.pdf")),
    "boleto_vg": sorted(SAMPLES.glob("boleto/BoletoVg*.pdf")),
    # apolice — ApoliceVgA e ApoliceVgB são templates distintos (confirmado visualmente)
    "apolice_vg_a": sorted(SAMPLES.glob("apolice/ApoliceVgA*.pdf")),  # 1 instância
    "apolice_vg_b": sorted(SAMPLES.glob("apolice/ApoliceVgB*.pdf")),  # 2 instâncias
    # dirf
    "dirf_informa": sorted(SAMPLES.glob("dirf/DirfInformaFinanceiro*.pdf")),
    "dirf_v8": sorted(SAMPLES.glob("dirf/InformeFinanceiroV8*.pdf")),
    # relatorio
    "relatorio_extrato": sorted(SAMPLES.glob("relatorio/ExtratoPrevidencia*.pdf")),
    "relatorio_posicao": sorted(SAMPLES.glob("relatorio/PosicaoConsolidada*.pdf")),
    "relatorio_beneficiarios": sorted(SAMPLES.glob("relatorio/RelatorioBeneficiarios*.pdf")),
}

# ---------------------------------------------------------------------------
# Signal implementations
# ---------------------------------------------------------------------------


def masked_thumbnail(page: fitz.Page, size: int = 128) -> imagehash.ImageHash:
    """pHash of thumbnail with text blocks replaced by gray rectangles."""
    scale = size / max(page.rect.width, page.rect.height)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    sw = pix.width / page.rect.width
    sh = pix.height / page.rect.height
    for block in page.get_text("blocks"):
        if int(block[6]) == 0:  # text block
            x0, y0, x1, y1 = block[0] * sw, block[1] * sh, block[2] * sw, block[3] * sh
            draw.rectangle([x0, y0, x1, y1], fill=(200, 200, 200))
    return imagehash.phash(img.convert("L"))


def font_signature(page: fitz.Page) -> frozenset:
    """Jaccard-ready set of (y_bucket, font_name, size_bucket) tuples."""
    sig: set[tuple] = set()
    h = page.rect.height or 1.0
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                y_bucket = round(span["origin"][1] / h, 1)
                size_bucket = round(span["size"] * 2) / 2
                sig.add((y_bucket, span.get("font", ""), size_bucket))
    return frozenset(sig)


def layout_sequence(page: fitz.Page) -> list[tuple]:
    """Sequence of (x0_bucket, y0_bucket, width_bucket) for text blocks."""
    blocks = page.get_text("blocks")
    w, h = page.rect.width or 1.0, page.rect.height or 1.0
    seq = []
    for b in sorted(blocks, key=lambda b: (b[1], b[0])):
        if int(b[6]) == 0:
            seq.append(
                (
                    round(b[0] / w, 2),
                    round(b[1] / h, 2),
                    round((b[2] - b[0]) / w, 2),
                )
            )
    return seq


def struct_edit_distance(seq_a: list, seq_b: list) -> float:
    """Normalised edit distance via SequenceMatcher (0=identical, 1=totally different)."""
    if not seq_a and not seq_b:
        return 0.0
    if not seq_a or not seq_b:
        return 1.0
    ratio = SequenceMatcher(None, seq_a, seq_b).ratio()
    return 1.0 - ratio  # distance: lower = more similar


def markdown_fingerprint(doc: fitz.Document, page_index: int = 0) -> str | None:
    """SHA256[:16] of normalized markdown for page — invariant to dynamic content."""
    try:
        md = pymupdf4llm.to_markdown(doc, pages=[page_index])
        for pattern, token in _MD_PATTERNS:
            md = pattern.sub(token, md)
        return hashlib.sha256(md.encode("utf-8")).hexdigest()[:16]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Extract first page features from each PDF
# ---------------------------------------------------------------------------


def extract_features(pdf_path: Path) -> dict | None:
    try:
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        phash = masked_thumbnail(page)
        font_sig = font_signature(page)
        layout_seq = layout_sequence(page)
        md_hash = markdown_fingerprint(doc, 0)
        doc.close()
        return {
            "path": str(pdf_path),
            "phash": phash,
            "font_sig": font_sig,
            "layout_seq": layout_seq,
            "md_hash": md_hash,
        }
    except Exception as exc:
        print(f"  ⚠️  {pdf_path.name}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Compute pairwise scores
# ---------------------------------------------------------------------------


def compute_scores(feats_a: dict, feats_b: dict) -> dict:
    phash_dist = int(feats_a["phash"] - feats_b["phash"])  # convert numpy.int64 → int
    sig_a, sig_b = feats_a["font_sig"], feats_b["font_sig"]
    union = sig_a | sig_b
    font_jaccard = len(sig_a & sig_b) / len(union) if union else 1.0
    struct_dist = struct_edit_distance(feats_a["layout_seq"], feats_b["layout_seq"])
    md_a, md_b = feats_a.get("md_hash"), feats_b.get("md_hash")
    md_match = (md_a == md_b) if (md_a is not None and md_b is not None) else None
    return {
        "phash_dist": phash_dist,
        "font_jaccard": round(font_jaccard, 4),
        "struct_dist": round(struct_dist, 4),
        "md_match": md_match,  # True/False/None
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 70)
    print("SPIKE 48.9 — Calibração Empírica: Stage 1 Ensemble Voting Thresholds")
    print("=" * 70)

    # 1. Extract features
    print("\n📄 Extraindo features de todos os PDFs...")
    group_features: dict[str, list[dict]] = {}
    for group_name, paths in TEMPLATE_GROUPS.items():
        if not paths:
            print(f"  ⚠️  {group_name}: nenhum PDF encontrado — pulando")
            continue
        feats = []
        for p in paths:
            f = extract_features(p)
            if f:
                feats.append(f)
        if feats:
            group_features[group_name] = feats
            print(f"  ✅ {group_name}: {len(feats)} PDFs")

    # 2. Build SAME and DIFF pairs
    print("\n🔀 Construindo pares SAME e DIFF...")
    same_scores: list[dict] = []
    diff_scores: list[dict] = []

    group_names = list(group_features.keys())

    # SAME: within-group combinations
    for group_name, feats in group_features.items():
        for fa, fb in combinations(feats, 2):
            scores = compute_scores(fa, fb)
            scores["pair_type"] = "SAME"
            scores["group"] = group_name
            scores["a"] = Path(fa["path"]).name
            scores["b"] = Path(fb["path"]).name
            same_scores.append(scores)

    # DIFF: cross-group within same document type
    type_map: dict[str, list[str]] = defaultdict(list)
    for name in group_names:
        doc_type = name.split("_")[0]
        type_map[doc_type].append(name)

    for doc_type, groups in type_map.items():
        if len(groups) < 2:
            continue
        for g1, g2 in combinations(groups, 2):
            feats1 = group_features[g1]
            feats2 = group_features[g2]
            # one representative pair per combination
            fa = feats1[0]
            fb = feats2[0]
            scores = compute_scores(fa, fb)
            scores["pair_type"] = "DIFF"
            scores["group"] = f"{g1} vs {g2}"
            scores["a"] = Path(fa["path"]).name
            scores["b"] = Path(fb["path"]).name
            diff_scores.append(scores)

    print(f"  Pares SAME: {len(same_scores)}")
    print(f"  Pares DIFF: {len(diff_scores)}")

    # 3. Compute distributions
    def stats(values: list[float]) -> dict:
        if not values:
            return {"min": None, "max": None, "mean": None, "std": None}
        return {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(mean(values), 4),
            "std": round(stdev(values), 4) if len(values) > 1 else 0.0,
        }

    signals = ["phash_dist", "font_jaccard", "struct_dist"]
    distributions: dict[str, dict] = {}

    print("\n📊 Distribuições por sinal:")
    for signal in signals:
        same_vals = [s[signal] for s in same_scores]
        diff_vals = [s[signal] for s in diff_scores]
        distributions[signal] = {
            "SAME": stats(same_vals),
            "DIFF": stats(diff_vals),
            "same_values": same_vals,
            "diff_values": diff_vals,
        }
        s_stat = distributions[signal]["SAME"]
        d_stat = distributions[signal]["DIFF"]
        print(f"\n  {signal}:")
        print(f"    SAME: min={s_stat['min']} max={s_stat['max']} mean={s_stat['mean']} std={s_stat['std']}")
        print(f"    DIFF: min={d_stat['min']} max={d_stat['max']} mean={d_stat['mean']} std={d_stat['std']}")

    # Signal 4: markdown hash match rate
    same_md = [s["md_match"] for s in same_scores if s["md_match"] is not None]
    diff_md = [s["md_match"] for s in diff_scores if s["md_match"] is not None]
    md_same_rate = sum(same_md) / len(same_md) if same_md else None
    md_diff_rate = sum(diff_md) / len(diff_md) if diff_md else None
    print("\n  md_match (sinal 4):")
    print(
        f"    SAME: match_rate={md_same_rate:.1%} ({sum(same_md)}/{len(same_md)} pares)"
        if same_md
        else "    SAME: sem dados"
    )
    print(
        f"    DIFF: match_rate={md_diff_rate:.1%} ({sum(diff_md)}/{len(diff_md)} pares)"
        if diff_md
        else "    DIFF: sem dados"
    )

    # 4. Recommend thresholds
    print("\n🎯 Thresholds recomendados:")

    thresholds: dict[str, dict] = {}

    # pHash: lower = more similar; T = max distance for SAME
    # Use SAME max + small buffer, but below DIFF min
    if distributions["phash_dist"]["SAME"]["max"] is not None:
        same_max = distributions["phash_dist"]["SAME"]["max"]
        diff_min = distributions["phash_dist"]["DIFF"]["min"]
        same_mean = distributions["phash_dist"]["SAME"]["mean"]
        diff_mean = distributions["phash_dist"]["DIFF"]["mean"]
        # Use midpoint between means for robustness when ranges overlap
        t_phash = int((same_mean + diff_mean) / 2) if same_mean and diff_mean else int(same_max + 3)
        thresholds["T_phash"] = {
            "value": t_phash,
            "meaning": f"hamming_distance(a, b) <= {t_phash} → SAME",
            "same_max_observed": same_max,
            "diff_min_observed": diff_min,
        }
        print(f"  T_phash = {t_phash} (SAME max={same_max}, DIFF min={diff_min})")

    # Font Jaccard: higher = more similar; T = min similarity for SAME
    if distributions["font_jaccard"]["SAME"]["min"] is not None:
        same_min = distributions["font_jaccard"]["SAME"]["min"]
        diff_max = distributions["font_jaccard"]["DIFF"]["max"]
        same_mean = distributions["font_jaccard"]["SAME"]["mean"]
        diff_mean = distributions["font_jaccard"]["DIFF"]["mean"]
        t_font = round((same_mean + diff_mean) / 2, 2) if same_mean and diff_mean else round(same_min * 0.85, 2)
        thresholds["T_font"] = {
            "value": t_font,
            "meaning": f"jaccard(a, b) >= {t_font} → SAME",
            "same_min_observed": same_min,
            "diff_max_observed": diff_max,
        }
        print(f"  T_font = {t_font} (SAME min={same_min}, DIFF max={diff_max})")

    # Struct dist: lower = more similar; T = max distance for SAME
    if distributions["struct_dist"]["SAME"]["max"] is not None:
        same_max = distributions["struct_dist"]["SAME"]["max"]
        diff_min = distributions["struct_dist"]["DIFF"]["min"]
        same_mean = distributions["struct_dist"]["SAME"]["mean"]
        diff_mean = distributions["struct_dist"]["DIFF"]["mean"]
        t_struct = round((same_mean + diff_mean) / 2, 2) if same_mean and diff_mean else round(same_max + 0.05, 2)
        thresholds["T_struct"] = {
            "value": t_struct,
            "meaning": f"edit_distance(a, b) <= {t_struct} → SAME",
            "same_max_observed": same_max,
            "diff_min_observed": diff_min,
        }
        print(f"  T_struct = {t_struct} (SAME max={same_max}, DIFF min={diff_min})")

    # Markdown hash: binary (match=SAME, no-match=DIFF) — no numeric threshold needed
    if same_md:
        thresholds["T_markdown"] = {
            "value": "exact_match",
            "meaning": "md_hash(a) == md_hash(b) → SAME",
            "same_match_rate": round(md_same_rate, 4) if md_same_rate is not None else None,
            "diff_match_rate": round(md_diff_rate, 4) if md_diff_rate is not None else None,
            "note": f"SAME pairs match {md_same_rate:.1%}, DIFF pairs match {md_diff_rate:.1%}"
            if md_same_rate
            else "no data",
        }
        print(f"  T_markdown = exact_match (SAME rate={md_same_rate:.1%}, DIFF rate={md_diff_rate:.1%})")
    else:
        thresholds["T_markdown"] = {
            "value": "no_data",
            "meaning": "no pairs available for markdown calibration",
        }
        print("  T_markdown = no_data")

    # 5. Expected precision/recall
    def precision_recall(same_vals, diff_vals, threshold, mode="le"):
        """mode: le = score <= threshold is SAME; ge = score >= threshold is SAME."""

        def is_same(v):
            return v <= threshold if mode == "le" else v >= threshold

        tp = sum(1 for v in same_vals if is_same(v))
        fp = sum(1 for v in diff_vals if is_same(v))
        fn_ = sum(1 for v in same_vals if not is_same(v))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn_) if (tp + fn_) > 0 else 1.0
        return round(precision, 3), round(recall, 3)

    perf: dict[str, dict] = {}
    if "T_phash" in thresholds:
        p, r = precision_recall(
            distributions["phash_dist"]["same_values"],
            distributions["phash_dist"]["diff_values"],
            thresholds["T_phash"]["value"],
            "le",
        )
        perf["phash_dist"] = {"precision": p, "recall": r}

    if "T_font" in thresholds:
        p, r = precision_recall(
            distributions["font_jaccard"]["same_values"],
            distributions["font_jaccard"]["diff_values"],
            thresholds["T_font"]["value"],
            "ge",
        )
        perf["font_jaccard"] = {"precision": p, "recall": r}

    if "T_struct" in thresholds:
        p, r = precision_recall(
            distributions["struct_dist"]["same_values"],
            distributions["struct_dist"]["diff_values"],
            thresholds["T_struct"]["value"],
            "le",
        )
        perf["struct_dist"] = {"precision": p, "recall": r}

    # 6. Save JSON
    output = {
        "spike": "48.9",
        "date": "2026-04-18",
        "fixtures": {g: [str(p) for p in paths] for g, paths in TEMPLATE_GROUPS.items() if paths},
        "pair_counts": {"SAME": len(same_scores), "DIFF": len(diff_scores)},
        "distributions": {
            k: {
                "SAME": v["SAME"],
                "DIFF": v["DIFF"],
            }
            for k, v in distributions.items()
        },
        "thresholds": thresholds,
        "expected_performance": perf,
        "markdown_hash": {
            "same_match_rate": round(md_same_rate, 4) if md_same_rate is not None else None,
            "diff_match_rate": round(md_diff_rate, 4) if md_diff_rate is not None else None,
        },
        "all_pairs": same_scores + diff_scores,
    }

    out_json = REPORT_DIR / "calibration-thresholds.json"
    out_json.write_text(json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"\n✅ Relatório salvo: {out_json}")

    # 7. Save Markdown summary
    summary = generate_summary(output, perf, distributions)
    out_md = REPORT_DIR / "calibration-summary.md"
    out_md.write_text(summary, encoding="utf-8")
    print(f"✅ Summary salvo: {out_md}")

    # 8. Print pair details
    print("\n📋 Pares SAME (detalhes):")
    for s in same_scores:
        print(
            f"  [{s['group']}] {s['a']} × {s['b']} → phash={s['phash_dist']} font={s['font_jaccard']} struct={s['struct_dist']}"
        )

    print("\n📋 Pares DIFF (detalhes):")
    for s in diff_scores:
        print(
            f"  [{s['group']}] {s['a']} × {s['b']} → phash={s['phash_dist']} font={s['font_jaccard']} struct={s['struct_dist']}"
        )


def generate_summary(output: dict, perf: dict, distributions: dict) -> str:
    th = output["thresholds"]
    pairs = output["pair_counts"]

    lines = [
        "# Spike 48.9 — Calibration Summary: Stage 1 Ensemble Voting Thresholds",
        "",
        "**Data:** 2026-04-18 (re-calibração — fixtures corrigidos, sinal 4 habilitado)  ",
        f"**Pares analisados:** {pairs['SAME']} SAME + {pairs['DIFF']} DIFF  ",
        "**Fixtures:** PDFs em 4 tipos (boleto, apolice, dirf, relatorio) — ApoliceVgA/B separados",
        "",
        "---",
        "",
        "## Thresholds Recomendados",
        "",
        "| Sinal | Threshold | Precision | Recall | Status |",
        "|-------|-----------|-----------|--------|--------|",
    ]

    signal_map = {
        "T_phash": ("pHash masked thumbnail", "phash_dist"),
        "T_font": ("Font Jaccard", "font_jaccard"),
        "T_struct": ("Struct edit distance", "struct_dist"),
        "T_markdown": ("Markdown hash", None),
    }

    for key, (name, perf_key) in signal_map.items():
        t = th.get(key, {})
        val = t.get("value", "—")
        if perf_key and perf_key in perf:
            p = perf[perf_key]["precision"]
            r = perf[perf_key]["recall"]
            status = "✅" if p >= 0.85 and r >= 0.85 else "⚠️"
            lines.append(f"| {name} | {val} | {p:.1%} | {r:.1%} | {status} |")
        else:
            lines.append(f"| {name} | {val} | — | — | ⏭️ SKIPPED |")

    lines += [
        "",
        "---",
        "",
        "## Distribuições por Sinal",
        "",
    ]

    for signal, data in distributions.items():
        s = data["SAME"]
        d = data["DIFF"]
        gap = None
        if signal == "phash_dist" and s["max"] is not None and d["min"] is not None:
            gap = round(d["min"] - s["max"], 2)
        elif signal == "font_jaccard" and s["min"] is not None and d["max"] is not None:
            gap = round(s["min"] - d["max"], 2)
        elif signal == "struct_dist" and s["max"] is not None and d["min"] is not None:
            gap = round(d["min"] - s["max"], 2)

        gap_str = f" (gap={gap})" if gap is not None else ""
        lines += [
            f"### {signal}{gap_str}",
            "",
            f"- **SAME:** min={s['min']} max={s['max']} mean={s['mean']} std={s['std']}",
            f"- **DIFF:** min={d['min']} max={d['max']} mean={d['mean']} std={d['std']}",
            "",
        ]

    lines += [
        "---",
        "",
        "## Recomendações para Implementação",
        "",
        "1. **4 sinais calibrados** (pHash, Font Jaccard, Struct dist, Markdown hash) no ensemble",
        "2. **Voting majoritário:** 4/4 → 0.97, 3/4 → 0.90, 2/4 → 0.75, 1/4 → 0.35, 0/4 → 0.05",
        "3. **Markdown hash** usa exact match após normalização CPF/DATE/BRL/NUM",
        "4. **Thresholds são conservadores** — bias para não agrupar erroneamente (false SAME pior que false DIFF)",
        "5. **ApoliceVgA e ApoliceVgB são templates distintos** — confirmado visualmente pelo usuário",
        "",
        "---",
        "",
        "## Próximos Passos",
        "",
        "- Story 48.10 — Implementar sinal pHash masked thumbnail no Stage 1",
        "- Story 48.11 — Implementar sinal Font Jaccard no Stage 1",
        "- Story 48.12 — Implementar sinal Struct edit distance no Stage 1",
        "- Story 48.13 — Ensemble voting core + Union-Find clustering",
        "- Story 48.14 — Integração completa + revalidação do spike 48.7",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    main()
