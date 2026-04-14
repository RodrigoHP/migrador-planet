# Auditoria: Canvas — Loop de Sincronização (edição → re-render)

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

### Seção 4 — HTML Generation (`editor_architecture_spec.md`)
Pipeline planejado:
```
Template Structure JSON → HTML Generator → Canvas Renderer
```
Qualquer edição visual deve percorrer esse pipeline e o Canvas atualizar em tempo real.

### Seção 13 — Code Editor Synchronization (`editor_architecture_spec.md`)
Dois sentidos de sincronização obrigatórios:

- **Visual → Code:** `Structure → HTML Generator → Canvas`
- **Code → Visual:** `HTML edit → HTML Parser → Structure Update → Canvas render`

### GAPs 1, 2, 3 — Gap Analysis Frontend v3 (`gap-analysis-frontend-v3.md`)

| GAP | Descrição |
|-----|-----------|
| 1 | Editar árvore/inspector não atualiza Canvas (sem geração HTML local) |
| 2 | Editar HTML no Monaco não atualiza templateStore (sem parser HTML→TreeNode) |
| 3 | Drag/resize muda store mas Canvas não reflete visualmente |

### Stories 29.1, 29.2, 29.3, 29.7 — Epic 29 (`epic-29-editor-loop-closure.md`)

- **29.1** — ADR de estratégia de re-render (pré-requisito técnico)
- **29.2** — Canvas re-render via templateStore: watcher + patch functions para GAPs 1+3
- **29.3** — Code → Structure bidirectional sync com DOMParser (GAP 2)
- **29.7** — Cobertura completa de mutações: patchRemoveNode, patchAddNode, patchMoveNode, font/color/weight

### ADR-029 (`adr-canvas-rerender-strategy.md`)
Opção C escolhida: **HTML String Patching** — patch cirúrgico via DOMParser no `generationStore.templateDraft.html` por `data-node-id`. Watcher existente no HTMLCanvas em `generationStore.templateDraft` dispara re-render automaticamente.

---

## Frontend — Status de Implementação

### `frontend/src/stores/generation.ts`

Patch functions implementadas (Story 29.2 + 29.7):

| Função | AC de referência | Status |
|--------|-----------------|--------|
| `patchNodeGeometry(nodeId, x, y, w, h)` | ADR-029, Story 29.2 | ✅ Implementado |
| `patchNodeText(nodeId, text)` | ADR-029, Story 29.2 | ✅ Implementado |
| `patchRemoveNode(nodeId)` | Story 29.7 | ✅ Implementado |
| `patchAddNode(node, parentNodeId)` | Story 29.7 | ✅ Implementado |
| `patchMoveNode(nodeId, newParentId)` | Story 29.7 | ✅ Implementado |
| `patchNodeVisibility(nodeId, visible)` | Story 30.4 | ✅ Implementado |
| `patchConvertNodeToTable(nodeId, rowNode)` | Story 30.2 | ✅ Implementado |

Todas as funções usam `DOMParser` (mais robusto que regex) e disparam re-render via novo objeto `templateDraft`.

### `frontend/src/stores/templateStore.ts`

Integração com generation patches:

| Mutação | Patch chamado | `mutationVersion.value++` | Status |
|---------|--------------|--------------------------|--------|
| `moveElement()` | `patchNodeGeometry()` | ✅ | ✅ Implementado |
| `resizeElement()` | `patchNodeGeometry()` | ✅ | ✅ Implementado |
| `updateNodeProperty('text', ...)` | `patchNodeText()` | ✅ | ✅ Implementado |
| `updateNodeProperty('visibility', ...)` | `patchNodeVisibility()` | ✅ (via mutationVersion) | ✅ Implementado |
| `removeNode()` | `patchRemoveNode()` | ✅ | ✅ Implementado |
| `addNode()` | `patchAddNode()` | ✅ | ✅ Implementado |
| `moveNode()` | `patchMoveNode()` | ✅ | ✅ Implementado |
| `convertToTable()` | `patchConvertNodeToTable()` | ✅ | ✅ Implementado |

**Observação:** `updateNodeProperties()` (bulk update) não chama nenhum patch e não incrementa `mutationVersion`. Chamadas via Inspector que usem essa função (em vez de `updateNodeProperty`) não dispararão re-render.

### `frontend/src/organisms/HTMLCanvas.vue` (linhas 540–547)

Watcher em `generationStore.templateDraft` já existia antes da Epic 29 e **não requereu modificação** (confirmado pelo ADR). Quando qualquer função `patch*` cria novo objeto `templateDraft`, o watcher dispara full re-render do iframe.

**Limitação conhecida e aceita no ADR:** elementos sem `data-node-id` (rect, line, image, chart no stage5) não são atualizados pelo patch.

### `frontend/src/composables/useCanvasInteraction.ts`

- `endDrag()` (linha 369) → chama `templateStore.moveElement()` → que chama `patchNodeGeometry()` ✅
- `endResize()` (linha 451) → chama `templateStore.resizeElement()` → que chama `patchNodeGeometry()` ✅
- Feedback visual **durante** drag/resize: apenas via `selectionState` (overlay se move), o iframe renderizado permanece estático até `endDrag`/`endResize` ⚠️

### `frontend/src/stores/codeStore.ts`

Story 29.3 implementada:

- `applyMonacoEdit(key, content)` — quando `key === 'html'`, chama `scheduleHtmlSync(content)` (debounce 800ms) ✅
- `syncHtmlToTree(html)` (Story 30.3 — extended) — DOMParser completo com:
  - Sync de `text` e `data-field` de nós existentes ✅
  - Sync de posição/tamanho via inline styles ✅
  - Remoção de nós que desapareceram do HTML ✅
  - Adição de nós novos com `data-node-id` via `addNodeFromSync()` ✅
- Flag `_isSyncing` previne loop code→tree→code ✅
- Watch em `generationStore.templateDraft?.html` → atualiza `fileContents.html` no Monaco ✅
- Watch em `templateStore.documentTree` → regenera HTML scaffold (apenas quando não há templateDraft do backend) ✅

### `frontend/src/organisms/MonacoTabsInner.vue`

- `editor.onDidChangeModelContent()` → `codeStore.applyMonacoEdit(key, editor.getValue())` ✅ (confirmado no arquivo, linha 145/154)

---

## Backend — Status de Implementação

O ADR-029 descartou solução via backend (Opção A): nenhum endpoint síncrono aceita `documentTree` e retorna HTML. A solução escolhida (Opção C) não requer alterações de backend para o loop de edição. O backend (`stage5_template_generation.py`) continua sendo responsável pelo HTML inicial, que deve incluir `data-node-id` em todos os elementos bindáveis para que o patch funcione.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | `updateNodeProperties()` (bulk update) não chama patch nem incrementa `mutationVersion` — propriedades editadas em lote pelo inspector não refletem no Canvas | 🟡 Importante | Frontend | `templateStore.ts` linha 136–140 |
| 2 | Feedback visual durante drag é apenas na overlay (CSS); o iframe só atualiza ao soltar (endDrag) | 🟢 Menor | Frontend | `useCanvasInteraction.ts` |
| 3 | Elementos sem `data-node-id` (rect, line, image, chart no stage5) não são atualizados pelo patch | 🟡 Importante | Backend/Frontend | ADR-029 Limitações, `stage5_template_generation.py` |
| 4 | Redo não implementado — apenas Undo (Ctrl+Z). Ctrl+Y não faz redo | 🟡 Importante | Frontend | `templateStore.ts`, `EditorLayout.vue` |
| 5 | `patchNodeStyle` ausente — font_size, font_weight, color não têm patch dedicado (Story 29.7 menciona `borderStyleGenerator.ts` mas patch de estilo tipográfico não está em generation.ts) | 🟡 Importante | Frontend | `generation.ts`, `borderStyleGenerator.ts` |

---

## Backlog Gerado

1. **Adicionar chamadas de patch em `updateNodeProperties()`** — bulk property update (Inspector level save) deve chamar a função de patch correspondente e incrementar `mutationVersion`. Escopo: `frontend/src/stores/templateStore.ts`.

2. **Implementar `patchNodeStyle()` em `generation.ts`** — suporte a font-size, font-weight, color e outras propriedades tipográficas via `data-node-id`. Escopo: `frontend/src/stores/generation.ts`.

3. **Adicionar `data-node-id` a rect, line, image, chart no `stage5_template_generation.py`** — pré-requisito para que o patch visual funcione nesses tipos. Escopo: `backend/services/stages/stage5_template_generation.py`.

4. **Implementar Redo (Ctrl+Y)** — `templateStore` tem `undoStack` mas sem `redoStack`. Adicionar estrutura de redo. Escopo: `frontend/src/stores/templateStore.ts`, `frontend/src/layouts/EditorLayout.vue`.

5. **Feedback visual em tempo real durante drag** — considerar mover o elemento no DOM do iframe via `postMessage` enquanto drag está ativo, em vez de esperar `endDrag`. Escopo: `useCanvasInteraction.ts`, `HTMLCanvas.vue`.

---

## Status Geral

🟡 **Parcial** — O loop principal (editar → re-render) está implementado para as mutações mais críticas via HTML String Patching (ADR-029, Stories 29.2/29.3/29.7). Os gaps remanescentes afetam casos específicos: bulk updates via `updateNodeProperties`, tipos sem `data-node-id` e ausência de Redo.
