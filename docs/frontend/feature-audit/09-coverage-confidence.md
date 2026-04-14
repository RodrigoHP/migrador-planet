# Auditoria: Sistema de Cobertura + Confiança Expandida

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

### FR29 — Sistema de Cobertura (`docs/prd-v3.md` linha 268)
- Percentual de cobertura na toolbar, clicável para popover com breakdown por tipo: campos, tabelas, imagens, gráficos (N de M por categoria)
- Thresholds: ≥95% ✅ completo, 80-95% ⚠️ revisão recomendada, <80% 🔴 análise incompleta
- Toggle Modo Cobertura na toolbar: overlay colorido no Canvas (🟩 mapeado, 🟥 sem binding, 🟨 não confirmado, 🟪 tabela, 🟧 laranja tracejado = seção opcional, 📊 laranja sólido = gráfico)
- Modo Cobertura no PDF Referência: overlays 🟦 texto detectado, 🟩 detectado+mapeado, 🟥 detectado não mapeado, 🟨 não confirmado, 🟪 tabela, 📊 gráfico
- Cobertura por Layout Type (atualiza ao trocar tipo)
- Cobertura atualiza em tempo real ao mapear/desmapar
- Cálculo ponderado por tipo de elemento

### FR33 — Confiança Expandida (`docs/prd-v3.md` linha 294)
- Pontuação de confiança na toolbar, clicável para popover com 5 fatores: Estabilidade de Layout, Detecção de Âncoras, Qualidade do Grid, Variabilidade de Campos, Concordância da Visão
- Thresholds: ≥95% ✅, 80-95% ⚠️, <80% 🔴 revisão humana
- Por Layout Type

### Wireframe — Toolbar (`docs/wireframes/wireframes-mid-fi.md` linha 401)
- Popover de confiança com barras de progresso para 5 fatores e nível threshold
- Popover de cobertura com "N de M" para 4 categorias e nível threshold
- Ambos fecham ao clicar fora

### UX Spec — Seção 9 (`docs/ideias/ux/template_editor_main_screen_spec.md` linha 378)
- Coverage Score com lista de campos/status e botão "Highlight Missing Fields"

---

## Frontend — Status de Implementação

### CoverageOverlay.vue (`frontend/src/organisms/CoverageOverlay.vue`)
**Implementado:**
- Overlay posicionado absolutamente com bounding boxes para alvo `canvas` e `pdf`
- Mapa de cores para Canvas: `bound` (verde), `unbound` (vermelho), `unconfirmed` (amarelo), `table` (roxo), `table_container` (roxo claro), `table_cell` (roxo médio), `optional_section` (laranja tracejado), `chart` (laranja sólido)
- Mapa de cores para PDF: `text_block` (azul), `mapped` (verde), `unmapped` (vermelho), `unconfirmed` (amarelo), `table` (roxo), `chart` (laranja)
- Lógica de hover para containers de tabela (revela células ao passar o mouse)
- Prop `target: 'canvas' | 'pdf'` e `visible: boolean`
- Lê do `coverageStore.getOverlayData(layoutId, target)` via `layoutStore.activeLayoutId`
- Integrado ao SyncView (canvas e pdf) e ao PDFReference

**Gap menor:**
- Ícone 📊 para gráficos não é renderizado no overlay — apenas a cor de fundo laranja; o ícone textual está ausente

### CoveragePopover.vue (`frontend/src/organisms/CoveragePopover.vue`)
**Implementado:**
- Header com percentual geral e ícone threshold (✅/⚠️/🔴)
- Breakdown para 4 categorias: Campos, Tabelas, Imagens, Gráficos via componente `CoverageBreakdown`
- Fecha ao clicar fora via `useClickOutside`
- Thresholds corretos (≥95%, 80-95%, <80%)
- Lê de `coverageStore.getForLayout(activeLayoutId)`

### ConfidencePopover.vue (`frontend/src/organisms/ConfidencePopover.vue`)
**Implementado:**
- Header com pontuação geral e ícone threshold
- Breakdown de exatamente 5 fatores via `ConfidenceFactor`: `layout_stability`, `anchor_detection`, `grid_quality`, `field_variability`, `vision_agreement` — todos os fatores da spec FR33
- Fecha ao clicar fora
- Lê de `confidenceStore.getForLayout(activeLayoutId)`

### TopToolbar.vue (`frontend/src/organisms/TopToolbar.vue`)
**Implementado:**
- Badge de Confiança (`ConfidenceBadgeMetric`) clicável abre `ConfidencePopover`
- Badge de Cobertura (`CoverageBadge`) clicável abre `CoveragePopover`
- Toggle Modo Cobertura (🗺️) via `editorStore.toggleCoverage()`
- Toggle Diff (🔀), Snap (🧲), Auto Fix (🔧) presentes
- Layout Selector oculto quando apenas 1 layout (`layoutStore.layoutTypes.length > 1`)

### coverageStore.ts (`frontend/src/stores/coverageStore.ts`)
**Implementado:**
- `coverageByLayout: Map<string, CoverageData>` por Layout Type
- `overlayDataByLayout: Map<string, Record<OverlayTarget, OverlayItemData[]>>` — canvas + pdf por layout
- `activeLayoutCoverage` e `thresholdLevel` computados e reativos ao layout ativo
- `loadCoverage`, `updateForLayout`, `loadOverlayItems`, `setOverlayData`
- `loadOverlayItems` mapeia `BackendOverlayItem.bbox_canvas` e `bbox_pdf` para canvas e pdf separadamente

**Gap crítico:**
- `updateForLayout()` existe mas não é chamado automaticamente quando o operador altera bindings no editor — não existe watcher conectando mudanças de binding ao recálculo de cobertura. A cobertura só é atualizada ao trocar de Layout Type (via `layout.ts`) ou ao carregar novo pipeline.

### confidenceStore.ts (`frontend/src/stores/confidenceStore.ts`)
**Implementado:**
- `confidenceByLayout: Map<string, ConfidenceFactors>` por Layout Type
- `activeLayoutConfidence`, `overallForActiveLayout`, `thresholdLevel`
- `loadConfidence`, `updateForLayout`, `backendWarnings`

---

## Backend — Status de Implementação

### `_step_5_3_coverage` (`backend/services/stages/stage5_template_generation.py`, linhas 864–920)
**Implementado:**
- Calcula cobertura separadamente por Layout Type (`layout_id`)
- Campos: `mapped_fields` via `field_mappings` filtrados por `layout_type_id`; `total_xsd_fields` de `field_tree.flat_paths`
- Tabelas: `_count_nodes_by_type(tree, "table")` e `_count_mapped_tables()`
- Imagens: contadas e todas marcadas como mapeadas (`mapped_images = total_images`)
- Gráficos: total contado mas `"charts": {"mapped": 0, "total": total_charts}` — `mapped` hardcoded como 0
- Cálculo ponderado: `f_pct * 0.6 + t_pct * 0.25 + i_pct * 0.15` — gráficos excluídos da fórmula
- Retorna estrutura correta `{fields, tables, images, charts, percentage}` consumida pelo frontend

**Gaps críticos:**
- `charts.mapped` sempre 0 — gráficos nunca contam como mapeados independente do estado
- Peso de gráficos ausente na fórmula ponderada (spec prevê cálculo ponderado por tipo incluindo gráficos)
- `total_xsd_fields` usa todos os campos do XSD sem filtrar por layout — pode inflar denominador para layouts que não possuem todos os campos do XSD

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | `charts.mapped` hardcoded como 0 — cobertura de gráficos nunca é contabilizada | 🔴 Crítico | Backend | `stage5_template_generation.py:916` / FR29 |
| 2 | Gráficos excluídos da fórmula ponderada (somente campos+tabelas+imagens = 100%) | 🔴 Crítico | Backend | `stage5_template_generation.py:910` / FR29 |
| 3 | Cobertura não atualiza em tempo real ao mapear/desmapar campo manualmente no editor | 🟡 Importante | Frontend | `coverageStore.ts` / FR29 |
| 4 | `total_xsd_fields` não filtrado por layout — denominador potencialmente incorreto para layouts parciais | 🟡 Importante | Backend | `stage5_template_generation.py:876-878` / FR29 |
| 5 | Ícone 📊 textual ausente no CoverageOverlay para itens do tipo `chart` (apenas cor de fundo) | 🟢 Menor | Frontend | `CoverageOverlay.vue` / FR29 wireframe |
| 6 | Thresholds individuais por fator de confiança não exibidos (apenas o overall tem threshold) | 🟢 Menor | Frontend | `ConfidencePopover.vue` / FR33 |

---

## Backlog Gerado

1. **[Backend] Corrigir `_step_5_3_coverage`: implementar `_count_mapped_charts(tree, layout_mappings)` e incluir gráficos no cálculo ponderado** — `stage5_template_generation.py` linhas 903-916. Ajustar pesos (ex: campos 55% + tabelas 25% + imagens 10% + gráficos 10%).
2. **[Backend] Filtrar `total_xsd_fields` por Layout Type** — em `_step_5_3_coverage`, usar apenas campos relevantes ao layout ativo, não o total global do XSD.
3. **[Frontend] Atualização em tempo real de cobertura** — adicionar watcher no `templateStore` para mudanças de binding; ao detectar mudança, recalcular localmente e chamar `coverageStore.updateForLayout()`.
4. **[Frontend] Renderizar ícone 📊 no CoverageOverlay para tipo `chart`** — adicionar elemento visual (pseudo-elemento CSS ou `::after`) com o ícone para distinguir graficamente gráficos no overlay.

---

## Status Geral

🟡 Parcial — O frontend está bem estruturado: popover de cobertura e confiança funcionais, overlay colorido com todas as cores da spec, atualização por Layout Type. O gap crítico está no backend: gráficos nunca entram no cálculo ponderado (`mapped: 0` hardcoded, peso ausente na fórmula). A atualização em tempo real ao editar bindings também está ausente.
