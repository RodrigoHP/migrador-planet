# Auditoria: Tela de Progresso + Pipeline (Stages 1-5)

**Data:** 2026-04-07  
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**Fontes:** `docs/prd-v3.md` (FR35), `docs/wireframes/wireframes-mid-fi.md` (Estado: Analyzing), `docs/architecture/architecture-v5.md` (pipeline 8 blocos / 23 stages)

### FR35 — Tela de Progresso Dedicada

A tela de progresso é uma tela **intermediária dedicada** entre Upload e Editor. O Editor **não abre** até o pipeline finalizar — sem Canvas parcial visível. Ao concluir todos os blocos, navega **automaticamente** para o Editor sem intervenção do operador.

Requisitos da tela:
- Pipeline exibido como **8 blocos lógicos / 23 estágios** com indicadores visuais (✅ concluído, 🔄 em progresso, ○ pendente)
- **Barra de progresso geral** com percentual total
- **Resumo parcial atualizado em tempo real**: PDFs processados, páginas, layouts detectados
- **Tempo estimado** visível durante o processamento
- **Botão Cancelar** que interrompe o pipeline e retorna ao Upload
- **Navegação automática para o Editor** ao finalizar — sem clique manual

### Pipeline planejado (architecture-v5.md)

8 blocos lógicos, 23 estágios:
1. Aquisição (2 stages) — upload PDFs + XSD, análise de PDFs
2. Descoberta de Layout (5 stages) — esqueleto, agrupamento, representativas, impressão digital, registro
3. Inteligência (5 stages) — alinhamento, análise multi-exemplo, estabilidade, variantes, normalização
4. Tabelas (2 stages) — detecção e estruturação
5. Semântica (1 stage) — análise de significado
6. Visão (1 stage) — análise visual por IA
7. Mapeamento (4 stages) — matching campos XSD ↔ PDF
8. Validação (3 stages) — verificação de integridade

### SSE e Confiabilidade
- Replay buffer para late-connects (clientes que conectam após eventos iniciais)
- Persistência de job com TTL cleanup
- Reconexão automática em caso de perda de conexão

---

## Frontend — Status de Implementação

### AnalyzingPage.vue (`frontend/src/pages/AnalyzingPage.vue`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Tela dedicada sem Canvas/Editor visível | ✅ Implementado | Página separada; sem render do editor durante análise |
| Indicadores visuais por estágio (✅/🔄/○) | ✅ Implementado | `AnalyzingStepper` com estados `done/active/pending/error/warning` |
| Resumo parcial (PDFs, páginas, layouts) | ✅ Implementado | `summaryData` com `pdfCount`, `pageCount`, `layoutsDetected` em info-cards |
| Tempo estimado | ✅ Implementado | `estimatedTimeLabel` computed — média de estágios concluídos × restantes |
| Botão Cancelar funcional | ✅ Implementado | `handleCancel()` faz `POST /api/analyze/{jobId}/cancel` |
| Navegação automática para Editor ao concluir | ✅ Implementado | `fetchAndLoadResult()` → `router.push('/editor')` ao receber `pipeline_completed` |
| Reconexão automática (max 3 tentativas) | ✅ Implementado | `reconnectAttempts` / `MAX_RECONNECT = 3` com timer |
| Banner de sessão perdida (servidor reiniciado) | ✅ Implementado | `sessionLost` banner com botão "Voltar ao Upload" |
| Sub-steps por estágio com pill "Sub-etapa X de Y" | ✅ Implementado | `subStepPill` computed com `SUB_STEP_LABELS` |
| Dreno de eventos com stagger visual (60 ms) | ✅ Implementado | `_drainEventQueue()` com `setTimeout(60)` |
| Checkpoint de serviço com decisão do operador | ✅ Implementado | `CheckpointCard` com timeout automático |
| Card de erro com opção de decisão | ✅ Implementado | `ErrorCard` com `handleErrorDecision()` |
| Acordeões de estágios concluídos | ✅ Implementado | `CompletedStageAccordion` com sumário por estágio |
| Avisos de degradação do pipeline (banner) | ✅ Implementado | `pipelineWarnings` com banner descartável |
| **Barra de progresso geral com percentual** | ❌ Não implementado | `v2ProgressPct` é computado e monitorado, mas não há barra de progresso exibida na UI — apenas indicadores por estágio no stepper |
| **8 blocos / 23 stages conforme spec** | ❌ Divergência | Pipeline implementado com **5 stages** (não 8 blocos / 23 stages): Layout Clustering, Deep Extraction, Structural Analysis, Field Mapping, Template Generation |

### analyzingPageConstantsV2.ts (`frontend/src/pages/analyzingPageConstantsV2.ts`)

- `PIPELINE_V2_STAGES`: 5 stages (Story 13.3 — redesign explícito)
- `TOTAL_V2_STAGES = 5`
- Sub-steps mapeados: 1.0-1.16 (Stage 1), 2.1-2.9 (Stage 2), 3.1-3.4 (Stage 3), 4.1-4.7 (Stage 4), 5.1-5.7 (Stage 5) — total ~36 sub-steps granulares, mais detalhados que os 23 stages do spec original

---

## Backend — Status de Implementação

### `backend/routers/analyze.py`

| Item planejado | Status | Detalhe |
|---|---|---|
| Endpoint SSE `GET /api/analyze/{jobId}/progress` | ✅ Implementado | `_event_generator()` via `EventSourceResponse` |
| Replay buffer para late-connects | ✅ Implementado | `event_log` append-only; todos os eventos passados são reenviados primeiro |
| Delay de 150ms entre eventos históricos | ✅ Implementado | `await asyncio.sleep(0.15)` para eventos históricos vs `sleep(0)` para live |
| Persistência de job com TTL (1 hora) | ✅ Implementado | `_JOB_TTL_SECONDS = 3600`; `_evict_stale_jobs()` |
| Limpeza de diretórios órfãos (24h) | ✅ Implementado | `_cleanup_orphaned_dirs()` com `_ORPHAN_TTL_SECONDS = 86_400` |
| Endpoint `POST /api/analyze/{jobId}/cancel` | ✅ Implementado | `cancel_flag` asyncio.Event no job_state |
| Endpoint `GET /api/analyze/{jobId}/result` | ✅ Implementado | Retorna `{status, result, error}` |
| Rate limiting no endpoint de análise | ✅ Implementado | `_RATE_LIMIT_ANALYZE = "10/minute"` via slowapi |
| **Pipeline 8 blocos / 23 stages** | ❌ Divergência | `pipeline_orchestrator_v2.py` define 5 stages com pesos iguais (20% cada); a nomenclatura v1 com 23 stages foi removida no Epic 15 |

### `backend/services/pipeline_orchestrator_v2.py`

- **5 stages** com peso 0.20 cada: Layout Clustering (1), Deep Extraction (2), Structural Analysis (3), Field Mapping (4), Template Generation (5)
- Suporte a `PipelineAbortError` para cancelamento pelo operador
- `handle_service_failure()` para checkpoints de serviço com fallback/retry/abort
- Função `compute_overall_progress(stage, sub_progress_pct)` calcula progresso geral corretamente

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Pipeline implementado com 5 stages em vez de 8 blocos / 23 stages conforme architecture-v5.md e FR35; a divergência é documentada internamente (Story 13.3), mas não está refletida no PRD | 🟡 Importante | Backend + Docs | FR35, architecture-v5.md seção 1, `analyzingPageConstantsV2.ts` comentário "Story 13.3" |
| 2 | ~~Barra de progresso geral~~ — **DESCARTADO**: wireframe v2 (`wireframe-progress-screen-v2.html`) redesenhou para barras de progresso **por estágio** dentro dos cards de detalhe, não barra geral. Implementação atual (stepper + sub-steps) está alinhada com o wireframe v2 aprovado por UX | ✅ Resolvido | — | Decisão UX wireframe v2 |
| 3 | ~~Navegação automática para Editor~~ — **DESCARTADO**: wireframe v2 exibe `CompletedSummary` com resumo final e botão "Abrir Editor" de propósito — decisão UX para que o operador veja o resumo antes de avançar. PRD v3 diverge mas wireframe v2 é a spec visual aprovada | ✅ Resolvido | — | Decisão UX wireframe v2 |
| 4 | ~~Job state apenas em memória~~ — **CORRIGIDO**: `RedisJobStore` (Story 15.4) já implementado em `services/job_store.py`. Jobs persistem via Redis quando `REDIS_URL` configurado. `_pipeline_jobs` dict é cache in-process com fallback ao Redis em `/status` e `/result`. `recover_running_jobs()` marca jobs interrompidos como "failed" no startup. Único cenário não coberto: SSE stream não reconecta a job do Redis após restart (coberto pelo banner `sessionLost`) | ✅ Resolvido | — | `job_store.py`, Story 15.4 |

---

## Backlog Gerado

1. **[Docs] Atualizar PRD e architecture para refletir pipeline v2 (5 stages):** O PRD v3.0 e architecture-v5.md ainda descrevem 8 blocos / 23 stages que foram substituídos. Sincronizar a documentação com a implementação atual (Story 13.3) para evitar confusão futura.

2. ~~**[Frontend] Adicionar barra de progresso geral com percentual**~~ — **DESCARTADO:** wireframe v2 usa progresso por estágio dentro dos cards. Implementação atual está alinhada.

3. ~~**[Frontend] Implementar navegação automática para Editor**~~ — **DESCARTADO:** wireframe v2 exibe CompletedSummary com botão "Abrir Editor" de propósito (decisão UX).

4. ~~**[Backend] Persistência de job em Redis**~~ — **DESCARTADO:** já implementado na Story 15.4 (`services/job_store.py` com `RedisJobStore`).

---

## Status Geral

🟢 Quase completo — A infraestrutura SSE com replay buffer, reconexão automática, cancelamento, checkpoints de serviço, indicadores visuais por estágio e persistência Redis está completamente implementada. Único gap restante: documentação (PRD/architecture) desatualizada referenciando 8 blocos/23 stages em vez dos 5 stages implementados (Story 13.3).
