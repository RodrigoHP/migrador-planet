# Auditoria: Snap & Alignment

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

### Spec Completa de Snap (`template_editor_snap_behavior.md`)

A spec define múltiplos modos de snap simultâneos:

| Modo | Descrição |
|------|-----------|
| **4.1 Grid Snap** | Alinhamento a grade invisível configurável |
| **4.2 Element Snap** | Snap às bordas e centros de outros elementos |
| **4.3 Column Snap** | Guias de colunas detectadas do PDF pelo pipeline |
| **4.4 Margin Snap** | Snap às margens da página |
| **4.5 Center Snap** | Snap ao centro vertical/horizontal |

**Seção 5 — Snap Lines visuais:** linhas guia temporárias durante drag (vertical e horizontal).

**Seção 6 — Snap Configuration:** toggle ON/OFF na toolbar; opções: Snap to Grid, Snap to Elements, Snap to Columns, Snap to Margins.

**Seção 12 — Snap Distance Threshold:** `snapThreshold = 8px` — snap ativa apenas quando elemento está dentro dessa distância.

**Seção 13 — Smart Snap:** usa Layout Skeleton detectado do PDF (colunas, linhas, regiões).

**Seção 14 — Snap Interaction Flow:** durante drag → verifica âncoras próximas → dentro do threshold → linha aparece → elemento alinha.

### Wireframes Mid-Fi (`wireframes-mid-fi.md`)
- **Snap** — toggle de alinhamento magnético na toolbar (`🧲 Snap`), **ativo por padrão**
- Ao arrastar/redimensionar no Canvas, alinha às linhas de grade, colunas detectadas e bordas de outros elementos
- Toolbar: `[ 🗺️ Cobertura ] [ 🔀 Diff ] [ 🧲 Snap ] [ 🔧 Auto Fix ] [ 💾 Salvar ] [ 📦 Exportar ]`
- Componente `SnapGuides` listado na hierarquia do Canvas no wireframe

---

## Frontend — Status de Implementação

### Toggle Snap na Toolbar (`TopToolbar.vue`, `editorStore.ts`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Botão Snap na toolbar | ✅ | `TopToolbar.vue` linha 68–71: `:active="editorStore.snapEnabled"`, `@click="editorStore.toggleSnap()"` |
| Estado persistido em store | ✅ | `editorStore.snapEnabled` (ref, padrão `false`) |
| Ativo por padrão | ❌ | Spec: "ativo por padrão"; código: `snapEnabled = ref<boolean>(false)` — inicia desabilitado |
| Grid size configurável | ✅ | `editorStore.gridSize = ref<number>(8)` com `setGridSize(size)` |

### Snap to Grid (`useCanvasInteraction.ts`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Snap to grid durante drag | ✅ | `snapToGrid(value)` usa `currentGridSize` (8px padrão) |
| Snap to grid durante resize | ✅ | `snapToGrid(width/height)` em `updateResize()` |
| Grade invisível configurável | ✅ | `editorStore.gridSize` (8, 16, 24px) |
| Threshold de grid snap | ✅ | `SNAP_THRESHOLD = 8` aplicado ao delta de grid |

### Snap to Other Elements (`useCanvasInteraction.ts`)

| Feature | Status | Observação |
|---------|--------|-----------|
| Snap às bordas de outros elementos | ✅ | `calcSnapLines()` itera sobre `elementBoxes` e verifica borda esquerda/direita (vertical) e topo/base (horizontal) |
| Snap ao centro de outros elementos | ❌ | Apenas bordas verificadas; centros dos outros elementos não são candidatos |
| Threshold elemento snap | ✅ | `SNAP_THRESHOLD = 8px` — mesmo valor da spec |
| Element boxes registradas | ✅ | `registerElementBox()` e `updateSelectionBox()` populam `elementBoxes` Map |

### Snap Lines Visuais

| Componente | Arquivo | Status | Observação |
|-----------|---------|--------|-----------|
| `SnapLineOverlay.vue` | `frontend/src/components/SnapLineOverlay.vue` | ✅ | SVG com linhas dashed magenta (#ff00ff) + labels de distância em px |
| `CanvasSnapLines.vue` | `frontend/src/organisms/CanvasSnapLines.vue` | ✅ | SVG alternativo com linhas dashed azul (#2563eb), sem labels |
| Exibição durante drag | ✅ | `activeSnapLines` computed: retorna `dragState.snapLines` quando `isDragging && snapEnabled` |
| Linhas aparecem no overlay | ✅ | `CanvasSelectionOverlay.vue` renderiza linhas via template `v-if="showSnapLines"` |
| Snap lines durante resize | ❌ | `activeSnapLines` só retorna linhas quando `isDragging`; resize não gera snap lines visuais |

**Nota:** Dois componentes de snap lines existem (`SnapLineOverlay.vue` e `CanvasSnapLines.vue`) com estilos visuais diferentes. `CanvasSnapLines.vue` não está referenciado em `HTMLCanvas.vue`; `CanvasSelectionOverlay.vue` renderiza as linhas inline sem usar nenhum dos dois componentes externos.

### Column Position Guides (Snap 4.3 — Column Snap)

| Feature | Status | Observação |
|---------|--------|-----------|
| Array `columnPositions` existe no HTMLCanvas | ✅ | `HTMLCanvas.vue` linha 268: `const columnPositions: number[] = []` |
| `columnPositions` populado com dados reais | ❌ | Array **sempre vazio** — nunca recebe dados do backend/store |
| Column guides renderizados | ❌ | Passado como prop mas sem dados; GAP 8 do gap-analysis-v3 |
| Snap às colunas detectadas | ❌ | `calcSnapLines()` não consulta `columnPositions` do store |

### Margin Snap (Snap 4.4)

| Feature | Status | Observação |
|---------|--------|-----------|
| Snap às margens da página | ❌ | Não implementado em `calcSnapLines()` |

### Center Snap (Snap 4.5)

| Feature | Status | Observação |
|---------|--------|-----------|
| Snap ao centro vertical/horizontal do elemento móvel | ❌ | `calcSnapLines()` não verifica centros dos outros elementos como âncoras |

### Ferramentas de Alinhamento (`useAlignmentTools.ts`)

| Função | Status | Cobertura |
|--------|--------|-----------|
| `alignLeft(boxes)` | ✅ | Alinha bordas esquerdas ao mínimo X |
| `alignCenterH(boxes)` | ✅ | Alinha centros horizontais à média |
| `alignRight(boxes)` | ✅ | Alinha bordas direitas ao máximo X+width |
| `alignTop(boxes)` | ✅ | Alinha bordas superiores ao mínimo Y |
| `alignMiddleV(boxes)` | ✅ | Alinha centros verticais à média |
| `alignBottom(boxes)` | ✅ | Alinha bordas inferiores ao máximo Y+height |
| `distributeH(boxes)` | ✅ | Distribui horizontalmente com espaçamento igual |
| `distributeV(boxes)` | ✅ | Distribui verticalmente com espaçamento igual |
| UI de alignment tools na toolbar/inspector | ❌ | Funções existem mas não há botões de UI expostos ao usuário |

---

## Backend — Status de Implementação

O backend deveria fornecer `columnPositions` (posições de colunas detectadas pelo pipeline de visão) para o `HTMLCanvas`. Esse dado não está sendo entregue ao frontend. O `stage3_structural_analysis.py` ou `stage5_template_generation.py` poderia incluir `column_positions: number[]` no payload de resposta ao frontend.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Snap desabilitado por padrão (`false`) — spec define "ativo por padrão" | 🟡 Importante | Frontend | `editorStore.ts` linha 24 |
| 2 | `columnPositions` sempre vazio — Column Snap (4.3) não funciona | 🟡 Importante | Backend+Frontend | `HTMLCanvas.vue` linha 268, GAP 8 gap-analysis-v3 |
| 3 | Snap lines visuais ausentes durante resize — apenas durante drag | 🟡 Importante | Frontend | `useCanvasInteraction.ts` `activeSnapLines` |
| 4 | Center Snap (4.5) não implementado — outros elementos não são âncoras de centro | 🟢 Menor | Frontend | `useCanvasInteraction.ts` `calcSnapLines()` |
| 5 | Margin Snap (4.4) não implementado | 🟢 Menor | Frontend | `useCanvasInteraction.ts` `calcSnapLines()` |
| 6 | UI de ferramentas de alinhamento não exposta — funções existem mas sem botões | 🟡 Importante | Frontend | `useAlignmentTools.ts`, ausente em TopToolbar/Inspector |
| 7 | `CanvasSnapLines.vue` existe mas não está usado no `HTMLCanvas.vue` — componente órfão | 🟢 Menor | Frontend | `organisms/CanvasSnapLines.vue` |
| 8 | Dois componentes de snap lines com estilos divergentes — `SnapLineOverlay.vue` (magenta + labels) vs inline no overlay (sem labels) | 🟢 Menor | Frontend | `components/SnapLineOverlay.vue`, `CanvasSelectionOverlay.vue` |

---

## Backlog Gerado

1. **Corrigir padrão do Snap para `true`** — Alterar `snapEnabled = ref<boolean>(false)` para `ref<boolean>(true)` no `editorStore.ts`. Escopo: `frontend/src/stores/editorStore.ts`.

2. **Integrar `columnPositions` do backend** — Pipeline (`stage3_structural_analysis.py` ou `stage5`) deve incluir `column_positions: number[]` no payload. Frontend (`HTMLCanvas.vue`) deve receber do store e popular `columnPositions`. `calcSnapLines()` deve verificar essas posições como âncoras adicionais. Escopo: backend + `frontend/src/stores/generation.ts` + `useCanvasInteraction.ts`.

3. **Adicionar snap lines durante resize** — Modificar `activeSnapLines` computed para retornar linhas também durante `isResizing`. Calcular snap lines com base no `selectionState.boundingBox` atual em `updateResize()`. Escopo: `frontend/src/composables/useCanvasInteraction.ts`.

4. **Adicionar Center Snap** — Em `calcSnapLines()`, incluir `box.x + box.width/2` e `box.y + box.height/2` dos outros elementos como candidatos de snap. Escopo: `frontend/src/composables/useCanvasInteraction.ts`.

5. **Expor ferramentas de alinhamento na UI** — Adicionar botões de alignment (alinhar esquerda, centro, direita, topo, base, distribuir) na TopToolbar ou Inspector quando `multiSelection.size > 1`. Usar funções de `useAlignmentTools.ts` para calcular deltas e aplicar via `templateStore.moveElement()`. Escopo: `frontend/src/organisms/TopToolbar.vue` ou `frontend/src/organisms/InspectorPanel.vue`.

6. **Consolidar componentes de snap lines** — Decidir entre `CanvasSnapLines.vue` e o rendering inline do `CanvasSelectionOverlay.vue`. Remover o órfão ou integrar o componente dedicado. Escopo: `frontend/src/organisms/CanvasSnapLines.vue`, `frontend/src/organisms/CanvasSelectionOverlay.vue`.
