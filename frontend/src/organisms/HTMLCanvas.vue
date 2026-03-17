<template>
  <div class="html-canvas" data-testid="html-canvas">
    <!-- Scrollable container -->
    <div
      ref="scrollContainerRef"
      class="html-canvas__scroll"
      @scroll="onScroll"
    >
      <!-- Scaled content wrapper -->
      <div
        class="html-canvas__content"
        :style="{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }"
        data-testid="html-canvas-content"
      >
        <template v-for="(page, index) in pages" :key="page.pageNum">
          <!-- Page wrapper (observed for lazy loading) -->
          <div
            :ref="(el) => setPageRef(el, page.pageNum)"
            :data-page-wrapper="page.pageNum"
            class="html-canvas__page-wrapper"
            :style="{ width: `${pageWidth}px` }"
          >
            <!-- Page with relative positioning for guides overlay -->
            <div
              class="html-canvas__page"
              :style="{ width: `${pageWidth}px`, minHeight: `${pageHeight}px` }"
              :data-page="page.pageNum"
            >
              <!-- Actual page content or placeholder -->
              <iframe
                v-if="isPageVisible(page.pageNum)"
                :srcdoc="buildPageSrcdoc(page.html, page.css)"
                :title="`Página ${page.pageNum}`"
                class="html-canvas__iframe"
                :style="{ width: `${pageWidth}px`, height: `${pageHeight}px` }"
                sandbox="allow-same-origin"
                scrolling="no"
                data-testid="html-canvas-iframe"
              />
              <div
                v-else
                class="html-canvas__placeholder"
                :style="{ width: `${pageWidth}px`, height: `${pageHeight}px` }"
                :aria-label="`Placeholder página ${page.pageNum}`"
              />

              <!-- Guides overlay per page -->
              <CanvasGuides
                :page-width="pageWidth"
                :page-height="pageHeight"
                :margins="defaultMargins"
                :header-height="headerHeight"
                :footer-height="footerHeight"
                :column-positions="columnPositions"
              />

              <!-- Coverage overlay per page -->
              <CoverageOverlay
                target="canvas"
                :visible="editorStore.coverageMode"
              />
            </div>
          </div>

          <!-- Page break divider (after every page except the last) -->
          <div
            v-if="index < pages.length - 1"
            class="html-canvas__page-break"
            role="separator"
            aria-label="Quebra de página"
            data-testid="page-break"
          >
            <span class="html-canvas__page-break-line" />
            <span class="html-canvas__page-break-label">--- QUEBRA DE PÁGINA ---</span>
            <span class="html-canvas__page-break-line" />
          </div>
        </template>

        <!-- Empty state -->
        <div v-if="pages.length === 0" class="html-canvas__empty" data-testid="html-canvas-empty">
          <span>Nenhum template carregado</span>
        </div>
      </div>
    </div>

    <!-- Footer: zoom controls -->
    <div class="html-canvas__footer">
      <ZoomControls />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useGenerationStore } from '@/stores/generation'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import { useCanvas } from '@/composables/useCanvas'
import ZoomControls from '@/molecules/ZoomControls.vue'
import CanvasGuides from '@/molecules/CanvasGuides.vue'
import CoverageOverlay from '@/organisms/CoverageOverlay.vue'

// ─── Page Sizes ───────────────────────────────────────────────────────────────
const PAGE_SIZES: Record<string, { width: number; height: number }> = {
  A4: { width: 794, height: 1123 },
  Letter: { width: 816, height: 1056 },
}

// ─── Stores & Composable ─────────────────────────────────────────────────────
const generationStore = useGenerationStore()
const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const { zoomLevel, visiblePages, setupObserver, observePage, unobservePage, teardownObserver, isPageVisible } =
  useCanvas()

// ─── Refs ─────────────────────────────────────────────────────────────────────
const scrollContainerRef = ref<HTMLElement | null>(null)
const pageRefs = ref<Map<number, HTMLElement>>(new Map())

// ─── Page Dimensions ──────────────────────────────────────────────────────────
const pageSize = computed(() => {
  const sizeKey = (templateStore.documentTree?.root?.properties?.pageSize as string) ?? 'A4'
  return PAGE_SIZES[sizeKey] ?? PAGE_SIZES['A4']!
})
const pageWidth = computed(() => pageSize.value.width)
const pageHeight = computed(() => pageSize.value.height)

// ─── Guide Positions ─────────────────────────────────────────────────────────
const defaultMargins = { top: 40, bottom: 40, left: 40, right: 40 }
const headerHeight = 80
const footerHeight = 60
const columnPositions: number[] = []

// ─── Pages Parsing ────────────────────────────────────────────────────────────
interface CanvasPage {
  pageNum: number
  html: string
  css: string
}

const pages = computed<CanvasPage[]>(() => {
  const draft = generationStore.templateDraft
  if (!draft) return []

  const css = draft.css ?? ''
  const html = draft.html ?? ''

  // Parse <div class="page" data-page="N"> elements
  const parser = typeof DOMParser !== 'undefined' ? new DOMParser() : null
  if (!parser) {
    // SSR / test fallback: treat entire HTML as page 1
    return [{ pageNum: 1, html, css }]
  }

  const doc = parser.parseFromString(`<div id="_root">${html}</div>`, 'text/html')
  const pageEls = doc.querySelectorAll('[data-page]')

  if (pageEls.length === 0) {
    // No page dividers — treat entire HTML as single page
    return [{ pageNum: 1, html, css }]
  }

  const result: CanvasPage[] = []
  pageEls.forEach((el) => {
    const num = Number((el as HTMLElement).dataset.page)
    result.push({ pageNum: isNaN(num) ? result.length + 1 : num, html: el.outerHTML, css })
  })
  return result
})

// ─── Iframe srcdoc Builder ───────────────────────────────────────────────────
function buildPageSrcdoc(html: string, css: string): string {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { overflow: hidden; }
${css}
</style>
</head>
<body>${html}</body>
</html>`
}

// ─── Page Refs & Observer ─────────────────────────────────────────────────────
function setPageRef(el: unknown, pageNum: number) {
  const htmlEl = el as HTMLElement | null
  if (htmlEl) {
    if (!pageRefs.value.has(pageNum)) {
      pageRefs.value.set(pageNum, htmlEl)
      observePage(htmlEl)
    }
  } else {
    const existing = pageRefs.value.get(pageNum)
    if (existing) {
      unobservePage(existing)
      pageRefs.value.delete(pageNum)
    }
  }
}

function onScroll(_event: Event) {
  // scroll position tracking (reserved for future use)
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(() => {
  if (scrollContainerRef.value) {
    setupObserver(scrollContainerRef.value)
  }

  // Seed initial visibility: mark first page visible
  if (pages.value.length > 0) {
    const first = pages.value[0]!
    visiblePages.value = new Set([first.pageNum])
  }
})

onUnmounted(() => {
  teardownObserver()
  pageRefs.value.clear()
})

// Re-seed visible pages when template changes
watch(
  () => generationStore.templateDraft,
  () => {
    pageRefs.value.clear()
    nextTick(() => {
      if (pages.value.length > 0) {
        visiblePages.value = new Set([pages.value[0]!.pageNum])
      }
    })
  }
)
</script>

<style scoped>
.html-canvas {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-200, #e5e7eb);
}

/* Scrollable area */
.html-canvas__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem 1rem;
  scroll-behavior: smooth;
}

/* Zoom transform container */
.html-canvas__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  transform-origin: top center;
  /* width is dictated by page width */
}

/* Page wrapper (sentinel for IntersectionObserver) */
.html-canvas__page-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Individual page — "sheet of paper" appearance */
.html-canvas__page {
  position: relative;
  background: #ffffff;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -2px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* Iframe fills the page exactly */
.html-canvas__iframe {
  display: block;
  border: none;
  overflow: hidden;
}

/* Placeholder for lazy-loaded pages */
.html-canvas__placeholder {
  background: #f9fafb;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Page break separator */
.html-canvas__page-break {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  margin: 1.5rem 0;
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.html-canvas__page-break-line {
  flex: 1;
  height: 1px;
  border-top: 1px dashed var(--color-neutral-400, #9ca3af);
}

.html-canvas__page-break-label {
  white-space: nowrap;
  flex-shrink: 0;
}

/* Footer with zoom controls */
.html-canvas__footer {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  background: var(--color-neutral-50, #f9fafb);
  border-top: 1px solid var(--color-neutral-300, #d1d5db);
}

/* Empty state */
.html-canvas__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  font-size: 0.875rem;
  color: var(--color-neutral-400, #9ca3af);
}
</style>
