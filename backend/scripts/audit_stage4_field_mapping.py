#!/usr/bin/env python3
"""Audit do Stage 4 — Field Mapping (Pilar B)

Roda o pipeline completo (Stages 1-4) no BoletoVg.pdf + BoletoVg.xsd
e reporta o que foi mapeado, o que não foi, e onde está errando.

Usage:
    cd backend
    python scripts/audit_stage4_field_mapping.py

    # Com Gemini (precisa OPENROUTER_API_KEY):
    OPENROUTER_API_KEY=sk-... python scripts/audit_stage4_field_mapping.py

    # Sem LLM (só fuzzy fallback):
    python scripts/audit_stage4_field_mapping.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Força UTF-8 no stdout (Windows console)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Adiciona backend/ ao path
BACKEND_DIR = Path(__file__).parent.parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Carrega .env — mesmo padrão do main.py
from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")  # raiz — primário
load_dotenv(BACKEND_DIR / ".env", override=False)  # backend/ — secundário

PDF_PATH = BACKEND_DIR / "tests/fixtures/samples/boleto/BoletoVg.pdf"
XSD_PATH = BACKEND_DIR / "tests/fixtures/samples/boleto/BoletoVg.xsd"


# ---------------------------------------------------------------------------
# Mocks mínimos para rodar fora do contexto HTTP
# ---------------------------------------------------------------------------


class _NoopStorage:
    """Storage que não faz nada — só para o pipeline não quebrar."""

    async def upload_file(self, *a, **kw):
        return "local://noop"

    async def get_file(self, *a, **kw):
        return None

    async def save_job_result(self, *a, **kw):
        pass

    async def update_job_status(self, *a, **kw):
        pass


async def _noop_emit(event: dict) -> None:
    """Silencia os eventos SSE durante o audit."""
    pass


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def _print_separator(title: str = "") -> None:
    line = "─" * 70
    if title:
        print(f"\n{line}")
        print(f"  {title}")
        print(line)
    else:
        print(line)


def _print_mapping_report(result: dict) -> None:
    field_mappings = result.get("field_mappings", [])
    validation = result.get("validation_result") or {}
    confidence_scores = result.get("confidence_scores", {})

    if not field_mappings:
        print("\n⚠️  Nenhum field_mapping retornado pelo pipeline.")
        print("   Verifique se o Stage 3 detectou campos dynamic nos PDFs.")
        return

    mapped = [m for m in field_mappings if m.get("xsd_field_path")]
    unmapped = [m for m in field_mappings if not m.get("xsd_field_path")]
    ambiguous = [m for m in field_mappings if m.get("is_ambiguous")]

    _print_separator("RESUMO")
    total = len(field_mappings)
    print(f"  Total de campos dynamic detectados : {total}")
    print(f"  Mapeados para XSD                  : {len(mapped)} ({100 * len(mapped) // total if total else 0}%)")
    print(f"  Não mapeados (unmapped)             : {len(unmapped)} ({100 * len(unmapped) // total if total else 0}%)")
    print(f"  Ambíguos                            : {len(ambiguous)}")

    # Confidence scores por layout
    if confidence_scores:
        _print_separator("CONFIDENCE SCORES POR LAYOUT")
        for layout_id, score in confidence_scores.items():
            if isinstance(score, dict):
                overall = score.get("overall", score.get("score", "?"))
                factors = score.get("factors", {})
                print(f"\n  Layout: {layout_id}")
                print(f"    Overall  : {overall}")
                if factors:
                    for k, v in factors.items():
                        print(f"    {k:<22}: {v}")
            else:
                print(f"  {layout_id}: {score}")

    # Mapeamentos bem-sucedidos
    _print_separator("CAMPOS MAPEADOS")
    for m in sorted(mapped, key=lambda x: x.get("confidence", 0), reverse=True):
        label = m.get("label_text", "").strip()
        value = m.get("pdf_text", "").strip()
        path = m.get("xsd_field_path", "")
        conf = m.get("confidence", 0)
        fmt = m.get("detected_format", "")
        ambig = " ⚠️ ambíguo" if m.get("is_ambiguous") else ""
        fmt_str = f" [{fmt}]" if fmt else ""
        print(f"  {conf:.2f}  {label or '(sem label)':<28} → {path}{fmt_str}{ambig}")
        if value and value != label:
            print(f"         value: {value[:60]}")

    # Campos não mapeados
    if unmapped:
        _print_separator("CAMPOS NÃO MAPEADOS (orphans)")
        for m in unmapped:
            label = m.get("label_text", "").strip()
            value = m.get("pdf_text", "").strip()
            fmt = m.get("detected_format", "")
            fmt_str = f" [{fmt}]" if fmt else ""
            print(f"  ✗  {label or '(sem label)':<28}  value: {value[:50]}{fmt_str}")

    # Orphans do ValidationResult
    orphans = validation.get("orphans", [])
    if orphans:
        _print_separator("ORPHANS (ValidationResult)")
        for o in orphans:
            print(f"  - {o}")

    # Erros e warnings
    errors = validation.get("errors", [])
    warnings_v = validation.get("warnings", [])
    if errors or warnings_v:
        _print_separator("VALIDAÇÃO")
        for e in errors:
            print(f"  ERROR: {e}")
        for w in warnings_v:
            print(f"  WARN : {w}")

    # Campo XSD obrigatórios sem mapeamento
    unmapped_required = validation.get("unmapped_required", [])
    if unmapped_required:
        _print_separator("XSD REQUIRED SEM MAPEAMENTO")
        for r in unmapped_required:
            print(f"  ✗ {r}")


def _print_flat_paths(result: dict) -> None:
    """Mostra todos os paths do XSD para referência."""
    field_tree = result.get("field_tree") or {}
    flat = field_tree.get("flat_paths", [])
    if flat:
        _print_separator(f"XSD FLAT PATHS ({len(flat)} campos)")
        for p in flat[:60]:
            print(f"  {p}")
        if len(flat) > 60:
            print(f"  ... + {len(flat) - 60} mais")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    if not PDF_PATH.exists():
        print(f"ERRO: PDF não encontrado: {PDF_PATH}")
        sys.exit(1)
    if not XSD_PATH.exists():
        print(f"ERRO: XSD não encontrado: {XSD_PATH}")
        sys.exit(1)

    has_llm = bool(os.getenv("OPENROUTER_API_KEY"))
    mode = "Gemini Flash (LLM)" if has_llm else "fuzzy fallback (sem OPENROUTER_API_KEY)"

    print("\n" + "═" * 70)
    print("  AUDIT — Stage 4 Field Mapping (Pilar B)")
    print("═" * 70)
    print(f"  PDF : {PDF_PATH.name}")
    print(f"  XSD : {XSD_PATH.name}")
    print(f"  Modo: {mode}")
    print("  PDFs: 3x mesmo arquivo (multi-sample para Stage 3)")

    # 3 cópias do mesmo PDF para Stage 3 ter multi-sample
    pdf_docs = [{"id": f"boleto_{i}", "path": str(PDF_PATH), "name": f"BoletoVg_{i}.pdf"} for i in range(3)]

    job = {
        "job_id": "audit-stage4-001",
        "status": "running",
        "created_at": "2026-04-14T00:00:00",
    }

    print("\n  Executando pipeline (Stages 1-4)...")

    # Silencia Stage 5 para não precisar de storage real
    import unittest.mock as mock

    from services.pipeline_orchestrator_v2 import run_pipeline_v2

    with mock.patch("services.stages.stage5_template_generation._step_5_7_persist", new=mock.AsyncMock()):
        result = await run_pipeline_v2(
            pdf_documents=pdf_docs,
            xsd_path=str(XSD_PATH),
            storage=_NoopStorage(),
            job=job,
            emit_progress=_noop_emit,
        )

    print("  ✓ Pipeline concluído\n")

    _print_flat_paths(result)
    _print_mapping_report(result)

    _print_separator()
    print()


if __name__ == "__main__":
    asyncio.run(main())
