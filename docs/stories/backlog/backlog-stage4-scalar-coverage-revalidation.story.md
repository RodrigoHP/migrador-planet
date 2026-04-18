# Backlog — Stage 4: Re-validação E2E Scalar Coverage com Stage 1 Fixado

**Tipo:** Validação / Re-execução de Spike  
**Prioridade:** P1 — pré-requisito para declarar Pilar B COMPLETO  
**Esforço estimado:** 2–4h (re-executar spike 48.7 com Stage 1 correto)  
**Dependências:** Deploy da branch `feature/epic-48-pilar-b` + Railway funcional

---

## Problema

No spike 48.7, o scalar coverage medido foi **63.2%** (threshold ≥ 80% = FAIL). Porém, esse número foi medido com Stage 1 quebrado: o bug de clusterização (`0.8*geo + 0.2*den`) fazia 3 PDFs do mesmo template virarem 3 clusters separados — então Stage 3 via apenas 1 PDF por cluster e detectava menos campos dinâmicos.

Com Stage 1 corrigido (ensemble voting 4-signal, stories 48.9/48.10/48.11), os 3 PDFs devem cair no mesmo cluster → Stage 3 vê 3 instâncias → mais comparações cross-instance → mais campos dinâmicos detectados → cobertura esperada ≥ 75–80%.

**Este número NUNCA foi medido com Stage 1 correto em produção.**

---

## Objetivo

Re-executar o script `backend/scripts/spike_48_validate_e2e.py` contra a Railway com Stage 1 fixado e medir:

1. **Stage 1:** ≤ layouts distintos detectados (deve ser 1 cluster para 3× PosicaoConsolidada)
2. **Stage 4 scalar coverage:** % de campos escalares com binding XSD correto
3. **Stage 5 `data-list`:** deve estar preenchido (fix `82a1d56` já incluso na branch)

---

## Acceptance Criteria

- [ ] **AC1:** Branch `feature/epic-48-pilar-b` deployada no Railway e funcional
- [ ] **AC2:** Script `spike_48_validate_e2e.py` executado contra Railway (3+ PDFs PosicaoConsolidada)
- [ ] **AC3:** Stage 1 resultado: PosicaoConsolidada×3 → 1 cluster (era 3 com Stage 1 quebrado)
- [ ] **AC4:** Scalar coverage medido e documentado
  - Se ≥ 80% → **PILAR B COMPLETO** (declarar formalmente, atualizar `pilar-b-final-report.md`)
  - Se < 80% → Abrir story de melhoria Stage 4 (sinônimos PT-BR, normalização de labels)
- [ ] **AC5:** `docs/reports/epic-48/pilar-b-final-report.md` atualizado com resultado real

---

## Contexto Técnico

### Script de validação existente

```bash
cd backend
python scripts/spike_48_validate_e2e.py \
  --api-url https://your-railway-url.railway.app \
  --pdf-dir tests/fixtures/samples/relatorio \
  --template-type posicao_consolidada
```

### Tabela de referência (spike 48.7 com Stage 1 quebrado)

| Stage | Métrica | Resultado 48.7 | Threshold | Verdict |
|-------|---------|---------------|-----------|---------|
| Stage 1 | Clusters por run | 3 clusters / 3 PDFs | = layouts | FIXADO |
| Stage 3.1 | Dynamic/static recall | 100% | ≥ 80% | PASS |
| Stage 4 | Scalar coverage | **63.2%** | ≥ 80% | **PENDENTE** |
| Stage 5 | `<repeat>` presente | Sim | Sim | PASS |
| Stage 5 | `data-list` preenchido | Vazio | Sim | FIXADO |

### Estimativa de impacto do Stage 1 fix no scalar coverage

- Stage 1 quebrado: 1 PDF / cluster → Stage 3 detecta N campos fixos = falsos fixos
- Stage 1 correto: 3 PDFs / cluster → Stage 3 detecta diferenças cross-instance → mais dinâmicos
- Estimativa conservadora (da análise do spike 48.7): +15–20 pp de cobertura → ~75–80%

---

## Se scalar coverage < 80% após re-validação

Abrir story separada para melhorar Stage 4:

| Técnica | Impacto esperado | Esforço |
|---------|-----------------|---------|
| Sinônimos PT-BR para labels | +5–10 pp | 4h |
| Normalização de labels (remove acentos, lowercase) | +2–5 pp | 2h |
| Prompt Gemini mais rico (mais exemplos few-shot) | +5–10 pp | 3h |
| Fallback por substring match | +3–5 pp | 2h |

---

## Quando Executar

**Imediatamente após:** merge da branch `feature/epic-48-pilar-b` na main + deploy Railway.

**Bloqueador para:** declarar Pilar B COMPLETO (necessário antes de Epic 49 ter seu pré-requisito confirmado).

---

## Referências

- Script: `backend/scripts/spike_48_validate_e2e.py`
- Relatório base: `docs/reports/epic-48/pilar-b-final-report.md`
- Findings originais: `docs/reports/epic-48/spike-48-7-findings.md`
- Stage 1 fix: stories 48.9/48.10/48.11
- Fix `data-list`: commit `82a1d56`

---

**Criado em:** 2026-04-18  
**Origem:** Story 48.8 AC5 — gaps pendentes exigem backlog de correção documentado
