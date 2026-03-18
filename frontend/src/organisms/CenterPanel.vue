<template>
  <div class="center-panel">
    <!-- Tab buttons -->
    <nav class="center-panel__tabs" role="tablist" aria-label="Painel central">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        role="tab"
        :aria-selected="editorStore.activeCenterTab === tab.id"
        :class="['center-panel__tab', editorStore.activeCenterTab === tab.id && 'center-panel__tab--active']"
        type="button"
        @click="editorStore.setActiveCenterTab(tab.id)"
      >
        <span class="center-panel__tab-icon">{{ tab.icon }}</span>
        <span class="center-panel__tab-label">{{ tab.label }}</span>
      </button>
    </nav>

    <!-- Tab content -->
    <div class="center-panel__content" role="tabpanel">
      <template v-if="editorStore.activeCenterTab === 'canvas'">
        <HTMLCanvas class="center-panel__full" />
      </template>

      <template v-else-if="editorStore.activeCenterTab === 'pdf'">
        <PDFReference class="center-panel__full" />
      </template>

      <template v-else-if="editorStore.activeCenterTab === 'code'">
        <MonacoTabs class="center-panel__full" />
      </template>

      <template v-else-if="editorStore.activeCenterTab === 'sync'">
        <div class="center-panel__placeholder center-panel__placeholder--soon">
          <span class="center-panel__placeholder-text">Sincronizar</span>
          <span class="center-panel__placeholder-badge">Em breve (Epic 8)</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useEditorStore } from '@/stores/editorStore'
import type { CenterTab } from '@/types/editor.types'
import PDFReference from './PDFReference.vue'
import HTMLCanvas from './HTMLCanvas.vue'
import MonacoTabs from './MonacoTabs.vue'

const editorStore = useEditorStore()

const tabs: Array<{ id: CenterTab; icon: string; label: string }> = [
  { id: 'canvas', icon: '🖥️', label: 'Canvas' },
  { id: 'pdf', icon: '📄', label: 'PDF' },
  { id: 'code', icon: '</>', label: 'Código' },
  { id: 'sync', icon: '🔗', label: 'Sincronizar' },
]
</script>

<style scoped>
.center-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-100, #f3f4f6);
}

.center-panel__tabs {
  display: flex;
  flex-shrink: 0;
  border-bottom: 1px solid var(--color-neutral-300, #d1d5db);
  background: var(--color-neutral-50, #f9fafb);
}

.center-panel__tab {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.625rem 0.875rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-neutral-500, #6b7280);
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}

.center-panel__tab:hover {
  color: var(--color-neutral-700, #374151);
}

.center-panel__tab--active {
  color: var(--color-primary-600, #2563eb);
  border-bottom-color: var(--color-primary-600, #2563eb);
}

.center-panel__tab-icon {
  font-size: 0.875rem;
}

.center-panel__content {
  flex: 1;
  overflow: auto;
}

.center-panel__full {
  width: 100%;
  height: 100%;
}

.center-panel__placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.5rem;
  padding: 2rem;
}

.center-panel__placeholder-text {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-neutral-500, #6b7280);
}

.center-panel__placeholder-sub {
  font-size: 0.8125rem;
  color: var(--color-neutral-400, #9ca3af);
}

.center-panel__placeholder--soon .center-panel__placeholder-text {
  color: var(--color-neutral-400, #9ca3af);
}

.center-panel__placeholder-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: var(--color-neutral-200, #e5e7eb);
  color: var(--color-neutral-600, #4b5563);
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}
</style>
