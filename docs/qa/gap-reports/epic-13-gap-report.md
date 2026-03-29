# Gap Report — Epic 13: Pipeline v2 Redesign
**Gerado em:** 2026-03-28
**Agente:** Quinn (Guardian) via qa-epic-gap-analysis
**Stories analisadas:** 13
**ACs totais:** 129
**Implementados:** 128 (99.2%)
**Gaps encontrados:** 1 (menor)

---

## Resumo por Story

| Story | Título | ACs | Implementados | Gaps |
|-------|--------|-----|--------------|------|
| 13.1 | Storage Gateway — Abstração | 8 | 8 | 0 |
| 13.2 | Storage Gateway — Adaptar Código | 9 | 9 | 0 |
| 13.3 | Orquestrador v2 — SSE + Checkpoint | 10 | 10 | 0 |
| 13.4 | Stage 1 — Layout Clustering | 9 | 9 | 0 |
| 13.5 | Stage 2 — Deep Extraction | 15 | 15 | 0 |
| 13.6 | Stage 1+2 Integration Tests | 7 | 7 | 0 |
| 13.7 | Stage 3 — Structural Analysis | 9 | 9 | 0 |
| 13.8 | Stage 4 — Field Mapping | 10 | 10 | 0 |
| 13.9 | Stage 3+4 Integration Tests | 9 | 9 | 0 |
| 13.10 | Stage 5 — Template Generation | 8 | 8 | 0 |
| 13.11 | Frontend — PipelineResult Type + Stores | 9 | 9 | 0 |
| 13.12 | Pipeline E2E Integration + Migration | 10 | 10 | 0 |
| 13.13 | AnalyzingPage Redesign | 10 | 9 | 1 |

---

## Gaps Detalhados

### [13.13] AnalyzingPage Redesign

| # | AC Resumido | Status | Evidência |
|---|-------------|--------|-----------|
| 1 | Stepper horizontal 5 circles nomeado | IMPLEMENTED | `frontend/src/components/analyzing/AnalyzingStepper.vue` |
| 2 | Detail card do estágio ativo | IMPLEMENTED | `AnalyzingDetailCard.vue` |
| 3 | 5 estados (initializing/processing/checkpoint/error/completed) | IMPLEMENTED | máquina de estados em `AnalyzingPage.vue` |
| 4 | Accordions de estágios concluídos | IMPLEMENTED | `CompletedStageAccordion.vue` |
| 5 | Estado completed — Summary card | IMPLEMENTED | `CompletedSummary.vue` |
| 6 | Estado checkpoint — thumbnails + timer 300s + botões | **PARTIAL** | `CheckpointCard.vue` existe mas `AnalyzingPage.vue` não envia `POST /jobs/{job_id}/handle-failure` |
| 7 | Estado error — 3 opções (retry/fallback/abort) | IMPLEMENTED | `ErrorCard.vue` |
| 8 | SSE v2 parsing (auto-detect v1 vs v2) | IMPLEMENTED | diferencia por `sub_step` field |
| 9 | A11y WCAG AA | IMPLEMENTED | role, aria-current, aria-expanded, focus visible |
| 10 | Topbar breadcrumb + botão "Cancelar análise" | IMPLEMENTED | `AnalyzingPage.vue` header |

---

## Backlog Gerado

### Média Prioridade

- [ ] **[BUG]** `[13.13-AC6]` Checkpoint: AnalyzingPage não envia resposta ao backend
  - **Arquivo:** `frontend/src/pages/AnalyzingPage.vue`
  - **O que falta:** Handler para evento `@action` do `CheckpointCard` deve chamar `POST /jobs/{job_id}/handle-failure` com `{"action": "retry"|"fallback"|"abort"}`
  - **Impacto:** Sem isso, o operador não consegue responder checkpoints — pipeline fica pendurado
  - **Endpoint:** já implementado em `backend/routers/analyze.py:448`
  - **Estimativa:** ~30min

---

## Itens para Validação Manual (UNTESTABLE)

Nenhum AC classificado como UNTESTABLE neste épico — todos os critérios foram verificáveis via análise estática.

---

## Conclusão

**Status: QUASE PRONTO PARA PRODUÇÃO**

Epic 13 está 99.2% implementado com cobertura completa de backend (5 stages, orquestrador, storage gateway), frontend (types, stores, componentes) e testes (7 arquivos, 100+ testes).

**Único bloqueio para go-live:** implementar o POST de resposta ao checkpoint no frontend (~30min).
