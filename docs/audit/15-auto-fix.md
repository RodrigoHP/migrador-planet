# Auditoria: Auto-correção por IA

**Data:** 2026-04-07
**Status Geral:** 🟢 Implementado

---

## O que foi planejado

**FR34** (PRD v3.0, seção "Auto-correção por IA"):

- Detecção automática de problemas: spacing, grid alignment, font inconsistencies, column alignment
- Lista de issues detectados com severidade e confiança
- Aplicar fix individual vs aplicar todos
- Preview do fix antes de aplicar
- Undo de fix aplicado
- Integração com `templateStore` (fix atualiza a árvore)

**`docs/ideias/ux/template_editor_main_screen_spec.md`** seção toolbar — "Auto Fix Layout":

> Automatically fixes: spacing problems, grid alignment, font inconsistencies, column alignment.

---

## O que foi planejado (detalhado técnico)

O planejamento técnico implícito (confirmado pelo código implementado) inclui:

- Backend rule-based detection (`_run_rule_based_detection`) para problemas determinísticos
- Backend AI-based detection via OpenRouter/Claude Sonnet para sugestões semânticas
- Frontend: painel modal com fluxo de revisão sugestão-a-sugestão
- Aceitar/Pular/Rejeitar por sugestão individual
- Aceitar todas (batch) ou aceitar por tipo
- Preview inline da sugestão (valor atual vs sugerido)
- Undo via `templateStore.pushUndoSnapshot()` antes de aplicar
- Limite de execuções por sessão (`SESSION_RUN_LIMIT`)

---

## Frontend — Status de Implementação

### Componentes existentes

| Componente | Arquivo | Status |
|---|---|---|
| Painel Auto Fix | `frontend/src/organisms/AutoFixPanel.vue` | Implementado |
| Store Auto Fix | `frontend/src/stores/autoFixStore.ts` | Implementado |
| Fix Preview (molecule) | `frontend/src/molecules/FixPreview.vue` | Implementado |
| Confidence Badge (molecule) | `frontend/src/molecules/ConfidenceBadge.vue` | Implementado |

### O que funciona

**AutoFixPanel.vue:**
- Modal com Teleport para `body`, disparado por `autoFixStore.isOpen`
- Estados visuais: loading (spinner), error, empty (sem sugestões), finished (resumo), active (sugestão atual)
- Progresso: barra de progresso com texto "Sugestão N de Total"
- Sugestão atual: badge de tipo, `FixPreview` (current_value → suggested_value), `ConfidenceBadge` com score 0-100
- Botões por sugestão: ✅ Aceitar / ⏭️ Pular / ❌ Rejeitar
- **Batch actions** (Story 14.11):
  - "Aceitar Todas (N)" com preview modal inline
  - Dropdown de tipo (se > 1 tipo) + "Aceitar Tipo"
  - Preview expansível (+N mais) antes de confirmar batch
- Resumo final: aceitas / rejeitadas / puladas

**autoFixStore.ts:**
- `runAutoFix()`: POST para `/api/auto-fix` com `template_state` (documentTree) e `pdf_extraction` opcional
- Limite `SESSION_RUN_LIMIT` (padrão 5 via `VITE_AUTOFIX_LIMIT`) — botão desabilitado quando atingido
- `acceptCurrent()`: `templateStore.pushUndoSnapshot()` → `_applySuggestion()` → avança
- `rejectCurrent()` e `skipCurrent()`: apenas registram e avançam
- `batchAcceptAll()`: snapshot único + aplica todas; `batchAcceptByType()`: snapshot único + aplica filtro de tipo, demais vão para skipped
- `_applySuggestion()`: mapeia `FixType` → `propKey` via `propMap` e chama `templateStore.updateNodeProperty(element_id, propKey, suggested_value)`
- Mapping completo: spacing→padding, alignment→textAlign, font→fontFamily, binding→binding, position→x, border-refine→border, background-refine→backgroundColor, text-align→textAlign, z-order→zIndex
- `reset()` disponível para nova sessão

**TopToolbar.vue — botão Auto Fix:**
- Botão "🔧 Auto Fix" desabilitado quando `autoFixStore.isLimitReached || autoFixStore.isRunning`
- Tooltip exibe "Limite de Auto Fix atingido nesta sessão" quando limite atingido
- Clique chama `autoFixStore.runAutoFix()`

### O que falta / está incompleto

- **Preview do fix antes de aplicar no Canvas**: o `FixPreview` exibe `current_value` e `suggested_value` como texto, mas não renderiza uma prévia visual do elemento com e sem o fix no Canvas. O operador vê apenas os valores em string.
- **Integração completa com Canvas após aceitar**: `_applySuggestion` chama `templateStore.updateNodeProperty` mas, conforme GAP 1/3 do `gap-analysis-frontend-v3.md`, mutações no `templateStore` podem não refletir imediatamente no iframe do Canvas (depende de Story 29.2 estar completa). O fix é aplicado no store mas o Canvas pode não atualizar visualmente sem re-render.
- **Undo de fix individual vs undo batch**: `pushUndoSnapshot()` é chamado uma vez por `acceptCurrent()` (snapshot antes de cada fix) e uma vez por `batchAcceptAll()` / `batchAcceptByType()` (snapshot único antes do batch). O undo desfaz o último snapshot — para batch, desfaz tudo de uma vez; para individuais, permite desfazer um a um. Mas não há botão "Desfazer" visível no `AutoFixPanel.vue` — o undo é via Ctrl+Z do editor (se implementado).
- **Sugestões de `spacing` / `alignment` genéricas**: o tipo `spacing` mapeia para `padding` e `alignment` mapeia para `textAlign` — perdendo especificidade de margin, gap, line-height, grid-alignment.
- **`position` mapeia apenas para `x`**: fix de posição aplica apenas `x`, ignorando `y`.

---

## Backend — Status de Implementação

### `backend/routers/auto_fix.py`

**Rule-based detection (`_run_rule_based_detection`)** — 4 regras implementadas:

| Regra | Função | O que detecta |
|-------|--------|---------------|
| Border issues | `_detect_border_issues` | Elementos PDF com linha/rect sem borda CSS correspondente (`border_{side}_width == 0`) |
| Background issues | `_detect_background_issues` | Retângulos preenchidos no PDF sem `background_color` CSS ou com cor diferente (tolerância RGB ±10) |
| Text alignment | `_detect_text_align_issues` | Texto alinhado à direita/centro no PDF mas CSS tem `text-align: left` (tolerância 5px) |
| Z-order | `_detect_zorder_issues` | Elementos sobrepostos (>10% de overlap) sem `zIndex` explícito |

**Geometria:**
- `_find_overlapping_node`: encontra nó do template com maior área de sobreposição com bbox do PDF
- `_bboxes_overlap`: detecta sobreposição > 10% do menor bounding box
- `_colors_match`: compara hex colors com tolerância por canal RGB

**AI-based detection:**
- Modelo: `anthropic/claude-sonnet-4-5` via OpenRouter
- Prompt estruturado com categorias: spacing, alignment, font, binding, position, border-refine, background-refine, text-align, z-order
- Resposta JSON com até `MAX_SUGGESTIONS = 20` sugestões (deduzidas as rule-based)
- Merge: rule-based first (deterministic) + LLM
- Trunca template_state > 8000 chars e pdf_extraction > 4000 chars para evitar limite de tokens
- Retorna 503 se `OPENROUTER_API_KEY` não configurado

**Observações:**
- Rule-based só executa se `pdf_extraction` estiver presente no body — sem dados de extração PDF, apenas o LLM gera sugestões
- Tipos de sugestão LLM não são validados contra enum — qualquer string aceita, frontend mostra badge com fallback

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Preview visual do fix no Canvas não implementado — só texto current_value/suggested_value | 🟡 Importante | `AutoFixPanel.vue` — `FixPreview` apenas textual | FR34 "preview do fix antes de aplicar" |
| 2 | `_applySuggestion` aplica ao store mas Canvas pode não atualizar (GAP 1/3 não fechado) | 🟡 Importante | `autoFixStore._applySuggestion` + `HTMLCanvas.vue` sem watcher | gap-analysis-frontend-v3 GAP 1+3, Story 29.2 |
| 3 | Fix de `spacing` → mapeia para `padding` apenas (não margem/gap/line-height) | 🟡 Importante | `autoFixStore._applySuggestion propMap` | FR34 |
| 4 | Fix de `position` → aplica apenas `x`, ignora `y` | 🟡 Importante | `autoFixStore._applySuggestion propMap.position = 'x'` | FR34 |
| 5 | Botão "Desfazer" não visível no AutoFixPanel — undo só via Ctrl+Z externo | 🟢 Menor | `AutoFixPanel.vue` — sem botão undo explícito | FR34 "undo de fix aplicado" |
| 6 | Rule-based detection inativa sem `pdf_extraction` — quando pipeline não envia dados, apenas LLM funciona | 🟢 Menor | `backend/routers/auto_fix.py:_run_rule_based_detection` | — |
| 7 | Tipos de sugestão do LLM não validados contra enum — string qualquer aceita | 🟢 Menor | `auto_fix.py` — FixSuggestion.type sem enum constraint | — |

---

## Backlog Gerado

1. **Preview visual no Canvas**: implementar "modo de preview" no `AutoFixPanel` que aplica temporariamente o `suggested_value` ao elemento no Canvas (sem snapshot de undo) e desfaz ao clicar "Rejeitar" ou "Pular". Requer que GAP 1/3 (Story 29.2) esteja completo.
2. **Botão "Desfazer último fix"** no `AutoFixPanel`: chamar `templateStore.undo()` e recuar `currentIndex` (ou exibir o fix como "desfeito" na lista de `appliedFixes`).
3. **Expandir `propMap` para `spacing`**: mapear para objeto `{ padding, margin, lineHeight }` ou usar `suggested_value` como CSS property genérica (ex: `"padding: 8px; margin: 4px"`).
4. **Corrigir `position` para incluir `y`**: ao aceitar fix de `position`, parsear `suggested_value` como `"x,y"` ou usar propriedade `y` separada.
5. **Validar tipo de sugestão LLM contra enum** no backend: adicionar lista de tipos válidos ao modelo Pydantic `FixSuggestion`.
6. **Expor `pdf_extraction` via `templateStore`**: garantir que o campo `pdfExtraction` seja populado em `loadFromPipelineResult` para que rule-based detection funcione no auto-fix.

---

## Status Geral

🟢 **Implementado** — O Auto Fix está completo com fluxo modal de revisão sugestão-a-sugestão, batch por tipo, aceitar/pular/rejeitar, undo via snapshot, integração com `templateStore`, rule-based detection (4 regras geométricas) e AI detection via Claude Sonnet. Os gaps são secundários: o preview visual do fix é apenas textual (não renderiza no Canvas), a aplicação ao Canvas depende do GAP 1/3 do editor loop closure (Story 29.2), e o propMap tem algumas simplificações (spacing→padding apenas, position→x apenas).
