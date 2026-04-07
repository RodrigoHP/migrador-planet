<template>
  <div class="console-panel" role="region" aria-label="Console de avisos">
    <div v-if="warnings.length === 0" class="console-panel__empty" data-testid="console-empty">
      <span class="console-panel__ok-icon" aria-hidden="true">✅</span>
      <span>Nenhum problema detectado</span>
    </div>
    <ul v-else class="console-panel__list" role="list" data-testid="console-list">
      <li
        v-for="warning in warnings"
        :key="warning.id"
        class="console-panel__item"
        :class="[`console-panel__item--${warning.severity}`, { 'console-panel__item--clickable': !!warning.nodeId }]"
        role="listitem"
        :tabindex="warning.nodeId ? 0 : -1"
        :data-testid="`console-warning-${warning.id}`"
        :aria-label="warning.message"
        @click="warning.nodeId ? selectNode(warning.nodeId) : undefined"
        @keydown.enter="warning.nodeId ? selectNode(warning.nodeId) : undefined"
        @keydown.space.prevent="warning.nodeId ? selectNode(warning.nodeId) : undefined"
      >
        <span class="console-panel__icon" aria-hidden="true">⚠</span>
        <span class="console-panel__message">{{ warning.message }}</span>
        <span
          v-if="warning.category"
          class="console-panel__badge"
          :data-testid="`console-badge-${warning.id}`"
        >{{ warning.category }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import { useConfidenceStore } from '@/stores/confidenceStore'

const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const confidenceStore = useConfidenceStore()

export interface ConsolePanelWarning {
  /** Unique identifier — for local warnings uses nodeId, for backend warnings uses BackendWarning.id */
  id: string
  nodeId?: string
  message: string
  severity: 'warning' | 'error'
  category?: string
}

// Node types that should be mapped to a field (bindable)
const BINDABLE_TYPES = new Set(['field', 'value', 'likely_dynamic', 'dynamic'])

const warnings = computed<ConsolePanelWarning[]>(() => {
  const result: ConsolePanelWarning[] = []

  // Local warnings: unmapped bindable nodes
  for (const node of templateStore.flatNodes.values()) {
    if (!BINDABLE_TYPES.has(node.type)) continue
    if (node.binding) continue
    result.push({
      id: node.id,
      nodeId: node.id,
      message: `Campo "${node.name || node.type}" não mapeado`,
      severity: 'warning',
    })
  }

  // Story 30.5 — backend warnings from pipeline processing
  for (const bw of confidenceStore.backendWarnings) {
    result.push({
      id: bw.id,
      nodeId: bw.nodeId,
      message: bw.message,
      severity: bw.severity,
      category: bw.category,
    })
  }

  return result
})

// Exposed for EditorLayout badge (AC4)
defineExpose({ warnings })

function selectNode(nodeId: string) {
  editorStore.selectElement(nodeId)
}
</script>

<style scoped>
.console-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-size: 12px;
  color: var(--color-text-primary, #e5e7eb);
  background: var(--color-bg-secondary, #1e1e2e);
}

.console-panel__empty {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  color: var(--color-text-secondary, #9ca3af);
}

.console-panel__ok-icon {
  font-size: 14px;
}

.console-panel__list {
  flex: 1;
  overflow-y: auto;
  list-style: none;
  margin: 0;
  padding: 4px 0;
}

.console-panel__item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 4px 12px;
  user-select: none;
  transition: background 0.1s;
}

.console-panel__item--clickable {
  cursor: pointer;
}

.console-panel__item--clickable:hover,
.console-panel__item--clickable:focus {
  background: var(--color-bg-hover, #2a2a3e);
  outline: none;
}

.console-panel__item--warning .console-panel__icon {
  color: #f59e0b;
  flex-shrink: 0;
}

.console-panel__item--error .console-panel__icon {
  color: #ef4444;
  flex-shrink: 0;
}

.console-panel__message {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.console-panel__badge {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--color-bg-elevated, #2a2a3e);
  border: 1px solid var(--color-border, #3b3b52);
  font-size: 10px;
  color: var(--color-text-muted, #9ca3af);
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
