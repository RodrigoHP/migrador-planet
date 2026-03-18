<template>
  <div class="zoom-controls" role="group" aria-label="Controles de zoom">
    <button
      class="zoom-controls__btn"
      type="button"
      :disabled="zoomLevel <= ZOOM_MIN"
      aria-label="Reduzir zoom"
      @click="zoomOut"
    >
      &minus;
    </button>
    <span class="zoom-controls__value" aria-live="polite" aria-atomic="true">
      {{ zoomLevel }}%
    </span>
    <button
      class="zoom-controls__btn"
      type="button"
      :disabled="zoomLevel >= ZOOM_MAX"
      aria-label="Aumentar zoom"
      @click="zoomIn"
    >
      +
    </button>
  </div>
</template>

<script setup lang="ts">
import { useCanvas } from '@/composables/useCanvas'

const { zoomLevel, zoomIn, zoomOut, ZOOM_MIN, ZOOM_MAX } = useCanvas()
</script>

<style scoped>
.zoom-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-neutral-50, #f9fafb);
  border: 1px solid var(--color-neutral-300, #d1d5db);
  border-radius: 0.375rem;
  user-select: none;
}

.zoom-controls__btn {
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

.zoom-controls__btn:hover:not(:disabled) {
  background: var(--color-neutral-200, #e5e7eb);
}

.zoom-controls__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.zoom-controls__value {
  min-width: 3rem;
  text-align: center;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
}
</style>
