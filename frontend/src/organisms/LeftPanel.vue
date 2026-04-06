<template>
  <div class="left-panel">
    <!-- Tab buttons -->
    <nav class="left-panel__tabs" role="tablist" aria-label="Painel esquerdo">
      <button
        v-for="tab in visibleTabs"
        :key="tab.id"
        role="tab"
        :aria-selected="editorStore.activeLeftTab === tab.id"
        :class="['left-panel__tab', editorStore.activeLeftTab === tab.id && 'left-panel__tab--active']"
        type="button"
        @click="editorStore.setActiveLeftTab(tab.id)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <!-- Tab content -->
    <div class="left-panel__content" role="tabpanel">
      <!-- v-show preserves StructureTree state (expandedNodes) across tab switches -->
      <StructureTree
        v-show="editorStore.activeLeftTab === 'structure'"
        class="left-panel__tree"
      />
      <FieldNavigator
        v-if="editorStore.activeLeftTab === 'fields'"
        class="left-panel__field-navigator"
      />
      <FileExplorer
        v-if="editorStore.activeLeftTab === 'files'"
        class="left-panel__file-explorer"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useEditorStore } from '@/stores/editorStore'
import StructureTree from '@/organisms/StructureTree.vue'
import FieldNavigator from '@/organisms/FieldNavigator.vue'
import FileExplorer from '@/organisms/FileExplorer.vue'
import type { LeftTab } from '@/types/editor.types'

const editorStore = useEditorStore()

const allTabs: Array<{ id: LeftTab; label: string; showOnlyWhenCode?: boolean }> = [
  { id: 'structure', label: 'Estrutura' },
  { id: 'fields',    label: 'Campos' },
  { id: 'files',     label: 'Arquivos', showOnlyWhenCode: true },
]

/** Show [Arquivos] tab only when Code tab is active in center panel */
const visibleTabs = computed(() =>
  allTabs.filter((tab) => {
    if (tab.showOnlyWhenCode) return editorStore.activeCenterTab === 'code'
    return true
  }),
)

/** When code tab is activated, auto-switch left panel to [Arquivos] */
watch(
  () => editorStore.activeCenterTab,
  (tab) => {
    if (tab === 'code') {
      editorStore.setActiveLeftTab('files')
    } else if (editorStore.activeLeftTab === 'files') {
      editorStore.setActiveLeftTab('structure')
    }
  },
)
</script>

<style scoped>
.left-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.left-panel__tabs {
  display: flex;
  flex-shrink: 0;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.left-panel__tab {
  flex: 1;
  padding: 0.625rem 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-neutral-400, #9ca3af);
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.left-panel__tab:hover {
  color: var(--color-neutral-100, #f3f4f6);
}

.left-panel__tab--active {
  color: var(--color-primary-400, #60a5fa);
  border-bottom-color: var(--color-primary-400, #60a5fa);
}

.left-panel__content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.left-panel__tree {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.left-panel__field-navigator {
  flex: 1;
  overflow: hidden;
}

.left-panel__file-explorer {
  flex: 1;
  overflow: hidden;
}

.left-panel__placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.25rem;
  padding: 2rem 1rem;
}

.left-panel__placeholder-text {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-400, #9ca3af);
}

.left-panel__placeholder-sub {
  font-size: 0.75rem;
  color: var(--color-neutral-500, #6b7280);
  text-align: center;
}
</style>
