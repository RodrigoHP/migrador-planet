# Epic 37 — Tech Debt Epics 33-36 ✅ DONE

**Status:** Done (2026-04-08) — PR #60 mergeado
**Nota:** Este epic foi reutilizado para 3 stories de tech-debt. As 8 stories originais de Canvas UX Polish foram renumeradas para **Epic 39** (`epic-39-canvas-ux-polish.md`).

## Stories Executadas

| Story | Titulo | Status |
|-------|--------|--------|
| 37.1 | Testes MonacoTabsInner.vue | Done |
| 37.2 | Expandir testes DiffViewer.vue | Done |
| 37.3 | Type safety DiffViewer/session/coverageStore | Done |

---

## ~~Plano Original (DESCARTADO — movido para Epic 39)~~

~~**Prioridade:** P2~~
~~**Fase:** 3~~
~~**Estimativa:** 8 stories~~
~~**Dependências:** Epic 33 (inspector loop — patches precisam funcionar)~~
~~**Objetivo:** Polimento da experiência de edição visual: redo, snap completo, zoom consistente, ferramentas de alinhamento e guias visuais acessíveis.~~

---

## Contexto

Redo não existe, snap está desabilitado por padrão, column snap nunca funciona (array vazio), snap lines ausentes durante resize, ferramentas de alinhamento existem sem botões na UI, zoom inconsistente entre composables, mousewheel ausente, guias visuais sem toggle na toolbar.

---

## Stories

### 37.1 — Implementar Redo (Ctrl+Y)
**Gap:** I9
**Escopo:** Frontend (`templateStore.ts`, `EditorLayout.vue`)
**AC:**
- [ ] `redoStack` adicionado ao templateStore (max 20, mesmo que undoStack)
- [ ] `undoLastAction()` move snapshot para `redoStack`
- [ ] `redoAction()` move snapshot de volta, aplica estado
- [ ] Ctrl+Y registrado em `EditorLayout.vue` global keydown listener
- [ ] Redo limpo quando nova mutação ocorre (comportamento padrão)
- [ ] Teste: move elemento → Ctrl+Z → Ctrl+Y → elemento volta à posição movida

### 37.2 — Snap habilitado por padrão
**Gap:** I10
**Escopo:** Frontend (`editorStore.ts`)
**AC:**
- [ ] `snapEnabled = ref<boolean>(true)` (era `false`)
- [ ] Ao abrir editor pela primeira vez, snap já está ativo
- [ ] Toggle na toolbar reflete estado correto
- [ ] Arrastar elemento mostra snap lines imediatamente

### 37.3 — Column Snap funcional com dados do backend
**Gap:** I11
**Escopo:** Backend + Frontend
**AC:**
- [ ] Pipeline (stage3 ou stage5) inclui `column_positions: number[]` no payload de resultado
- [ ] `generationStore` ou `layoutStore` armazena posições de colunas por Layout Type
- [ ] `HTMLCanvas.vue` popula `columnPositions` do store (não array vazio)
- [ ] `calcSnapLines()` verifica `columnPositions` como âncoras adicionais
- [ ] Snap ativa ao arrastar elemento perto de coluna detectada

### 37.4 — Snap lines durante resize
**Gap:** I12
**Escopo:** Frontend (`useCanvasInteraction.ts`)
**AC:**
- [ ] `activeSnapLines` retorna linhas quando `isResizing` (não só `isDragging`)
- [ ] `updateResize()` calcula snap lines baseado no bounding box atual
- [ ] Linhas visuais aparecem durante resize
- [ ] Snap to grid funciona durante resize com feedback visual

### 37.5 — Verificar cobertura das ferramentas de alinhamento existentes
**Gap:** I13
**Escopo:** Frontend (`HTMLCanvas.vue`, `InspectorPanel.vue`)
**QA Note:** **Já implementado** em `HTMLCanvas.vue` como floating toolbar com 6 align + 2 distribute. Verificar se cobertura é suficiente ou se precisa botões também no Inspector.
**AC:**
- [ ] Verificar que floating toolbar em `HTMLCanvas.vue` aparece quando `multiSelection.size > 1`
- [ ] Confirmar 6 alinhamentos (esquerda, centro H, direita, topo, centro V, base) + 2 distribuições (H, V)
- [ ] Avaliar se botões adicionais no InspectorPanel são necessários para acessibilidade
- [ ] Se necessário: adicionar botões no Inspector duplicando chamadas a `useAlignmentTools.ts`
- [ ] Resultado aplicado via `templateStore.moveElement()` com undo snapshot

### 37.6 — Mousewheel zoom + atalhos de teclado
**Gap:** I38
**Escopo:** Frontend (`useZoom.ts`, `useCanvas.ts`, `HTMLCanvas.vue`)
**QA Note:** ZOOM_MAX **já está correto** (125 canvas, 200 PDF). Gap real é mousewheel e atalhos de teclado ausentes.
**AC:**
- [ ] Ctrl+scroll no Canvas → `useCanvas.setZoom()` incrementa/decrementa por ZOOM_STEP
- [ ] Zoom suave (sem saltos bruscos)
- [ ] Ctrl++ e Ctrl+- como atalhos de teclado registrados em `EditorLayout.vue`
- [ ] ZOOM_MAX mantido: 125% para Canvas, 200% para PDF (já correto — não alterar)

### 37.7 — Toggle "Mostrar Guias" na toolbar (apenas botão)
**Gap:** I39
**Escopo:** Frontend (`TopToolbar.vue`)
**QA Note:** `showGuides` state e `CanvasGuides.vue` **já existem**. Falta apenas o botão na TopToolbar.
**AC:**
- [ ] Adicionar botão com ícone de régua/grade no grupo de toggles da TopToolbar
- [ ] Botão liga/desliga `editorStore.showGuides` (state já existe)
- [ ] `CanvasGuides.vue` já renderiza guias — verificar que funciona ao toggle
- [ ] Estado visual do botão reflete `editorStore.showGuides`

### 37.8 — Renomeação de Layout Types
**Gap:** I37
**Escopo:** Frontend (`LayoutSelector.vue`, `layout.ts`)
**AC:**
- [ ] Duplo-clique no nome do Layout Type no LayoutSelector → campo editável inline
- [ ] Ou: ícone de lápis ao lado do nome
- [ ] Nome customizado persiste no `layoutStore` e no save do projeto
- [ ] Nome exibido em todos os locais que referenciam o Layout Type (toolbar, árvore, coverage popover)
- [ ] Nome padrão permanece "A", "B", "C" se não renomeado
