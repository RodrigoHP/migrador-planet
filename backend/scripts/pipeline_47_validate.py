"""
Epic 47 — Validação Pilar A: upload + analyze via Railway API.

Uso:
    TOKEN=eyJ... python scripts/pipeline_47_validate.py

Requer: requests (pip install requests)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_URL = "https://migrador-planet-production.up.railway.app"
TOKEN = os.environ.get("TOKEN", "")
if not TOKEN:
    print("ERRO: passe o token via TOKEN=... python pipeline_47_validate.py")
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}"}
SAMPLES = Path("tests/fixtures/samples")
XSD_PATH = Path("D:/Downloads/Corporate.BoletoConvenio.xsd")
REPORT_DIR = Path("../docs/reports/epic-47")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Grupos de PDFs — mesmo tipo juntos para clustering correto
GROUPS = [
    {
        "name": "relatorio-posicao",
        "story": "47.1",
        "pdfs": [
            SAMPLES / "relatorio/PosicaoConsolidada.pdf",
            SAMPLES / "relatorio/RelatorioPosicaoConsolidada.pdf",
            SAMPLES / "relatorio/RelatorioBeneficiario.pdf",
        ],
    },
    {
        "name": "relatorio-extrato",
        "story": "47.1",
        "pdfs": [
            SAMPLES / "relatorio/PrevidenciaExtrato.pdf",
            SAMPLES / "apolice/ApoliceVg.pdf",
        ],
    },
    {
        "name": "boleto",
        "story": "47.2",
        "pdfs": [
            SAMPLES / "boleto/BoletoCorporateMercantil.pdf",
            SAMPLES / "boleto/BoletoVg.pdf",
            SAMPLES / "boleto/BoletoIndividual_05220_unlocked.pdf",
        ],
    },
    {
        "name": "dirf",
        "story": "47.3",
        "pdfs": [
            SAMPLES / "dirf/DirfInformaFinanceiro.pdf",
        ],
    },
    {
        "name": "certificado",
        "story": "47.5",
        "pdfs": [
            SAMPLES / "certificado/CertificadoPrevidencia.pdf",
            SAMPLES / "certificado/CertificadoVI.pdf",
            SAMPLES / "certificado/CertificadoPrevcom.pdf",
        ],
    },
    {
        "name": "certificado-fontes",
        "story": "47.5",
        "pdfs": [
            SAMPLES / "certificado/CertificadoHinode.pdf",
            SAMPLES / "certificado/CertiticadoPrevidencia.pdf",
        ],
    },
]


def upload(group: dict) -> str | None:
    """Faz upload dos PDFs + XSD e retorna job_id."""
    pdfs = [p for p in group["pdfs"] if p.exists()]
    missing = [p.name for p in group["pdfs"] if not p.exists()]
    if missing:
        print(f"  ⚠️  Arquivos não encontrados: {missing}")
    if not pdfs:
        print("  ❌ Nenhum PDF disponível, pulando grupo.")
        return None

    files = [("pdfs[]", (p.name, open(p, "rb"), "application/pdf")) for p in pdfs]
    files.append(("xsd", ("schema.xsd", open(XSD_PATH, "rb"), "application/xml")))
    data = {"template_name": group["name"]}

    print(f"  Uploading {len(pdfs)} PDFs... ", end="", flush=True)
    resp = requests.post(f"{BASE_URL}/api/upload", files=files, data=data, headers=HEADERS, timeout=120)
    if resp.status_code != 200:
        print(f"ERRO {resp.status_code}: {resp.text[:200]}")
        return None
    job_id = resp.json()["job_id"]
    print(f"job_id={job_id}")
    return job_id


def analyze(job_id: str) -> bool:
    """Dispara o pipeline para o job_id."""
    resp = requests.post(
        f"{BASE_URL}/api/analyze",
        json={"job_id": job_id},
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ❌ Analyze ERRO {resp.status_code}: {resp.text[:200]}")
        return False
    print(f"  Pipeline iniciado: {resp.json().get('status')}")
    return True


def handle_service_failure(job_id: str) -> bool:
    """Desbloqueia pipeline em awaiting_confirmation com ação fallback."""
    resp = requests.post(
        f"{BASE_URL}/api/jobs/{job_id}/handle-failure",
        json={"action": "fallback"},
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code == 200:
        print(" [fallback→continuando]", end="", flush=True)
        return True
    # 409 = já não está mais em awaiting_confirmation (resolveu sozinho)
    return False


def poll_status(job_id: str, timeout: int = 600) -> dict | None:
    """Polling até pipeline completar ou timeout.

    Trata awaiting_confirmation automaticamente com fallback.
    """
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        resp = requests.get(
            f"{BASE_URL}/api/analyze/{job_id}/status",
            headers=HEADERS,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            if status == "completed":
                print(" ✅ concluído")
                return data
            elif status == "failed":
                print(f" ❌ falhou: {data.get('error', '?')[:100]}")
                return data
            elif status == "awaiting_confirmation":
                print(" [serviço falhou]", end="", flush=True)
                handle_service_failure(job_id)
        print(".", end="", flush=True)
        dots += 1
        if dots % 30 == 0:
            elapsed = int(time.time() - start)
            print(f" [{elapsed}s]", end="", flush=True)
        time.sleep(5)
    print(f" ⏱️  timeout ({timeout}s)")
    return None


def summarize_result(result: dict) -> dict:
    """Extrai métricas relevantes do resultado do pipeline."""
    if not result or result.get("status") == "failed":
        return {"status": "failed", "error": result.get("error", "unknown") if result else "timeout"}

    data = result.get("result") or result
    layout_types = data.get("layout_types", [])
    summary = {
        "status": "completed",
        "layout_count": len(layout_types),
        "layouts": [],
        "total_field_mappings": 0,
    }
    for lt in layout_types:
        tree_root = (lt.get("documentTree") or {}).get("root")
        node_counts: dict = {}

        def walk(node):
            if not node:
                return
            t = node.get("type", "?")
            node_counts[t] = node_counts.get(t, 0) + 1
            for child in node.get("children", []):
                walk(child)

        if tree_root:
            walk(tree_root)
        mappings = lt.get("fieldMappings") or lt.get("field_mappings") or []
        mapped = len(mappings)
        summary["total_field_mappings"] += mapped
        conf = lt.get("confidence", {})
        overall = conf.get("overall", 0) if isinstance(conf, dict) else 0
        summary["layouts"].append(
            {
                "id": lt.get("id", "?"),
                "pages": lt.get("page_count", 0),
                "confidence_overall": overall,
                "field_mappings": mapped,
                "node_counts": node_counts,
            }
        )
    return summary


# ─── Main ─────────────────────────────────────────────────────────────────────

print("=" * 70)
print("EPIC 47 — Validação Pilar A — Pipeline Railway")
print(f"Backend: {BASE_URL}")
print("=" * 70)

all_results = []

for group in GROUPS:
    print(f"\n{'─' * 60}")
    print(f"[{group['story']}] {group['name'].upper()}")

    job_id = upload(group)
    if not job_id:
        all_results.append({"group": group["name"], "story": group["story"], "status": "upload_failed"})
        continue

    if not analyze(job_id):
        all_results.append(
            {"group": group["name"], "story": group["story"], "job_id": job_id, "status": "analyze_failed"}
        )
        continue

    print("  Aguardando pipeline", end="", flush=True)
    raw_result = poll_status(job_id)

    summary = summarize_result(raw_result)
    summary["group"] = group["name"]
    summary["story"] = group["story"]
    summary["job_id"] = job_id
    all_results.append(summary)

    if summary["status"] == "completed":
        for lt in summary["layouts"]:
            print(
                f"  Layout {lt['id']}: conf={lt['confidence_overall']} | mappings={lt['field_mappings']} | nodes={lt['node_counts']}"
            )

    # Salvar resultado bruto por grupo
    if raw_result:
        raw_path = REPORT_DIR / f"pipeline-{group['name']}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_result, f, ensure_ascii=False, indent=2, default=str)

# ─── Relatório final ──────────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("SUMÁRIO FINAL")
print(f"{'─' * 70}")

for r in all_results:
    status_icon = "✅" if r["status"] == "completed" else "❌"
    layouts = r.get("layout_count", 0)
    mappings = r.get("total_field_mappings", 0)
    print(f"  {status_icon} [{r['story']}] {r['group']:25s} layouts={layouts} mappings={mappings}")

report_path = REPORT_DIR / "pipeline-results-summary.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

print(f"\nRelatórios salvos em: {REPORT_DIR}")
