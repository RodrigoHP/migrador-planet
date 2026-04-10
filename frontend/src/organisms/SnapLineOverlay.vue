<template>
  <svg
    v-if="snapLines.length > 0"
    class="snap-line-overlay"
    :width="canvasWidth"
    :height="canvasHeight"
    aria-hidden="true"
  >
    <template v-for="(line, idx) in snapLines" :key="idx">
      <!-- Snap line -->
      <line
        v-if="line.orientation === 'vertical'"
        :x1="line.position"
        :y1="line.start"
        :x2="line.position"
        :y2="line.end"
        class="snap-line-overlay__line"
      />
      <line
        v-else
        :x1="line.start"
        :y1="line.position"
        :x2="line.end"
        :y2="line.position"
        class="snap-line-overlay__line"
      />

      <!-- Distance label -->
      <text
        v-if="line.orientation === 'vertical'"
        :x="line.position + 4"
        :y="(line.start + line.end) / 2"
        class="snap-line-overlay__label"
      >
        {{ Math.round(line.end - line.start) }}px
      </text>
      <text
        v-else
        :x="(line.start + line.end) / 2"
        :y="line.position - 4"
        class="snap-line-overlay__label"
      >
        {{ Math.round(line.end - line.start) }}px
      </text>
    </template>
  </svg>
</template>

<script setup lang="ts">
import type { SnapLine } from '@/composables/useCanvasInteraction'

defineProps<{
  snapLines: SnapLine[]
  canvasWidth: number
  canvasHeight: number
}>()
</script>

<style scoped>
.snap-line-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 90;
  overflow: visible;
}

.snap-line-overlay__line {
  stroke: #ff00ff;
  stroke-width: 1;
  stroke-dasharray: 4 3;
}

.snap-line-overlay__label {
  fill: #ff00ff;
  font-size: 10px;
  font-family: monospace;
  font-weight: 600;
}
</style>
