# Gap Analysis v2 — Frontend: Spec vs Implementação Atual

**Data:** 2026-04-07
**Autor:** Análise automatizada (Claude Code)
**Contexto:** Atualização do gap analysis original (2026-03-16) que listava ~58 items faltantes. A grande maioria já foi implementada. Este documento reflete o estado real do código.

**Resultado geral: ~88% implementado, com 3 gaps estruturais críticos.**

---

## GAPS ENCONTRADOS

---

### GAP 1 — Pipeline de Regeneração HTML (CRÍTICO)

**Spec:** `docs/ideias/ux/editor_architecture_spec.md` (seções 4, 13)
```
Template Structure JSON → HTML Generator → Canvas Renderer
```
Qualquer edição na árvore/inspector deve regenerar HTML automaticamente e o Canvas atualizar.

**Código:** O `generationStore` (`frontend/src/stores/generation.ts`) apenas **recebe** HTML pré-gerado do backend via `loadTemplateDraft()`. Não existe `generateHTML()`, `renderTemplate()` ou `buildHTML()` no frontend. O `HTMLCanvas.vue` (linhas 268-298) usa `DOMParser` apenas para **dividir** o HTML em páginas por `data-layout-type`.

**Impacto:** Editar propriedades via Inspector ou mover elementos no Canvas atualiza o `templateStore` mas o iframe continua mostrando HTML antigo. O loop "editar → ver resultado" está quebrado para edições locais.

**Arquivos:**
- `frontend/src/stores/generation.ts` — Precisa de lógica de geração ou trigger para backend
- `frontend/src/stores/templateStore.ts` — Mutações não disparam regeneração
- `frontend/src/organisms/HTMLCanvas.vue` — Sem watcher em templateStore

---

### GAP 2 — Code → Structure Parser (CRÍTICO)

**Spec:** `docs/ideias/ux/editor_architecture_spec.md` (seção 13)
```
Code Mode: HTML edit → HTML Parser → Structure Update → Canvas render
```
**Wireframe:** "Sincronização bidirecional — editar no código atualiza a estrutura (stores)"

**Código:** `MonacoTabsInner.vue` salva edições no `codeStore.setFileContent()` mas **não atualiza o templateStore**. Não existe nenhum parser `HTML → TreeNode` no frontend.

**Impacto:** Editar HTML no Code Editor e editar a árvore são ações semi-independentes. Mudanças no código não refletem na árvore.

**Arquivos:**
- `frontend/src/organisms/MonacoTabsInner.vue` — Precisa de trigger para parser
- `frontend/src/stores/codeStore.ts` — Não conecta com templateStore
- Não existe: parser HTML → TreeNode

---

### GAP 3 — Canvas Incremental Updates (CRÍTICO)

**Spec:** `docs/ideias/ux/canvas_complete_spec.md` (seções 8-9, 15)
```
User drags element → Editor updates template.json → HTML generator runs → Canvas re-renders
```

**Código:** `templateStore.moveNode()`, `updateNodeProperty()` atualizam o estado mas **não há watcher no HTMLCanvas que observe essas mudanças**. `useCanvasInteraction.ts` — `endDrag()` e `endResize()` chamam `templateStore.moveElement()`/`resizeElement()` mas o Canvas não reflete.

**Impacto:** Arrastar um elemento muda os dados no store mas a posição visual no iframe permanece inalterada.

**Arquivos:**
- `frontend/src/organisms/HTMLCanvas.vue` — Precisa de watcher ou mecanismo incremental
- `frontend/src/composables/useCanvasInteraction.ts` — endDrag/endResize precisam disparar re-render
- `frontend/src/stores/generation.ts` — Precisa regenerar após mutações

---

### GAP 4 — Console/Warnings Panel (IMPORTANTE)

**Spec:** `docs/wireframes/wireframes-mid-fi.md` (Bottom Panel)
```
⚠ Field telefone not mapped
⚠ Table header inconsistent
⚠ Chart data source missing
```

**Código:** Bottom panel tem `TestDataPanel.vue` e `TestReportPanel.vue`. Não existe `ConsolePanel`, `WarningsPanel` ou `DiagnosticsPanel`.

**Arquivos:**
- `frontend/src/layouts/EditorLayout.vue` — Precisa de nova aba
- Componente ConsolePanel não existe

---

### GAP 5 — Canvas Context Menu (IMPORTANTE)

**Spec:** `docs/ideias/ux/template_editor_main_screen_spec.md` (seção 4)
```
Right click menu: Map field, Convert to table, Mark as static text, Remove element
```

**Código:** `StructureTree.vue` tem context menu completo mas **apenas na árvore**. `HTMLCanvas.vue` e `CanvasSelectionOverlay.vue` não têm handler para `contextmenu`.

**Arquivos:**
- `frontend/src/organisms/HTMLCanvas.vue` ou `CanvasSelectionOverlay.vue` — Precisa handler
- Pode reaproveitar lógica do StructureTree

---

### GAP 6 — Canvas Column Guides (MENOR)

**Spec:** Guides mostrando posições de colunas detectadas.

**Código:** `HTMLCanvas.vue` — Array `columnPositions: number[]` existe mas está sempre vazio.

---

### GAP 7 — Tab/Shift+Tab Navigation no Canvas (MENOR)

**Spec:** Navegação entre elementos via Tab.

**Código:** `useCanvasKeyboard.ts` suporta Arrow keys, Delete, Ctrl+Z/Y, Ctrl+D, Ctrl+A, Escape. Sem Tab/Shift+Tab.

---

### GAP 8 — FileExplorer Create/Delete/Rename (MENOR — decisão MVP)

**Código:** `FileExplorer.vue` — Footer: "Criar/excluir/renomear: bloqueado (MVP)". Intencional.

---

### GAP 9 — Asset Management Completo (MENOR)

**Spec:** Replace image, Remove image, Download asset.

**Código:** `ImageInspector.vue` existe mas upload/replace/download de assets é parcial.

---

## O QUE O GAP ANALYSIS v1 LISTAVA COMO FALTANTE E JÁ FOI IMPLEMENTADO

| Componente | Status | Arquivo |
|-----------|--------|---------|
| EditorLayout (5 regiões) | ✅ | `layouts/EditorLayout.vue` |
| TopToolbar | ✅ (15.9KB) | `organisms/TopToolbar.vue` |
| StructureTree | ✅ (15.9KB) | `organisms/StructureTree.vue` |
| FieldNavigator | ✅ (14.1KB) | `organisms/FieldNavigator.vue` |
| HTMLCanvas | ✅ (25KB) | `organisms/HTMLCanvas.vue` |
| PDFReference | ✅ (12.4KB) | `organisms/PDFReference.vue` |
| SyncView | ✅ (17.8KB) | `organisms/SyncView.vue` |
| FileExplorer | ✅ parcial (9KB) | `organisms/FileExplorer.vue` |
| InspectorPanel | ✅ (2.9KB) | `organisms/InspectorPanel.vue` |
| PageInspector | ✅ | `organisms/inspectors/PageInspector.vue` |
| SectionInspector | ✅ | `organisms/inspectors/SectionInspector.vue` |
| TableInspector | ✅ (12.4KB) | `organisms/inspectors/TableInspector.vue` |
| ChartInspector | ✅ (18.3KB) | `organisms/inspectors/ChartInspector.vue` |
| ContainerInspector | ✅ | `organisms/inspectors/ContainerInspector.vue` |
| ImageInspector | ✅ (17.9KB) | `organisms/inspectors/ImageInspector.vue` |
| ElementInspector | ✅ (20.8KB) | `organisms/inspectors/ElementInspector.vue` |
| MultiDocAnalyzer | ✅ (8.6KB) | `organisms/MultiDocAnalyzer.vue` |
| TestDataPanel | ✅ (22KB) | `organisms/TestDataPanel.vue` |
| TestReportPanel | ✅ (12.3KB) | `organisms/TestReportPanel.vue` |
| DiffViewer | ✅ (14KB) | `organisms/DiffViewer.vue` |
| ConfidencePopover | ✅ | `organisms/ConfidencePopover.vue` |
| CoveragePopover | ✅ | `organisms/CoveragePopover.vue` |
| CoverageOverlay | ✅ | `organisms/CoverageOverlay.vue` |
| SyntheticGenerator | ✅ | `utils/syntheticGenerator.ts` |
| VisibilityControl (AND/OR) | ✅ | `molecules/VisibilityControl.vue` |
| AnalyzingProgress | ✅ (redesenhado: 5 stages, 43 sub-steps) | `pages/AnalyzingPage.vue` |
| editorStore | ✅ | `stores/editorStore.ts` |
| templateStore (com undo) | ✅ | `stores/templateStore.ts` |
| inspectorStore | ✅ | `stores/inspectorStore.ts` |
| coverageStore | ✅ | `stores/coverageStore.ts` |
| confidenceStore | ✅ | `stores/confidenceStore.ts` |
| testDataStore | ✅ | `stores/testDataStore.ts` |
| multiDocStore | ✅ | `stores/multiDocStore.ts` |
| diffStore | ✅ | `stores/diffStore.ts` |
| autoFixStore | ✅ | `stores/autoFixStore.ts` |
| useCanvas | ✅ | `composables/useCanvas.ts` |
| useSync | ✅ | `composables/useSync.ts` |
| useExport | ✅ | `composables/useExport.ts` |
| usePagination | ✅ | `composables/usePagination.ts` |
| useCanvasInteraction (18KB) | ✅ | `composables/useCanvasInteraction.ts` |
| useCanvasKeyboard | ✅ | `composables/useCanvasKeyboard.ts` |
| useAlignmentTools | ✅ | `composables/useAlignmentTools.ts` |
| All 15 moléculas | ✅ | `molecules/` |
| All 4 átomos | ✅ | `atoms/` |

---

## RESUMO POR CRITICIDADE

### Críticos
| # | Gap | Loop afetado |
|---|-----|-------------|
| 1 | Pipeline HTML Generator | Edições na árvore não atualizam Canvas |
| 2 | Code → Structure parser | Edições no código não atualizam árvore |
| 3 | Canvas incremental updates | Drag/resize muda store mas Canvas não reflete |

### Importantes
| # | Gap |
|---|-----|
| 4 | Console/Warnings panel |
| 5 | Canvas context menu |

### Menores
| # | Gap |
|---|-----|
| 6 | Column guides (dados vazios) |
| 7 | Tab navigation no Canvas |
| 8 | FileExplorer CRUD (decisão MVP) |
| 9 | Asset management completo |

---

## NOTA

O gap analysis v1 (`docs/architecture/gap-analysis-frontend.md`, 2026-03-16) está **desatualizado**. Dos 58 items listados como faltantes, a grande maioria foi implementada. Este documento (v2) substitui a versão anterior como referência atual.
