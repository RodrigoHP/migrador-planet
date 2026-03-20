<template>
  <svg
    class="canvas-snap-lines"
    :width="pageWidth"
    :height="pageHeight"
    aria-hidden="true"
  >
    <line
      v-for="(line, i) in snapLines"
      :key="i"
      :x1="line.orientation === 'vertical' ? line.position : line.start"
      :y1="line.orientation === 'horizontal' ? line.position : line.start"
      :x2="line.orientation === 'vertical' ? line.position : line.end"
      :y2="line.orientation === 'horizontal' ? line.position : line.end"
      stroke="#2563eb"
      stroke-width="1"
      stroke-dasharray="4,4"
    />
  </svg>
</template>

<script setup lang="ts">
import type { SnapLine } from '@/composables/useCanvasInteraction'

interface Props {
  snapLines: SnapLine[]
  pageWidth: number
  pageHeight: number
}

defineProps<Props>()
</script>

<style scoped>
.canvas-snap-lines {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 50;
}
</style>
