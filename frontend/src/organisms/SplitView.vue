<template>
  <div class="split-view" data-testid="split-view">
    <!-- Left: Canvas -->
    <div
      class="split-view__left"
      :style="{ flexBasis: `${leftWidth}%` }"
    >
      <HTMLCanvas class="split-view__panel" />
    </div>

    <!-- Drag handle -->
    <div
      class="split-view__handle"
      data-testid="split-view-handle"
      @pointerdown="startResize"
    />

    <!-- Right: Monaco -->
    <div
      class="split-view__right"
      :style="{ flexBasis: `${100 - leftWidth}%` }"
    >
      <MonacoTabs class="split-view__panel" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import HTMLCanvas from './HTMLCanvas.vue'
import MonacoTabs from './MonacoTabs.vue'

const leftWidth = ref(50)

function startResize(e: PointerEvent) {
  const startX = e.clientX
  const startWidth = leftWidth.value
  const container = (e.target as HTMLElement).parentElement!
  const containerWidth = container.getBoundingClientRect().width

  function onMove(ev: PointerEvent) {
    const dx = ev.clientX - startX
    const pct = startWidth + (dx / containerWidth) * 100
    leftWidth.value = Math.min(80, Math.max(20, pct))
  }

  function onUp() {
    document.removeEventListener('pointermove', onMove)
    document.removeEventListener('pointerup', onUp)
  }

  document.addEventListener('pointermove', onMove)
  document.addEventListener('pointerup', onUp)
}
</script>

<style scoped>
.split-view {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.split-view__left,
.split-view__right {
  overflow: hidden;
  min-width: 0;
}

.split-view__panel {
  width: 100%;
  height: 100%;
}

.split-view__handle {
  width: 6px;
  cursor: col-resize;
  background: var(--color-neutral-200, #e5e7eb);
  flex-shrink: 0;
  transition: background 0.15s;
}

.split-view__handle:hover {
  background: var(--color-primary-400, #60a5fa);
}
</style>
