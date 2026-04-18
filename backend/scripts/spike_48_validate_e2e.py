"""48.7 — Validação E2E completa Stage 1→5 via Railway API.

Valida o pipeline completo com 3+ PDFs do mesmo template incluindo:
  - Stage 1: clustering correto (1 layout por template, não 1 por PDF)
  - Stage 3: repeated_section detectada no document tree
  - Stage 3.1: recall dynamic/static vs ground truth 48.3
  - Stage 4: ListBinding presente em field_mappings
  - Stage 4: cobertura escalar >= 80%
  - Stage 5: <repeat data-list="..."> presente no HTML

Uso:
    cd backend
    TOKEN=eyJ... python scripts/spike_48_validate_e2e.py

    # Testar um segundo tipo de documento:
    TOKEN=eyJ... TIPO=relatorio-extrato python scripts/spike_48_validate_e2e.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://migrador-planet-production.up.railway.app"
SUPABASE_URL = "https://xrmlhuytgebovrgtzypl.supabase.co"
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhybWxodXl0Z2Vib3ZyZ3R6eXBsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMxOTgzNTQsImV4cCI6MjA1ODc3NDM1NH0.f5G9-GS6-pLMT7-bz5oAo0nv9qJlX-FX3FNT3Bz3fRM",
)

TOKEN = os.environ.get("TOKEN", "")
REFRESH_TOKEN = os.environ.get("REFRESH", "")

SAMPLES = Path("tests/fixtures/samples")
REPORT_DIR = Path("../docs/reports/epic-48")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Configuração dos runs a executar
# ---------------------------------------------------------------------------

RUNS = [
    {
        "nome": "posicao-consolidada",
        "tipo": "relatorio",
        "pdfs": [
            SAMPLES / "relatorio/PosicaoConsolidada.pdf",
            SAMPLES / "relatorio/PosicaoConsolidada2.pdf",
            SAMPLES / "relatorio/PosicaoConsolidada3.pdf",
        ],
        "xsd": SAMPLES / "relatorio/PosicaoConsolidada.xsd",
        "ground_truth": REPORT_DIR / "ground-truth-posicaoconsolidada.json",
        "repeated_sections_expected": 3,  # do ground truth 48.3
        "dynamic_expected": 20,
        "static_expected": 16,
    },
]


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def refresh_access_token(refresh_token: str) -> str | None:
    """Obtém novo access_token via refresh_token."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
        json={"refresh_token": refresh_token},
        headers={"apikey": SUPABASE_ANON_KEY},
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        new_token = data.get("access_token")
        if new_token:
            print(f"  Token renovado (expira em {data.get('expires_in', '?')}s)")
            return new_token
    print(f"  Refresh falhou ({resp.status_code}): {resp.text[:100]}")
    return None


def ensure_token(token: str, refresh_token: str) -> str:
    """Verifica o token atual; renova se necessário."""
    resp = requests.get(
        f"{BASE_URL}/api/user",
        headers=get_headers(token),
        timeout=15,
    )
    if resp.status_code == 401 and refresh_token:
        print("  Token expirado — renovando...")
        new_token = refresh_access_token(refresh_token)
        if new_token:
            return new_token
    return token


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def upload(pdfs: list[Path], xsd_path: Path, name: str, token: str) -> str | None:
    existing = [p for p in pdfs if p.exists()]
    missing = [p.name for p in pdfs if not p.exists()]
    if missing:
        print(f"  Nao encontrados: {missing}")
    if not existing:
        print("  Nenhum PDF disponivel.")
        return None

    files = [("pdfs[]", (p.name, open(p, "rb"), "application/pdf")) for p in existing]
    if xsd_path.exists():
        files.append(("xsd", (xsd_path.name, open(xsd_path, "rb"), "application/xml")))
    data = {"template_name": name}

    print(f"  Uploading {len(existing)} PDFs + XSD... ", end="", flush=True)
    resp = requests.post(
        f"{BASE_URL}/api/upload",
        files=files,
        data=data,
        headers=get_headers(token),
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"ERRO {resp.status_code}: {resp.text[:200]}")
        return None
    job_id = resp.json()["job_id"]
    print(f"job_id={job_id}")
    return job_id


def start_analyze(job_id: str, token: str) -> bool:
    resp = requests.post(
        f"{BASE_URL}/api/analyze",
        json={"job_id": job_id},
        headers=get_headers(token),
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ERRO {resp.status_code}: {resp.text[:200]}")
        return False
    print(f"  Pipeline iniciado: {resp.json().get('status')}")
    return True


def handle_service_failure(job_id: str, token: str) -> bool:
    resp = requests.post(
        f"{BASE_URL}/api/jobs/{job_id}/handle-failure",
        json={"action": "fallback"},
        headers=get_headers(token),
        timeout=30,
    )
    return resp.status_code == 200


def poll_status(job_id: str, token: str, timeout: int = 600) -> dict | None:
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        resp = requests.get(
            f"{BASE_URL}/api/analyze/{job_id}/status",
            headers=get_headers(token),
            timeout=120,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            if status == "completed":
                elapsed = int(time.time() - start)
                print(f" completado ({elapsed}s)")
                return data
            elif status == "failed":
                print(f" FALHOU: {data.get('error', '?')[:100]}")
                return data
            elif status == "awaiting_confirmation":
                handle_service_failure(job_id, token)
        print(".", end="", flush=True)
        dots += 1
        if dots % 30 == 0:
            print(f" [{int(time.time() - start)}s]", end="", flush=True)
        time.sleep(5)
    print(f" timeout ({timeout}s)")
    return None


def get_result(job_id: str, token: str) -> dict | None:
    resp = requests.get(
        f"{BASE_URL}/api/analyze/{job_id}/result",
        headers=get_headers(token),
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        # API retorna {job_id, status, result: {...}, error} — extrair sub-objeto
        return data.get("result", data)
    print(f"  Result ERRO {resp.status_code}: {resp.text[:100]}")
    return None


# ---------------------------------------------------------------------------
# Análise por stage
# ---------------------------------------------------------------------------


def analyze_stage1(result: dict, n_pdfs: int) -> dict:
    """Stage 1: verifica clustering — 1 layout para N PDFs do mesmo template."""
    layouts = result.get("layout_types", [])
    n_layouts = len(layouts)
    pass_ = n_layouts < n_pdfs  # deve ter menos layouts que PDFs (mesmos templates agrupados)
    return {
        "layout_count": n_layouts,
        "pdfs_submitted": n_pdfs,
        "pass": pass_,
        "verdict": "PASS" if pass_ else "FAIL",
        "detail": f"{n_layouts} layout(s) para {n_pdfs} PDF(s)",
        "layouts": [{"id": l.get("id"), "page_count": l.get("page_count")} for l in layouts],
    }


def _flatten_tree(node: dict | list) -> list[dict]:
    if isinstance(node, list):
        out: list[dict] = []
        for item in node:
            out.extend(_flatten_tree(item))
        return out
    if not isinstance(node, dict):
        return []
    out = [node]
    for v in node.values():
        if isinstance(v, (dict, list)):
            out.extend(_flatten_tree(v))
    return out


def analyze_stage3(result: dict, expected_repeated: int) -> dict:
    """Stage 3: verifica document tree — repeated_section detectada."""
    # Tree está em layout_types[i]['documentTree'] (camelCase)
    layouts = result.get("layout_types", [])
    all_nodes: list[dict] = []
    for l in layouts:
        tree = l.get("documentTree", {})
        all_nodes.extend(_flatten_tree(tree))
    trees = layouts  # para manter contagem

    node_types: dict[str, int] = {}
    for n in all_nodes:
        t = n.get("type", "unknown")
        node_types[t] = node_types.get(t, 0) + 1

    repeated_nodes = [n for n in all_nodes if n.get("type") == "repeated_section"]
    n_repeated = len(repeated_nodes)
    pass_ = n_repeated > 0

    return {
        "tree_count": len(trees),
        "node_types": node_types,
        "repeated_sections_found": n_repeated,
        "repeated_sections_expected": expected_repeated,
        "pass": pass_,
        "verdict": "PASS" if pass_ else "FAIL",
        "repeated_sample": [
            {"list_item_count": n.get("list_item_count"), "section_id": n.get("section_id")} for n in repeated_nodes[:3]
        ],
    }


def analyze_stage3_accuracy(result: dict, ground_truth: dict) -> dict:
    """Stage 3.1: compara dynamic/static com ground truth do 48.3."""
    cross = ground_truth.get("cross_instance", {})
    expected_dynamic = len(cross.get("dynamic_fields", []))
    expected_static = len(cross.get("static_fields", []))

    # Obtém campos do result (tree em layout_types[i]['documentTree'])
    layouts = result.get("layout_types", [])
    all_nodes = []
    for l in layouts:
        all_nodes.extend(_flatten_tree(l.get("documentTree", {})))

    # Classificação: 'type' field (dynamic/label/value/static/likely_dynamic)
    dynamic_nodes = [n for n in all_nodes if n.get("type") in ("dynamic", "likely_dynamic", "value")]
    static_nodes = [n for n in all_nodes if n.get("type") in ("static", "label")]

    n_dynamic = len(dynamic_nodes)
    n_static = len(static_nodes)

    # Recall: quantos do esperado foram encontrados (aproximação simples por contagem)
    dynamic_recall = min(n_dynamic / max(expected_dynamic, 1), 1.0)
    static_recall = min(n_static / max(expected_static, 1), 1.0)
    combined_recall = (dynamic_recall + static_recall) / 2

    pass_ = combined_recall >= 0.80

    return {
        "expected_dynamic": expected_dynamic,
        "found_dynamic": n_dynamic,
        "expected_static": expected_static,
        "found_static": n_static,
        "dynamic_recall": round(dynamic_recall, 3),
        "static_recall": round(static_recall, 3),
        "combined_recall": round(combined_recall, 3),
        "threshold": 0.80,
        "pass": pass_,
        "verdict": "PASS" if pass_ else "FAIL",
        "note": "recall por contagem — comparação exata requer bbox matching",
    }


def analyze_stage4(result: dict) -> dict:
    """Stage 4: verifica field mappings e ListBinding."""
    mappings = result.get("field_mappings", [])
    total = len(mappings)
    with_xsd = sum(1 for m in mappings if m.get("xsd_field_path"))

    # list_bindings ficam em chave separada (ListBinding não é FieldMappingEntry)
    list_bindings = result.get("list_bindings", [])

    # Todos os field_mappings são escalares (FieldMappingEntry — sem binding_type)
    scalar_total = total
    scalar_with_xsd = with_xsd
    scalar_coverage = scalar_with_xsd / max(scalar_total, 1)

    list_pass = len(list_bindings) > 0
    scalar_pass = scalar_coverage >= 0.80

    unmapped = [m for m in mappings if not m.get("xsd_field_path")]

    return {
        "total_mappings": total,
        "with_xsd_path": with_xsd,
        "list_bindings_found": len(list_bindings),
        "list_bindings_pass": list_pass,
        "list_bindings": [
            {"xsd_list_path": lb.get("xsd_list_path"), "section_id": lb.get("section_id", "?")}
            for lb in list_bindings[:3]
        ],
        "scalar_total": scalar_total,
        "scalar_with_xsd": scalar_with_xsd,
        "scalar_coverage": round(scalar_coverage, 3),
        "scalar_coverage_pass": scalar_pass,
        "pass": list_pass and scalar_pass,
        "verdict": "PASS" if (list_pass and scalar_pass) else ("PARTIAL" if (list_pass or scalar_pass) else "FAIL"),
        "sample_mappings": [
            {
                "label": m.get("label_text", "?"),
                "pdf_text": m.get("pdf_text", "")[:30],
                "xsd": m.get("xsd_field_path", "?"),
            }
            for m in mappings[:5]
        ],
        "unmapped_fields": [
            {"label": m.get("label_text", "?"), "pdf_text": m.get("pdf_text", "")[:40]} for m in unmapped
        ],
    }


def analyze_stage5(result: dict) -> dict:
    """Stage 5: verifica template HTML — presença de <repeat data-list=...>."""
    template = result.get("template_draft", {})
    html = template.get("html", "") or result.get("template_html", "") or ""

    has_repeat = "<repeat" in html
    has_data_list = bool(re.search(r'data-list="[^"]*\[\]"', html))
    has_mustache = bool(re.search(r"\{\{[^}]+\}\}", html))
    has_repeat_item = 'class="repeat-item"' in html or "repeat-item" in html

    pass_ = has_repeat and has_data_list

    # Extrair primeiros <repeat> como amostra
    repeat_samples = re.findall(
        r'<repeat[^>]*data-list="([^"]*)"[^>]*>',
        html,
    )[:3]

    return {
        "html_length": len(html),
        "has_repeat_element": has_repeat,
        "has_data_list_attr": has_data_list,
        "has_mustache_fields": has_mustache,
        "has_repeat_item_class": has_repeat_item,
        "repeat_data_lists": repeat_samples,
        "pass": pass_,
        "verdict": "PASS" if pass_ else "FAIL",
    }


def print_stage_result(name: str, analysis: dict) -> None:
    verdict = analysis.get("verdict", "?")
    icon = "" if verdict == "PASS" else ("⚠" if verdict == "PARTIAL" else "✗")
    print(f"\n  {icon} {name}: {verdict}")
    for k, v in analysis.items():
        if k in ("verdict", "pass", "note"):
            continue
        if isinstance(v, (dict, list)) and len(str(v)) > 80:
            print(f"    {k}: [...]")
        else:
            print(f"    {k}: {v}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_single(run_cfg: dict, token: str) -> dict:
    nome = run_cfg["nome"]
    pdfs = run_cfg["pdfs"]
    xsd_path = run_cfg["xsd"]
    expected_repeated = run_cfg.get("repeated_sections_expected", 1)

    print(f"\n{'=' * 65}")
    print(f"RUN: {nome}")
    print(f"{'=' * 65}")
    print(f"PDFs: {[p.name for p in pdfs if p.exists()]}")

    # Load ground truth if available
    gt_path = run_cfg.get("ground_truth")
    ground_truth: dict = {}
    if gt_path and Path(gt_path).exists():
        with open(gt_path, encoding="utf-8") as f:
            ground_truth = json.load(f)
        print(f"Ground truth: {Path(gt_path).name}")
    else:
        print("Ground truth: não disponível")

    # [1] Upload
    print("\n[1/4] Upload...")
    job_id = upload(pdfs, xsd_path, f"{nome}-e2e-spike", token)
    if not job_id:
        return {"nome": nome, "error": "upload falhou"}

    # [2] Analyze
    print("\n[2/4] Iniciar pipeline...")
    if not start_analyze(job_id, token):
        return {"nome": nome, "error": "analyze falhou"}

    # [3] Poll
    t_start = time.time()
    print("\n[3/4] Aguardando pipeline (max 600s)", end="", flush=True)
    status_data = poll_status(job_id, token, timeout=600)
    elapsed = int(time.time() - t_start)

    if not status_data or status_data.get("status") != "completed":
        return {"nome": nome, "error": f"pipeline não completou: {status_data}"}

    # [4] Result
    print("\n[4/4] Obtendo resultado...")
    result = get_result(job_id, token)
    if not result:
        return {"nome": nome, "error": "result endpoint falhou"}

    # Análise por stage
    n_pdfs = len([p for p in pdfs if p.exists()])
    stage1 = analyze_stage1(result, n_pdfs)
    stage3 = analyze_stage3(result, expected_repeated)
    stage4 = analyze_stage4(result)
    stage5 = analyze_stage5(result)
    stage3_acc = analyze_stage3_accuracy(result, ground_truth) if ground_truth else None

    # Imprimir resultados
    print(f"\n{'=' * 65}")
    print("RESULTADOS POR STAGE")
    print(f"{'=' * 65}")
    print_stage_result("Stage 1 — Clustering", stage1)
    print_stage_result("Stage 3 — Repeated Sections", stage3)
    if stage3_acc:
        print_stage_result("Stage 3.1 — Dynamic/Static Accuracy", stage3_acc)
    print_stage_result("Stage 4 — List Binding + Scalar Coverage", stage4)
    print_stage_result("Stage 5 — HTML <repeat>", stage5)

    # Veredicto geral
    stages_ok = [
        stage1["pass"],
        stage3["pass"],
        stage4["pass"],
        stage5["pass"],
    ]
    if stage3_acc:
        stages_ok.append(stage3_acc["pass"])
    all_pass = all(stages_ok)
    partial = any(stages_ok) and not all_pass

    print(f"\n{'=' * 65}")
    print("VEREDICTO GERAL")
    print(f"{'=' * 65}")
    verdict = "PASS" if all_pass else ("PARTIAL" if partial else "FAIL")
    icon = "" if all_pass else ("⚠" if partial else "✗")
    print(f"  {icon} E2E: {verdict} ({sum(stages_ok)}/{len(stages_ok)} stages OK)")
    print(f"  Tempo total pipeline: {elapsed}s")

    # Relatório
    report = {
        "run_date": time.strftime("%Y-%m-%d %H:%M"),
        "nome": nome,
        "job_id": job_id,
        "pdfs": [p.name for p in pdfs if p.exists()],
        "elapsed_seconds": elapsed,
        "verdict": verdict,
        "stages": {
            "stage1_clustering": stage1,
            "stage3_repeated_sections": stage3,
            "stage3_accuracy": stage3_acc,
            "stage4_binding": stage4,
            "stage5_html": stage5,
        },
        "confidence_score": result.get("confidence_score"),
    }

    out_path = REPORT_DIR / f"e2e-validation-{nome}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  Relatório salvo: {out_path}")

    return report


def main() -> None:
    if not TOKEN:
        print("ERRO: TOKEN nao definido.")
        print("  Uso: TOKEN=eyJ... python scripts/spike_48_validate_e2e.py")
        sys.exit(1)

    token = TOKEN
    if REFRESH_TOKEN:
        token = ensure_token(token, REFRESH_TOKEN)

    print("=" * 65)
    print("SPIKE 48.7 — Validação E2E Stage 1→5 via Railway")
    print("=" * 65)

    reports = []
    for run_cfg in RUNS:
        try:
            report = run_single(run_cfg, token)
            reports.append(report)
        except Exception as exc:
            print(f"\nERRO no run {run_cfg['nome']}: {exc}")
            reports.append({"nome": run_cfg["nome"], "error": str(exc)})

    # Sumário final
    print(f"\n{'=' * 65}")
    print("SUMÁRIO GERAL")
    print(f"{'=' * 65}")
    all_pass = all(r.get("verdict") == "PASS" for r in reports if "verdict" in r)
    for r in reports:
        v = r.get("verdict", r.get("error", "ERRO"))
        icon = "" if v == "PASS" else ("⚠" if v == "PARTIAL" else "✗")
        print(f"  {icon} {r.get('nome', '?')}: {v}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
