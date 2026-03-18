<template>
  <!-- Anchor marker for canvas side -->
  <div
    class="layout-anchor layout-anchor--canvas"
    :style="canvasStyle"
    :title="anchorData.label"
    :aria-label="`Âncora: ${anchorData.label}`"
    data-testid="layout-anchor-canvas"
  >
    <span class="layout-anchor__dot" />
    <span class="layout-anchor__tooltip">{{ anchorData.label }}</span>
  </div>

  <!-- Anchor marker for PDF side -->
  <div
    class="layout-anchor layout-anchor--pdf"
    :style="pdfStyle"
    :title="anchorData.label"
    :aria-label="`Âncora PDF: ${anchorData.label}`"
    data-testid="layout-anchor-pdf"
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

const props = defineProps<{
  anchorData: AnchorData
}>()

const canvasStyle = computed(() => ({
  left: `${props.anchorData.canvasPosition.x}px`,
  top: `${props.anchorData.canvasPosition.y}px`,
}))

const pdfStyle = computed(() => ({
  left: `${props.anchorData.pdfPosition.x}px`,
  top: `${props.anchorData.pdfPosition.y}px`,
}))
</script>

<style scoped>
.layout-anchor {
  position: absolute;
  z-index: 30;
  pointer-events: auto;
  cursor: default;
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
</style>
