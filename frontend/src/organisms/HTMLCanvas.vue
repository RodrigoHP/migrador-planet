<template>
  <div
    class="html-canvas"
    data-testid="html-canvas"
    tabindex="0"
    @keydown="onCanvasKeyDown"
    @contextmenu.prevent="onContextMenu"
    @dragover.prevent="drag.onFieldDragOver"
    @dragleave="drag.onFieldDragLeave"
    @drop.prevent="drag.onFieldDrop"
    @dragend="drag.onFieldDragEnd"
    @wheel="zoom.onWheel"
  >
    <!-- Scrollable container -->
    <div ref="scrollContainerRef" class="html-canvas__scroll" @scroll="onScroll">
      <!-- Scaled content wrapper -->
      <div
        class="html-canvas__content"
        :style="{
          transform: `scale(${zoom.zoomLevel.value / 100})`,
          transformOrigin: 'top center',
        }"
        data-testid="html-canvas-content"
      >
        <template v-for="(page, index) in iframe.pages.value" :key="page.pageNum">
          <!-- Page wrapper (observed for lazy loading) -->
          <div
            :ref="(el) => setPageRef(el, page.pageNum)"
            :data-page-wrapper="page.pageNum"
            class="html-canvas__page-wrapper"
            :style="{ width: `${iframe.pageWidth.value}px` }"
          >
            <!-- Page with relative positioning for guides overlay -->
            <div
              class="html-canvas__page"
              :style="{
                width: `${iframe.pageWidth.value}px`,
                minHeight: `${iframe.pageHeight.value}px`,
              }"
              :data-page="page.pageNum"
            >
              <!-- Actual page content or placeholder -->
              <iframe
                v-if="zoom.isPageVisible(page.pageNum)"
                :srcdoc="iframe.buildPageSrcdoc(page.html, page.css)"
                :title="`Página ${page.pageNum}`"
                class="html-canvas__iframe"
                :style="{
                  width: `${iframe.pageWidth.value}px`,
                  height: `${iframe.pageHeight.value}px`,
                }"
                sandbox="allow-same-origin allow-scripts"
                scrolling="no"
                data-testid="html-canvas-iframe"
              />
              <div
                v-else
                class="html-canvas__placeholder"
                :style="{
                  width: `${iframe.pageWidth.value}px`,
                  height: `${iframe.pageHeight.value}px`,
                }"
                :aria-label="`Placeholder página ${page.pageNum}`"
              />

              <!-- Guides overlay per page -->
              <CanvasGuides
                :page-width="iframe.pageWidth.value"
                :page-height="iframe.pageHeight.value"
                :margins="defaultMargins"
                :header-height="headerHeight"
                :footer-height="footerHeight"
                :column-positions="columnPositions"
              />

              <!-- Coverage overlay per page -->
              <CoverageOverlay target="canvas" :visible="editorStore.coverageMode" />

              <!-- Selection overlay per page -->
              <CanvasSelectionOverlay
                :page-width="iframe.pageWidth.value"
                :page-height="iframe.pageHeight.value"
                :zoom-level="zoom.zoomLevel.value"
                :page-num="page.pageNum"
                :drop-target-node-id="drag.dropTargetNodeId.value"
                @element-selected="onElementSelected"
                @selection-cleared="onSelectionCleared"
              />

              <!-- Snap line overlay (Story 14.7) -->
              <SnapLineOverlay
                v-if="editorStore.snapEnabled && activeSnapLines.length > 0"
                :snap-lines="activeSnapLines"
                :canvas-width="iframe.pageWidth.value"
                :canvas-height="iframe.pageHeight.value"
              />
            </div>
          </div>

          <!-- Page break divider (after every page except the last) -->
          <div
            v-if="index < iframe.pages.value.length - 1"
            class="html-canvas__page-break"
            role="separator"
            aria-label="Quebra de página"
            data-testid="page-break"
          >
            <span class="html-canvas__page-break-line" />
            <span class="html-canvas__page-break-label">--- QUEBRA DE PAGINA ---</span>
            <span class="html-canvas__page-break-line" />
          </div>
        </template>

        <!-- Empty state -->
        <div
          v-if="iframe.pages.value.length === 0"
          class="html-canvas__empty"
          data-testid="html-canvas-empty"
        >
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
      <div
        v-if="totalPages > 1"
        class="html-canvas__page-nav"
        role="group"
        aria-label="Navegação de páginas"
      >
        <button
          class="html-canvas__page-nav-btn"
          type="button"
          :disabled="currentPage <= 1"
          aria-label="Página anterior"
          @click="navigateToPrevPage"
        >
          &#8592;
        </button>
        <span class="html-canvas__page-nav-label">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="html-canvas__page-nav-btn"
          type="button"
          :disabled="currentPage >= totalPages"
          aria-label="Próxima página"
          @click="navigateToNextPage"
        >
          &#8594;
        </button>
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

  <!-- Canvas context menu (teleported to body) — Story 29.6 -->
  <CanvasContextMenu
    :visible="contextMenuState.visible"
    :x="contextMenuState.x"
    :y="contextMenuState.y"
    @close="closeContextMenu"
    @map-field="handleCtxMapField"
    @convert-table="handleCtxConvertTable"
    @mark-static="handleCtxMarkStatic"
    @remove="handleCtxRemove"
  />
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import { useLayoutStore } from '@/stores/layout'
import { useGenerationStore } from '@/stores/generation'
import { useCanvasZoom } from '@/composables/useCanvasZoom'
import { useCanvasIframe } from '@/composables/useCanvasIframe'
import { useCanvasDrag } from '@/composables/useCanvasDrag'
import { useCanvasInteraction } from '@/composables/useCanvasInteraction'
import { useCanvasKeyboard } from '@/composables/useCanvasKeyboard'
import ZoomControls from '@/molecules/ZoomControls.vue'
import CanvasGuides from '@/molecules/CanvasGuides.vue'
import CoverageOverlay from '@/organisms/CoverageOverlay.vue'
import CanvasSelectionOverlay from '@/organisms/CanvasSelectionOverlay.vue'
import HierarchyPopup from '@/molecules/HierarchyPopup.vue'
import AlignmentToolbar from '@/molecules/AlignmentToolbar.vue'
import CanvasContextMenu from '@/molecules/CanvasContextMenu.vue'
import SnapLineOverlay from '@/organisms/SnapLineOverlay.vue'
import { PDF_TO_CSS_SCALE } from '@/types/pipeline.types'
import {
  alignLeft,
  alignCenterH,
  alignRight,
  alignTop,
  alignMiddleV,
  alignBottom,
  distributeH,
  distributeV,
  type Delta,
} from '@/composables/useAlignmentTools'

// ─── Stores & Composables ───────────────────────────────────────────────────
const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const layoutStore = useLayoutStore()
const generationStore = useGenerationStore()

const zoom = useCanvasZoom()
const iframe = useCanvasIframe()
const { handleKeyDown: onCanvasKeyDown } = useCanvasKeyboard()

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

const drag = useCanvasDrag(elementBoxes)

// ─── Refs ───────────────────────────────────────────────────────────────────
const scrollContainerRef = ref<HTMLElement | null>(null)
const pageRefs = ref<Map<number, HTMLElement>>(new Map())

// ─── Page Navigation ────────────────────────────────────────────────────────
const currentPage = ref<number>(1)
const totalPages = computed(() => iframe.pages.value.length)

function navigateToPrevPage() {
  if (currentPage.value > 1) zoom.scrollToPage(currentPage.value - 1)
}
function navigateToNextPage() {
  if (currentPage.value < totalPages.value) zoom.scrollToPage(currentPage.value + 1)
}

// ─── Guide Positions ────────────────────────────────────────────────────────
const defaultMargins = { top: 40, bottom: 40, left: 40, right: 40 }
const headerHeight = 80
const footerHeight = 60
const columnPositions = computed(() => {
  const raw = layoutStore.activeLayout?.gridInfo?.columnPositions ?? []
  return raw.map((pt) => Math.round(pt * PDF_TO_CSS_SCALE))
})

// ─── Alignment Tools (Story 14.5) ──────────────────────────────────────────
const alignToolbarPos = computed(() => {
  if (!isMultiSelecting.value) return { x: 0, y: 0 }
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity
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

const alignFns: Record<
  string,
  (
    boxes: Map<string, { x: number; y: number; width: number; height: number }>,
  ) => Map<string, Delta>
> = {
  left: alignLeft,
  'center-h': alignCenterH,
  right: alignRight,
  top: alignTop,
  'middle-v': alignMiddleV,
  bottom: alignBottom,
}
const distributeFns: Record<
  string,
  (
    boxes: Map<string, { x: number; y: number; width: number; height: number }>,
  ) => Map<string, Delta>
> = {
  'distribute-h': distributeH,
  'distribute-v': distributeV,
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

// ─── Page Refs & Observer ───────────────────────────────────────────────────
function setPageRef(el: unknown, pageNum: number) {
  const htmlEl = el as HTMLElement | null
  if (htmlEl) {
    if (!pageRefs.value.has(pageNum)) {
      pageRefs.value.set(pageNum, htmlEl)
      zoom.observePage(htmlEl)
    }
  } else {
    const existing = pageRefs.value.get(pageNum)
    if (existing) {
      zoom.unobservePage(existing)
      pageRefs.value.delete(pageNum)
    }
  }
}

function onScroll(_event: Event) {
  const container = scrollContainerRef.value
  if (!container || pageRefs.value.size === 0) return
  const viewportMid = container.scrollTop + container.clientHeight / 2
  let best = 1
  for (const [pageNum, el] of pageRefs.value) {
    if (el.offsetTop <= viewportMid) best = Math.max(best, pageNum)
  }
  currentPage.value = best
}

// ─── Context Menu (Story 29.6) ──────────────────────────────────────────────
const contextMenuState = reactive({
  visible: false,
  x: 0,
  y: 0,
  nodeId: null as string | null,
})

function onContextMenu(event: MouseEvent) {
  const nodeId = drag.getNodeAtScreenPosition(event.clientX, event.clientY)
  if (!nodeId) return
  contextMenuState.visible = true
  contextMenuState.x = event.clientX
  contextMenuState.y = event.clientY
  contextMenuState.nodeId = nodeId
  editorStore.selectElement(nodeId)
}

function closeContextMenu() {
  contextMenuState.visible = false
  contextMenuState.nodeId = null
}

function handleCtxMapField() {
  if (!contextMenuState.nodeId) return
  if (typeof (editorStore as Record<string, unknown>).openPanel === 'function') {
    ;(editorStore as Record<string, unknown>).openPanel('fields')
  }
  closeContextMenu()
}

function handleCtxConvertTable() {
  if (!contextMenuState.nodeId) {
    closeContextMenu()
    return
  }
  const ok = templateStore.convertToTable(contextMenuState.nodeId)
  if (!ok) {
    if (import.meta.env.DEV)
      console.warn('[Canvas] convertToTable: no nao convertivel:', contextMenuState.nodeId)
  }
  closeContextMenu()
}

function handleCtxMarkStatic() {
  if (!contextMenuState.nodeId) return
  templateStore.updateNodeProperty(contextMenuState.nodeId, 'type', 'static')
  closeContextMenu()
}

function handleCtxRemove() {
  if (!contextMenuState.nodeId) return
  templateStore.removeNode(contextMenuState.nodeId)
  closeContextMenu()
}

function _onDocumentClickForCtxMenu(event: MouseEvent) {
  if (!contextMenuState.visible) return
  const target = event.target as Node | null
  const menuEl = document.querySelector('[data-testid="canvas-context-menu"]')
  if (menuEl && target && menuEl.contains(target)) return
  closeContextMenu()
}

function _onDocumentKeyForCtxMenu(event: KeyboardEvent) {
  if (event.key === 'Escape' && contextMenuState.visible) closeContextMenu()
}

// ─── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(() => {
  if (scrollContainerRef.value) zoom.setupObserver(scrollContainerRef.value)
  if (iframe.pages.value.length > 0) {
    zoom.visiblePages.value = new Set(iframe.pages.value.map((p) => p.pageNum))
  }
  document.addEventListener('click', _onDocumentClickForCtxMenu, true)
  document.addEventListener('keydown', _onDocumentKeyForCtxMenu)
})

onUnmounted(() => {
  zoom.teardownObserver()
  pageRefs.value.clear()
  document.removeEventListener('click', _onDocumentClickForCtxMenu, true)
  document.removeEventListener('keydown', _onDocumentKeyForCtxMenu)
})

// Re-seed visible pages when template changes
watch(
  () => generationStore.templateDraft,
  async () => {
    currentPage.value = 1
    pageRefs.value.clear()
    await nextTick()
    if (iframe.pages.value.length > 0) {
      zoom.visiblePages.value = new Set(iframe.pages.value.map((p) => p.pageNum))
    }
  },
)

// Tree -> Canvas sync
watch(
  () => editorStore.selectedElementId,
  (id) => {
    if (id) {
      selectFromTree(id)
      const pageNum = iframe.findPageForElement(id)
      if (pageNum !== null && pageNum !== currentPage.value) zoom.scrollToPage(pageNum)
    }
  },
)

// Layout selector -> Canvas scroll
watch(
  () => layoutStore.pendingScrollToLayout,
  (layoutId) => {
    if (layoutId) {
      const pageNum = iframe.findPageForLayoutId(layoutId)
      if (pageNum) zoom.scrollToPage(pageNum)
      layoutStore.clearScrollTarget()
    }
  },
)

// Canvas scroll -> Layout sync
watch(currentPage, (pageNum) => {
  const page = iframe.pages.value.find((p) => p.pageNum === pageNum)
  if (!page) return
  const match = page.html.match(/data-layout-type="([^"]+)"/)
  if (match?.[1]) layoutStore.syncActiveLayoutFromScroll(match[1])
})

// ─── Unused but needed for template event binding ───────────────────────────
function onElementSelected(_elementId: string) {
  /* handled by useCanvasInteraction */
}
function onSelectionCleared() {
  /* handled by composable */
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

.html-canvas__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  transform-origin: top center;
}

.html-canvas__page-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.html-canvas__page {
  position: relative;
  background: #ffffff;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -2px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.html-canvas__iframe {
  display: block;
  border: none;
  overflow: hidden;
}

.html-canvas__placeholder {
  background: #f9fafb;
  display: flex;
  align-items: center;
  justify-content: center;
}

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

.html-canvas__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  font-size: 0.875rem;
  color: var(--color-neutral-400, #9ca3af);
}
</style>
