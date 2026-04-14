# Gap Analysis — Frontend: Wireframe v5.3 vs Implementado

**Data:** 2026-03-16
**Autor:** @architect (Aria)
**Contexto:** Análise de gaps entre o wireframe v5.3 (editor unificado) e o frontend atual (paradigma wizard v2.3)

---

## Resumo Executivo

O frontend atual reflete o paradigma wizard v2.3 (5 telas sequenciais). O wireframe v5.3 define um editor unificado com 5 regiões. A diferença é estrutural — ~58 componentes/módulos a criar ou adaptar.

---

## 1. Páginas

| Wireframe v5.3 | Frontend Atual | Status |
|----------------|----------------|--------|
| **HomePage** | `HomePage.vue` | ⚠️ Adaptar (cards Novo + Abrir Projeto) |
| **UploadPage** | `UploadPage.vue` | ⚠️ Adaptar (dropzone dados opcional, hints) |
| **AnalyzingPage** (progresso) | — | ❌ Criar |
| **TemplateEditor** (editor unificado) | — | ❌ Criar |
| ~~CamposPage~~ | `CamposPage.vue` | 🗑️ Obsoleta → aba Campos no editor |
| ~~LayoutPage~~ | `LayoutPage.vue` | 🗑️ Obsoleta → Inspetor |
| ~~GeracaoPage~~ | `GeracaoPage.vue` | 🗑️ Obsoleta → Canvas + Código |
| ~~ExportarPage~~ | `ExportarPage.vue` | 🗑️ Obsoleta → botão Exportar na toolbar |

---

## 2. Templates/Layouts

| Wireframe v5.3 | Frontend Atual | Status |
|----------------|----------------|--------|
| **EditorLayout** (5 regiões) | — | ❌ Criar |
| HomeLayout | `FullWidthLayout.vue` | ✅ Reutilizável |
| UploadLayout | `FullWidthLayout.vue` | ✅ Reutilizável |
| ModalLayout | — | ⚠️ Parcial (BibliotecasModal existe) |
| ~~WizardLayout~~ | `WizardLayout.vue` | 🗑️ Obsoleto |
| ~~SplitPaneLayout~~ | `SplitPaneLayout.vue` | 🗑️ Obsoleto |

---

## 3. Organismos — Novos (a criar)

| Componente | Complexidade | Descrição |
|-----------|-------------|-----------|
| **TopToolbar** | 🔴 Alta | Nome, confiança, cobertura, layout type selector, toggles, salvar, exportar |
| **StructureTree** | 🔴 Alta | Árvore hierárquica Document > Header > Flow > Footer com drag & drop |
| **FieldNavigator** | 🟡 Média | Lista de campos XSD com status |
| **HTMLCanvas** | 🔴 Alta | Iframe WYSIWYG com seleção, drag, resize, overlays, snap, zoom |
| **PDFReference** (aba) | 🟡 Média | PDF.js + overlays cobertura + seletor de documento |
| **SyncView** | 🔴 Alta | Split Canvas + PDF com scroll/seleção sincronizados |
| **FileExplorer** | 🟢 Baixa | Árvore de arquivos do template |
| **InspectorPanel** (router) | 🟡 Média | Switch entre 4 níveis de inspetor |
| **PageInspector** | 🟡 Média | Tamanho, margens, grid, colunas |
| **SectionInspector** | 🟡 Média | Altura, fundo, padding, repetição, visibilidade |
| **TableInspector** | 🟡 Média | Fonte dados, colunas, paginação, âncora |
| **ChartInspector** | 🟡 Média | Tipo, datasets, dimensões, estilo |
| **ContainerInspector** | 🟢 Baixa | Layout, espaçamento, padding |
| **ImageInspector** | 🟢 Baixa | Dimensões, escala, alinhamento, substituir |
| **ElementInspector** | 🟡 Média | Posição, tamanho, tipografia, binding, visibilidade |
| **MultiDocAnalyzer** | 🔴 Alta | Matriz de Variação + detecção automática |
| **TestDataPanel** | 🟡 Média | Lista datasets, validação, aplicar, testar |
| **DatasetList** | 🟢 Baixa | Lista com status badges |
| **SyntheticGenerator** | 🟡 Média | Gerar dados a partir do XSD |
| **TestReportPanel** | 🟡 Média | Tabela resumo + matriz cobertura |
| **DiffViewer** | 🔴 Alta | Lado a lado com destaque automático |
| **ConfidencePopover** | 🟢 Baixa | 5 fatores com barras de progresso |
| **CoveragePopover** | 🟢 Baixa | Breakdown por tipo |
| **CoverageOverlay** | 🟡 Média | Sobreposição colorida Canvas + PDF |
| **VisibilityControl** | 🟡 Média | Construtor SE/condição com E/OU |
| **AnalyzingProgress** | 🟡 Média | 8 blocos, 23 estágios, barra de progresso |

### Organismos existentes — adaptação necessária

| Componente Atual | Adaptação |
|-----------------|-----------|
| `AppHeader.vue` | Suportar toolbar do editor |
| `PDFViewer.vue` | Virar aba PDFReference + overlays |
| `MonacoTabs.vue` | Virar aba Código com explorador |
| `FieldMappingTable.vue` | Migrar para aba Campos |
| `FieldDetailPanel.vue` | Migrar para Inspetor hierárquico |
| `ChartjsConfigPanel.vue` | Migrar para Inspetor de Gráfico |
| `LayoutControls.vue` | Migrar para Inspetor de Página |
| `LayoutPreview.vue` | Migrar para Canvas HTML |
| `ExportChecklist.vue` | Simplificar — validação pré-export |
| `WizardStepper.vue` | 🗑️ Obsoleto |

---

## 4. Moléculas — Novos (a criar)

| Componente | Descrição |
|-----------|-----------|
| StructureTreeNode | Ícone + nome + binding + badge |
| FieldNavItem | Ícone + nome + badge status |
| VariationRow | Campo + ✔/✖ por documento |
| InspectorField | Rótulo + valor + ação |
| DatasetItem | Nome + status badge + botão deletar |
| TestReportRow | Dataset + páginas + cobertura + status |
| CoverageMatrixRow | Elemento + ✓/✕ por dataset |
| LayoutTypeTab | Nome + contador páginas |
| ConfidenceFactor | Rótulo + ProgressBar + % |
| SectionOverlay | Borda tracejada + rótulo seção |
| AnchorSelector | Dropdown (Topo/Fluxo/Rodapé) |
| PositionControl | Label + X + Y inputs |
| SizeControl | Label + L + A inputs |
| FontWarning | Nome fonte + fallback + botão upload |
| PageBreakLine | Linha tracejada + rótulo |

---

## 5. Átomos — Novos (a criar)

| Componente | Uso |
|-----------|-----|
| Toggle | Modo Cobertura, Diff, Snap |
| Input (genérico) | Nome template, busca, valores numéricos |
| Tooltip | Dicas contextuais |
| ZoomControl | Zoom do Canvas (50-125%) |

---

## 6. Stores (Pinia) — Gaps

| Store | Existe? | Status |
|-------|---------|--------|
| session | ✅ | Expandir |
| mapping | ✅ | Expandir |
| layout | ✅ | Expandir |
| generation | ✅ | Expandir |
| **editor** | ❌ | Criar (seleção, aba ativa, zoom) |
| **template** | ❌ | Criar (árvore de estrutura — fonte de verdade) |
| **inspector** | ❌ | Criar (nó selecionado, nível, propriedades) |
| **coverage** | ❌ | Criar (cobertura por layout type) |
| **confidence** | ❌ | Criar (5 fatores) |
| **testData** | ❌ | Criar (datasets, validação, relatório) |
| **multiDoc** | ❌ | Criar (matriz variação, detecções) |

---

## 7. Composables — Gaps

| Composable | Existe? | Status |
|-----------|---------|--------|
| useBibliotecas | ✅ | OK |
| useFileSystem | ✅ | OK |
| useProject | ✅ | OK |
| useSSE | ✅ | OK |
| **useCanvas** | ❌ | Criar (seleção, drag, resize, snap) |
| **usePagination** | ❌ | Criar (Layout Engine) |
| **useSync** | ❌ | Criar (scroll/seleção sincronizados) |
| **useExport** | ❌ | Criar (gerar ZIP) |
| **useKnockout** | ❌ | Criar (gerar bindings data-bind) |

---

## Contagem Final

| Categoria | Existem | Faltam | Obsoletos |
|-----------|---------|--------|-----------|
| Páginas | 2 (adaptar) | 2 (criar) | 4 (remover) |
| Templates | 1 | 1 | 2 |
| Organismos | 10 (adaptar) | 26 (criar) | 1 |
| Moléculas | 2 (adaptar) | 15 (criar) | 0 |
| Átomos | 7 | 4 (criar) | 0 |
| Stores | 4 (expandir) | 7 (criar) | 0 |
| Composables | 4 | 5 (criar) | 0 |

**Total: ~58 componentes/módulos a criar ou adaptar significativamente.**

---

## Inputs para Criação de Stories

Este gap analysis, combinado com os seguintes documentos, forma a base para o @sm criar stories:

1. `docs/prd-v3.md` — PRD v3.0
2. `docs/wireframes/wireframes-mid-fi.md` — Wireframe v5.3
3. `docs/architecture/architecture-v5.md` — Arquitetura v5.0
4. Este documento — Gap analysis frontend
