<template>
  <div
    v-if="visible && overlayItems.length > 0"
    class="coverage-overlay"
    aria-hidden="true"
    data-testid="coverage-overlay"
  >
    <div
      v-for="item in overlayItems"
      :key="item.elementId"
      class="coverage-overlay__item"
      :class="[
        itemClass(item),
        { 'coverage-overlay__item--dashed': item.status === 'optional_section' && target === 'canvas' },
        { 'coverage-overlay__item--table-container': item.overlay_type === 'table_container' },
        { 'coverage-overlay__item--table-cell': item.overlay_type === 'table_cell' },
        { 'coverage-overlay__item--table-cell--visible': item.overlay_type === 'table_cell' && isCellVisible(item) },
      ]"
      :style="itemStyle(item)"
      :title="`${item.elementId}: ${item.status}`"
      @mouseenter="onItemMouseEnter(item)"
      @mouseleave="onItemMouseLeave(item)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useCoverageStore } from '@/stores/coverageStore'
import { useLayoutStore } from '@/stores/layout'

export interface OverlayItem {
  elementId: string
  boundingBox: { x: number; y: number; w: number; h: number }
  status: string
  type: string
  overlay_type?: 'field' | 'table_container' | 'table_cell'
}

const props = defineProps<{
  target: 'canvas' | 'pdf'
  visible: boolean
}>()

// Overlay color maps
const CANVAS_COLORS: Record<string, string> = {
  bound: 'rgba(34, 197, 94, 0.3)',
  unbound: 'rgba(239, 68, 68, 0.3)',
  unconfirmed: 'rgba(234, 179, 8, 0.3)',
  table: 'rgba(168, 85, 247, 0.3)',
  table_container: 'rgba(168, 85, 247, 0.15)',
  table_cell: 'rgba(168, 85, 247, 0.25)',
  optional_section: 'rgba(249, 115, 22, 0.15)',
  chart: 'rgba(249, 115, 22, 0.3)',
}

const PDF_COLORS: Record<string, string> = {
  text_block: 'rgba(59, 130, 246, 0.3)',
  mapped: 'rgba(34, 197, 94, 0.3)',
  unmapped: 'rgba(239, 68, 68, 0.3)',
  unconfirmed: 'rgba(234, 179, 8, 0.3)',
  table: 'rgba(168, 85, 247, 0.3)',
  chart: 'rgba(249, 115, 22, 0.3)',
}

const coverageStore = useCoverageStore()
const layoutStore = useLayoutStore()

const overlayItems = computed<OverlayItem[]>(() => {
  const id = layoutStore.activeLayoutId
  if (!id) return []
  const data = coverageStore.getOverlayData(id, props.target)
  return data ?? []
})

function itemStyle(item: OverlayItem) {
  const colors = props.target === 'canvas' ? CANVAS_COLORS : PDF_COLORS
  const overlayType = item.overlay_type
  const colorKey = overlayType === 'table_container' || overlayType === 'table_cell' ? overlayType : item.status
  const bg = colors[colorKey] ?? 'rgba(107, 114, 128, 0.2)'
  const isDashed = item.status === 'optional_section' && props.target === 'canvas'
  const isTableContainer = overlayType === 'table_container'

  return {
    left: `${item.boundingBox.x}px`,
    top: `${item.boundingBox.y}px`,
    width: `${item.boundingBox.w}px`,
    height: `${item.boundingBox.h}px`,
    background: bg,
    border: isDashed
      ? `2px dashed #f97316`
      : isTableContainer
        ? `2px solid rgba(168, 85, 247, 0.6)`
        : `1px solid ${bg.replace('0.3', '0.6').replace('0.15', '0.5')}`,
  }
}

function itemClass(item: OverlayItem): string {
  return `coverage-overlay__item--${item.status}`
}

// ─── Table container/cell hover logic ─────────────────────────────────────
const hoveredContainerId = ref<string | null>(null)

function bboxContains(container: OverlayItem['boundingBox'], cell: OverlayItem['boundingBox']): boolean {
  return (
    cell.x >= container.x &&
    cell.y >= container.y &&
    cell.x + cell.w <= container.x + container.w &&
    cell.y + cell.h <= container.y + container.h
  )
}

function isCellVisible(cell: OverlayItem): boolean {
  if (!hoveredContainerId.value) return false
  // If the hovered element is a table_cell itself, show it
  if (hoveredContainerId.value === cell.elementId) return true
  // Find the hovered container and check if this cell is inside it
  const container = overlayItems.value.find(
    (it) => it.elementId === hoveredContainerId.value && it.overlay_type === 'table_container',
  )
  if (!container) return false
  return bboxContains(container.boundingBox, cell.boundingBox)
}

function onItemMouseEnter(item: OverlayItem) {
  if (item.overlay_type === 'table_container' || item.overlay_type === 'table_cell') {
    hoveredContainerId.value = item.elementId
  }
}

function onItemMouseLeave(item: OverlayItem) {
  if (hoveredContainerId.value === item.elementId) {
    hoveredContainerId.value = null
  }
}
</script>

<style scoped>
.coverage-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 20;
  overflow: hidden;
}

.coverage-overlay__item {
  position: absolute;
  border-radius: 2px;
}

.coverage-overlay__item--dashed {
  background: rgba(249, 115, 22, 0.1) !important;
}

.coverage-overlay__item--table-container {
  pointer-events: auto;
  cursor: pointer;
}

.coverage-overlay__item--table-cell {
  opacity: 0;
  transition: opacity 0.15s;
  pointer-events: auto;
}

.coverage-overlay__item--table-cell--visible {
  opacity: 1;
}
</style>
