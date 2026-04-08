<template>
  <div
    class="layout-anchor"
    :class="`layout-anchor--${side}`"
    :style="positionStyle"
    :title="anchorData.label"
    :aria-label="`Ancora ${side}: ${anchorData.label}`"
    :data-testid="`layout-anchor-${side}`"
    :data-anchor-id="anchorData.id"
    @click="$emit('select', anchorData.id)"
  >
    <span class="layout-anchor__dot" />
    <span class="layout-anchor__tooltip">{{ anchorData.label }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface AnchorData {
  id: string
  label: string
  canvasPosition: { x: number; y: number }
  pdfPosition: { x: number; y: number }
}

const props = withDefaults(defineProps<{
  anchorData: AnchorData
  side?: 'canvas' | 'pdf'
}>(), {
  side: 'canvas',
})

defineEmits<{
  select: [id: string]
}>()

const positionStyle = computed(() => {
  const pos = props.side === 'canvas'
    ? props.anchorData.canvasPosition
    : props.anchorData.pdfPosition
  return {
    left: `${pos.x}px`,
    top: `${pos.y}px`,
  }
})
</script>

<style scoped>
.layout-anchor {
  position: absolute;
  z-index: 30;
  pointer-events: auto;
  cursor: pointer;
}

.layout-anchor__dot {
  display: block;
  width: 10px;
  height: 10px;
  background: var(--color-primary-500, #3b82f6);
  border: 2px solid #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transform: translate(-50%, -50%);
}

.layout-anchor--canvas .layout-anchor__dot {
  background: #2563eb;
}

.layout-anchor--pdf .layout-anchor__dot {
  background: #7c3aed;
}

.layout-anchor__tooltip {
  position: absolute;
  left: 14px;
  top: -6px;
  background: rgba(17, 24, 39, 0.9);
  color: #fff;
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 40;
}

.layout-anchor:hover .layout-anchor__tooltip {
  opacity: 1;
}

/* Selected state */
.layout-anchor--selected .layout-anchor__dot {
  width: 14px;
  height: 14px;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.4), 0 1px 3px rgba(0, 0, 0, 0.3);
}
</style>
