# Auditoria: Gráficos + Código de Barras + SVG Inline

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR26** (`docs/prd-v3.md`, linha 250): Detecção de canvas de gráficos no PDF; ChartInspector com tipo (Barras, Linhas, Pizza, Rosca, Área, Empilhado), binding de dados (rótulos + datasets com campo/rótulo/cor), dimensões, estilo (legenda, grade, animação, rótulos de eixos), preview no Inspector. Confiança ≥60% → tipo pré-selecionado; <60% → operador seleciona. Fallback para imagem PNG. Gera `<canvas>` + configuração Chart.js no `base.js`; bibliotecas em `../Bibliotecas/js/`.

**FR31** (`docs/prd-v3.md`, linha 286): Detecção de elementos de código de barras no PDF; binding via JsBarcode CDN; configurável no Inspector.

**FR32** (`docs/prd-v3.md`, linha 290): Detecção de imagens vetoriais (SVG) no PDF; incorporação como SVG inline no `index.html`.

**`template_editor_main_screen_spec.md` seção Chart Inspector** (linha 232): tipo de gráfico, biblioteca Chart.js, binding (labels: campo, values: campo), dimensões (width/height).

**`docs/prd-v3.md` linha 410–411**: Bibliotecas JS em `../Bibliotecas/js/`: `Chart.min.js`, `chartjs-plugin-datalabels.min.js`, `knockout-3.4.2.js`, `knockout.mapping.js`. CDN externo: JsBarcode via `https://cdn.jsdelivr.net/jsbarcode/`.

---

## Frontend — Status de Implementação

**Componentes existentes:**

- `/home/user/migrador-planet/frontend/src/organisms/inspectors/ChartInspector.vue`: seção Geral (nome editável, badge de confiança com hint "Selecione o tipo manualmente" quando <60%), seção Tipo (dropdown bar/line/pie/doughnut/polarArea + checkbox barras empilhadas), seção Dados (campo Labels + datasets com label/campo/cor, adicionar/remover), seção Dimensões (largura/altura em px), seção Estilo (legenda, grid, animação, label eixo X/Y), seção Preview (ChartPreview component ou fallback "Imagem estática será usada"), seção Posição (Âncora/Manter Junto — read-only), seção Visibilidade (VisibilityControl), seção Fallback (checkbox "Usar imagem estática").
- `/home/user/migrador-planet/frontend/src/stores/chartStore.ts`: tipos `ChartType` (bar/line/pie/doughnut/polarArea), `ChartConfig` com id/name/type/confidence/labelsField/datasets/dimensions/styles/useFallback/stacked. `registerChart()` pre-seleciona tipo quando confidence ≥60% via `resolveType()`. `updateChart()`, `addDataset()`, `removeDataset()`, `setFallback()`, `reset()`.
- `/home/user/migrador-planet/frontend/src/stores/chartCodeGen.ts` (Story 9.7): `generateChartHtmlSnippet()` → `<canvas id>` ou `<img src>` (fallback). `generateChartJsBlock()` → `new Chart(document.getElementById(...), { type, data: { labels: ko.unwrap(data.labels), datasets }, options: { responsive: false, plugins, scales, animation } })`. `CHARTJS_SCRIPT_TAGS` referencia `../Bibliotecas/js/Chart.min.js` e `../Bibliotecas/js/chartjs-plugin-datalabels.min.js`. `buildChartJsSection()` agrega todos os charts não-fallback.
- `/home/user/migrador-planet/frontend/src/molecules/BarcodeInspector.vue`: seção Formato (select: CODE128/CODE39/EAN-13/EAN-8/UPC-A/ITF/MSI), seção Dados (select campo do templateStore), seção Opções (largura barra, altura, mostrar texto), seção Preview (CSS bars placeholder), seção Código gerado (mostra `<svg id>` + `JsBarcode("#id", ko.unwrap(data.campo), { format, lineColor, width, height, displayValue })`).

**O que funciona:**
- ChartInspector: seleção manual ou automática de tipo por confiança (FR26 confiança ≥60%/< 60%), múltiplos datasets com campo/cor/label, dimensões, estilos completos, preview inline via `ChartPreview`, fallback imagem estática.
- Geração de `<canvas>` + bloco `new Chart(...)` com `ko.unwrap(data.campo)` via chartCodeGen (FR26).
- Referência correta a `../Bibliotecas/js/Chart.min.js` e `chartjs-plugin-datalabels.min.js` (FR26, linha 411).
- BarcodeInspector: seleção de formato (CODE128 a MSI — 7 formatos), binding de campo, opções visuais, código gerado mostrando chamada `JsBarcode()` com `ko.unwrap(data.campo)` (FR31).
- Preview mockado de barras (CSS determinístico) no BarcodeInspector — sem renderização real de barcode no editor.
- Tipos suportados no ChartInspector: bar, line, pie, doughnut, polarArea — falta "Área" (`area`) e "Empilhado" (`stacked`) como tipo distinto (apenas como modifier via checkbox "Barras empilhadas"). A spec menciona "Área Empilhada" como tipo separado.

**O que falta:**
- Preview de gráfico no Canvas com dados de teste: ChartPreview existe no Inspector, mas preview no Canvas (iframe) com Chart.js ativo não foi verificado. A geração de `<canvas>` no template exige Chart.js carregado — no iframe do editor pode não estar disponível.
- JsBarcode CDN no template gerado: o BarcodeInspector gera corretamente o código JS, mas a referência `<script src="https://cdn.jsdelivr.net/jsbarcode/...">` no `index.html` exportado não foi encontrada no stage5. O código JS é gerado no frontend mas a injeção do CDN no template exportado não está confirmada.
- "Área" como tipo de gráfico independente (FR26 menciona "Área" e "Empilhado" como tipos, não apenas como modificador de Barras).
- MSI: presente no `BARCODE_FORMATS` do BarcodeInspector mas **ausente** no `_FORMAT_MAP` do backend `_barcode_to_svg_content()` — discrepância entre frontend e backend.

---

## Backend — Status de Implementação

**Stage 3** (`stage3_structural_analysis.py`):
- Detecção de gráficos e barcodes via Vision AI (GPT-4o / OpenRouter), função `chat_with_vision()` (linhas 443–568). Se `VISION_AI_ENABLED=false` ou sem cliente, pula detecção visual.
- Nós `"type": "chart"` com `chart_type`, `confidence`, `bbox`. Nós `"type": "barcode"` com `barcode_format`, `confidence`, `bbox`, `value` (extraído do texto próximo via `_extract_barcode_value()`).
- Charts e barcodes atribuídos às seções via `_assign_visual_elements_to_sections()` (linha 1306).
- **Detecção de SVG vetorial inline**: não encontrada — stage3 não identifica imagens vetoriais SVG do PDF. Apenas `barcode` (que gera SVG no stage5) e `chart_area` são detectados como elementos visuais especiais.

**Stage 5** (`stage5_template_generation.py`):
- `_barcode_to_svg_content()` (linhas 33–80): usa `python-barcode` com `SVGWriter`. Suporta CODE128, CODE39, EAN13, EAN8, UPC (upca), ITF. **MSI ausente** no `_FORMAT_MAP`.
- Barcode com valor conhecido: gera `<div>` posicionado com SVG inline escalável (width/height removidos, viewBox preservado) — implementação funcional.
- Barcode sem valor (campo dinâmico): placeholder posicionado (`data-value=""`) — o barcode dinâmico via JsBarcode CDN **não é injetado no HTML exportado**. O backend gera SVG estático via python-barcode apenas para valores estáticos de exemplo.
- SVG inline (FR32): **não implementado no stage5**. Não há lógica de detecção de SVG vetorial no PDF nem de embedding inline no `index.html`.
- JsBarcode CDN: **não encontrado** na geração do `index.html` ou `base.js` pelo stage5. O frontend (BarcodeInspector) gera o código JS correto mas o CDN não é injetado no template exportado pelo pipeline.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | JsBarcode CDN não injetado no template exportado — `<script src="https://cdn.jsdelivr.net/jsbarcode/...">` ausente no `index.html` gerado pelo stage5 | 🔴 Crítico | Backend (stage5) | FR31, `docs/prd-v3.md` linha 411 |
| 2 | SVG Inline (FR32) não implementado: stage3 não detecta SVGs vetoriais no PDF; stage5 não os embeda no `index.html` | 🔴 Crítico | Backend (stage3 + stage5) | FR32 |
| 3 | MSI barcode: presente no frontend (BarcodeInspector.vue BARCODE_FORMATS) mas ausente no `_FORMAT_MAP` do backend `_barcode_to_svg_content()` — gera CODE128 silenciosamente | 🟡 Importante | Backend (stage5) | FR31 |
| 4 | Preview de gráfico no Canvas iframe não verificado — Chart.js pode não estar disponível no contexto do editor | 🟡 Importante | Frontend | FR26, FR7 |
| 5 | Tipo de gráfico "Área" ausente como opção independente; apenas "Área Polar" (`polarArea`) disponível | 🟢 Menor | Frontend | FR26 (`docs/prd-v3.md` linha 250) |
| 6 | Detecção de gráficos no stage3 depende de Vision AI (GPT-4o) — se `VISION_AI_ENABLED=false`, nenhum gráfico é detectado e o ChartInspector nunca é ativado automaticamente | 🟢 Menor | Backend (stage3) | FR26 |

---

## Backlog Gerado

1. **JsBarcode CDN no template exportado**: Stage5 deve injetar `<script src="https://cdn.jsdelivr.net/jsbarcode/3.11.0/JsBarcode.all.min.js">` no `<head>` do `index.html` gerado quando há nós de barcode com binding dinâmico.
2. **SVG Inline (FR32)**: Implementar detecção de imagens vetoriais (SVG) no PDF durante stage3 (via PyMuPDF `page.get_drawings()` ou `page.get_images()` com SVG); no stage5, embutir SVG inline no `index.html`.
3. **MSI no backend**: Adicionar `"MSI": "msi"` ao `_FORMAT_MAP` de `_barcode_to_svg_content()` (requer verificar suporte em python-barcode).
4. **Preview de gráfico no Canvas**: Verificar/implementar que o iframe do Canvas carregue Chart.js localmente para renderizar `<canvas>` durante a edição.
5. **Tipo de gráfico "Área" (area chart)**: Adicionar `{ value: 'area', label: 'Área' }` ao ChartInspector e mapear para Chart.js `type: 'line'` com `fill: true`.
6. **Fallback de detecção sem Vision AI**: Quando `VISION_AI_ENABLED=false`, stage3 deve criar nós placeholder de gráfico/barcode a partir de heurísticas visuais básicas (ex: área retangular sem texto = possível gráfico).

---

## Status Geral

🟡 Parcial — O ChartInspector e o BarcodeInspector estão bem implementados no frontend, com geração correta de código Chart.js e JsBarcode. O gap crítico é a ausência de injeção do JsBarcode CDN no template exportado e a não implementação de SVG Inline (FR32). O barcode estático via python-barcode funciona no backend, mas o barcode dinâmico (via JsBarcode binding) não tem o CDN necessário no output final.
