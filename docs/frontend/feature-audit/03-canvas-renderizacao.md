# Auditoria: Canvas HTML — Renderização

**Data:** 2026-04-07  
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**Fontes:** `docs/ideias/ux/canvas_complete_spec.md` (seções 1-7), `docs/ideias/ux/editor_architecture_spec.md` (seções 4-5), `docs/architecture/editor-visual-capabilities.md` (seções 1.1 e 1.2)

### Canvas Spec (canvas_complete_spec.md)

O Canvas é o workspace visual central do editor. Renderiza o **HTML real do template final** dentro de um iframe para isolamento de CSS, fontes e regras de layout. O documento no Canvas é o mesmo HTML que gerará o PDF final — sem wireframes, sem placeholders.

Pipeline de renderização (seção 2):
```
template.json → HTML Template Generator → HTML + CSS + Knockout bindings → Canvas iframe → Rendered document
```

### Editor Architecture Spec (seções 4-5)

- HTML gerado a partir da árvore de estrutura (`document_tree`)
- Canvas exibe **live preview do HTML final** — não o PDF original
- Canvas simula paginação real; páginas empilhadas com header/footer repetidos

### Editor Visual Capabilities (editor-visual-capabilities.md — seções 1.1 e 1.2)

**Diagnóstico crítico (v1.1):** O Stage 5 original ignorava ~90% dos dados visuais já extraídos pelos Stages 2-3, entregando ~40-50% de fidelidade. A solução foi o redesenho do Stage 5 com dois sub-steps:

- **5.1 Tree-Driven HTML:** HTML hierárquico a partir de `document_trees` — sections, `<table>` real, label-value pairs, condicionais. Estimativa: +30% fidelidade (estrutura)
- **5.2 CSS-from-Extraction:** CSS dinâmico a partir de fontes, cores, drawn_elements, visual_regions. Estimativa: +35% fidelidade (visual)

Dados que **devem ser usados** (não hardcoded):
- `text_blocks[].font_name` → font-family real
- `text_blocks[].font_size` → tamanho real
- `text_blocks[].is_bold/is_italic` → peso e estilo
- `text_blocks[].color` (RGB int) → cor real
- `drawn_elements[type=line]` → bordas CSS
- `drawn_elements[type=rect, fill_color]` → backgrounds
- `pages[].width/height` → dimensões reais da página
- `visual_regions[].header/footer bbox` → alturas reais das zonas

### FR7 (PRD v3.0) — Canvas HTML

- Renderização em iframe isolado (WYSIWYG live)
- Scroll contínuo vertical com páginas empilhadas (gap e sombra)
- Lazy rendering (máx 5 páginas visíveis)
- Zoom (50-125%)
- Guias visuais (margens, limites Header/Flow/Footer, colunas, snap lines)
- Modo Cobertura overlay

---

## Frontend — Status de Implementação

### HTMLCanvas.vue (`frontend/src/organisms/HTMLCanvas.vue`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Renderização em iframe com isolamento CSS | ✅ Implementado | `<iframe :srcdoc="buildPageSrcdoc(page.html, page.css)" sandbox="allow-same-origin allow-scripts">` |
| Scroll contínuo vertical com páginas empilhadas | ✅ Implementado | `html-canvas__scroll` + páginas iteradas via `v-for` |
| Gap visual entre páginas (page break divider) | ✅ Implementado | `<div class="html-canvas__page-break">` com label "--- QUEBRA DE PÁGINA ---" |
| Lazy rendering (páginas fora da viewport como placeholder) | ✅ Implementado | `isPageVisible(page.pageNum)` via IntersectionObserver (`useCanvas`); placeholder `<div>` quando não visível |
| Zoom controls | ✅ Implementado | `ZoomControls` component; `zoomLevel` via CSS `transform: scale(...)` |
| Guias visuais (CanvasGuides) | ✅ Implementado | `<CanvasGuides>` com margens, header/footer height, column positions |
| Modo Cobertura overlay | ✅ Implementado | `<CoverageOverlay target="canvas" :visible="editorStore.coverageMode">` |
| Snap lines overlay | ✅ Implementado | `<SnapLineOverlay>` condicional em `editorStore.snapEnabled` |
| Seleção com HierarchyPopup | ✅ Implementado | `<HierarchyPopup>` com `ancestorIds` para seleção hierárquica |
| Navegação por página (prev/next) | ✅ Implementado | `navigateToPrevPage/Next` com botões ◁ ▷ |
| Context menu no canvas | ✅ Implementado | `<CanvasContextMenu>` (Story 29.6) |
| **Split de páginas via `data-layout-type`** | ✅ Implementado | `pages computed` parseia `[data-layout-type]` no HTML; fallback para `.page-content` múltiplos |
| **Aviso de contrato não-honrado** | ✅ Implementado | `console.warn` quando `[data-layout-type]` não encontrado no HTML gerado |
| Sombra entre páginas | ❌ Não implementado | Wireframe especifica gap e sombra; o divider CSS existe mas sombra por página não está visível |
| Zoom range 50-125% conforme FR7 | 🟡 Parcial | `ZoomControls` existe, mas range máximo depende da implementação do composable `useCanvas` |

### generation.ts (`frontend/src/stores/generation.ts`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Aceita formato monolítico `{html, css}` do backend | ✅ Implementado | `loadTemplateDraft()` formato 1 |
| Aceita formato paginado `{pages: []}` | ✅ Implementado | `loadTemplateDraft()` formatos 2 e 3 |
| Converte sempre para `TemplateDraft {html, css}` internamente | ✅ Implementado | `HTMLCanvas` converte para `CanvasPage[]` via DOMParser autônomo |
| Patch de geometria de nó no HTML string | ✅ Implementado | `patchNodeGeometry()` via DOMParser (ADR-029) |

---

## Backend — Status de Implementação

### `backend/routers/generate.py`

| Item planejado | Status | Detalhe |
|---|---|---|
| Pipeline de geração via `TemplateGenerator` | ✅ Implementado | `run_generation_pipeline()` + `TemplateGenerator.generate()` |
| **Pipeline principal de análise → template** | ⚠️ Obsoleto | `generate.py` usa `TemplateGenerator` legado (geração baseada em `field_mappings` flat sem árvore); o pipeline real de análise completo passa por `stage5_template_generation.py` via `pipeline_orchestrator_v2.py` |

### `backend/services/stages/stage5_template_generation.py` — Sub-step 5.1 (`_step_5_1_tree_driven_html`)

| Item planejado | Status | Detalhe |
|---|---|---|
| HTML gerado de `document_trees` (não de `field_mappings` flat) | ✅ Implementado | `_step_5_1_tree_driven_html()` itera `document_trees` por `layout_id` |
| `<div data-layout-type="...">` como wrapper por layout | ✅ Implementado | `_tree_to_html()` nó `document` → `<div class="page page-{name}" data-layout-type="{layout_name}">` |
| `<div class="page-content">` para páginas físicas (múltiplas por layout) | ✅ Implementado | Nó `page` → `<div class="page-content">` — `HTMLCanvas` detecta múltiplos `.page-content` e cria 1 `CanvasPage` por filho |
| Seções header/footer/flow com classes CSS | ✅ Implementado | `_tree_to_html()` nós `header/footer/flow` → `<div class="{node_type}">` |
| Tabelas reais `<table>` com `ko foreach` | ✅ Implementado | `_generate_table_html()` com `<thead>`, `<tbody data-bind="foreach: ...">` |
| Seções condicionais `<!-- ko if: ... -->` | ✅ Implementado | `variant == "conditional"` → wrapper `<!-- ko if: binding -->` |
| Z-order: rects (backgrounds) antes de zones antes de lines (bordas) | ✅ Implementado | Ordenação explícita `rects_c + zones_c + lines_c` no nó `page` |
| `data-node-id` em todos os elementos para seleção no Canvas | ✅ Implementado | `data-node-id="{block_id}"` em `span`, `div.section`, `table`, `img`, `rect` |
| Ko foreach para campos array (`[]` em `xsd_field_path`) | ✅ Implementado | `_is_array_field()` detecta arrays no `field_tree` XSD |

### `backend/services/stages/stage5_template_generation.py` — Sub-step 5.2 (`_step_5_2_css_from_extraction`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Dimensões de página de `pages[].width/height` (não hardcoded) | ✅ Implementado | `page_widths/heights` coletados de páginas representativas → `.page { width: Xpx; height: Ypx; }` |
| Font classes de `text_blocks[].font_name` (não "Arial" hardcoded) | ✅ Implementado | `.f-{safe_class} { font-family: '{clean_name}', sans-serif; font-size: Xpt; }` — top 20 fonts |
| Color classes de `text_blocks[].color` (não `#000` hardcoded) | ✅ Implementado | `.c-{hex} { color: #{hex}; }` para todas as cores únicas |
| Bordas de `drawn_elements[type=line]` | ✅ Implementado | `.border-N { border-{side}: Xpt solid #{hex}; }` — limite de 20 linhas |
| Backgrounds de `drawn_elements[type=rect, fill_color]` | ✅ Implementado | `.bg-N { background-color: #{hex}; }` — limite de 10 rects |
| Alturas de header/footer de `visual_regions` bbox | ✅ Implementado | `header_height_px` / `footer_height_px` de `visual_analysis`; fallback 15%/10% da página |
| Análise de alinhamento de texto (right/center) | ✅ Implementado | `.text-right / .text-center` se >30% dos blocos se enquadram |
| **`is_bold` / `is_italic` usados nas classes de fonte** | ❌ Não implementado | `_step_5_2_css_from_extraction` não lê `is_bold`/`is_italic` dos `text_blocks`; apenas `font_name` e `font_size` são usados — peso e estilo são perdidos nas classes CSS |
| **Font classes aplicadas nos elementos HTML** | ❌ Não implementado | Sub-step 5.1 gera `class="{safe_font_class}"` nos `span`/`label`; porém as classes de cor (`.c-{hex}`) e as classes de border (`.border-N`) / background (`.bg-N`) não são associadas aos elementos HTML — são geradas no CSS mas sem classe aplicada nos nós |

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Classes de cor (`.c-{hex}`), bordas (`.border-N`) e backgrounds (`.bg-N`) são geradas no CSS (5.2) mas nunca aplicadas nos elementos HTML (5.1); os elementos não recebem essas classes — resultado: texto sem cor real, sem bordas de drawn_elements, sem backgrounds de retângulos | 🔴 Crítico | Backend stage5 | `editor-visual-capabilities.md` seção 1.2; `_step_5_2_css_from_extraction()` linhas 784-809; `_tree_to_html()` nós `label/value/span` |
| 2 | `is_bold` e `is_italic` de `text_blocks` não são incorporados nas classes de fonte CSS (5.2); as classes `.f-{font}` geram apenas `font-family` e `font-size` — peso e estilo tipográfico são perdidos mesmo quando extraídos pelo Stage 2 | 🔴 Crítico | Backend stage5 | `editor-visual-capabilities.md` seção 1.1; `_step_5_2_css_from_extraction()` linhas 772-782 |
| 3 | Classes de cor em texto NÃO são aplicadas em `_tree_to_html`; sub-step 5.1 lê `color` dos nós e gera `color_style` inline (ex: `color:#FF0000`), mas isso só funciona para nós com `color` explícito; blocos que dependem das classes `.c-{hex}` (sem style inline) ficam sem cor | 🟡 Importante | Backend stage5 | `_tree_to_html()` linhas 399-402; `_step_5_2_css_from_extraction()` linhas 784-787 |
| 4 | `generate.py` (`/api/generate`) usa `TemplateGenerator` legado baseado em `field_mappings` flat — sem árvore, sem 5.1/5.2; esse endpoint ainda é importado por `generation.ts` e pode ser invocado no fluxo do editor, gerando HTML sem fidelidade visual | 🟡 Importante | Backend `generate.py` | `generate.py` linhas 64-66; `generation.ts` usa `previewJobId` |
| 5 | Sombra entre páginas não implementada; wireframe especifica gap com sombra (visual de "folha de papel") para diferenciar páginas no scroll contínuo | 🟢 Menor | Frontend HTMLCanvas | FR7 ("gap e sombra entre elas"); `html-canvas__page-break` CSS |
| 6 | Limite arbitrário de 20 drawn_lines e 10 drawn_rects em 5.2 pode truncar bordas e fundos de documentos densos (ex: boleto bancário com grade de 30+ linhas) | 🟢 Menor | Backend stage5 | `_step_5_2_css_from_extraction()` linhas 791, 805 |

---

## Backlog Gerado

1. **[Backend] Aplicar classes de cor/borda/background nos elementos HTML (5.1 ↔ 5.2):** Em `_tree_to_html()`, ao renderizar nós `label`, `value`, `section` e `rect`, aplicar as classes correspondentes geradas pelo 5.2: a cor mais próxima (`.c-{hex}`) no elemento de texto, a borda (`.border-N`) na section/div contendo a drawn_line, o background (`.bg-N`) na section/div que se sobrepõe ao drawn_rect. Isso fecha o principal gap de fidelidade visual.

2. **[Backend] Incluir `is_bold` e `is_italic` nas classes de fonte (5.2):** Em `_step_5_2_css_from_extraction()`, ao iterar `font_counter`, extrair também `is_bold` e `is_italic` do `text_block`. Gerar classes separadas por combinação font+size+bold+italic (ex: `.f-helvetica-bold`, `.f-helvetica-italic`). Atualizar `_step_5_1_tree_driven_html()` para atribuir a classe correta por variante tipográfica.

3. **[Backend] Aumentar ou tornar configurável o limite de drawn_elements:** Remover o hardcode de 20 linhas / 10 rects em `_step_5_2_css_from_extraction()`. Substituir por um limite configurável via env var (`MAX_BORDER_RULES`, `MAX_BG_RULES`) com padrão maior (ex: 50/20) para documentos densos como boletos.

4. **[Frontend] Adicionar sombra nas páginas do Canvas:** Em `html-canvas__page`, adicionar `box-shadow: 0 2px 8px rgba(0,0,0,0.15)` para replicar o visual de "folha de papel" especificado no wireframe.

5. **[Backend] Deprecar `generate.py` / `TemplateGenerator` legado:** O endpoint `POST /api/generate` usa geração flat sem árvore. Mapear onde ele é chamado no frontend (`generation.ts`, `previewJobId`) e redirecionar para o resultado já gerado pelo `stage5_template_generation.py` no pipeline principal. Isso elimina a dualidade de pipelines de geração.

---

## Status Geral

🟡 Parcial — A arquitetura iframe-isolado, a divisão de páginas via `data-layout-type`, o pipeline Tree-Driven HTML (5.1) com seções/tabelas/condicionais/data-node-id, e o CSS-from-Extraction (5.2) com fontes/cores/bordas reais estão todos implementados. O gap crítico é estrutural: as classes CSS geradas pelo 5.2 (cor, borda, background) não são aplicadas nos elementos HTML gerados pelo 5.1, anulando o ganho de fidelidade visual esperado. `is_bold`/`is_italic` também são descartados no CSS. Resultado prático: documentos renderizam com fontes aproximadas mas sem cores de texto, sem bordas de grid e sem fundos coloridos — fidelidade estimada em ~50-60% em vez dos ~85-90% previstos pelo redesenho do Stage 5.
