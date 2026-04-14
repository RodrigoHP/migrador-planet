# Epic 14 — Editor Visual Capabilities: 100% Fidelidade

## Epic Goal

Dotar o editor visual de todas as capacidades CSS e UX necessárias para que o operador consiga atingir **100% de fidelidade** na reprodução de qualquer documento PDF como template HTML — fechando os 10-15% restantes após o pipeline redesenhado (Stage 5 v3.16+), **sem edição manual de código**.

## Epic Description

### Existing System Context

- **Funcionalidade atual:** Editor visual Vue 3 + Pinia com canvas positioning, coverage overlay, element/section/table/image inspectors, autofix IA (5 tipos), multi-layout, conditional styling, undo/redo
- **Technology stack:** Vue 3, TypeScript, Pinia, Monaco Editor (read-only), FastAPI backend
- **Integration points:** templateStore, editorStore, autoFixStore, multiDocStore, useCanvasInteraction, usePreExportValidation
- **Referência arquitetural:** `docs/architecture/editor-visual-capabilities.md` v1.3 (@architect Aria)

### Enhancement Details

- **O que está sendo adicionado:** 15 features ausentes (F1-F15), 8 melhorias (M1-M8), 3 gaps (A/B/C), 4 novos AutoFix types
- **Diagnóstico raiz:** Stage 5 atual ignora 90% dos dados visuais → 40-50% fidelidade. Com Stage 5 redesenhado → 85-90%. Este epic fecha 90% → 100% via UI
- **Estratégia 3 camadas:** Pipeline (85-90%) → AutoFix refinamento (93-95%) → Editor UI (100%)
- **Success criteria:** Operador reproduz boleto bancário Bradesco com 100% fidelidade sem editar HTML/CSS manualmente

---

## Escopo por Wave

### Pre-Wave — Stage 5 Redesenhado (FORA DESTE EPIC)
O Stage 5 v3.16 (sub-steps 5.1 Tree-Driven HTML + 5.2 CSS-from-Extraction) é pré-requisito mas pertence ao epic de implementação do pipeline. Este epic assume que o Stage 5 entrega ~85-90%.

---

### Wave 1 — Escape Hatch + Essenciais (~6-8 dias)
**Objetivo:** Operador chega a 100% com esforço razoável.

| Story | Feature | Severidade | Executor | Quality Gate | Estimativa | Status |
|-------|---------|-----------|----------|--------------|------------|--------|
| 14.1 | **F5** CSS Live Editor — Monaco editável + live preview | CRITICO | @dev | @architect | M | ✅ Done |
| 14.2 | **F1** Border Editor — bordas per-lado em elementos e seções | CRITICO | @dev | @architect | M | ✅ Done |
| 14.3 | **F3** Text Alignment + **F9** Text Decoration/Transform | CRITICO+ALTO | @dev | @architect | S | ✅ Done |

### Wave 2 — Tabelas & Produtividade (~8-10 dias)
**Objetivo:** Operador chega a 100% em metade do tempo (sem depender de CSS direto).

| Story | Feature | Severidade | Executor | Quality Gate | Estimativa | Status |
|-------|---------|-----------|----------|--------------|------------|--------|
| 14.4 | **F2** Table Cell Borders — bordas per-célula, seleção, background | CRITICO | @dev | @architect | L | ✅ Done |
| 14.5 | **F4** Alignment Tools — toolbar contextual multi-select | CRITICO | @dev | @architect | M | ✅ Done |
| 14.6 | **F6** Background Color per-elemento + **M1** ColorPicker com opacity | ALTO | @dev | @architect | S | ✅ Done |

### Wave 3 — Refinamento & Produtividade (~8-10 dias)
**Objetivo:** Experiência profissional de edição.

| Story | Feature | Severidade | Executor | Quality Gate | Estimativa | Status |
|-------|---------|-----------|----------|--------------|------------|--------|
| 14.7 | **F10** Snap Lines Visuais + **F14** Keyboard Shortcuts posicionamento | ALTO+MEDIO | @dev | @architect | M | ✅ Done |
| 14.8 | **F8** Z-Index Layer Panel + **F7** Group/Ungroup | ALTO | @dev | @architect | M | ✅ Done |
| 14.9 | **F15** Copy/Paste + **F11** Padding per-elemento + **Gap A** KO validation | MEDIO+ALTO | @dev | @architect | M | ✅ Done |

### Wave 4 — Automação IA (~8-12 dias)
**Objetivo:** 93-95% automático, operador só ajusta 5-7%.

| Story | Feature | Severidade | Executor | Quality Gate | Estimativa | Status |
|-------|---------|-----------|----------|--------------|------------|--------|
| 14.10 | **F12** AutoFix novos fix types (border-refine, bg-refine, text-align, z-order) | MEDIO | @dev | @architect | L | ✅ Done |
| 14.11 | **F13** AutoFix Batch Accept + **M2** Limit configurável + **M8** Confidence display | MEDIO+BAIXO | @dev | @architect | S | ✅ Done |
| 14.12 | **M3** Table Inspector editável + **M4** Box Model + **M7** ConditionalStyle expandido | ALTO+MEDIO | @dev | @architect | M | ✅ Done |
| 14.13 | **Gap B** Visibility↔multiDocStore sync + **Gap C** AutoFix limit env var | MEDIO+BAIXO | @dev | @architect | S | ✅ Done |
| 14.14 | Fix is-table-cell flag | BAIXO | @dev | @qa | XS | 🔄 Ready |
| 14.15 | Fix ChartInspector ColorPicker | BAIXO | @dev | @qa | XS | 🔄 Ready |

---

## Stories Detalhadas

### Story 14.1 — CSS Live Editor (F5)
- **Description:** Transformar o Code Tab (read-only) em editor CSS editável com Monaco, live preview no canvas, syntax highlighting, autocomplete CSS, validação em tempo real. Separação CSS global (template) vs inline (elemento).
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, architecture_review]`
- **Onde:** Expandir Code Tab no `CenterPanel` + criar `codeStore.ts`
- **UX review:** TALVEZ — split view canvas↔code
- **Quality Gates:**
  - Pre-Commit: Monaco integration, live sync stability
  - Pre-PR: Performance (no canvas lag on CSS change), architecture review

### Story 14.2 — Border Editor (F1)
- **Description:** Adicionar controles de bordas completos: `border-width` (4 lados independentes), `border-color` (por lado com ColorPicker), `border-style` (solid/dashed/dotted/double/none), `border-radius`. UI shorthand visual (all sides / per side toggle).
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, ux_validation]`
- **Onde:** Nova seção "Borders" no `ElementInspector.vue` e `SectionInspector.vue`
- **UX review:** SIM — componente novo com 4 lados, estilos, cores, radius
- **Quality Gates:**
  - Pre-Commit: Component isolation, CSS property coverage
  - Pre-PR: Visual regression, boleto reproduction test

### Story 14.3 — Text Alignment + Text Decoration (F3 + F9)
- **Description:** (F3) Grupo de botões `text-align` (left/center/right/justify) + `vertical-align` (top/middle/bottom) no ElementInspector. (F9) Botões toggle B/I/U/Aa para `font-weight`, `font-style`, `text-decoration`, `text-transform`.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation]`
- **Onde:** Seção "Typography" do `ElementInspector.vue`
- **UX review:** NAO — controles padrão
- **Quality Gates:**
  - Pre-Commit: Button states, CSS property application
  - Pre-PR: Multi-element selection support

### Story 14.4 — Table Cell Borders (F2)
- **Description:** Seleção de célula individual na tabela, border per-célula (4 lados), `border-collapse` toggle, background color per-célula, padding per-célula. Sub-componente `TableCellEditor`.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, ux_validation]`
- **Onde:** Expandir `TableInspector.vue` com `TableCellEditor` sub-component
- **UX review:** SIM — seleção de célula + painel de bordas per-cell
- **Quality Gates:**
  - Pre-Commit: Cell selection, border independence
  - Pre-PR: Complex table reproduction (boleto grid)

### Story 14.5 — Alignment Tools (F4)
- **Description:** Toolbar contextual que aparece quando 2+ elementos selecionados. Botões: Align left/center/right, Align top/middle/bottom, Distribute horizontally/vertically.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, ux_validation]`
- **Onde:** Nova toolbar contextual + funções em `useCanvasInteraction.ts`
- **UX review:** SIM — toolbar nova com ícones
- **Quality Gates:**
  - Pre-Commit: Multi-select detection, alignment calculations
  - Pre-PR: Distribution uniformity test

### Story 14.6 — Background Color + ColorPicker Enhanced (F6 + M1)
- **Description:** (F6) `background-color` no `ElementInspector.vue` + transparent/inherit. (M1) ColorPicker com opacity slider (rgba), paleta de cores extraídas do PDF, presets recentes.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation]`
- **Onde:** Seção "Appearance" no `ElementInspector.vue` + `InspectorColorPicker.vue`
- **UX review:** NAO — reutiliza InspectorColorPicker
- **Quality Gates:**
  - Pre-Commit: Color validation, opacity range
  - Pre-PR: PDF color palette extraction accuracy

### Story 14.7 — Snap Lines Visuais + Keyboard Shortcuts (F10 + F14)
- **Description:** (F10) `SnapLineOverlay.vue` renderiza linhas magenta durante drag/resize com labels de distância px. (F14) Arrow keys: mover 1px, Shift+Arrow: 10px, Alt+Arrow: resize 1px, Ctrl+D: duplicar, Delete: remover.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation]`
- **Onde:** `SnapLineOverlay.vue` + key handlers no canvas wrapper
- **UX review:** NAO — padrão Figma/Photoshop
- **Quality Gates:**
  - Pre-Commit: Snap line rendering, key event handling
  - Pre-PR: Performance (no lag during drag with overlay)

### Story 14.8 — Layer Panel + Group/Ungroup (F8 + F7)
- **Description:** (F8) `LayerPanel.vue` no left sidebar — lista ordenável de elementos por z-index, drag-to-reorder, Bring to Front/Send to Back/Move Up/Move Down. (F7) Group/Ungroup com herança de move/resize e operações batch.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, ux_validation]`
- **Onde:** Novo `LayerPanel.vue` sidebar + `templateStore.ts` (modelo grupo)
- **UX review:** SIM — painel sidebar novo + visual de grupo no canvas
- **Quality Gates:**
  - Pre-Commit: z-index tracking, group model
  - Pre-PR: Drag-to-reorder stability, group resize proportionality

### Story 14.9 — Copy/Paste + Padding + KO Validation (F15 + F11 + Gap A)
- **Description:** (F15) Ctrl+C/V/D com clone completo de propriedades, suporte multi-select. (F11) Padding top/right/bottom/left no `ElementInspector.vue`. (Gap A) Validação de `<!-- ko if/foreach -->` contra XSD no `usePreExportValidation.ts`.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, security_scan]`
- **Onde:** `useCanvasInteraction.ts`, `ElementInspector.vue`, `usePreExportValidation.ts`
- **UX review:** NAO
- **Quality Gates:**
  - Pre-Commit: Clone fidelity, KO regex coverage
  - Pre-PR: Pre-export validation blocking on invalid bindings

### Story 14.10 — AutoFix Novos Fix Types (F12)
- **Description:** 4 novos fix types de refinamento: `border-refine` (drawn_elements vs CSS borders), `background-refine` (rects vs backgrounds), `text-align` (posição x vs CSS), `z-order` (overlaps vs z-index). Backend `/api/auto-fix` + `autoFixStore.ts`.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation, api_contract_validation]`
- **Onde:** Backend `/api/auto-fix` + `autoFixStore.ts`
- **Depende de:** F1, F3, F6, F8 (Wave 1-3) para que operador aceite/edite sugestões
- **Quality Gates:**
  - Pre-Commit: Fix type accuracy, comparison algorithm
  - Pre-PR: False positive rate < 10%

### Story 14.11 — AutoFix Batch Accept + Config + Confidence (F13 + M2 + M8)
- **Description:** (F13) "Accept All" e "Accept All of Type" com preview. (M2) `SESSION_RUN_LIMIT` configurável via `VITE_AUTOFIX_LIMIT`, default 5. (M8) Mostrar score de confiança por sugestão.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation]`
- **Onde:** `AutoFixPanel.vue` + `autoFixStore.ts`
- **Quality Gates:**
  - Pre-Commit: Batch operation atomicity, undo support
  - Pre-PR: Batch accept with undo rollback test

### Story 14.12 — Table Inspector Editável + Box Model + ConditionalStyle (M3 + M4 + M7)
- **Description:** (M3) Edição de width/align por coluna, adicionar/remover colunas, reordenar via drag. (M4) Visualização Box Model (margin/border/padding) como Chrome DevTools no ElementInspector. (M7) ConditionalStyle: adicionar border-color, font-weight, text-decoration, opacity.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation]`
- **Onde:** `TableInspector.vue`, `ElementInspector.vue`, `ConditionalStyleSection.vue`
- **Quality Gates:**
  - Pre-Commit: Column operations, box model accuracy
  - Pre-PR: Table column reorder stability

### Story 14.13 — Visibility↔multiDoc Sync + AutoFix Limit (Gap B + Gap C)
- **Description:** (Gap B) Watch `VisibilityControl.vue` mode changes e notificar `multiDocStore` com `addDetection()`. (Gap C) `SESSION_RUN_LIMIT = parseInt(import.meta.env.VITE_AUTOFIX_LIMIT ?? '5', 10)`.
- **Executor:** `@dev` | **Quality Gate:** `@architect`
- **Quality Gate Tools:** `[code_review, pattern_validation]`
- **Onde:** `VisibilityControl.vue`, `autoFixStore.ts`
- **Quality Gates:**
  - Pre-Commit: Store sync verification
  - Pre-PR: DiffViewer/VariationMatrix update on visibility change

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged — todas as features são aditivas ao editor
- [x] Database schema changes are backward compatible — N/A (frontend only + API extension)
- [x] UI changes follow existing patterns — inspectors, stores, composables Vue 3 + Pinia
- [x] Performance impact is minimal — lazy load de componentes novos (LayerPanel, TableCellEditor)

## Risk Mitigation

- **Primary Risk:** Regressão em features existentes do editor (drag, resize, inspectors)
- **Mitigation:** Cada wave tem testes visuais + testes unitários. QA gate por story
- **Rollback Plan:** Cada wave é um PR independente. Revert do PR reverte a wave inteira

**Quality Assurance Strategy:**

- **CodeRabbit Validation:** Todas as stories incluem pre-commit reviews
  - Wave 1-3: @architect valida padrões de componentes Vue, CSS property coverage
  - Wave 4: @architect valida API contracts do AutoFix
- **Regression Prevention:** Cada story verifica funcionalidade existente via testes
- **Wave Independence:** Cada wave é entregável independente — Wave 1 já desbloqueia 100% fidelidade (via CSS editor)

## Matriz @ux

| Story | UI novo? | @ux? |
|-------|---------|------|
| 14.1 F5 CSS Live Editor | TALVEZ | TALVEZ |
| 14.2 F1 Border Editor | SIM | SIM |
| 14.4 F2 Table Cell Editor | SIM | SIM |
| 14.5 F4 Alignment Tools | SIM | SIM |
| 14.8 F8+F7 Layer Panel + Groups | SIM | SIM |
| Demais stories | NAO | NAO |

## Definition of Done

- [x] 14 de 15 stories completadas com AC atendidos (14.14 e 14.15 em Ready)
- [ ] Funcionalidade existente verificada (sem regressão nos 35+ testes do Epic 12)
- [ ] Integration points (templateStore, editorStore, autoFixStore) funcionando
- [ ] Documentação atualizada (source-tree, tech-stack)
- [ ] Sem regressão em features existentes
- [ ] Boleto bancário Bradesco reproduzível com 100% fidelidade via UI

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing system running Vue 3 + TypeScript + Pinia (frontend), FastAPI + Python (backend)
- Integration points: templateStore, editorStore, autoFixStore, multiDocStore, useCanvasInteraction, usePreExportValidation, ElementInspector.vue, SectionInspector.vue, TableInspector.vue
- Existing patterns to follow: Inspector components (ElementInspector, SectionInspector, ImageInspector), Pinia stores, composables (useCanvasInteraction, useFontCascade, useZoom)
- Critical compatibility requirements: zero regression on existing drag/resize/inspect/autofix features
- Each story must include verification that existing functionality remains intact
- Waves are ordered by priority: Wave 1 deblocks 100% fidelity, Wave 2 speeds it up, Wave 3 polishes, Wave 4 automates

The epic should maintain system integrity while delivering 100% PDF fidelity via UI controls."

---

**Estimativa total:** ~30-40 dias (4 waves)
**Stories:** 13 stories (14.1 — 14.13)
**Referência arquitetural:** `docs/architecture/editor-visual-capabilities.md` v1.3

— Morgan, planejando o futuro 📊
