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
      :class="[itemClass(item), { 'coverage-overlay__item--dashed': item.status === 'optional_section' && target === 'canvas' }]"
      :style="itemStyle(item)"
      :title="`${item.elementId}: ${item.status}`"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCoverageStore } from '@/stores/coverageStore'
import { useLayoutStore } from '@/stores/layout'

export interface OverlayItem {
  elementId: string
  boundingBox: { x: number; y: number; w: number; h: number }
  status: string
  type: string
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
  const bg = colors[item.status] ?? 'rgba(107, 114, 128, 0.2)'
  const isDashed = item.status === 'optional_section' && props.target === 'canvas'

  return {
    left: `${item.boundingBox.x}px`,
    top: `${item.boundingBox.y}px`,
    width: `${item.boundingBox.w}px`,
    height: `${item.boundingBox.h}px`,
    background: bg,
    border: isDashed ? `2px dashed #f97316` : `1px solid ${bg.replace('0.3', '0.6').replace('0.15', '0.5')}`,
  }
}

function itemClass(item: OverlayItem): string {
  return `coverage-overlay__item--${item.status}`
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
</style>
