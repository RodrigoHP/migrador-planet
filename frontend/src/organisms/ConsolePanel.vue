<template>
  <div class="console-panel" role="region" aria-label="Console de avisos">
    <!-- Filter chips + Export button (Story 30.8) -->
    <div class="console-panel__toolbar" data-testid="console-toolbar">
      <div class="console-panel__filters" role="group" aria-label="Filtros de categoria">
        <button
          v-for="f in filterOptions"
          :key="f.value ?? 'all'"
          class="console-panel__chip"
          :class="{ 'console-panel__chip--active': activeFilter === f.value }"
          :data-testid="`console-filter-${f.value ?? 'all'}`"
          @click="activeFilter = f.value"
        >{{ f.label }}</button>
      </div>
      <button
        class="console-panel__export-btn"
        data-testid="console-export"
        :disabled="filteredWarnings.length === 0"
        @click="exportWarnings"
      >↓ JSON</button>
    </div>

    <div v-if="filteredWarnings.length === 0" class="console-panel__empty" data-testid="console-empty">
      <span class="console-panel__ok-icon" aria-hidden="true">✅</span>
      <span>Nenhum problema detectado</span>
    </div>
    <ul v-else class="console-panel__list" role="list" data-testid="console-list">
      <li
        v-for="warning in filteredWarnings"
        :key="warning.id"
        class="console-panel__item"
        :class="[`console-panel__item--${warning.severity}`, { 'console-panel__item--clickable': !!warning.nodeId || warning.id === 'coverage-low' }]"
        role="listitem"
        :tabindex="(warning.nodeId || warning.id === 'coverage-low') ? 0 : -1"
        :data-testid="`console-warning-${warning.id}`"
        :aria-label="warning.message"
        @click="onWarningClick(warning)"
        @keydown.enter="onWarningClick(warning)"
        @keydown.space.prevent="onWarningClick(warning)"
      >
        <span class="console-panel__icon" aria-hidden="true">⚠</span>
        <span class="console-panel__message">{{ warning.message }}</span>
        <span
          v-if="warning.category"
          class="console-panel__badge"
          :data-testid="`console-badge-${warning.id}`"
        >{{ warning.category }}</span>
        <button
          class="console-panel__dismiss"
          :data-testid="`console-dismiss-${warning.id}`"
          aria-label="Ignorar aviso"
          @click.stop="dismissWarning(warning.id)"
        >✕</button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useCoverageStore } from '@/stores/coverageStore'

const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const confidenceStore = useConfidenceStore()
const coverageStore = useCoverageStore()

export interface ConsolePanelWarning {
  /** Unique identifier — for local warnings uses nodeId, for backend warnings uses BackendWarning.id */
  id: string
  nodeId?: string
  message: string
  severity: 'warning' | 'error'
  category?: string
}

// ─── State ─────────────────────────────────────────────────────────────────
const activeFilter = ref<string | null>(null)
const dismissedIds = ref<Set<string>>(new Set())

// ─── Filter options (Story 30.8) ───────────────────────────────────────────
const filterOptions = [
  { label: 'Todos', value: null },
  { label: 'Não mapeado', value: 'missing_binding' },
  { label: 'Tabela', value: 'table_inconsistent' },
  { label: 'Confiança', value: 'low_confidence' },
  { label: 'Cobertura', value: 'low_coverage' },
]

// Node types that should be mapped to a field (bindable)
const BINDABLE_TYPES = new Set(['field', 'value', 'likely_dynamic', 'dynamic'])

const allWarnings = computed<ConsolePanelWarning[]>(() => {
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
      category: 'missing_binding',
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

  // Story 34.8 — coverage warning when below 80%
  const coverage = coverageStore.activeLayoutCoverage
  if (coverage && coverage.percentage < 80) {
    result.push({
      id: 'coverage-low',
      message: `Cobertura abaixo de 80% (atual: ${coverage.percentage}%) — revise campos não mapeados`,
      severity: 'warning',
      category: 'low_coverage',
    })
  }

  return result
})

// Filtered + dismissed warnings (Story 30.8)
const filteredWarnings = computed<ConsolePanelWarning[]>(() => {
  return allWarnings.value.filter((w) => {
    if (dismissedIds.value.has(w.id)) return false
    if (activeFilter.value !== null && w.category !== activeFilter.value) return false
    return true
  })
})

// Alias for backwards compat (exposed for EditorLayout badge — uses all, not filtered)
const warnings = allWarnings

// Exposed for EditorLayout badge (AC4 original)
defineExpose({ warnings })

// Story 34.8 — emit event for coverage popover
const emit = defineEmits<{
  (e: 'open-coverage'): void
}>()

function selectNode(nodeId: string) {
  editorStore.selectElement(nodeId)
}

function onWarningClick(warning: ConsolePanelWarning) {
  if (warning.id === 'coverage-low') {
    emit('open-coverage')
  } else if (warning.nodeId) {
    selectNode(warning.nodeId)
  }
}

function dismissWarning(id: string) {
  dismissedIds.value = new Set([...dismissedIds.value, id])
}

function exportWarnings() {
  const data = JSON.stringify(filteredWarnings.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'warnings.json'
  a.click()
  URL.revokeObjectURL(url)
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

.console-panel__toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-bottom: 1px solid var(--color-border, #3b3b52);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.console-panel__filters {
  display: flex;
  gap: 4px;
  flex: 1;
  flex-wrap: wrap;
}

.console-panel__chip {
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--color-border, #3b3b52);
  background: none;
  color: var(--color-text-muted, #9ca3af);
  font-size: 11px;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.console-panel__chip:hover {
  background: var(--color-bg-elevated, #2a2a3e);
}

.console-panel__chip--active {
  background: var(--color-primary, #6366f1);
  border-color: var(--color-primary, #6366f1);
  color: #fff;
}

.console-panel__export-btn {
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--color-border, #3b3b52);
  background: none;
  color: var(--color-text-muted, #9ca3af);
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}

.console-panel__export-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.console-panel__export-btn:not(:disabled):hover {
  background: var(--color-bg-elevated, #2a2a3e);
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
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--color-bg-elevated, #2a2a3e);
  border: 1px solid var(--color-border, #3b3b52);
  font-size: 10px;
  color: var(--color-text-muted, #9ca3af);
  white-space: nowrap;
  flex-shrink: 0;
}

.console-panel__dismiss {
  background: none;
  border: none;
  color: var(--color-text-muted, #9ca3af);
  cursor: pointer;
  font-size: 10px;
  padding: 0 2px;
  line-height: 1;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.1s;
}

.console-panel__item:hover .console-panel__dismiss,
.console-panel__item:focus-within .console-panel__dismiss {
  opacity: 1;
}
</style>
