"""48.7 — Validação multi-sample: 3x PosicaoConsolidada via Railway API.

Testa Stage 1 clustering com 3 instâncias do mesmo template.
Usa refresh_token para renovar JWT automaticamente.

Uso:
    TOKEN=eyJ... REFRESH=4osmbijrxbsy python scripts/spike_48_validate_multisample.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://migrador-planet-production.up.railway.app"
SUPABASE_URL = "https://xrmlhuytgebovrgtzypl.supabase.co"

TOKEN = os.environ.get("TOKEN", "")
REFRESH_TOKEN = os.environ.get("REFRESH", "4osmbijrxbsy")

SAMPLES = Path("tests/fixtures/samples")
# Usar BoletoVg.xsd como placeholder (sem XSD de relatorio disponivel)
XSD_PATH = SAMPLES / "boleto/BoletoVg.xsd"
REPORT_DIR = Path("../docs/reports/epic-48")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

MULTI_SAMPLE_PDFS = [
    SAMPLES / "relatorio/PosicaoConsolidada.pdf",
    SAMPLES / "relatorio/PosicaoConsolidada2.pdf",
    SAMPLES / "relatorio/PosicaoConsolidada3.pdf",
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
        headers={"apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"},  # anon key placeholder
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


# ---------------------------------------------------------------------------
# API helpers (mesmos do pipeline_47_validate.py)
# ---------------------------------------------------------------------------


def upload(pdfs: list[Path], xsd_path: Path, name: str, token: str) -> str | None:
    existing = [p for p in pdfs if p.exists()]
    missing = [p.name for p in pdfs if not p.exists()]
    if missing:
        print(f"  ⚠️  Nao encontrados: {missing}")
    if not existing:
        print("  Nenhum PDF disponivel.")
        return None

    files = [("pdfs[]", (p.name, open(p, "rb"), "application/pdf")) for p in existing]
    files.append(("xsd", (xsd_path.name, open(xsd_path, "rb"), "application/xml")))
    data = {"template_name": name}

    print(f"  Uploading {len(existing)} PDFs... ", end="", flush=True)
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


def analyze(job_id: str, token: str) -> bool:
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
    if resp.status_code == 200:
        print(" [fallback]", end="", flush=True)
        return True
    return False


def poll_status(job_id: str, token: str, timeout: int = 600) -> dict | None:
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        resp = requests.get(
            f"{BASE_URL}/api/analyze/{job_id}/status",
            headers=get_headers(token),
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            if status == "completed":
                print(" completado")
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
        return resp.json()
    print(f"  Result ERRO {resp.status_code}")
    return None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def analyze_stage1(result: dict) -> dict:
    """Verifica Stage 1: quantos layouts foram detectados."""
    layouts = result.get("layout_types", [])
    return {
        "layout_count": len(layouts),
        "layouts": [{"id": l.get("id"), "page_count": l.get("page_count")} for l in layouts],
    }


def analyze_stage3(result: dict) -> dict:
    """Verifica Stage 3: nodes no document tree."""
    trees = result.get("document_trees", [])
    totals: dict[str, int] = {}
    for tree in trees:
        for node in _flatten_tree(tree):
            t = node.get("type", "unknown")
            totals[t] = totals.get(t, 0) + 1
    return {"node_types": totals, "tree_count": len(trees)}


def _flatten_tree(node: dict | list) -> list[dict]:
    if isinstance(node, list):
        out = []
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


def analyze_field_mappings(result: dict) -> dict:
    mappings = result.get("field_mappings", [])
    return {
        "total": len(mappings),
        "with_xsd_path": sum(1 for m in mappings if m.get("xsd_field_path")),
        "sample": [{"field": m.get("field_name", "?"), "xsd": m.get("xsd_field_path", "?")} for m in mappings[:5]],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not TOKEN:
        print("ERRO: TOKEN nao definido. Passe via TOKEN=eyJ... python ...")
        sys.exit(1)

    token = TOKEN

    print("=" * 65)
    print("SPIKE 48.7 — Multi-Sample: 3x PosicaoConsolidada")
    print("=" * 65)
    print(f"\nPDFs: {[p.name for p in MULTI_SAMPLE_PDFS]}")

    # Upload
    print("\n[1/4] Upload...")
    job_id = upload(MULTI_SAMPLE_PDFS, XSD_PATH, "posicao-consolidada-multisample", token)
    if not job_id:
        print("ABORTADO: upload falhou.")
        sys.exit(1)

    # Analyze
    print("\n[2/4] Iniciar pipeline...")
    if not analyze(job_id, token):
        sys.exit(1)

    # Poll
    print("\n[3/4] Aguardando pipeline", end="", flush=True)
    status_data = poll_status(job_id, token, timeout=600)
    if not status_data or status_data.get("status") != "completed":
        print(f"\nPipeline nao completou: {status_data}")
        sys.exit(1)

    # Result
    print("\n[4/4] Obtendo resultado...")
    result = get_result(job_id, token)
    if not result:
        sys.exit(1)

    # Analyze stages
    print("\n" + "=" * 65)
    print("RESULTADOS")
    print("=" * 65)

    stage1 = analyze_stage1(result)
    print("\nStage 1 — Clustering:")
    print(f"  Layouts detectados: {stage1['layout_count']}")
    for l in stage1["layouts"]:
        print(f"  Layout {l['id']}: {l.get('page_count', '?')} paginas")

    stage3 = analyze_stage3(result)
    print("\nStage 3 — Document Tree:")
    print(f"  Trees: {stage3['tree_count']}")
    for ntype, count in sorted(stage3["node_types"].items(), key=lambda x: -x[1])[:10]:
        print(f"  {ntype}: {count}")

    fm = analyze_field_mappings(result)
    print("\nStage 4 — Field Mappings:")
    print(f"  Total: {fm['total']} | Com XSD path: {fm['with_xsd_path']}")

    print(f"\nScore: {result.get('confidence_score', '?')}")

    # Veredicto Stage 1
    print("\n" + "=" * 65)
    print("VEREDICTO Stage 1")
    print("=" * 65)
    n_layouts = stage1["layout_count"]
    n_pdfs = len([p for p in MULTI_SAMPLE_PDFS if p.exists()])
    if n_layouts < n_pdfs:
        print(f"  PASS: {n_layouts} layout(s) para {n_pdfs} PDFs")
        print("  Stage 1 agrupou corretamente — nao criou 1 cluster por PDF")
    elif n_layouts == n_pdfs:
        print(f"  FAIL: {n_layouts} layouts = {n_pdfs} PDFs — clustering nao agrupou")
    else:
        print(f"  ATENCAO: {n_layouts} layouts para {n_pdfs} PDFs — inesperado")

    # Salvar
    report = {
        "run_date": time.strftime("%Y-%m-%d %H:%M"),
        "job_id": job_id,
        "pdfs": [p.name for p in MULTI_SAMPLE_PDFS],
        "stage1": stage1,
        "stage3": stage3,
        "field_mappings": fm,
        "confidence_score": result.get("confidence_score"),
        "full_result": result,
    }
    out_path = REPORT_DIR / "multisample-posicao-result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nRelatorio salvo: {out_path}")


if __name__ == "__main__":
    main()
