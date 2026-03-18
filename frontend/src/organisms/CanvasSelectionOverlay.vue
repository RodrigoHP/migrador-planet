<template>
  <div
    ref="overlayRef"
    class="canvas-selection-overlay"
    data-testid="canvas-selection-overlay"
    @click.self="onOverlayClick"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseLeave"
  >
    <!-- Selection box -->
    <div
      v-if="showSelectionBox && selectionBox"
      class="canvas-selection-overlay__selection"
      :style="selectionBoxStyle"
      data-testid="selection-box"
      @mousedown.prevent="onSelectionMouseDown"
    >
      <!-- 8 Resize handles -->
      <div
        v-for="handle in handles"
        :key="handle.index"
        class="canvas-selection-overlay__handle"
        :style="handleStyle(handle)"
        :data-handle-index="handle.index"
        data-testid="resize-handle"
        @mousedown.prevent.stop="onHandleMouseDown(handle.index, $event)"
      />
    </div>

    <!-- Multi-selection highlight boxes -->
    <div
      v-for="id in multiSelectedIds"
      :key="`multi-${id}`"
      class="canvas-selection-overlay__multi-selection"
      :style="multiBoxStyle(id)"
      data-testid="multi-selection-box"
    />

    <!-- Snap guide lines -->
    <template v-if="showSnapLines">
      <div
        v-for="(line, idx) in snapLines"
        :key="`snap-${idx}`"
        class="canvas-selection-overlay__snap-line"
        :class="`canvas-selection-overlay__snap-line--${line.orientation}`"
        :style="snapLineStyle(line)"
        data-testid="snap-line"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import type { BoundingBox, SelectionHandle, SnapLine } from '@/composables/useCanvasInteraction'
import { useCanvasInteraction } from '@/composables/useCanvasInteraction'

interface Props {
  /** Width of the canvas page in pixels (pre-zoom) */
  pageWidth?: number
  /** Height of the canvas page in pixels (pre-zoom) */
  pageHeight?: number
  /** Current zoom level (0–125) */
  zoomLevel?: number
  /** Page number this overlay covers */
  pageNum?: number
}

const props = withDefaults(defineProps<Props>(), {
  pageWidth: 794,
  pageHeight: 1123,
  zoomLevel: 100,
  pageNum: 1,
})

const emit = defineEmits<{
  (e: 'element-selected', elementId: string): void
  (e: 'selection-cleared'): void
}>()

// ─── Composable ───────────────────────────────────────────────────────────────
const {
  selectionState,
  dragState,
  resizeState,
  multiSelection,
  elementBoxes,
  snapEnabled,
  startDrag,
  updateDrag,
  endDrag,
  startResize,
  updateResize,
  endResize,
  clearSelection,
} = useCanvasInteraction()

// ─── Computed ─────────────────────────────────────────────────────────────────

const scale = computed(() => props.zoomLevel / 100)

const selectionBox = computed<BoundingBox | null>(() => selectionState.value.boundingBox)

const handles = computed<SelectionHandle[]>(() => selectionState.value.handles)

const snapLines = computed<SnapLine[]>(() => dragState.value.snapLines)

const showSnapLines = computed(
  () => snapEnabled.value && (dragState.value.isDragging || resizeState.value.isResizing)
)

const showSelectionBox = computed(
  () => selectionState.value.elementId !== null && selectionBox.value !== null
)

const multiSelectedIds = computed<string[]>(() => {
  if (multiSelection.value.size <= 1) return []
  const primary = selectionState.value.elementId
  return [...multiSelection.value].filter((id) => id !== primary)
})

// ─── Styles ───────────────────────────────────────────────────────────────────

const HANDLE_SIZE = 8 // px
const HANDLE_OFFSET = HANDLE_SIZE / 2

function scaleBox(box: BoundingBox) {
  return {
    left: `${box.x * scale.value}px`,
    top: `${box.y * scale.value}px`,
    width: `${box.width * scale.value}px`,
    height: `${box.height * scale.value}px`,
  }
}

const selectionBoxStyle = computed(() => {
  if (!selectionBox.value) return {}
  return {
    position: 'absolute' as const,
    ...scaleBox(selectionBox.value),
    border: '2px solid #3b82f6',
    cursor: dragState.value.isDragging ? 'grabbing' : 'grab',
    boxSizing: 'border-box' as const,
    zIndex: 100,
    pointerEvents: 'all' as const,
  }
})

function handleStyle(handle: SelectionHandle): Record<string, string> {
  if (!selectionBox.value) return {}
  const box = selectionBox.value
  // Positions relative to the scaled selection box top-left
  const posMap: Record<number, { x: number; y: number }> = {
    0: { x: 0, y: 0 },
    1: { x: box.width / 2, y: 0 },
    2: { x: box.width, y: 0 },
    3: { x: 0, y: box.height / 2 },
    4: { x: box.width, y: box.height / 2 },
    5: { x: 0, y: box.height },
    6: { x: box.width / 2, y: box.height },
    7: { x: box.width, y: box.height },
  }
  const pos = posMap[handle.index] ?? { x: 0, y: 0 }
  return {
    position: 'absolute',
    width: `${HANDLE_SIZE}px`,
    height: `${HANDLE_SIZE}px`,
    background: '#ffffff',
    border: '2px solid #3b82f6',
    borderRadius: '2px',
    left: `${pos.x * scale.value - HANDLE_OFFSET}px`,
    top: `${pos.y * scale.value - HANDLE_OFFSET}px`,
    cursor: handle.cursor,
    zIndex: '101',
    boxSizing: 'border-box',
  }
}

function multiBoxStyle(id: string): Record<string, string> {
  const box = elementBoxes.value.get(id)
  if (!box) return { display: 'none' }
  return {
    position: 'absolute',
    ...scaleBox(box),
    border: '1px dashed #3b82f6',
    background: 'rgba(59,130,246,0.08)',
    pointerEvents: 'none',
    zIndex: '99',
    boxSizing: 'border-box',
  }
}

function snapLineStyle(line: SnapLine): Record<string, string> {
  if (line.orientation === 'horizontal') {
    return {
      position: 'absolute',
      left: `${line.start * scale.value}px`,
      top: `${line.position * scale.value}px`,
      width: `${(line.end - line.start) * scale.value}px`,
      height: '1px',
      background: '#f59e0b',
      pointerEvents: 'none',
      zIndex: '102',
    }
  } else {
    return {
      position: 'absolute',
      left: `${line.position * scale.value}px`,
      top: `${line.start * scale.value}px`,
      width: '1px',
      height: `${(line.end - line.start) * scale.value}px`,
      background: '#f59e0b',
      pointerEvents: 'none',
      zIndex: '102',
    }
  }
}

// ─── Event Handlers ───────────────────────────────────────────────────────────

function onOverlayClick() {
  clearSelection()
  emit('selection-cleared')
}

function onSelectionMouseDown(event: MouseEvent) {
  startDrag(event.clientX, event.clientY)
}

function onHandleMouseDown(handleIndex: number, event: MouseEvent) {
  startResize(handleIndex, event.clientX, event.clientY)
}

function onMouseMove(event: MouseEvent) {
  if (dragState.value.isDragging) {
    updateDrag(event.clientX, event.clientY)
  } else if (resizeState.value.isResizing) {
    updateResize(event.clientX, event.clientY)
  }
}

function onMouseUp() {
  if (dragState.value.isDragging) {
    endDrag()
  } else if (resizeState.value.isResizing) {
    endResize()
  }
}

function onMouseLeave() {
  if (dragState.value.isDragging) {
    endDrag()
  } else if (resizeState.value.isResizing) {
    endResize()
  }
}

// ─── postMessage listener ────────────────────────────────────────────────────

// Listen for messages from iframe content
function handleIframeMessage(event: MessageEvent) {
  if (event.data?.type === 'canvas-element-clicked') {
    const { elementId, boundingBox, ancestorIds, ctrlKey, shiftKey } = event.data
    if (!elementId || !boundingBox) return

    // If nested element, show hierarchy popup
    if (ancestorIds && ancestorIds.length > 1) {
      // Let the parent component know to show hierarchy popup
      // For now, emit the leaf element and let HierarchyPopup handle
    }

    // Import dynamically to avoid circular dep
    const interactionComposable = useCanvasInteraction()
    interactionComposable.registerElementBox(elementId, boundingBox)
    interactionComposable.selectElement(elementId, boundingBox, {
      ctrl: ctrlKey ?? false,
      shift: shiftKey ?? false,
    })
    emit('element-selected', elementId)
  }

  if (event.data?.type === 'canvas-element-bbox') {
    const { elementId, boundingBox } = event.data
    if (elementId && boundingBox) {
      const interactionComposable = useCanvasInteraction()
      interactionComposable.registerElementBox(elementId, boundingBox)
    }
  }
}

onMounted(() => {
  window.addEventListener('message', handleIframeMessage)
})

onUnmounted(() => {
  window.removeEventListener('message', handleIframeMessage)
})
</script>

<style scoped>
.canvas-selection-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  pointer-events: none; /* passthrough by default, only handles and selection box capture events */
  overflow: hidden;
}

/* The overlay itself captures clicks when NOT over elements */
.canvas-selection-overlay:not(:has(.canvas-selection-overlay__selection:hover)) {
  pointer-events: auto;
}

.canvas-selection-overlay__selection {
  pointer-events: all;
}

.canvas-selection-overlay__handle {
  pointer-events: all;
}

.canvas-selection-overlay__multi-selection {
  pointer-events: none;
}

.canvas-selection-overlay__snap-line {
  pointer-events: none;
}
</style>
