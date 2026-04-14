# Epic 34 — Field Mapping & Coverage Accuracy

**Prioridade:** P1
**Fase:** 2
**Estimativa:** 7 stories (originalmente 8 — 34.4 removida por já estar implementada)
**Dependências:** Nenhuma (paralelo ao Epic 33)
**Objetivo:** Mapeamento de campos mostra confiança real, cobertura é precisa e atualiza em tempo real, e o operador tem ferramentas eficientes para mapear campos manualmente.

---

## Contexto

O matching automático via Gemini Flash funciona, mas a confiança exibida é hardcoded 'medium', gráficos nunca contam na cobertura (mapped=0), a cobertura não atualiza ao editar, e faltam ferramentas de produtividade no FieldNavigator (busca, agrupamento por tipo).

> **Nota QA (2026-04-07):** Story 34.4 (Drag campo para Canvas) **removida** — já implementada em commit 863792c (Story 28.4). `FieldNavItem.vue` tem `draggable="true"`, `HTMLCanvas.vue` tem `onFieldDrop` com confirmação.

---

## Stories

### 34.1 — Propagar score de confiança real ao frontend
**Gap:** C10
**Escopo:** Frontend (`mapping.ts`, `pipeline.types.ts`) + Backend (contrato de dados)
**QA Note:** `FieldMappingEntry` type em `pipeline.types.ts` precisa ser estendido com campo `confidence`.
**AC:**
- [x] Extend `FieldMappingEntry` type em `pipeline.types.ts` com campo `confidence: number | string`
- [x] `loadPipelineFields()` usa `entry.confidence` real do pipeline (não hardcoded 'medium')
- [x] `FieldMappingTable` exibe ConfidenceBadge com score real (0-100 ou low/medium/high derivado)
- [x] FieldNavigator reflete confiança correta nos badges de status
- [x] Score numérico do stage4 (`confidence_score`) mapeado para categorias: <40% low, 40-75% medium, >75% high

### 34.2 — Corrigir cobertura de gráficos
**Gap:** C11
**Escopo:** Backend (`stage5_template_generation.py`)
**AC:**
- [x] `_count_mapped_charts()` implementado — conta gráficos com binding de dados configurado
- [x] `charts.mapped` reflete contagem real (não hardcoded 0)
- [x] Gráficos incluídos na fórmula ponderada (ex: campos 55% + tabelas 25% + imagens 10% + gráficos 10%)
- [x] Percentual de cobertura mais preciso nos testes com boleto + gráficos

### 34.3 — Cobertura atualiza em tempo real
**Gap:** I20
**Escopo:** Frontend (`coverageStore.ts`, `templateStore.ts`)
**AC:**
- [x] Watcher em `templateStore` detecta mudanças de binding (map/unmap)
- [x] `coverageStore.updateForLayout()` recalcula localmente após cada mudança
- [x] CoverageBadge na toolbar atualiza sem recarregar
- [x] CoveragePopover breakdown reflete estado atual
- [x] CoverageOverlay atualiza overlays em tempo real

### ~~34.4~~ — REMOVIDA (já implementada na Story 28.4, commit 863792c)
> `FieldNavItem.vue:121` tem `draggable="true"`, `HTMLCanvas.vue:617-662` tem `onFieldDragOver` + `onFieldDrop` com diálogo de confirmação.

### 34.5 — Agrupamento por tipo no FieldNavigator
**Gap:** I18
**Escopo:** Frontend (`FieldNavigator.vue`)
**AC:**
- [x] Toggle ou tabs para alternar entre agrupamento por status (atual) e por tipo
- [x] Agrupamento por tipo: Campos, Tabelas, Gráficos, Seções, Recursos
- [x] Contagem por grupo visível no header de cada seção
- [x] Estado do toggle persiste na sessão

### 34.6 — Busca/filtro no FieldNavigator
**Gap:** I19
**Escopo:** Frontend (`FieldNavigator.vue`)
**AC:**
- [x] Input de texto no topo do FieldNavigator
- [x] Filtra `fieldNavItems` por nome (case-insensitive, substring match)
- [x] Resultado atualiza em tempo real (debounce 200ms)
- [x] Limpar filtro com botão ✕ ou Escape
- [x] Quando filtro ativo, todos os grupos expandidos

### 34.7 — Auto-bind semântico (match nome → campo XSD)
**Gap:** I15
**Escopo:** Backend (`stage3_structural_analysis.py`)
**AC:**
- [x] Após `_extract_semantic_name()`, tenta match por similaridade com campos XSD
- [x] Normalização: lowercase, remove acentos, remove pontuação
- [x] Levenshtein similarity > 0.7 → salva como `suggested_binding` no nó
- [x] Frontend usa `suggested_binding` para pré-popular binding (status 'unconfirmed')
- [x] Operador pode confirmar ou alterar sugestão
- [x] Coverage aumenta com auto-bind vs sem (teste comparativo)

### 34.8 — Integrar ConsolePanel com coverageStore
**Gap:** I35
**Escopo:** Frontend (`ConsolePanel.vue`, `coverageStore.ts`)
**AC:**
- [x] Warning automático quando `coverageStore.activeLayoutCoverage.percentage < 80`
- [x] Warning com texto "Cobertura abaixo de 80% (atual: X%) — revise campos não mapeados"
- [x] Warning clicável → abre CoveragePopover
- [x] Warning desaparece quando cobertura sobe acima de 80%
