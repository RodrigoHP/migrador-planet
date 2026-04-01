<template>
  <div class="inspector-panel">
    <!-- Header / Title -->
    <div class="inspector-panel__header">
      <span class="inspector-panel__title">{{ panelTitle }}</span>
    </div>

    <!-- Scrollable content -->
    <div class="inspector-panel__content">
      <component :is="activeInspector" :node="inspector.selectedNode" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useInspectorStore } from '@/stores/inspectorStore'
import type { InspectorLevel } from '@/types/inspector.types'
import PageInspector from './inspectors/PageInspector.vue'
import SectionInspector from './inspectors/SectionInspector.vue'
import ComponentInspector from './inspectors/ComponentInspector.vue'
import ElementInspector from './inspectors/ElementInspector.vue'
import StructuralNodeInfo from './inspectors/StructuralNodeInfo.vue'

const inspector = useInspectorStore()

// ─── Level → Inspector component map ────────────────────────────────────────
// Story 28.6: 'structural' routes to StructuralNodeInfo for header/footer/flow
const inspectorMap: Record<InspectorLevel, unknown> = {
  page: PageInspector,
  section: SectionInspector,
  component: ComponentInspector,
  element: ElementInspector,
  structural: StructuralNodeInfo,
}

// AC 2 + AC 4: route to inspector based on level; default (no selection) → PageInspector
const activeInspector = computed(() => inspectorMap[inspector.level] ?? PageInspector)

// AC 5: title = "Inspetor de {levelLabel}: {node.name}"
const levelLabelPt: Record<InspectorLevel, string> = {
  page: 'Página',
  section: 'Seção',
  component: 'Componente',
  element: 'Elemento',
  structural: 'Estrutural',
}

const panelTitle = computed(() => {
  const levelLabel = levelLabelPt[inspector.level] ?? inspector.currentLevelLabel
  const nodeName = inspector.selectedNode?.name ?? 'Documento'
  return `Inspetor de ${levelLabel}: ${nodeName}`
})
</script>

<style scoped>
.inspector-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-800, #1f2937);
}

.inspector-panel__header {
  flex-shrink: 0;
  padding: 0.625rem 0.75rem;
  background: var(--color-neutral-900, #111827);
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.inspector-panel__title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-200, #e5e7eb);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.inspector-panel__content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Scrollbar styling */
.inspector-panel__content::-webkit-scrollbar {
  width: 4px;
}
.inspector-panel__content::-webkit-scrollbar-track {
  background: transparent;
}
.inspector-panel__content::-webkit-scrollbar-thumb {
  background: var(--color-neutral-600, #4b5563);
  border-radius: 2px;
}
</style>
