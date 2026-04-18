# Pilar B — Relatório Final (Epic 48)

**Status:** `current`  
**Data:** 2026-04-18  
**Decisão formal:** **GAPS PENDENTES (aceitos)**

---

## Evidências por Stage

| Stage | Métrica | Resultado (spike 48.7) | Threshold | Verdict | Obs |
|-------|---------|----------------------|-----------|---------|-----|
| Stage 1 | Clusters por run (same-template) | 3 clusters / 3 PDFs | = layouts distintos | **FIXADO** | Gap 1 corrigido via ensemble voting 4-signal (48.9/48.10/48.11) |
| Stage 3 | Repeated sections recall | 22 seções detectadas | ≥ 75% gt | **PASS** | 22/22 detectadas |
| Stage 3.1 | Dynamic/static recall | 100% | ≥ 80% | **PASS** | Medido com Stage 1 quebrado — esperado manter ou melhorar |
| Stage 4 | ListBinding presente | 22 ListBindings | ≥ 1 por tipo | **PASS** | |
| Stage 4 | Cobertura binding escalar | 63.2% | ≥ 80% | **PENDENTE** | Medido com Stage 1 quebrado — re-validar |
| Stage 5 | `<repeat>` no HTML | 22 elementos | Sim | **PASS** | |
| Stage 5 | `data-list` preenchido | Vazio no spike | Sim | **FIXADO** | Fix em commit `82a1d56` |

---

## Decisão Formal

**GAPS PENDENTES (aceitos)**

### Justificativa

O core do Pilar B está funcionando:
- Stage 3 detecta seções repetidas corretamente
- Stage 4 gera ListBinding com `xsd_list_path`
- Stage 5 gera `<repeat data-list="...">` no HTML

Os dois gaps identificados no spike 48.7 foram **endereçados**:

1. **Gap 1 — Stage 1 clustering:** FIXADO via ensemble voting 4-signal (stories 48.9/48.10/48.11). Validação local 7/7 casos passando.

2. **Gap 2 — Scalar coverage 63.2%:** O próprio findings doc (`spike-48-7-findings.md` §Gap 2) estima que corrigir o Gap 1 eleva a cobertura para ~75–80% sem tocar Stage 4. Esta estimativa precisa ser validada com uma re-execução do spike 48.7 com Stage 1 corrigido.

### Gaps aceitos (não bloqueiam Pilar C)

| Gap | Status | Ação |
|-----|--------|------|
| Scalar coverage re-validação | **Pendente** | Re-executar spike E2E com Stage 1 fixado em produção |
| Scalar coverage < 80% se persistir | **Backlog** | Expandir Stage 4: sinônimos PT-BR, normalização de labels, prompt Gemini mais rico |

---

## Próximo: Re-validação E2E (recomendada antes de Pilar C)

Executar `backend/scripts/spike_48_validate_e2e.py` com Stage 1 corrigido (deploy da branch `feature/epic-48-pilar-b` para Railway) e medir:

1. Stage 1: ≤ layouts distintos (deve ser 1 cluster para 3× PosicaoConsolidada)
2. Stage 4 scalar coverage: esperado ≥ 75–80% com Stage 1 correto
3. Stage 5 `data-list`: deve estar preenchido (fix `82a1d56` já deployado)

Se scalar coverage ≥ 80% após re-validação → **PILAR B COMPLETO**.  
Se scalar coverage < 80% → atacar Stage 4 (sinônimos + prompt Gemini) antes de Pilar C.

---

## Próximo Epic — Pilar C: Editor Visual

Independente da re-validação, o **Pilar C** pode começar, pois:
- O `<repeat data-list="Propostas[]">` já é gerado pelo Stage 5
- O editor Vue 3 precisa renderizar esse `<repeat>` como um loop interativo (expandir/colapsar, editar item template, vincular a fonte de dados)

**Pré-requisito para Pilar C:** deploy da branch atual + re-validação E2E confirmar Stage 1 fix em produção.

---

## Artefatos Gerados

| Artefato | Localização |
|---------|-------------|
| Spike 48.7 findings | `docs/reports/epic-48/spike-48-7-findings.md` |
| E2E validation result | `docs/reports/epic-48/e2e-validation-posicao-consolidada.json` |
| Calibração ensemble | `docs/reports/epic-48/calibration-summary.md` |
| Thresholds JSON | `docs/reports/epic-48/calibration-thresholds.json` |
| Ground truth | `docs/reports/epic-48/ground-truth-posicaoconsolidada.json` |
| Validação local Stage 1 | `backend/scripts/spike_48_validate_stage1_local.py` |
