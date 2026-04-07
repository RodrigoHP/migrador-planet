<template>
  <div class="sync-view" data-testid="sync-view">
    <!-- Toolbar -->
    <div class="sync-view__toolbar">
      <span class="sync-view__title">🔗 Visualização Sincronizada</span>

      <!-- Scroll lock toggle -->
      <button
        class="sync-view__lock-btn"
        :class="{ 'sync-view__lock-btn--active': scrollLocked }"
        type="button"
        :aria-pressed="scrollLocked"
        :title="scrollLocked ? 'Scroll sincronizado (clique para desativar)' : 'Scroll independente (clique para sincronizar)'"
        @click="toggleScrollLock"
      >
        {{ scrollLocked ? '🔒 Scroll Sync' : '🔓 Scroll Livre' }}
      </button>
    </div>

    <!-- Split panels container -->
    <div class="sync-view__panels" data-testid="sync-panels">
      <!-- Canvas panel (left) -->
      <div
        class="sync-view__panel sync-view__panel--canvas"
        :style="{ flex: `0 0 ${leftWidth}%` }"
        data-testid="sync-panel-canvas"
      >
        <div class="sync-view__panel-header">
          <span class="sync-view__panel-label">🖥️ Canvas (Template)</span>
          <!-- Independent zoom for canvas -->
          <div class="sync-view__zoom" role="group" aria-label="Zoom do Canvas">
            <button
              class="sync-view__zoom-btn"
              type="button"
              :disabled="canvasZoom.zoomLevel.value <= canvasZoom.ZOOM_MIN"
              aria-label="Reduzir zoom canvas"
              @click="canvasZoom.zoomOut"
            >
              &minus;
            </button>
            <span class="sync-view__zoom-value">{{ canvasZoom.zoomLevel.value }}%</span>
            <button
              class="sync-view__zoom-btn"
              type="button"
              :disabled="canvasZoom.zoomLevel.value >= canvasZoom.ZOOM_MAX"
              aria-label="Aumentar zoom canvas"
              @click="canvasZoom.zoomIn"
            >
              +
            </button>
          </div>
        </div>
        <div
          ref="canvasPanelRef"
          class="sync-view__panel-scroll"
          data-testid="canvas-panel-scroll"
          @scroll="onCanvasScroll"
        >
          <div
            class="sync-view__panel-content"
            :style="{ transform: `scale(${canvasZoom.zoomLevel.value / 100})`, transformOrigin: 'top center' }"
          >
            <!-- Canvas pages -->
            <template v-if="pages.length > 0">
              <div
                v-for="page in pages"
                :key="page.pageNum"
                class="sync-view__page"
              >
                <iframe
                  :srcdoc="page.srcdoc"
                  :title="`Página Canvas ${page.pageNum}`"
                  class="sync-view__iframe"
                  :style="{ width: `${PAGE_WIDTH}px`, height: `${PAGE_HEIGHT}px` }"
                  sandbox="allow-same-origin allow-scripts"
                  scrolling="no"
                  data-testid="sync-canvas-iframe"
                />
                <!-- Coverage overlay for canvas -->
                <CoverageOverlay
                  target="canvas"
                  :visible="editorStore.coverageMode"
                />
                <!-- Layout anchors (canvas side) -->
                <LayoutAnchor
                  v-for="anchor in anchors"
                  :key="`canvas-${anchor.id}`"
                  :anchor-data="anchor"
                />
              </div>
            </template>
            <div v-else class="sync-view__empty">Nenhum template carregado</div>
          </div>
        </div>
      </div>

      <!-- Resizable divider -->
      <div
        class="sync-view__divider"
        role="separator"
        aria-label="Divisor redimensionável"
        data-testid="sync-divider"
        @mousedown="startResize"
      >
        <div class="sync-view__divider-handle" />
      </div>

      <!-- PDF panel (right) -->
      <div
        class="sync-view__panel sync-view__panel--pdf"
        :style="{ flex: `0 0 ${100 - leftWidth}%` }"
        data-testid="sync-panel-pdf"
      >
        <div class="sync-view__panel-header">
          <span class="sync-view__panel-label">📄 PDF (Referência)</span>
          <!-- Independent zoom for PDF -->
          <div class="sync-view__zoom" role="group" aria-label="Zoom do PDF">
            <button
              class="sync-view__zoom-btn"
              type="button"
              :disabled="pdfZoom.zoomLevel.value <= pdfZoom.ZOOM_MIN"
              aria-label="Reduzir zoom PDF"
              @click="pdfZoom.zoomOut"
            >
              &minus;
            </button>
            <span class="sync-view__zoom-value">{{ pdfZoom.zoomLevel.value }}%</span>
            <button
              class="sync-view__zoom-btn"
              type="button"
              :disabled="pdfZoom.zoomLevel.value >= pdfZoom.ZOOM_MAX"
              aria-label="Aumentar zoom PDF"
              @click="pdfZoom.zoomIn"
            >
              +
            </button>
          </div>
        </div>
        <div
          ref="pdfPanelRef"
          class="sync-view__panel-scroll"
          data-testid="pdf-panel-scroll"
          @scroll="onPdfScroll"
        >
          <div
            class="sync-view__panel-content"
            :style="{ transform: `scale(${pdfZoom.zoomLevel.value / 100})`, transformOrigin: 'top center' }"
          >
            <!-- PDF pages — 1 canvas por página do PDF -->
            <template v-if="hasPdf">
              <div
                v-for="pageNum in totalPdfPages"
                :key="pageNum"
                class="sync-view__pdf-page"
              >
                <canvas
                  :ref="(el) => setPdfCanvasRef(el, pageNum)"
                  class="sync-view__pdf-canvas"
                  :aria-label="`PDF página ${pageNum}`"
                  data-testid="sync-pdf-canvas"
                />
                <!-- Coverage overlay for PDF -->
                <CoverageOverlay
                  target="pdf"
                  :visible="editorStore.coverageMode"
                />
              </div>
            </template>
            <div v-else class="sync-view__empty">Nenhum PDF disponível</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useEditorStore } from '@/stores/editorStore'
import { useGenerationStore } from '@/stores/generation'
import { useSessionStore } from '@/stores/session'
import { useSync } from '@/composables/useSync'
import { useZoom } from '@/composables/useZoom'
import { usePdfRenderer } from '@/composables/usePdfRenderer'
import CoverageOverlay from '@/organisms/CoverageOverlay.vue'
import LayoutAnchor from '@/molecules/LayoutAnchor.vue'
import type { AnchorData } from '@/molecules/LayoutAnchor.vue'

// ─── Page Dimensions ──────────────────────────────────────────────────────────
const PAGE_WIDTH = 794
const PAGE_HEIGHT = 1123

// ─── Stores ───────────────────────────────────────────────────────────────────
const editorStore = useEditorStore()
const generationStore = useGenerationStore()
const sessionStore = useSessionStore()

// ─── Composables ──────────────────────────────────────────────────────────────
const { scrollLocked, syncScroll, syncSelection, toggleScrollLock } = useSync()
// Independent zoom instances per panel
const canvasZoom = useZoom(100)
const pdfZoom = useZoom(100)
const renderer = usePdfRenderer()

// ─── Refs ─────────────────────────────────────────────────────────────────────
const canvasPanelRef = ref<HTMLElement | null>(null)
const pdfPanelRef = ref<HTMLElement | null>(null)
const pdfCanvasRefs = ref<Map<number, HTMLCanvasElement>>(new Map())

function setPdfCanvasRef(el: unknown, pageNum: number) {
  const canvas = el as HTMLCanvasElement | null
  if (canvas) {
    pdfCanvasRefs.value.set(pageNum, canvas)
  } else {
    pdfCanvasRefs.value.delete(pageNum)
  }
}

// ─── Split panel resize state ─────────────────────────────────────────────────
const leftWidth = ref<number>(50) // percentage

function startResize(event: MouseEvent) {
  event.preventDefault()
  const container = (event.currentTarget as HTMLElement).closest('.sync-view__panels') as HTMLElement | null
  if (!container) return

  const startX = event.clientX
  const startLeft = leftWidth.value
  const containerWidth = container.getBoundingClientRect().width

  function onMouseMove(e: MouseEvent) {
    const delta = e.clientX - startX
    const deltaPct = (delta / containerWidth) * 100
    leftWidth.value = Math.max(20, Math.min(80, startLeft + deltaPct))
  }

  function onMouseUp() {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// ─── Canvas pages ─────────────────────────────────────────────────────────────
interface SyncPage {
  pageNum: number
  srcdoc: string
}

const pages = computed<SyncPage[]>(() => {
  const draft = generationStore.templateDraft
  if (!draft) return []
  const css = draft.css ?? ''
  const html = draft.html ?? ''

  const parser = typeof DOMParser !== 'undefined' ? new DOMParser() : null
  if (!parser) return [{ pageNum: 1, srcdoc: buildSrcdoc(html, css) }]

  const doc = parser.parseFromString(`<div id="_root">${html}</div>`, 'text/html')
  const layoutEls = doc.querySelectorAll('[data-layout-type]')
  if (layoutEls.length === 0) return [{ pageNum: 1, srcdoc: buildSrcdoc(html, css) }]

  const result: SyncPage[] = []
  layoutEls.forEach((layoutEl) => {
    // FIX: stage5 gera 1 .page[data-layout-type] com N .page-content filhos (1 por
    // página física do PDF). Cada .page-content tem .flow position:absolute;top:0 →
    // ao renderizar no mesmo iframe, as páginas físicas ficam sobrepostas.
    // Solução: criar 1 SyncPage por .page-content, clonando o wrapper externo para
    // manter a âncora position:relative dos filhos position:absolute.
    const pageContents = Array.from(layoutEl.children).filter(
      (child) => child.classList.contains('page-content'),
    )
    if (pageContents.length > 1) {
      pageContents.forEach((pageContent) => {
        const wrapper = layoutEl.cloneNode(false) as Element
        wrapper.appendChild(pageContent.cloneNode(true))
        result.push({
          pageNum: result.length + 1,
          srcdoc: buildSrcdoc(wrapper.outerHTML, css),
        })
      })
    } else {
      result.push({
        pageNum: result.length + 1,
        srcdoc: buildSrcdoc(layoutEl.outerHTML, css),
      })
    }
  })
  return result
})

function buildSrcdoc(html: string, css: string): string {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>* { box-sizing: border-box; margin: 0; padding: 0; } body { overflow: hidden; } ${css}</style></head><body>${html}</body></html>`
}

// ─── PDF ──────────────────────────────────────────────────────────────────────
const totalPdfPages = computed(() => renderer.totalPages.value)
const hasPdf = computed(() => sessionStore.uploadedPdfs.length > 0 && totalPdfPages.value > 0)

async function loadPdf() {
  const pdf = sessionStore.uploadedPdfs[0]
  if (!pdf) return
  await renderer.loadPdf(pdf.bytes)
  // totalPdfPages muda → template re-renderiza N canvases → aguarda nextTick
  await nextTick()
  await renderAllPdfPages()
}

async function renderAllPdfPages() {
  if (!renderer.pdfDocument.value) return
  for (let page = 1; page <= totalPdfPages.value; page++) {
    const canvas = pdfCanvasRefs.value.get(page)
    if (canvas) {
      await renderer.renderPage(page, canvas)
    }
  }
}

// Re-renderiza se o documento PDF for trocado externamente
watch(totalPdfPages, async (n) => {
  if (n > 0) {
    await nextTick()
    await renderAllPdfPages()
  }
})

// ─── Scroll handlers ──────────────────────────────────────────────────────────
function onCanvasScroll() {
  if (canvasPanelRef.value && pdfPanelRef.value) {
    syncScroll(canvasPanelRef.value, pdfPanelRef.value)
  }
}

function onPdfScroll() {
  if (pdfPanelRef.value && canvasPanelRef.value) {
    syncScroll(pdfPanelRef.value, canvasPanelRef.value)
  }
}

// ─── Layout anchors (sample data — replaced by real data in production) ────────
const anchors = computed<AnchorData[]>(() => [])

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadPdf()
})

onUnmounted(() => {
  // cleanup handled by renderer internally
})

// Expose for tests
defineExpose({ scrollLocked, canvasZoom, pdfZoom, syncSelection })
</script>

<style scoped>
.sync-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-100, #f3f4f6);
}

/* Toolbar */
.sync-view__toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
  padding: 0.4rem 0.75rem;
  background: var(--color-neutral-50, #f9fafb);
  border-bottom: 1px solid var(--color-neutral-300, #d1d5db);
}

.sync-view__title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
  flex: 1;
}

.sync-view__lock-btn {
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.375rem;
  background: #fff;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.sync-view__lock-btn--active {
  background: var(--color-primary-50, #eff6ff);
  border-color: var(--color-primary-300, #93c5fd);
  color: var(--color-primary-700, #1d4ed8);
}

/* Split panels */
.sync-view__panels {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.sync-view__panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.sync-view__panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0.375rem 0.625rem;
  background: var(--color-neutral-50, #f9fafb);
  border-bottom: 1px solid var(--color-neutral-200, #e5e7eb);
}

.sync-view__panel-label {
  flex: 1;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-600, #4b5563);
}

/* Zoom controls inside panel header */
.sync-view__zoom {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.sync-view__zoom-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.25rem;
  background: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  line-height: 1;
}

.sync-view__zoom-btn:hover:not(:disabled) {
  background: var(--color-neutral-200, #e5e7eb);
}

.sync-view__zoom-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sync-view__zoom-value {
  min-width: 2.75rem;
  text-align: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
}

/* Scrollable panel body */
.sync-view__panel-scroll {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
}

.sync-view__panel-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  transform-origin: top center;
}

/* Individual canvas page */
.sync-view__page {
  position: relative;
  background: #fff;
  box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.sync-view__iframe {
  display: block;
  border: none;
  overflow: hidden;
}

/* PDF pages — empilhadas verticalmente (espelha layout do painel canvas) */
.sync-view__pdf-page {
  position: relative;
  display: inline-block;
  background: #fff;
  box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.sync-view__pdf-canvas {
  display: block;
  max-width: 100%;
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  border-radius: 0.375rem;
}

/* Empty state */
.sync-view__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  font-size: 0.875rem;
  color: var(--color-neutral-400, #9ca3af);
}

/* Resizable divider */
.sync-view__divider {
  flex-shrink: 0;
  width: 6px;
  background: var(--color-neutral-200, #e5e7eb);
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
  position: relative;
  z-index: 10;
}

.sync-view__divider:hover {
  background: var(--color-primary-200, #bfdbfe);
}

.sync-view__divider-handle {
  width: 2px;
  height: 2rem;
  background: var(--color-neutral-400, #9ca3af);
  border-radius: 1px;
}
</style>
