# Auditoria: Canvas — Interação (drag, resize, seleção, context menu, undo, clipboard)

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

### Seções 6–9 — Canvas Interaction Model (`canvas_complete_spec.md`)
Interações suportadas: Selection, Dragging, Resizing, Inspection. Regra fundamental: **o Canvas NÃO cria elementos novos** (seção 17: "The Canvas does NOT… Generate templates").

### Seção 9 — Element Selection (`editor_architecture_spec.md`)
- Clicar elemento → seleciona na Árvore + abre Inspector
- Bidirecional: Tree selection → Canvas highlight, Canvas selection → Tree node

### Seção 10 — Hierarchical Selection (`editor_architecture_spec.md`)
Quando elemento está aninhado (texto > célula > linha > tabela), popup permite escolher nível:
```
Select Element: Text | Cell | Row | Table
```

### Seções 8–15 — Canvas Interactions (`canvas_complete_spec.md`)
- Dragging: move com feedback visual, atualiza template.json
- Resizing: handles nas bordas, modifica layout properties
- Scrolling vertical dentro do iframe

### Wireframes Mid-Fi (`wireframes-mid-fi.md`)
- Clicar → seleciona na Árvore + Inspetor
- Arrastar → move, atualiza store
- Redimensionar via handles → ajusta tamanho no store
- **Seleção hierárquica** popup
- **Snap** — toggle na toolbar (ativo por padrão)
- **Context menu** (Canvas): Snap e Cobertura como toggles; Árvore tem menu de clique direito
- Canvas NÃO permite criar elementos novos

### Keyboard/Clipboard (implícito em componentes implementados)
Baseado nos arquivos de implementação identificados: Arrow keys, Ctrl+D, Delete, Ctrl+C, Ctrl+V, Ctrl+Z, Ctrl+A (Ctrl+A não documentado na spec explicitamente).

---

## Frontend — Status de Implementação

### Seleção (`useCanvasInteraction.ts`, `CanvasSelectionOverlay.vue`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Clicar elemento → seleciona na Árvore | ✅ | `selectElement()` chama `editorStore.selectElement()` |
| Clicar elemento → abre Inspector | ✅ | `selectElement()` chama `inspectorStore.selectNode()` |
| Tree → Canvas highlight (selectFromTree) | ✅ | `selectFromTree()` atualiza `selectionState` |
| Multi-seleção (Ctrl+Click) | ✅ | `multiSelection` Set com lógica toggle |
| Shift+Click range | ✅ (simplificado) | Adiciona ao Set sem range real |
| Seleção hierárquica popup | ✅ | `showHierarchyPopup()` / `hierarchyPopup` ref + `HierarchyPopup.vue` |
| Clear selection (click em vazio) | ✅ | `clearSelection()` |

### Drag (`useCanvasInteraction.ts`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Arrastar → move elemento | ✅ | `startDrag/updateDrag/endDrag` + `templateStore.moveElement()` |
| Feedback visual durante drag | ⚠️ Parcial | Overlay se move; iframe só re-renderiza em `endDrag` |
| Multi-seleção drag | ✅ | `endDrag()` aplica delta a todos os IDs em `multiSelection` |
| Snap durante drag | ✅ | `calcSnapLines()` integrado em `updateDrag()` |

### Resize (`useCanvasInteraction.ts`, `CanvasSelectionOverlay.vue`)

| Feature | Status | Observação |
|---------|--------|-----------|
| 8 handles de resize (TL,TM,TR,ML,MR,BL,BM,BR) | ✅ | Implementados em `computeHandles()` |
| Resize → atualiza store | ✅ | `endResize()` → `templateStore.resizeElement()` |
| Tamanho mínimo (10px) | ✅ | `Math.max(width, 10)` em `updateResize()` |
| Snap ao redimensionar | ✅ | `snapToGrid(width/height)` em `updateResize()` |
| Feedback visual durante resize | ⚠️ Parcial | Igual ao drag: overlay move; iframe só atualiza em `endResize` |

### Context Menu no Canvas (`CanvasContextMenu.vue`, `HTMLCanvas.vue`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Clique direito abre menu | ✅ | `@contextmenu.prevent="onContextMenu"` em `HTMLCanvas.vue` linha 7 |
| Menu com 4 ações | ✅ | Mapear Campo, Converter para Tabela, Marcar Texto Estático, Remover |
| Mapear Campo | ⚠️ Parcial | Abre painel "fields" via `editorStore.openPanel('fields')` mas não navega diretamente ao campo correspondente |
| Converter para Tabela | ✅ | `templateStore.convertToTable()` + `patchConvertNodeToTable()` |
| Marcar como Texto Estático | ✅ | `updateNodeProperty(id, 'type', 'static')` |
| Remover Elemento | ✅ | `templateStore.removeNode()` |
| Fechar com Escape | ✅ | `_onDocumentKeyForCtxMenu` |
| Fechar com clique fora | ✅ | `_onDocumentClickForCtxMenu` |
| Menu NÃO aparece em área vazia | ✅ | `onContextMenu` retorna se `getNodeAtScreenPosition` retornar null |

### Undo/Redo (`templateStore.ts`, `EditorLayout.vue`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Ctrl+Z — Undo | ✅ | `EditorLayout.vue` linha 135: global keydown listener → `templateStore.undoLastAction()` |
| Ctrl+Y — Redo | ❌ | Não implementado; `undoStack` existe mas não há `redoStack` |
| Undo stack (max 20) | ✅ | `UNDO_MAX = 20` em `templateStore.ts` |
| Undo para moveElement | ✅ | `pushUndoSnapshot()` chamado antes |
| Undo para resizeElement | ✅ | `pushUndoSnapshot()` chamado antes |
| Undo para removeNode | ✅ | `pushUndoSnapshot()` chamado antes |
| Undo para addNode | ✅ | `pushUndoSnapshot()` chamado antes |

### Clipboard e Duplicate (`useClipboard.ts`, `useCanvasKeyboard.ts`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Ctrl+C — Copiar | ✅ | `copySelection()` via `useClipboard` |
| Ctrl+V — Colar | ✅ | `pasteFromClipboard()` via `useClipboard` |
| Ctrl+D — Duplicar | ✅ | `duplicateNode()` + offset +10px |
| Multi-seleção copy/paste | ✅ | `multiSelection` Set suportado em `copySelection` |
| Paste com posição relativa | ✅ | Calcula posição relativa ao `minX/minY` do grupo |

### Keyboard Navigation (`useCanvasKeyboard.ts`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Arrow keys — mover 1px | ✅ | |
| Shift+Arrow — mover gridSize | ✅ | |
| Alt+Arrow — redimensionar 1px | ✅ | |
| Delete/Backspace — remover | ✅ | Guard para input/textarea/select |
| Tab/Shift+Tab — navegar entre elementos | ❌ | Não implementado (GAP 9 do gap-analysis-v3) |
| Ctrl+A — selecionar tudo | ❌ | Não implementado |

### Grouping/Ungroup (`useGrouping.ts`)

| Feature | Status | Observação |
|---------|--------|-----------|
| `createGroup(nodeIds)` | ✅ | Usa `templateStore.groupNodes()`, marca com `isGroup=true` |
| `ungroupNode(groupNodeId)` | ✅ | Move filhos para pai do grupo, remove grupo |
| `moveGroup(groupId, dx, dy)` | ✅ | Aplica delta a todos os filhos |
| `resizeGroup` proporcional | ✅ | Escala filhos proporcionalmente |
| UI para agrupar no Canvas | ❌ | `useGrouping` existe mas sem trigger via seleção multi no Canvas; disponível via Árvore |

### Regra: Canvas NÃO cria elementos novos

✅ Confirmado — `onFieldDrop` no `HTMLCanvas.vue` faz mapeamento de campos, não criação de novos nós estruturais.

---

## Backend — Status de Implementação

Nenhum endpoint de backend é necessário para as interações locais do Canvas. O backend fornece o HTML inicial via `loadTemplateDraft`. Todas as interações de drag, resize, seleção e undo operam no store local.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Redo (Ctrl+Y) não implementado — apenas Undo | 🟡 Importante | Frontend | `templateStore.ts`, `EditorLayout.vue` |
| 2 | Tab/Shift+Tab navegação entre elementos no Canvas | 🟢 Menor | Frontend | `useCanvasKeyboard.ts`, GAP 9 gap-analysis-v3 |
| 3 | Ctrl+A selecionar tudo no Canvas | 🟢 Menor | Frontend | `useCanvasKeyboard.ts` |
| 4 | "Mapear Campo" no context menu não navega ao campo específico — apenas abre painel Fields | 🟢 Menor | Frontend | `HTMLCanvas.vue` `handleCtxMapField()` |
| 5 | UI de Grouping não disponível via Canvas — só via Árvore; sem atalho de teclado para agrupar | 🟢 Menor | Frontend | `useGrouping.ts`, ausência de handler no Canvas |
| 6 | Feedback visual de drag/resize em tempo real: iframe só atualiza ao soltar | 🟢 Menor | Frontend | `useCanvasInteraction.ts` endDrag/endResize |
| 7 | Shift+Click range selection simplificado — não seleciona elementos entre dois pontos, apenas adiciona ao Set | 🟢 Menor | Frontend | `useCanvasInteraction.ts` selectElement() |

---

## Backlog Gerado

1. **Implementar Redo (Ctrl+Y)** — Adicionar `redoStack` ao `templateStore`, popular em `undoLastAction()`, consumir com novo `redoAction()`. Adicionar listener Ctrl+Y no `EditorLayout.vue`. Escopo: `frontend/src/stores/templateStore.ts`, `frontend/src/layouts/EditorLayout.vue`.

2. **Implementar Tab/Shift+Tab navigation** — Em `useCanvasKeyboard.ts`, ao pressionar Tab: encontrar próximo nó na ordem do flat map; Shift+Tab: anterior. Escopo: `frontend/src/composables/useCanvasKeyboard.ts`.

3. **Implementar Ctrl+A — selecionar todos os elementos visíveis** — Em `useCanvasKeyboard.ts`, registrar todos os IDs do `templateStore.flatNodes` no `multiSelection`. Escopo: `frontend/src/composables/useCanvasKeyboard.ts`.

4. **Melhorar "Mapear Campo" do context menu** — Ao abrir FieldNavigator, pré-selecionar o campo mais próximo do `nodeId` clicado (usar `confidenceStore` ou busca por nome). Escopo: `frontend/src/organisms/HTMLCanvas.vue`.

5. **Adicionar atalho de teclado para Group/Ungroup** — Ctrl+G para agrupar seleção múltipla, Ctrl+Shift+G para desagrupar. Integrar `useGrouping` ao `useCanvasKeyboard`. Escopo: `frontend/src/composables/useCanvasKeyboard.ts`.
