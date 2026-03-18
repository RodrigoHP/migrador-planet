<template>
  <div class="field-navigator">
    <!-- Summary header -->
    <div class="field-navigator__summary">
      <span class="field-navigator__summary-text">{{ mappedCount }} de {{ totalCount }} campos mapeados</span>
      <ProgressBar :value="progressPct" :animated="false" class="field-navigator__progress" />
    </div>

    <!-- Sort controls -->
    <div class="field-navigator__sort">
      <span class="field-navigator__sort-label">Ordenar:</span>
      <button
        v-for="key in sortKeys"
        :key="key.value"
        class="field-navigator__sort-btn"
        :class="{ 'field-navigator__sort-btn--active': sortBy === key.value }"
        type="button"
        @click="setSortBy(key.value)"
      >
        {{ key.label }}
      </button>
    </div>

    <!-- Groups -->
    <div class="field-navigator__groups">
      <div
        v-for="group in visibleGroups"
        :key="group.type"
        class="field-navigator__group"
      >
        <!-- Group header -->
        <button
          class="field-navigator__group-header"
          type="button"
          :aria-expanded="!collapsedGroups.has(group.type)"
          @click="toggleGroup(group.type)"
        >
          <span class="field-navigator__group-icon" aria-hidden="true">{{ group.icon }}</span>
          <span class="field-navigator__group-label">{{ group.label }}</span>
          <span class="field-navigator__group-count">({{ group.fields.length }})</span>
          <span class="field-navigator__group-toggle" aria-hidden="true">
            {{ collapsedGroups.has(group.type) ? '▶' : '▼' }}
          </span>
        </button>

        <!-- Group items -->
        <div v-if="!collapsedGroups.has(group.type)" class="field-navigator__group-items">
          <FieldNavItemVue
            v-for="field in group.fields"
            :key="field.path"
            :field="field"
            :is-selected="selectedFieldPath === field.path"
            @select="onSelectField"
          />
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="visibleGroups.length === 0" class="field-navigator__empty">
        <span>Nenhum campo disponível</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMappingStore } from '@/stores/mapping'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useEditorStore } from '@/stores/editorStore'
import { useTemplateStore } from '@/stores/templateStore'
import ProgressBar from '@/atoms/ProgressBar.vue'
import FieldNavItemVue from '@/molecules/FieldNavItem.vue'
import type { FieldNavItem, FieldNavType, FieldNavSortKey } from '@/types/field-navigator.types'
import { TYPE_GROUPS, TYPE_ORDER, STATUS_ORDER } from '@/types/field-navigator.types'

const mappingStore = useMappingStore()
const inspectorStore = useInspectorStore()
const editorStore = useEditorStore()
const templateStore = useTemplateStore()

// ─── Sort state ────────────────────────────────────────────────────────────
const sortBy = ref<FieldNavSortKey>('name')
const collapsedGroups = ref<Set<FieldNavType>>(new Set())
const selectedFieldPath = ref<string | null>(null)

const sortKeys: Array<{ value: FieldNavSortKey; label: string }> = [
  { value: 'name', label: 'Nome' },
  { value: 'status', label: 'Status' },
  { value: 'type', label: 'Tipo' },
]

function setSortBy(key: FieldNavSortKey) {
  sortBy.value = key
}

function toggleGroup(type: FieldNavType) {
  if (collapsedGroups.value.has(type)) {
    collapsedGroups.value.delete(type)
  } else {
    collapsedGroups.value.add(type)
  }
  // Trigger reactivity since Set mutations are not reactive by default
  collapsedGroups.value = new Set(collapsedGroups.value)
}

// ─── Computed counts ───────────────────────────────────────────────────────
const fields = computed<FieldNavItem[]>(() => mappingStore.fieldNavItems)

const mappedCount = computed(() => fields.value.filter((f) => f.status === 'mapped').length)
const totalCount = computed(() => fields.value.length)

const progressPct = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((mappedCount.value / totalCount.value) * 100)
})

// ─── Sorted fields ─────────────────────────────────────────────────────────
const sortedFields = computed<FieldNavItem[]>(() => {
  const copy = [...fields.value]
  switch (sortBy.value) {
    case 'name':
      return copy.sort((a, b) => a.name.localeCompare(b.name))
    case 'status':
      return copy.sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])
    case 'type':
      return copy.sort((a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type))
    default:
      return copy
  }
})

// ─── Grouped fields ────────────────────────────────────────────────────────
interface FieldGroup {
  type: FieldNavType
  icon: string
  label: string
  fields: FieldNavItem[]
}

const visibleGroups = computed<FieldGroup[]>(() => {
  const groups: FieldGroup[] = []
  for (const type of TYPE_ORDER) {
    const groupFields = sortedFields.value.filter((f) => f.type === type)
    if (groupFields.length > 0) {
      const config = TYPE_GROUPS[type]
      groups.push({ type, icon: config.icon, label: config.label, fields: groupFields })
    }
  }
  return groups
})

// ─── Selection ─────────────────────────────────────────────────────────────
function onSelectField(field: FieldNavItem) {
  selectedFieldPath.value = field.path

  // If the field has a nodeId, resolve the node in templateStore
  if (field.nodeId) {
    const node = templateStore.getNodeById(field.nodeId)
    if (node) {
      inspectorStore.selectNode(node)
      editorStore.selectElement(node.id)
      return
    }
  }

  // Fallback: search by binding in flatNodes
  if (field.binding) {
    for (const node of templateStore.flatNodes.values()) {
      if (node.binding === field.binding) {
        inspectorStore.selectNode(node)
        editorStore.selectElement(node.id)
        return
      }
    }
  }
}
</script>

<style scoped>
.field-navigator {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-size: 0.8125rem;
}

/* Summary */
.field-navigator__summary {
  flex-shrink: 0;
  padding: 0.625rem 0.75rem 0.5rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.field-navigator__summary-text {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-200, #e5e7eb);
  margin-bottom: 0.375rem;
}

.field-navigator__progress {
  height: 0.375rem;
}

/* Sort controls */
.field-navigator__sort {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.field-navigator__sort-label {
  font-size: 0.6875rem;
  color: var(--color-neutral-500, #6b7280);
  margin-right: 0.125rem;
}

.field-navigator__sort-btn {
  padding: 0.125rem 0.375rem;
  background: none;
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  transition: background-color 0.1s, color 0.1s;
}

.field-navigator__sort-btn:hover {
  background-color: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
}

.field-navigator__sort-btn--active {
  background-color: var(--color-primary-800, #1e40af);
  border-color: var(--color-primary-500, #3b82f6);
  color: var(--color-primary-200, #bfdbfe);
}

/* Groups */
.field-navigator__groups {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.field-navigator__group {
  border-bottom: 1px solid var(--color-neutral-750, #2d3748);
}

.field-navigator__group-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
  padding: 0.375rem 0.75rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-200, #e5e7eb);
  text-align: left;
  transition: background-color 0.1s;
}

.field-navigator__group-header:hover {
  background-color: var(--color-neutral-750, #2d3748);
}

.field-navigator__group-icon {
  font-size: 0.875rem;
}

.field-navigator__group-label {
  flex: 1;
}

.field-navigator__group-count {
  font-size: 0.6875rem;
  font-weight: 400;
  color: var(--color-neutral-500, #6b7280);
}

.field-navigator__group-toggle {
  font-size: 0.5rem;
  color: var(--color-neutral-500, #6b7280);
}

.field-navigator__group-items {
  padding-bottom: 0.25rem;
}

/* Empty state */
.field-navigator__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  color: var(--color-neutral-500, #6b7280);
  font-size: 0.8125rem;
}
</style>
