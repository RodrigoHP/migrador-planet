# Auditoria do Editor — Índice Consolidado

**Data:** 2026-04-07
**Total de funcionalidades auditadas:** 27
**Objetivo:** Identificar gaps entre o planejado (docs/prd-v3.md) e o implementado (front + back), por funcionalidade, para montar backlog de fechamento.

---

## Legenda de Status

| Símbolo | Significado |
|---------|-------------|
| 🔴 | **Crítico** — gaps que quebram funcionalidade ou violam requisito fundamental |
| 🟡 | **Parcial** — funcionalidade existe mas com gaps significativos |
| 🟢 | **Implementado** — funcionalidade completa ou com gaps apenas menores |

---

## Resumo Executivo

| Status | Qtd | Funcionalidades |
|--------|-----|----------------|
| 🔴 Crítico | 1 | index-html (ZIP quebrado) |
| 🟡 Parcial | 24 | maioria das funcionalidades |
| 🟢 Implementado | 2 | test-data, auto-fix |

---

## Índice por Área

### Pipeline de Entrada

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 01 | Upload + Fluxo de Navegação | 🟡 Parcial | [01-upload-flow.md](01-upload-flow.md) |
| 02 | Tela de Progresso + Pipeline (Stages 1-5) | 🟡 Parcial | [02-analyzing-pipeline.md](02-analyzing-pipeline.md) |

**Principais gaps:** geração sintética de dados do XSD (FR2b). ~~Barra de progresso percentual~~ e ~~navegação automática~~ descartados — wireframe v2 redesenhou para progresso por estágio e clique manual "Abrir Editor" (decisão UX). Redis para job_state já implementado (Story 15.4).

---

### Canvas

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 03 | Canvas HTML — Renderização | 🟡 Parcial | [03-canvas-renderizacao.md](03-canvas-renderizacao.md) |
| 03b | Canvas — Loop de Sincronização | 🟡 Parcial | [03b-canvas-sincronizacao.md](03b-canvas-sincronizacao.md) |
| 04 | Canvas — Interação (drag, resize, seleção, context menu, undo) | 🟡 Parcial | [04-canvas-interaction.md](04-canvas-interaction.md) |
| 05 | Snap & Alignment | 🟡 Parcial | [05-snap-alignment.md](05-snap-alignment.md) |
| 25 | Zoom | 🟡 Parcial | [25-zoom.md](25-zoom.md) |

**Principais gaps:** CSS de cor/borda/background do stage5 não aplicado no HTML (fidelidade ~50-60% em vez de 85-90%), bulk updates sem re-render, ausência de Redo, zoom por mousewheel ausente, inconsistência ZOOM_MAX entre composables.

---

### Painel Esquerdo

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 06 | Árvore de Estrutura | 🟡 Parcial | [06-structure-tree.md](06-structure-tree.md) |
| 22 | Layer Panel + Console/Warnings | 🟡 Parcial | [22-layer-panel-console.md](22-layer-panel-console.md) |
| 23 | Bibliotecas — Snippets e Componentes | 🟡 Parcial | [23-bibliotecas.md](23-bibliotecas.md) |

**Principais gaps:** nível `page` intermediário na árvore, auto-bind semântico não implementado; visibilidade/lock por camada ausentes no LayerPanel; Bibliotecas é um asset manager, não catálogo de componentes estruturais.

---

### Inspetor

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 07 | Inspetor Hierárquico (4 níveis) | 🟡 Parcial | [07-inspector-hierarquico.md](07-inspector-hierarquico.md) |
| 08 | Field Mapping — Field Navigator + Auto-binding | 🟡 Parcial | [08-field-mapping.md](08-field-mapping.md) |
| 26 | Assets (Imagens Embutidas) | 🟡 Parcial | [26-assets.md](26-assets.md) |

**Principais gaps:** Header/Footer/Flow roteados incorretamente no inspetor; posição/tamanho read-only; drag de campo para Canvas ausente; Vision AI + pgvector não implementados; extração automática de imagens do PDF não confirmada.

---

### Painel Central (Abas)

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 13 | Editor de Código (Monaco) — Sincronização Bidirecional | 🟡 Parcial | [13-code-editor.md](13-code-editor.md) |
| 11 | Modo Diff | 🟡 Parcial | [11-diff-mode.md](11-diff-mode.md) |
| 12 | Sync View / Compare (PDF vs Canvas) | 🟡 Parcial | [12-sync-view-compare.md](12-sync-view-compare.md) |

**Principais gaps:** sincronização structure→code suprimida; tipo `moved` (🟨) nunca gerado; painel de inferências Diff ausente; âncoras de layout hardcoded como `[]`; seleção Canvas→PDF não funcional.

---

### Painel Inferior

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 14 | Área de Testes — Data Playground + Test Report | 🟢 Implementado | [14-test-data.md](14-test-data.md) |

**Gaps menores:** Monaco no modal usa fallback textarea, dados de upload inicial não chegam automaticamente ao painel.

---

### Toolbar e Ações Globais

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 24 | Toolbar Principal (TopToolbar) | 🟡 Parcial | [24-toolbar.md](24-toolbar.md) |
| 14b | Salvar / Abrir Projeto | 🟡 Parcial | [14b-salvar-projeto.md](14b-salvar-projeto.md) |
| 14c | Exportar — ZIP com HTML/CSS/JS | 🟡 Parcial | [14c-exportar.md](14c-exportar.md) |
| 15 | Auto-correção por IA (Auto Fix) | 🟢 Implementado | [15-auto-fix.md](15-auto-fix.md) |

**Principais gaps:** toggle "Mostrar Guias" ausente da toolbar; save não inclui assets nem código Monaco editado; edições manuais no Monaco não chegam ao ZIP.

---

### Layout e Estrutura do Documento

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 16 | Layout Types — clustering, seletor, Canvas por tipo | 🟡 Parcial | [16-layout-types.md](16-layout-types.md) |
| 17 | Paginação + Header/Footer multi-página | 🟡 Parcial | [17-pagination-header-footer.md](17-pagination-header-footer.md) |
| 09 | Sistema de Cobertura + Confiança | 🟡 Parcial | [09-coverage-confidence.md](09-coverage-confidence.md) |
| 10 | Analisador Multi-Documento | 🟡 Parcial | [10-multi-doc-analyzer.md](10-multi-doc-analyzer.md) |

**Principais gaps:** Layout Variants Explorer não implementado; funções de paginação runtime ausentes no `base.js` gerado; gráficos não entram no cálculo de cobertura (`mapped: 0` hardcoded); Matriz exibe Layout Types × PDFs em vez de Campos × PDFs.

---

### Elementos Especiais

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 18 | Tabelas + Loops/Foreach | 🟡 Parcial | [18-tables-loops.md](18-tables-loops.md) |
| 19 | Gráficos + Código de Barras + SVG Inline | 🟡 Parcial | [19-charts-barcode-svg.md](19-charts-barcode-svg.md) |
| 20 | Condicionais + Tematização Condicional | 🟡 Parcial | [20-conditional-visibility.md](20-conditional-visibility.md) |
| 21 | Fontes Customizadas + Estilos | 🟡 Parcial | [21-fonts-styles.md](21-fonts-styles.md) |

**Principais gaps:** JsBarcode CDN ausente no template exportado; SVG inline não implementado (FR32); Tematização Condicional (variações cor/imagem) sem UI; `@font-face` embedding ausente no ZIP.

---

### Output / Export

| # | Funcionalidade | Status | Arquivo |
|---|---------------|--------|---------|
| 27 | Geração de index.html (Output Template) | 🔴 Crítico | [27-index-html.md](27-index-html.md) |

**Gaps críticos:** ZIP sem `css/style.css`, sem `assets/`, com referência `../Bibliotecas/js/` externa — **NFR7 violado** (ZIP não é autocontido; template não renderiza localmente).

---

## Top 10 Gaps Mais Críticos (Backlog Prioritário)

| Prioridade | Gap | Funcionalidade | Impacto |
|-----------|-----|---------------|---------|
| 1 | ZIP sem `css/style.css` e sem `assets/` — output quebrado | 27-index-html | 🔴 Todo export |
| 2 | ZIP depende de `../Bibliotecas/js/` externas — NFR7 violado | 27-index-html | 🔴 Autocontido |
| 3 | CSS de cor/borda/background não aplicado no HTML gerado — fidelidade visual 50-60% | 03-canvas-renderizacao | 🔴 Toda renderização |
| 4 | Edições Monaco não chegam ao ZIP de export (regenera do zero) | 14c-exportar | 🔴 Edições manuais perdidas |
| 5 | Extração automática de imagens do PDF para `assets/` não confirmada | 26-assets | 🔴 FR14 |
| 6 | Âncoras de layout hardcoded como `[]` — SyncView sem âncoras visuais | 12-sync-view-compare | 🟡 FR28 |
| 7 | Funções de paginação runtime ausentes no `base.js` gerado | 17-pagination-header-footer | 🟡 Templates multi-página |
| 8 | Gráficos com `mapped: 0` hardcoded — cobertura incorreta | 09-coverage-confidence | 🟡 Métricas |
| 9 | Tipo `moved` nunca gerado no Diff Mode — diff parcialmente cego | 11-diff-mode | 🟡 FR41 |
| 10 | Bibliotecas é asset manager, não catálogo de componentes | 23-bibliotecas | 🟡 FR27a (propósito) |

---

## Como Usar Esta Auditoria

1. **Para priorizar backlog:** ordenar pela coluna de prioridade acima + consultar gaps de cada arquivo
2. **Para criar stories:** cada arquivo tem seção "Backlog Gerado" com itens prontos para virar stories
3. **Para avaliar cobertura:** status 🟡/🔴 indica que a funcionalidade existe mas com gaps — não é retrabalho do zero
4. **Para agente de análise:** cada arquivo segue estrutura: Planejado → Frontend → Backend → Gaps → Backlog → Status
