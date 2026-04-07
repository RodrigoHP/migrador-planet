# Gap Analysis v3 — Frontend: Spec vs Implementação Atual

**Data:** 2026-04-07
**Autor:** Análise automatizada (Claude Code)
**Contexto:** Atualização do gap analysis v2 com novo GAP crítico (#4 — Nomes genéricos na árvore) confirmado por screenshot real do editor. Este documento reflete o estado real do código comparado com as specs em `docs/ideias/ux/` e `docs/wireframes/wireframes-mid-fi.md`.

**Resultado geral: ~88% implementado, mas com 4 gaps estruturais críticos.**

---

## GAPS ENCONTRADOS (o que NÃO está implementado conforme spec)

---

### GAP 1 — Pipeline de Regeneração HTML (CRÍTICO)

**O que a spec define:**
- `docs/ideias/ux/editor_architecture_spec.md` (seções 4, 13):
  ```
  Template Structure JSON → HTML Generator → Canvas Renderer
  ```
- Qualquer edição na árvore de estrutura ou no inspector deve regenerar o HTML automaticamente e o Canvas atualizar em tempo real.

**O que o código faz:**
- `frontend/src/stores/generation.ts` — O `generationStore` apenas **recebe** HTML pré-gerado do backend via `loadTemplateDraft()`. Não existe nenhuma função `generateHTML()`, `renderTemplate()` ou `buildHTML()` no frontend.
- `frontend/src/organisms/HTMLCanvas.vue` (linhas 268-298) — Usa `DOMParser` apenas para **dividir** o HTML em páginas por `data-layout-type`, não para gerar HTML.
- `frontend/src/organisms/HTMLCanvas.vue` (linhas 493-502) — Watch em `generationStore.templateDraft` faz full re-render, mas este só dispara quando o backend envia novo HTML.

**Consequência:**
- Editar propriedades via Inspector ou mover elementos no Canvas atualiza o `templateStore` mas **o iframe continua mostrando HTML antigo**. O loop "editar → ver resultado" está quebrado para edições locais sem round-trip ao backend.

**Arquivos envolvidos:**
- `frontend/src/stores/generation.ts` — Precisa de lógica de geração ou trigger para backend
- `frontend/src/stores/templateStore.ts` — Mutações (moveNode, updateNodeProperty, etc.) não disparam regeneração
- `frontend/src/organisms/HTMLCanvas.vue` — Sem watcher em templateStore

---

### GAP 2 — Code → Structure Parser (CRÍTICO)

**O que a spec define:**
- `docs/ideias/ux/editor_architecture_spec.md` (seção 13):
  ```
  Code Mode: HTML edit → HTML Parser → Structure Update → Canvas render
  ```
- `docs/wireframes/wireframes-mid-fi.md` (Aba Código, anotações):
  > "Sincronização bidirecional — editar no código atualiza a estrutura (stores); editar na estrutura/inspetor regenera o código"

**O que o código faz:**
- `frontend/src/organisms/MonacoTabsInner.vue` — Edições no Monaco salvam no `codeStore.setFileContent()` mas **NÃO disparam atualização do templateStore**.
- Não existe nenhuma função `parseHTML()`, `htmlToTree()` ou similar no frontend.
- O `DOMParser` em `HTMLCanvas.vue` (linha 276) é usado **apenas** para split de páginas, não para parsing de estrutura.

**Consequência:**
- Editar HTML no Code Editor e editar a árvore de estrutura são ações **semi-independentes**. Mudanças no código não refletem na árvore nem no Canvas (a menos que o backend processe).

**Arquivos envolvidos:**
- `frontend/src/organisms/MonacoTabsInner.vue` — Precisa de trigger para parser
- Não existe: parser HTML → TreeNode (precisa ser criado ou delegado ao backend)
- `frontend/src/stores/codeStore.ts` — Não conecta com templateStore

---

### GAP 3 — Canvas Incremental Updates (CRÍTICO)

**O que a spec define:**
- `docs/ideias/ux/canvas_complete_spec.md` (seções 8-9, 15):
  ```
  User drags element → Editor updates template.json → HTML generator runs → Canvas re-renders
  ```

**O que o código faz:**
- `frontend/src/stores/templateStore.ts` — `moveNode()`, `updateNodeProperty()`, `updateNodeProperties()` atualizam o estado mas **não há watcher no HTMLCanvas que observe essas mudanças**.
- `frontend/src/organisms/HTMLCanvas.vue` (linhas 493-545) — Watchers existentes:
  - `generationStore.templateDraft` → full re-render (OK, mas precisa ser disparado)
  - `editorStore.selectedElementId` → apenas scroll
  - `layoutStore.pendingScrollToLayout` → apenas scroll
  - **Nenhum watcher em `templateStore`** para detectar mudanças de propriedades
- `frontend/src/composables/useCanvasInteraction.ts` — `endDrag()` e `endResize()` chamam `templateStore.moveElement()`/`resizeElement()` mas o resultado visual **não aparece no Canvas**.

**Consequência:**
- Arrastar um elemento muda os dados no store mas a posição visual no iframe permanece inalterada. O usuário não vê o resultado da sua ação.

**Arquivos envolvidos:**
- `frontend/src/organisms/HTMLCanvas.vue` — Precisa de watcher em templateStore ou mecanismo de update incremental
- `frontend/src/composables/useCanvasInteraction.ts` — `endDrag()` e `endResize()` precisam disparar re-render
- `frontend/src/stores/generation.ts` — Precisa regenerar HTML após mutações no templateStore

---

### GAP 4 — Nomes Genéricos na Árvore de Estrutura (CRÍTICO — UX)

**O que a spec define:**
- `docs/wireframes/wireframes-mid-fi.md` (Anotações do Painel Esquerdo — Aba "Estrutura"):
  ```
  📄 Document
  ├ 📦 Header
  │ ├ 🖼 Logo
  │ ├ 🔤 Cliente → {{cliente}}
  │ └ 🔤 CPF → {{cpf}}
  ├ 📦 Flow
  │ ├ 📋 Tabela movimentos → {{movimentos}}
  │ │ ├ data
  │ │ ├ descricao
  │ │ └ valor
  │ ├ 📊 Gráfico vendas → {{vendasMensais}}
  │ └ 🔤 Total → {{valorTotal}}
  └ 📦 Footer
    └ 🔤 Página → {{pageNum}}
  ```
- Os nomes devem ser **semânticos e legíveis** pelo operador: "Cliente", "CPF", "Tabela movimentos", "Gráfico vendas"
- Bindings devem aparecer ao lado: `→ {{campo}}`
- Seções devem ter nomes descritivos: "Dados do Sacado", "Valores", "Código de Barras"
- `docs/ideias/ux/template_structure_view_spec.md` (seções Element Types, Binding Display):
  > "Binding Display: Cliente → {{cliente}}, CPF → {{cpf}}, Table movimentos → {{movimentos}}"

**O que o código faz:**
- `frontend/src/molecules/StructureTreeNode.vue` (linha 37):
  ```html
  <span class="structure-tree-node__name">{{ node.name || node.type }}</span>
  ```
  O componente frontend está correto — mostra `name` e faz fallback para `type`.

- **O problema é na origem dos dados.** O pipeline/backend popula `TreeNode.name` com o **mesmo valor do `type`** (ou não popula). Resultado visível na interface:
  ```
  📄 document
  ├ 📄 page
  │ ├ 📦 header                    0/1
  │ ├ 📦 flow                      0/66
  │ │ ├ 📦 section                 0/4
  │ │ ├ 📦 section                 0/14
  │ │ │ ├ abc label
  │ │ │ ├ abc field
  │ │ │ │ ├ abc label
  │ │ │ │ └ abc value
  │ │ │ ├ ~ likely_dynamic
  │ │ │ ├ ~ likely_dynamic
  │ │ │ ├ ~ likely_dynamic
  ```

**Problemas concretos observados (screenshot real de "Boleto Bancário"):**
1. **Nomes genéricos repetidos** — "label" aparece 4+ vezes sem distinção. "section" aparece 2x. Operador não sabe qual é qual.
2. **"likely_dynamic" exposto cru** — Tipo interno do pipeline exibido como nome. Deveria mostrar o texto detectado no PDF (ex: "R$ 1.500,00")
3. **Sem nomes semânticos** — Deveria ser "Cedente", "CNPJ", "Valor", "Vencimento". Mostra "label", "value", "field".
4. **"page" como nível** — A spec tem Document > Header/Flow/Footer. O pipeline gera um nível "page" intermediário não especificado.
5. **Nenhum binding exibido** — Todos os pontos são vermelhos (unbound). Sem `→ {{campo}}` ao lado.
6. **Coverage 0/66** — Nada mapeado, possivelmente porque nomes genéricos dificultam auto-mapping.

**Onde corrigir:**
- **Backend/Pipeline** — O stage que gera o `DocumentTree` precisa:
  1. Extrair texto real do PDF para usar como `node.name` (ex: detectar "Cliente:" e nomear o nó "Cliente")
  2. Renomear `likely_dynamic` para o texto detectado ou um nome descritivo
  3. Dar nomes únicos a seções (ex: "Seção Dados Pessoais", "Seção Valores")
  4. Remover ou aplanar o nível `page` se não faz parte da spec
  5. Tentar auto-bind com campos do XSD baseado em proximidade semântica
- **Frontend** — O componente `StructureTreeNode.vue` já está correto. Nenhuma mudança necessária no frontend.

**Arquivos envolvidos (investigar no backend):**
- Pipeline stage que gera `DocumentTree` (stage de Mapeamento ou Semântica)
- Endpoint que entrega a árvore ao frontend
- `frontend/src/types/template.types.ts` — Tipo `TreeNode` (referência para contrato)

---

### GAP 5 — Console/Warnings Panel (IMPORTANTE)

**O que a spec define:**
- `docs/wireframes/wireframes-mid-fi.md` (seção 8, Bottom Panel):
  ```
  Console / Warnings
  ⚠ Field telefone not mapped
  ⚠ Table header inconsistent
  ⚠ Chart data source missing
  ```
- `docs/ideias/ux/template_editor_main_screen_spec.md` (seção 8):
  > Displays detected issues em tempo real durante edição.

**O que o código faz:**
- Bottom panel tem apenas `TestDataPanel.vue` e `TestReportPanel.vue`.
- Não existe `ConsolePanel`, `WarningsPanel` ou `DiagnosticsPanel`.
- `AnalyzingPage.vue` tem um `pipeline-warnings-banner` mas isso é só na tela de progresso, não no editor.

**Arquivos envolvidos:**
- `frontend/src/layouts/EditorLayout.vue` — Precisa de nova aba no bottom panel
- Não existe: componente ConsolePanel (precisa ser criado)

---

### GAP 6 — Canvas Context Menu / Clique Direito (IMPORTANTE)

**O que a spec define:**
- `docs/ideias/ux/template_editor_main_screen_spec.md` (seção 4):
  ```
  Right click menu:
    Map field
    Convert to table
    Mark as static text
    Remove element
  ```

**O que o código faz:**
- `frontend/src/organisms/StructureTree.vue` — Tem context menu completo (Add, Group, Duplicate, Remove, Move to), mas **apenas na árvore**.
- `frontend/src/organisms/HTMLCanvas.vue` — **Não tem handler para `contextmenu`**. Não existe menu de clique direito no canvas.
- `frontend/src/organisms/CanvasSelectionOverlay.vue` — Também sem contextmenu.

**Arquivos envolvidos:**
- `frontend/src/organisms/HTMLCanvas.vue` — Precisa de handler contextmenu
- `frontend/src/organisms/CanvasSelectionOverlay.vue` — Ou aqui
- Reaproveitar lógica do StructureTree context menu

---

### GAP 7 — AnalyzingPage Divergente (MENOR — NÃO É GAP REAL)

**O que a spec define:**
- `docs/wireframes/wireframes-mid-fi.md` (Estado Analyzing): 8 blocos com 23 estágios

**O que o código faz:**
- `frontend/src/pages/analyzingPageConstantsV2.ts` — 5 estágios com 43 sub-steps (Story 13.3 redesenhou de 28 stages granulares para 5 stages substanciais).
- Funcionalidade equivalente, apenas formato diferente.

**Veredicto:** Não é gap real — foi redesenhado intencionalmente na Story 13.3.

---

### GAP 8 — Canvas Column Guides (MENOR)

**O que a spec define:**
- Guides mostrando posições de colunas detectadas pelo pipeline.

**O que o código faz:**
- `frontend/src/organisms/HTMLCanvas.vue` — Array `columnPositions: number[]` existe mas está **sempre vazio** (`[]`). Nunca é populado.

**Arquivos envolvidos:**
- `frontend/src/organisms/HTMLCanvas.vue` — `columnPositions` precisa receber dados do backend/store

---

### GAP 9 — Tab/Shift+Tab Navigation no Canvas (MENOR)

**O que a spec define:**
- Navegação entre elementos via Tab no Canvas.

**O que o código faz:**
- `frontend/src/composables/useCanvasKeyboard.ts` — Suporta Arrow keys, Delete, Ctrl+Z/Y, Ctrl+D, Ctrl+A, Escape. **Não tem Tab/Shift+Tab**.

---

### GAP 10 — FileExplorer Create/Delete/Rename (MENOR — decisão MVP)

**O que a spec define:**
- Gerenciamento completo de arquivos do template.

**O que o código faz:**
- `frontend/src/organisms/FileExplorer.vue` — Footer: "Criar/excluir/renomear: bloqueado (MVP)". Bloqueio intencional.

---

### GAP 11 — Asset Management Completo (MENOR)

**O que a spec define:**
- `docs/ideias/ux/template_editor_main_screen_spec.md` (seção 5, Asset Inspector):
  > Replace image, Remove image, Download asset

**O que o código faz:**
- `frontend/src/organisms/inspectors/ImageInspector.vue` existe com propriedades de imagem, mas upload/replace/download de assets é parcial.

---

## O QUE JÁ ESTÁ IMPLEMENTADO (conforme spec)

Abaixo a lista do que o gap analysis original (v1) listava como faltante e **JÁ FOI IMPLEMENTADO**:

| Componente (gap analysis v1) | Status Atual | Arquivo |
|-------------------------------|-------------|---------|
| EditorLayout (5 regiões) | ✅ Implementado | `layouts/EditorLayout.vue` |
| TopToolbar | ✅ Completo (15.9KB) | `organisms/TopToolbar.vue` |
| StructureTree | ✅ Completo (15.9KB) | `organisms/StructureTree.vue` |
| FieldNavigator | ✅ Completo (14.1KB) | `organisms/FieldNavigator.vue` |
| HTMLCanvas | ✅ Completo (25KB) | `organisms/HTMLCanvas.vue` |
| PDFReference | ✅ Completo (12.4KB) | `organisms/PDFReference.vue` |
| SyncView | ✅ Completo (17.8KB) | `organisms/SyncView.vue` |
| FileExplorer | ✅ Parcial (9KB) | `organisms/FileExplorer.vue` |
| InspectorPanel | ✅ Completo (2.9KB) | `organisms/InspectorPanel.vue` |
| PageInspector | ✅ Implementado | `organisms/inspectors/PageInspector.vue` |
| SectionInspector | ✅ Implementado | `organisms/inspectors/SectionInspector.vue` |
| TableInspector | ✅ Completo (12.4KB) | `organisms/inspectors/TableInspector.vue` |
| ChartInspector | ✅ Completo (18.3KB) | `organisms/inspectors/ChartInspector.vue` |
| ContainerInspector | ✅ Implementado | `organisms/inspectors/ContainerInspector.vue` |
| ImageInspector | ✅ Completo (17.9KB) | `organisms/inspectors/ImageInspector.vue` |
| ElementInspector | ✅ Completo (20.8KB) | `organisms/inspectors/ElementInspector.vue` |
| MultiDocAnalyzer | ✅ Implementado (8.6KB) | `organisms/MultiDocAnalyzer.vue` |
| TestDataPanel | ✅ Completo (22KB) | `organisms/TestDataPanel.vue` |
| TestReportPanel | ✅ Completo (12.3KB) | `organisms/TestReportPanel.vue` |
| DiffViewer | ✅ Completo (14KB) | `organisms/DiffViewer.vue` |
| ConfidencePopover | ✅ Implementado | `organisms/ConfidencePopover.vue` |
| CoveragePopover | ✅ Implementado | `organisms/CoveragePopover.vue` |
| CoverageOverlay | ✅ Implementado | `organisms/CoverageOverlay.vue` |
| SyntheticGenerator | ✅ Completo | `utils/syntheticGenerator.ts` |
| VisibilityControl | ✅ Completo com builder AND/OR | `molecules/VisibilityControl.vue` |
| editorStore | ✅ Completo | `stores/editorStore.ts` |
| templateStore | ✅ Completo com undo | `stores/templateStore.ts` |
| inspectorStore | ✅ Completo | `stores/inspectorStore.ts` |
| coverageStore | ✅ Completo | `stores/coverageStore.ts` |
| confidenceStore | ✅ Completo | `stores/confidenceStore.ts` |
| testDataStore | ✅ Completo | `stores/testDataStore.ts` |
| multiDocStore | ✅ Completo | `stores/multiDocStore.ts` |
| diffStore | ✅ Completo | `stores/diffStore.ts` |
| autoFixStore | ✅ Completo | `stores/autoFixStore.ts` |
| useCanvas | ✅ Completo | `composables/useCanvas.ts` |
| useSync | ✅ Completo | `composables/useSync.ts` |
| useExport | ✅ Completo | `composables/useExport.ts` |
| usePagination | ✅ Completo | `composables/usePagination.ts` |
| useCanvasInteraction | ✅ Completo (18KB) | `composables/useCanvasInteraction.ts` |
| useCanvasKeyboard | ✅ Completo | `composables/useCanvasKeyboard.ts` |
| useAlignmentTools | ✅ Completo | `composables/useAlignmentTools.ts` |

**Moléculas e átomos**: Todos os 15 listados como faltantes no gap analysis v1 foram implementados (StructureTreeNode, FieldNavItem, InspectorField, PositionControl, SizeControl, FontWarning, ZoomControl, Toggle, etc.)

---

## RESUMO FINAL POR CRITICIDADE

### Críticos (loop fundamental de edição quebrado)
| # | Gap | Impacto |
|---|-----|---------|
| 1 | Pipeline HTML Generator no frontend | Edições na árvore não atualizam Canvas |
| 2 | Code → Structure parser | Edições no código não atualizam árvore |
| 3 | Canvas incremental updates | Drag/resize muda store mas Canvas não reflete |
| 4 | Nomes genéricos na Árvore de Estrutura | Operador não consegue navegar/identificar elementos. "label", "field", "likely_dynamic" em vez de "Cliente", "CPF", "Valor". Inutiliza a árvore na prática. |

### Importantes (features significativas da spec)
| # | Gap | Impacto |
|---|-----|---------|
| 5 | Console/Warnings panel | Sem feedback de problemas durante edição |
| 6 | Canvas context menu | Sem acesso rápido a ações no clique direito |

### Menores (polish/UX)
| # | Gap | Impacto |
|---|-----|---------|
| 8 | Column guides (dados vazios) | Sem guias de colunas detectadas |
| 9 | Tab navigation no Canvas | Navegação limitada a arrow keys |
| 10 | FileExplorer CRUD | Decisão MVP intencional |
| 11 | Asset management | Upload/replace parcial |

---

## Changelog v2 → v3

- **Adicionado GAP 4** — Nomes genéricos na Árvore de Estrutura (CRÍTICO — UX). Confirmado por screenshot real do editor mostrando "Boleto Bancário" com nomes tipo "label", "field", "likely_dynamic" em vez de nomes semânticos.
- **Resultado geral** atualizado de "3 gaps críticos" para "4 gaps críticos".
- GAPs renumerados (antigo GAP 4-9 → GAP 5-11).

---

## Nota

Os documentos anteriores permanecem como referência histórica:
- `gap-analysis-frontend.md` (v1, 2026-03-16) — Gap analysis original (~58 items)
- `gap-analysis-frontend-v2.md` (v2, 2026-04-07) — Primeira atualização (3 gaps críticos)
- Este documento (v3) é a **referência atual**.
