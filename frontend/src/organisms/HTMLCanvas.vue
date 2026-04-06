<template>
  <div
    class="html-canvas"
    data-testid="html-canvas"
    tabindex="0"
    @keydown="onCanvasKeyDown"
    @dragover.prevent="onFieldDragOver"
    @dragleave="onFieldDragLeave"
    @drop.prevent="onFieldDrop"
    @dragend="onFieldDragEnd"
  >
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
                sandbox="allow-same-origin allow-scripts"
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

              <!-- Selection overlay per page -->
              <CanvasSelectionOverlay
                :page-width="pageWidth"
                :page-height="pageHeight"
                :zoom-level="zoomLevel"
                :page-num="page.pageNum"
                :drop-target-node-id="dropTargetNodeId"
                @element-selected="onElementSelected"
                @selection-cleared="onSelectionCleared"
              />

              <!-- Snap line overlay (Story 14.7) -->
              <SnapLineOverlay
                v-if="editorStore.snapEnabled && activeSnapLines.length > 0"
                :snap-lines="activeSnapLines"
                :canvas-width="pageWidth"
                :canvas-height="pageHeight"
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

    <!-- Alignment toolbar (multi-select) -->
    <AlignmentToolbar
      :visible="isMultiSelecting"
      :position="alignToolbarPos"
      :selected-count="multiSelection.size"
      @align="onAlignAction"
      @distribute="onDistributeAction"
    />

    <!-- Footer: page navigation + zoom controls -->
    <div class="html-canvas__footer">
      <div v-if="totalPages > 1" class="html-canvas__page-nav" role="group" aria-label="Navegação de páginas">
        <button
          class="html-canvas__page-nav-btn"
          type="button"
          :disabled="currentPage <= 1"
          aria-label="Página anterior"
          @click="navigateToPrevPage"
        >&#8592;</button>
        <span class="html-canvas__page-nav-label">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="html-canvas__page-nav-btn"
          type="button"
          :disabled="currentPage >= totalPages"
          aria-label="Próxima página"
          @click="navigateToNextPage"
        >&#8594;</button>
      </div>
      <ZoomControls />
    </div>
  </div>

  <!-- Hierarchy popup (teleported to body) -->
  <HierarchyPopup
    :visible="hierarchyPopup.visible"
    :x="hierarchyPopup.x"
    :y="hierarchyPopup.y"
    :ancestor-ids="hierarchyPopup.ancestorIds"
    @select="selectFromHierarchy"
    @close="hideHierarchyPopup"
  />
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useGenerationStore } from '@/stores/generation'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import { useLayoutStore } from '@/stores/layout'
import { useCanvas } from '@/composables/useCanvas'
import { useCanvasInteraction } from '@/composables/useCanvasInteraction'
import ZoomControls from '@/molecules/ZoomControls.vue'
import CanvasGuides from '@/molecules/CanvasGuides.vue'
import CoverageOverlay from '@/organisms/CoverageOverlay.vue'
import CanvasSelectionOverlay from '@/organisms/CanvasSelectionOverlay.vue'
import HierarchyPopup from '@/molecules/HierarchyPopup.vue'
import AlignmentToolbar from '@/molecules/AlignmentToolbar.vue'
import SnapLineOverlay from '@/components/SnapLineOverlay.vue'
import { generateAllBorderOverrides } from '@/utils/borderStyleGenerator'
import { useCanvasKeyboard } from '@/composables/useCanvasKeyboard'
import { useMappingStore } from '@/stores/mapping'
import {
  alignLeft, alignCenterH, alignRight,
  alignTop, alignMiddleV, alignBottom,
  distributeH, distributeV,
  type Delta,
} from '@/composables/useAlignmentTools'

// ─── Page Sizes ───────────────────────────────────────────────────────────────
const PAGE_SIZES: Record<string, { width: number; height: number }> = {
  A4: { width: 794, height: 1123 },
  Letter: { width: 816, height: 1056 },
}

// ─── Stores & Composable ─────────────────────────────────────────────────────
const generationStore = useGenerationStore()
const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const layoutStore = useLayoutStore()
const mappingStore = useMappingStore()
const { zoomLevel, visiblePages, scrollToPage, setupObserver, observePage, unobservePage, teardownObserver, isPageVisible } =
  useCanvas()
const {
  hierarchyPopup,
  selectFromTree,
  selectFromHierarchy,
  hideHierarchyPopup,
  multiSelection,
  isMultiSelecting,
  elementBoxes,
  activeSnapLines,
} = useCanvasInteraction()

const { handleKeyDown: onCanvasKeyDown } = useCanvasKeyboard()

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

// ─── Page Navigation ─────────────────────────────────────────────────────────
const currentPage = computed(() => {
  if (visiblePages.value.size === 0) return 1
  return Math.max(...visiblePages.value)
})

const totalPages = computed(() => pages.value.length)

function navigateToPrevPage() {
  if (currentPage.value > 1) scrollToPage(currentPage.value - 1)
}

function navigateToNextPage() {
  if (currentPage.value < totalPages.value) scrollToPage(currentPage.value + 1)
}

/** Returns the page number that contains the element with the given node ID */
function findPageForElement(id: string): number | null {
  for (const page of pages.value) {
    if (page.html.includes(`data-node-id="${id}"`)) return page.pageNum
  }
  return null
}

/** Scrolls the canvas to the page that belongs to the given layout type ID */
function scrollToLayoutId(layoutId: string) {
  const page = pages.value.find((p) => p.html.includes(`data-layout-type="${layoutId}"`))
  if (page) scrollToPage(page.pageNum)
}

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

const borderOverrideCss = computed(() => {
  return generateAllBorderOverrides(templateStore.flatNodes)
})

const pages = computed<CanvasPage[]>(() => {
  const draft = generationStore.templateDraft
  if (!draft) return []

  const css = (draft.css ?? '') + borderOverrideCss.value
  const html = draft.html ?? ''

  // Parse <div class="page" data-layout-type="X"> elements (backend contract)
  const parser = typeof DOMParser !== 'undefined' ? new DOMParser() : null
  if (!parser) {
    // SSR / test fallback: treat entire HTML as page 1
    return [{ pageNum: 1, html, css }]
  }

  const doc = parser.parseFromString(`<div id="_root">${html}</div>`, 'text/html')
  const pageEls = doc.querySelectorAll('[data-layout-type]')

  if (pageEls.length === 0) {
    if (html) {
      console.warn('[HTMLCanvas] Nenhum elemento [data-layout-type] encontrado no HTML gerado. Verifique o contrato de atributo HTML entre backend e frontend.')
    }
    // No page dividers — treat entire HTML as single page
    return [{ pageNum: 1, html, css }]
  }

  const result: CanvasPage[] = []
  pageEls.forEach((el) => {
    result.push({ pageNum: result.length + 1, html: el.outerHTML, css })
  })
  return result
})

// ─── Iframe srcdoc Builder ───────────────────────────────────────────────────
const CANVAS_INTERACTION_SCRIPT = `
<script>
(function() {
  // Build ancestor chain for an element
  function getAncestorIds(el) {
    var ids = [];
    var current = el;
    while (current && current !== document.body) {
      if (current.dataset && current.dataset.nodeId) {
        ids.push(current.dataset.nodeId);
      } else if (current.id) {
        ids.push(current.id);
      }
      current = current.parentElement;
    }
    return ids;
  }

  // Get bounding box relative to document
  function getRelativeBox(el) {
    var rect = el.getBoundingClientRect();
    var bodyRect = document.body.getBoundingClientRect();
    return {
      x: rect.left - bodyRect.left,
      y: rect.top - bodyRect.top,
      width: rect.width,
      height: rect.height
    };
  }

  // Click handler
  document.addEventListener('click', function(e) {
    var target = e.target;
    if (!target || target === document.body || target === document.documentElement) return;

    // Walk up to find an element with data-node-id or a meaningful tag
    var el = target;
    while (el && el !== document.body) {
      var nodeId = (el.dataset && el.dataset.nodeId) ? el.dataset.nodeId : el.id;
      if (nodeId) {
        var box = getRelativeBox(el);
        var ancestorIds = getAncestorIds(el);
        window.parent.postMessage({
          type: 'canvas-element-clicked',
          elementId: nodeId,
          boundingBox: box,
          ancestorIds: ancestorIds,
          ctrlKey: e.ctrlKey,
          shiftKey: e.shiftKey
        }, '*');
        break;
      }
      el = el.parentElement;
    }
  }, true);

  // Report bounding boxes of all data-node-id elements after render
  function reportAllBoxes() {
    var els = document.querySelectorAll('[data-node-id], [id]');
    els.forEach(function(el) {
      var nodeId = (el.dataset && el.dataset.nodeId) ? el.dataset.nodeId : el.id;
      if (!nodeId) return;
      var box = getRelativeBox(el);
      if (box.width === 0 && box.height === 0) return;
      window.parent.postMessage({
        type: 'canvas-element-bbox',
        elementId: nodeId,
        boundingBox: box
      }, '*');
    });
  }

  // Report after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', reportAllBoxes);
  } else {
    setTimeout(reportAllBoxes, 50);
  }
})();
<\/script>`

// ─── Alignment Tools (Story 14.5) ────────────────────────────────────────────
const alignToolbarPos = computed(() => {
  if (!isMultiSelecting.value) return { x: 0, y: 0 }
  let minX = Infinity, minY = Infinity, maxX = -Infinity
  for (const id of multiSelection.value) {
    const box = elementBoxes.value.get(id)
    if (!box) continue
    if (box.x < minX) minX = box.x
    if (box.y < minY) minY = box.y
    if (box.x + box.width > maxX) maxX = box.x + box.width
  }
  return { x: (minX + maxX) / 2 - 80, y: minY }
})

function getSelectedBoxes(): Map<string, { x: number; y: number; width: number; height: number }> {
  const result = new Map<string, { x: number; y: number; width: number; height: number }>()
  for (const id of multiSelection.value) {
    const box = elementBoxes.value.get(id)
    if (box) result.set(id, box)
  }
  return result
}

function applyDeltas(deltas: Map<string, Delta>) {
  templateStore.pushUndoSnapshot()
  for (const [id, delta] of deltas) {
    if (delta.dx !== 0 || delta.dy !== 0) {
      templateStore.moveElement(id, delta.dx, delta.dy)
    }
  }
}

const alignFns: Record<string, (boxes: Map<string, { x: number; y: number; width: number; height: number }>) => Map<string, Delta>> = {
  'left': alignLeft, 'center-h': alignCenterH, 'right': alignRight,
  'top': alignTop, 'middle-v': alignMiddleV, 'bottom': alignBottom,
}

const distributeFns: Record<string, (boxes: Map<string, { x: number; y: number; width: number; height: number }>) => Map<string, Delta>> = {
  'distribute-h': distributeH, 'distribute-v': distributeV,
}

function onAlignAction(type: string) {
  const fn = alignFns[type]
  if (!fn) return
  applyDeltas(fn(getSelectedBoxes()))
}

function onDistributeAction(type: string) {
  const fn = distributeFns[type]
  if (!fn) return
  applyDeltas(fn(getSelectedBoxes()))
}

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
<body>${html}
${CANVAS_INTERACTION_SCRIPT}
</body>
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

  // Seed all pages visible — CSS transform on parent breaks IntersectionObserver
  // detection for pages below the fold until user scrolls (AP-layout-transform)
  if (pages.value.length > 0) {
    visiblePages.value = new Set(pages.value.map((p) => p.pageNum))
  }
})

onUnmounted(() => {
  teardownObserver()
  pageRefs.value.clear()
})

// Re-seed visible pages when template changes
// Seed ALL pages: CSS transform on parent breaks IntersectionObserver for below-fold pages (AP-layout-transform)
watch(
  () => generationStore.templateDraft,
  async () => {
    pageRefs.value.clear()
    await nextTick()
    if (pages.value.length > 0) {
      visiblePages.value = new Set(pages.value.map((p) => p.pageNum))
    }
  }
)

// ─── Tree → Canvas sync: watch editorStore.selectedElementId ─────────────────
watch(
  () => editorStore.selectedElementId,
  (id) => {
    if (id) {
      selectFromTree(id)
      // Auto-scroll to the page containing this element
      const pageNum = findPageForElement(id)
      if (pageNum !== null && pageNum !== currentPage.value) {
        scrollToPage(pageNum)
      }
    }
  },
)

// ─── Layout selector → Canvas scroll ────────────────────────────────────────
// When user selects a layout via LayoutSelector, scroll canvas to that section
watch(
  () => layoutStore.pendingScrollToLayout,
  (layoutId) => {
    if (layoutId) {
      scrollToLayoutId(layoutId)
      layoutStore.clearScrollTarget()
    }
  },
)

// ─── Canvas scroll → Layout sync (Option C) ──────────────────────────────────
// When user scrolls, sync activeLayoutId to the most visible layout section
watch(
  visiblePages,
  (visible) => {
    if (visible.size === 0) return
    const firstVisible = Math.min(...visible)
    const page = pages.value.find((p) => p.pageNum === firstVisible)
    if (!page) return
    const match = page.html.match(/data-layout-type="([^"]+)"/)
    if (match?.[1]) {
      layoutStore.syncActiveLayoutFromScroll(match[1])
    }
  },
)

// ─── Story 28.4: Drag field → Canvas drop handlers ───────────────────────────

/** nodeId of the element currently under the drag cursor (drop target) */
const dropTargetNodeId = ref<string | null>(null)

/**
 * Find the canvas node whose bounding box contains the given screen coordinates.
 * Uses elementBoxes from useCanvasInteraction (populated via iframe postMessage).
 */
function getNodeAtScreenPosition(clientX: number, clientY: number): string | null {
  for (const [nodeId, box] of elementBoxes.value.entries()) {
    if (
      clientX >= box.left &&
      clientX <= box.left + box.width &&
      clientY >= box.top &&
      clientY <= box.top + box.height
    ) {
      // Found a node; prefer the most specific (smallest area)
      return nodeId
    }
  }
  return null
}

function onFieldDragOver(event: DragEvent) {
  // Only handle field drags from FieldNavItem
  const types = event.dataTransfer?.types ?? []
  if (!types.includes('drag-type') && !types.includes('field-path')) {
    return
  }
  const nodeId = getNodeAtScreenPosition(event.clientX, event.clientY)
  dropTargetNodeId.value = nodeId
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = nodeId ? 'copy' : 'none'
  }
}

function onFieldDragLeave(event: DragEvent) {
  // Only clear if leaving the canvas container entirely
  const canvas = event.currentTarget as HTMLElement | null
  if (!canvas?.contains(event.relatedTarget as Node | null)) {
    dropTargetNodeId.value = null
  }
}

async function onFieldDrop(event: DragEvent) {
  const dragType = event.dataTransfer?.getData('drag-type')
  if (dragType !== 'field') {
    dropTargetNodeId.value = null
    return
  }

  const xsdPath = event.dataTransfer?.getData('field-path')
  const targetNodeId = dropTargetNodeId.value
  dropTargetNodeId.value = null

  if (!targetNodeId || !xsdPath) return

  // Check if target node already has a binding
  const targetNode = templateStore.getNodeById(targetNodeId)
  if (targetNode?.binding) {
    // Use browser confirm as fallback (project may not have a modal dialog store)
    const confirmed = window.confirm(
      `Substituir binding de "${targetNode.binding}" por "${xsdPath}"?`,
    )
    if (!confirmed) return
  }

  mappingStore.updateNodeBinding(targetNodeId, xsdPath)
}

function onFieldDragEnd() {
  dropTargetNodeId.value = null
}

// ─── Canvas interaction event handlers ───────────────────────────────────────
function onElementSelected(_elementId: string) {
  // Already handled by useCanvasInteraction composable
}

function onSelectionCleared() {
  // Already handled by composable's clearSelection
}
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

/* Footer with page nav + zoom controls */
.html-canvas__footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  background: var(--color-neutral-50, #f9fafb);
  border-top: 1px solid var(--color-neutral-300, #d1d5db);
}

.html-canvas__page-nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-neutral-50, #f9fafb);
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.375rem;
  user-select: none;
}

.html-canvas__page-nav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  background: none;
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
  transition: background 0.15s;
}

.html-canvas__page-nav-btn:hover:not(:disabled) {
  background: var(--color-neutral-200, #e5e7eb);
}

.html-canvas__page-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.html-canvas__page-nav-label {
  min-width: 3rem;
  text-align: center;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
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
