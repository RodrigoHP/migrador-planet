# Auditoria: Sync View / Compare (PDF original vs Canvas HTML)

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

### FR28 — Sync View (`docs/prd-v3.md` linha 260)
- Painel central (aba Sincronizar): split view Canvas (template gerado) à esquerda, PDF (documento original) à direita
- Scroll sincronizado entre os dois painéis
- Seleção sincronizada: clicar no Canvas destaca bounding box correspondente no PDF (usando coordenadas detectadas pelo pipeline)
- Âncoras de layout: marcadores conectando visualmente estrutura do template ao original
- Integra com Modo Cobertura
- Usa página representativa do Layout Type ativo
- Zoom independente por painel

### FR43 — PDF Referência (`docs/prd-v3.md` linha 264)
- Aba separada "PDF Referência": PDF original da página representativa via PDF.js
- Seletor de documento (dropdown com todos os PDFs)
- Navegação entre páginas
- Indicador de cluster ("Página representativa de N páginas")
- Modo Cobertura ativo: overlays por categoria (🟦 texto, 🟩 detectado+mapeado, 🟥 não mapeado, 🟨 não confirmado, 🟪 tabela, 📊 gráfico)
- Zoom independente do Canvas

### Sync View Spec (`docs/ideias/ux/sync_view_layout_anchors_spec.md`)
- Split view com scroll e seleção sincronizados (seções 4 e 5)
- Âncoras de layout visíveis em ambos os painéis conectando estrutura (seção 10)
- Usa página representativa por Layout Type (seção 12)
- Integração com Coverage Mode (seção 6)
- Layout Types independentes com seletor (seção 11)

### Wireframe — Aba Sincronizar (`docs/wireframes/wireframes-mid-fi.md` linha 360)
- Split view Canvas (esquerda) + PDF (direita) com 50/50 e divisor redimensionável
- Scroll sincronizado (rolar um painel rola o outro)
- Seleção sincronizada: clicar no Canvas destaca bounding box correspondente no PDF
- Âncoras de layout como pontos de referência em ambos os painéis
- Zoom independente por painel (controles individuais de + e -)
- CoverageOverlay integrado em ambos quando Modo Cobertura ativo

---

## Frontend — Status de Implementação

### SyncView.vue (`frontend/src/organisms/SyncView.vue`)
**Implementado:**
- Split view Canvas (esquerda) + PDF (direita) com proporção configurável via divisor redimensionável (`startResize` com `mousedown/mousemove/mouseup`)
- Proporção inicial 50/50 com limites 20%-80%
- Scroll sincronizado: `onCanvasScroll` e `onPdfScroll` chamam `syncScroll` de `useSync`; toggle de scroll lock com botão 🔒/🔓
- Zoom independente por painel via `useZoom(100)` instanciado separadamente para canvas e PDF
- Renderização do Canvas: extrai páginas do `generationStore.templateDraft` como `<iframe srcdoc>` com `[data-layout-type]` — corretamente usa `data-layout-type` (não `data-page`) após fix documentado no código
- Renderização do PDF: usa `usePdfRenderer`, renderiza todas as páginas em `<canvas>` empilhados
- `CoverageOverlay` integrado em ambos os painéis (target `'canvas'` e `'pdf'`), visível quando `editorStore.coverageMode`
- `LayoutAnchor` importado e renderizado no painel Canvas

**Gaps:**
- `anchors` computed retorna sempre `[]` (array vazio hardcoded em linha 343: `const anchors = computed<AnchorData[]>(() => [])`) — âncoras de layout não são carregadas do pipeline
- `syncSelection` exposto via `defineExpose` mas não conectado a cliques nos `<iframe>` do Canvas — seleção sincronizada não funciona
- SyncView carrega sempre `sessionStore.uploadedPdfs[0]` — não usa a página representativa do Layout Type ativo, ignora o Layout Type selecionado na toolbar
- Não há passagem de page representativa do layoutStore para o renderer (ignora `representativePage`)

### useSync.ts (`frontend/src/composables/useSync.ts`)
**Implementado:**
- `scrollLocked: Ref<boolean>` — flag de sincronização de scroll
- `syncScroll(sourcePanel, targetPanel)` — mapeamento proporcional `scrollTop / (scrollHeight - clientHeight)` com guarda anti-recursão via `isSyncing`
- `syncSelection(canvasElementId)` — salva `selectedElementId` (para consumo externo)
- `toggleScrollLock()`, `clearSelection()`

**Gap:**
- `syncSelection` só registra o elementId selecionado; não há consumidor ativo que ouça `selectedElementId` e destaque o bounding box correspondente no painel PDF. A cadeia de highlight Canvas → PDF não está completa.

### PDFReference.vue (`frontend/src/organisms/PDFReference.vue`)
**Implementado:**
- Toolbar com seletor de documento (dropdown de `sessionStore.uploadedPdfs`)
- Navegação de página (◀ Anterior / Próxima ▶) via `renderer.prevPage()` / `renderer.nextPage()`
- Indicador de cluster: "Página representativa de N páginas" (visível quando `clusterPageCount > 1`)
- Controles de zoom: editorStore.pdfZoom (50-200%)
- `CoverageOverlay target='pdf'` integrado e visível quando `editorStore.coverageMode`
- PDF carregado via 3 tiers: memória → IndexedDB → servidor
- Watch em `representativePage`: ao trocar Layout Type, navega automaticamente para a página representativa
- Context menu ao clicar com botão direito no canvas (criar campo/seção)

**Gap:**
- Zoom controlado por `editorStore.pdfZoom` mas renderização não reaplica ao fazer zoom: `renderCurrentPage()` re-renderiza na resolução fixa sem multiplicar pelo zoom. O zoom visual é apenas CSS transform implícito via fator no renderer, sem `viewport.scale` dinâmico.

### PDFViewer.vue (`frontend/src/organisms/PDFViewer.vue`)
- Componente básico (`pdfBytes + pageRef + boundingBox` props)
- Renderização simples com navegação de página
- Não tem CoverageOverlay integrado
- Separado do PDFReference — aparentemente um componente legado ou alternativo

### session.ts (scroll sync state)
- `pdfZoom` persiste no estado da sessão
- `coverageMode` e `diffMode` persistidos em `editorStore`
- Não há state de scroll position persistido

---

## Backend — Status de Implementação

Sync View não requer backend dedicado. Depende de dados gerados pelo pipeline:
- `generationStore.templateDraft.html` / `.css` para o painel Canvas
- `sessionStore.uploadedPdfs[*].bytes` para renderização PDF
- `layoutStore.activeLayout.representativePages` para navegação da página representativa
- `coverageStore.overlayDataByLayout` para os overlays

**Gap indireto:**
- O pipeline não retorna dados de âncoras de layout prontos para consumo pelo SyncView. A spec (sync_view_layout_anchors_spec.md seções 8-10) prevê que anchors são detectados durante o pipeline, mas não há campo `anchors` na resposta do pipeline sendo consumido.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Âncoras de layout sempre vazias — `anchors = []` hardcoded, nenhuma âncora carregada do pipeline | 🔴 Crítico | Frontend / SyncView.vue:343 | FR28 — âncoras de layout / sync_view_spec seção 10 |
| 2 | Seleção sincronizada não funcional — `syncSelection` não conectado a cliques nos iframes do Canvas | 🔴 Crítico | Frontend / SyncView.vue + useSync.ts | FR28 — "clicar no Canvas destaca bounding box no PDF" |
| 3 | SyncView ignora Layout Type ativo e página representativa — sempre usa primeiro PDF carregado | 🟡 Importante | Frontend / SyncView.vue:302-308 | FR28 — "usa página representativa do Layout Type ativo" |
| 4 | Highlight do PDF ao selecionar elemento no Canvas não implementado — `selectedElementId` sem consumidor | 🟡 Importante | Frontend / useSync.ts | FR28 — seleção sincronizada / sync_view_spec seção 5 |
| 5 | PDFReference zoom não reaplica escala de renderização — zoom visual sem efeito real de resolução | 🟢 Menor | Frontend / PDFReference.vue:304-307 | FR43 — zoom independente |
| 6 | Âncoras ausentes na resposta do pipeline — backend não retorna campo `anchors` estruturado | 🟡 Importante | Backend / pipeline output | sync_view_spec seção 8 |
| 7 | PDFViewer.vue (componente alternativo) sem CoverageOverlay — pode ser usado em contextos que não têm overlay de cobertura | 🟢 Menor | Frontend / PDFViewer.vue | FR43 — overlays no Modo Cobertura |

---

## Backlog Gerado

1. **[Frontend] Implementar âncoras de layout no SyncView** — substituir `anchors = []` por consumo de dados reais; definir estrutura `AnchorData` no pipeline e populá-la via store; renderizar `LayoutAnchor` em ambos os painéis com linha conectora visual.
2. **[Backend] Retornar âncoras de layout na resposta do pipeline** — stage de análise (Stage 3 ou 5) deve emitir lista de anchors por Layout Type com `{id, label, bbox_canvas, bbox_pdf}`; consumida pelo frontend via `layoutStore` ou store dedicado.
3. **[Frontend] Implementar seleção sincronizada no SyncView** — conectar clique nos `<iframe>` do Canvas a `syncSelection(elementId)` via `postMessage`; adicionar watch em `selectedElementId` que destaca o bounding box correspondente no painel PDF usando dados de `coverageStore.overlayData`.
4. **[Frontend] Usar página representativa do Layout Type ativo no SyncView** — em `loadPdf()`, ler `layoutStore.activeLayout.representativePages[0]` e navegar para essa página ao carregar o PDF; reagir a mudanças de layout ativo.
5. **[Frontend] Corrigir zoom do PDFReference para aplicar `scale` na renderização** — em `renderCurrentPage()`, passar `editorStore.pdfZoom / 100` como `scale` no `viewport.getViewport({ scale })` do PDF.js.

---

## Status Geral

🟡 Parcial — O split view com scroll sincronizado e zoom independente por painel está implementado e funcional. PDFReference com seletor de documento, navegação, indicador de cluster e CoverageOverlay também estão bem implementados. Os gaps críticos são: âncoras de layout hardcoded como array vazio (nenhuma âncora visível), seleção sincronizada não funcional (syncSelection não conectado aos iframes), e SyncView ignorando o Layout Type ativo para selecionar a página representativa do PDF.
