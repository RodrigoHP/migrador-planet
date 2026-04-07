# Auditoria: Zoom

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR7** — Canvas HTML deve suportar zoom de 50% a 125% com guias visuais.

**FR28** — Sync View deve ter zoom independente por painel (Canvas + PDF).

**FR43** — Aba PDF Referência deve ter zoom independente do Canvas.

Fonte: `docs/prd-v3.md` FR7, FR28, FR43.

---

## Frontend — Status de Implementação

**useCanvas.ts** (`frontend/src/composables/useCanvas.ts`) — **Implementado:**
- `ZOOM_MIN = 50`, `ZOOM_MAX = 125`, `ZOOM_STEP = 10`
- `zoomLevel` computado sincronizado com `editorStore.zoomLevel` via Pinia
- `zoomIn()`, `zoomOut()`, `setZoom()` com clamping correto

**ZoomControls.vue** (`frontend/src/molecules/ZoomControls.vue`) — **Implementado:**
- Botões − / + com disable nos limites
- Valor atual exibido com `aria-live` (acessibilidade)
- Consome `useCanvas()` — sincronizado com editorStore
- Posicionamento: renderizado no Canvas, não na TopToolbar

**useZoom.ts** (`frontend/src/composables/useZoom.ts`) — **Implementado (standalone):**
- Composable independente com estado isolado por chamada
- `ZOOM_MIN = 50`, `ZOOM_MAX = 200`, `ZOOM_STEP = 10`
- **Divergência:** ZOOM_MAX = 200, diferente do `useCanvas` (125) e do FR7 (125%)
- Usado para painéis com zoom independente (SyncView, PDF Renderer)

**editorStore:** persiste `zoomLevel` (Canvas) e `pdfZoom` (PDF Referência) separadamente — estado correto para zoom independente por painel.

**O que falta no frontend:**
- Zoom por mousewheel (Ctrl+scroll) não confirmado implementado no Canvas
- Sem controle de zoom na TopToolbar (gap identificado na auditoria 24)
- ZoomControls para o painel PDF Referência / SyncView não verificado se existe UI dedicada
- Atalho de teclado para zoom (Ctrl++, Ctrl+−) não confirmado
- "Fit to page" / reset zoom não implementado

---

## Backend — Status de Implementação

Zoom é funcionalidade exclusivamente de frontend — sem dependências de backend.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | `useZoom.ts` tem ZOOM_MAX = 200, diverge do FR7 (50–125%) e do `useCanvas` (125) — inconsistência entre composables | 🟡 Importante | Frontend | FR7 |
| 2 | Zoom por mousewheel (Ctrl+scroll) não confirmado implementado | 🟡 Importante | Frontend | FR7 |
| 3 | ZoomControls da TopToolbar ausente — zoom só acessível no footer do Canvas | 🟡 Importante | Frontend | FR7 |
| 4 | UI de zoom para painel PDF Referência e SyncView não confirmada | 🟡 Importante | Frontend | FR28, FR43 |
| 5 | Reset / "Fit to page" não implementado | 🟢 Menor | Frontend | FR7 |
| 6 | Atalhos de teclado para zoom (Ctrl++/Ctrl+−) não confirmados | 🟢 Menor | Frontend | FR7 |

---

## Backlog Gerado

1. **Harmonizar ZOOM_MAX** — Alinhar `useZoom.ts` com `useCanvas.ts` (max 125% para Canvas, documentar se painéis PDF podem ir até 200%).
2. **Zoom por mousewheel** — Implementar handler `wheel` no Canvas com `Ctrl+scroll`, usando `useCanvas.setZoom()`.
3. **ZoomControls na TopToolbar** — Integrar ZoomControls.vue na área direita da toolbar (ver auditoria 24).
4. **UI de zoom para PDF/SyncView** — Verificar se pdfZoom tem controles visuais nos painéis PDF Referência e SyncView; implementar se ausentes.
5. **Botão "Fit to page"** — Adicionar opção para resetar zoom para valor que encaixa a página na viewport.

---

## Status Geral

🟡 Parcial — Infraestrutura de zoom está implementada (useCanvas, useZoom, ZoomControls, estado persistido na store). O gap principal é a inconsistência entre composables (max 125 vs 200), ausência de zoom por mousewheel e posicionamento do controle de zoom fora da toolbar principal conforme especificado no FR7.
