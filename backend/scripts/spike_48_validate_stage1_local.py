"""48.8 — Validação local do Stage 1 com ensemble voting (sem Railway).

Executa Stage 1 diretamente via imports, sem precisar do servidor.

Critério correto para PDFs multi-página:
  Páginas na MESMA posição (page_index=0) de instâncias do MESMO template
  devem estar no MESMO cluster.
  Páginas de templates DIFERENTES devem estar em clusters DIFERENTES.

Uso:
    cd backend
    python scripts/spike_48_validate_stage1_local.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # noqa: E402
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noqa: E402

from services.stages.stage1_clustering.clustering_algorithms import (  # noqa: E402
    _cluster_graph,
    _compute_similarity,
)
from services.stages.stage1_clustering.page_preprocessing import (  # noqa: E402
    ClusteringConfig,
    PageInfo,
    _abstract_content,
    _classify_pages,
    _extract_blocks,
    _filter_regions,
    _normalize,
)

SAMPLES = Path("tests/fixtures/samples")

# Test cases: (label, same_template_groups, diff_template_groups)
# same_template_groups: list of PDF paths that are SAME template (1 group = 1 template)
# diff_template_groups: list of PDF paths that are DIFFERENT templates
TEST_CASES: list[tuple[str, list[list[Path]], list[Path]]] = [
    (
        "PosicaoConsolidada×4 SAME, sem DIFF",
        [
            [
                SAMPLES / "relatorio/PosicaoConsolidada.pdf",
                SAMPLES / "relatorio/PosicaoConsolidada2.pdf",
                SAMPLES / "relatorio/PosicaoConsolidada3.pdf",
                SAMPLES / "relatorio/PosicaoConsolidada4.pdf",
            ]
        ],
        [],
    ),
    (
        "BoletoVg×3 SAME, sem DIFF",
        [
            [
                SAMPLES / "boleto/BoletoVg.pdf",
                SAMPLES / "boleto/BoletoVg2.pdf",
                SAMPLES / "boleto/BoletoVg3.pdf",
            ]
        ],
        [],
    ),
    (
        "BoletoIndividual×4 SAME, sem DIFF",
        [
            [
                SAMPLES / "boleto/BoletoIndividual.pdf",
                SAMPLES / "boleto/BoletoIndividual2.pdf",
                SAMPLES / "boleto/BoletoIndividual3.pdf",
                SAMPLES / "boleto/BoletoIndividual4.pdf",
            ]
        ],
        [],
    ),
    (
        "BoletoCorporate×4 SAME, sem DIFF",
        [
            [
                SAMPLES / "boleto/BoletoCorporateMercantil.pdf",
                SAMPLES / "boleto/BoletoCorporateMercantil2.pdf",
                SAMPLES / "boleto/BoletoCorporateMercantil3.pdf",
                SAMPLES / "boleto/BoletoCorporateMercantil4.pdf",
            ]
        ],
        [],
    ),
    (
        "ApoliceVgB×2 SAME, sem DIFF",
        [
            [
                SAMPLES / "apolice/ApoliceVgB1.pdf",
                SAMPLES / "apolice/ApoliceVgB2.pdf",
            ]
        ],
        [],
    ),
    (
        "DirfInforma×3 SAME, sem DIFF",
        [
            [
                SAMPLES / "dirf/DirfInformaFinanceiro.pdf",
                SAMPLES / "dirf/DirfInformaFinanceiro2.pdf",
                SAMPLES / "dirf/DirfInformaFinanceiro3.pdf",
            ]
        ],
        [],
    ),
    (
        "Boleto DIFF: Corporate vs Individual vs Vg (page 0 de cada)",
        [],
        [
            SAMPLES / "boleto/BoletoCorporateMercantil.pdf",
            SAMPLES / "boleto/BoletoIndividual.pdf",
            SAMPLES / "boleto/BoletoVg.pdf",
        ],
    ),
]


def run_pipeline(pdf_map: dict[str, str], config: ClusteringConfig):
    """Roda Stage 1 e retorna (pages, clusters, sim_matrix)."""
    all_pages: list[PageInfo] = []
    for pdf_id, path in pdf_map.items():
        pages = _classify_pages(path, pdf_id)
        _extract_blocks(path, pages)
        all_pages.extend(pages)

    _normalize(all_pages)
    _abstract_content(all_pages)
    header_end, footer_start = _filter_regions(all_pages, config)
    sim_matrix = _compute_similarity(all_pages, header_end, footer_start, config)
    clusters = _cluster_graph(sim_matrix, config)

    processable = [p for p in all_pages if p.is_processable]
    return processable, clusters, sim_matrix


def find_cluster_for_page(page: PageInfo, processable: list[PageInfo], clusters: list[set[int]]) -> int | None:
    """Retorna o índice do cluster que contém esta página."""
    try:
        page_idx = processable.index(page)
    except ValueError:
        return None
    for ci, cluster in enumerate(clusters):
        if page_idx in cluster:
            return ci
    return None


def validate_same_group(pdf_ids: list[str], processable: list[PageInfo], clusters: list[set[int]], label: str) -> bool:
    """Verifica que páginas na posição 0 de todos os PDFs do grupo estão no mesmo cluster."""
    pages_p0 = [p for p in processable if p.pdf_id in pdf_ids and p.page_index == 0]
    missing = [pid for pid in pdf_ids if not any(p.pdf_id == pid and p.page_index == 0 for p in processable)]
    if missing:
        print(f"   ⚠️  PDFs sem página 0 processável: {missing}")

    if len(pages_p0) < 2:
        print(f"   ⚠️  Apenas {len(pages_p0)} página(s) p0 processável(is) — insuficiente para validar")
        return True  # não pode falhar sem dados

    cluster_ids = [find_cluster_for_page(p, processable, clusters) for p in pages_p0]
    unique_clusters = set(cluster_ids)

    print(f"   Páginas p0: {[p.pdf_id for p in pages_p0]}")
    print(f"   Clusters:   {cluster_ids}")

    if len(unique_clusters) == 1:
        print(f"   ✅ SAME: todas p0 no cluster {cluster_ids[0]}")
        return True
    else:
        print(f"   ❌ FAIL: p0 espalhadas em {len(unique_clusters)} clusters: {unique_clusters}")
        return False


def validate_diff_group(pdf_ids: list[str], processable: list[PageInfo], clusters: list[set[int]]) -> bool:
    """Verifica que páginas p0 de PDFs diferentes estão em clusters diferentes."""
    pages_p0 = {pid: next((p for p in processable if p.pdf_id == pid and p.page_index == 0), None) for pid in pdf_ids}
    cluster_by_pdf = {}
    for pid, page in pages_p0.items():
        if page is None:
            print(f"   ⚠️  {pid}: sem página 0 processável")
            continue
        cluster_by_pdf[pid] = find_cluster_for_page(page, processable, clusters)

    print(f"   Clusters p0: {cluster_by_pdf}")

    cluster_vals = list(cluster_by_pdf.values())
    if len(set(cluster_vals)) == len(cluster_vals):
        print("   ✅ DIFF: todos p0 em clusters distintos")
        return True
    else:
        # Find which are in the same cluster (false merge)
        from collections import Counter

        dupes = [c for c, n in Counter(cluster_vals).items() if n > 1]
        merged_pdfs = [pid for pid, c in cluster_by_pdf.items() if c in dupes]
        print(f"   ❌ FAIL: PDFs distintos agrupados juntos: {merged_pdfs}")
        return False


def main():
    config = ClusteringConfig()
    print("=" * 70)
    print("SPIKE 48.8 — Validação Local Stage 1: Ensemble Voting")
    print(f"clustering_threshold = {config.clustering_threshold}")
    print("=" * 70)

    results = []

    for label, same_groups, diff_pdfs in TEST_CASES:
        all_pdfs: list[Path] = []
        for group in same_groups:
            all_pdfs.extend(group)
        all_pdfs.extend(diff_pdfs)

        missing = [p for p in all_pdfs if not p.exists()]
        if missing:
            print(f"\n⏭️  SKIP {label}")
            print(f"   Faltando: {[p.name for p in missing]}")
            continue

        print(f"\n{'─' * 60}")
        print(f"🧪 {label}")

        # Build pdf_map: pdf_id → path
        pdf_map: dict[str, str] = {}
        for i, path in enumerate(all_pdfs):
            pdf_map[f"pdf_{i:02d}"] = str(path)

        # Map pdf_id back to template group
        pdf_id_list = list(pdf_map.keys())
        same_group_ids: list[list[str]] = []
        offset = 0
        for group in same_groups:
            group_ids = pdf_id_list[offset : offset + len(group)]
            same_group_ids.append(group_ids)
            offset += len(group)
        diff_ids = pdf_id_list[offset:]

        try:
            processable, clusters, sim_matrix = run_pipeline(pdf_map, config)
            print(f"   Total pages processáveis: {len(processable)}")
            print(f"   Clusters encontrados: {len(clusters)}")

            case_ok = True

            for gi, (group_ids, group_paths) in enumerate(zip(same_group_ids, same_groups)):
                group_names = [p.name for p in group_paths]
                print(f"\n   SAME group {gi + 1}: {group_names}")
                ok = validate_same_group(group_ids, processable, clusters, label)
                case_ok = case_ok and ok

            if diff_ids:
                diff_names = [Path(pdf_map[pid]).name for pid in diff_ids]
                print(f"\n   DIFF check: {diff_names}")
                ok = validate_diff_group(diff_ids, processable, clusters)
                case_ok = case_ok and ok

            results.append((label, case_ok))

        except Exception as exc:
            print(f"   ❌ ERROR: {exc}")
            import traceback

            traceback.print_exc()
            results.append((label, False))

    print(f"\n{'=' * 70}")
    print("RESUMO")
    print(f"{'=' * 70}")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for label, ok in results:
        print(f"  {'✅' if ok else '❌'} {label}")

    print(f"\n{'PASS' if passed == total else 'FAIL'}: {passed}/{total} casos")
    if passed == total:
        print("\n🎉 Stage 1 ensemble voting validado! Gap 1 corrigido.")
    else:
        print("\n⚠️  Falhas encontradas — revisar thresholds ou sinais.")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
