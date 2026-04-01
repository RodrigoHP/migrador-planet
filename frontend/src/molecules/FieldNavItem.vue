<template>
  <div
    class="field-nav-item"
    :class="{
      'field-nav-item--selected': isSelected,
      'field-nav-item--dragging': isDragging,
    }"
    role="button"
    tabindex="0"
    :aria-selected="isSelected"
    draggable="true"
    @click="handleClick"
    @keydown.enter="emit('select', field)"
    @keydown.space.prevent="emit('select', field)"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd"
  >
    <!-- Status badge -->
    <span
      class="field-nav-item__status"
      :class="`field-nav-item__status--${field.status}`"
      :title="statusLabel"
      aria-hidden="true"
    >{{ statusIcon }}</span>

    <!-- Content: 2-line layout (Story 28.2) -->
    <div class="field-nav-item__content">
      <!-- Primary: semantic name (or raw name fallback) -->
      <div class="field-nav-item__primary">
        <span class="field-nav-item__name">{{ displayName }}</span>
        <!-- Ambiguous badge -->
        <span
          v-if="field.isAmbiguous"
          class="field-nav-item__ambiguous"
          title="Campo ambíguo — clique para resolver"
          aria-label="Campo ambíguo"
        >⚡</span>
        <!-- Optional badge -->
        <span v-if="field.isOptional" class="field-nav-item__optional" title="Campo opcional">⚠</span>
      </div>
      <!-- Secondary: raw PDF text + XSD path as subtitle -->
      <div v-if="field.rawPdfText || field.path" class="field-nav-item__secondary">
        <span v-if="field.rawPdfText" class="field-nav-item__raw-text">{{ field.rawPdfText }}</span>
        <span v-if="field.rawPdfText && field.path" class="field-nav-item__sep"> · </span>
        <span v-if="field.path" class="field-nav-item__xsd-path">{{ field.path }}</span>
      </div>
    </div>

    <!-- [Vincular →] button for unmapped fields (Story 28.2) -->
    <button
      v-if="field.status === 'unmapped' && !field.isAmbiguous"
      class="field-nav-item__bind-btn"
      title="Vincular campo XSD"
      @click.stop="emit('open-binding', field)"
    >
      Vincular →
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FieldNavItem } from '@/types/field-navigator.types'
import { TYPE_GROUPS } from '@/types/field-navigator.types'

const props = defineProps<{
  field: FieldNavItem
  isSelected: boolean
}>()

const emit = defineEmits<{
  select: [field: FieldNavItem]
  'open-ambiguous': [field: FieldNavItem]
  'open-binding': [field: FieldNavItem]
}>()

const isDragging = ref(false)

const typeIcon = computed(() => TYPE_GROUPS[props.field.type]?.icon ?? '📋')

// Story 28.2 — semantic display name: prefer semanticName, then derive from XSD path, then name
const displayName = computed<string>(() => {
  if (props.field.semanticName) return props.field.semanticName
  if (props.field.path) {
    const segment = props.field.path.split('.').pop() ?? props.field.path
    return segment.charAt(0).toUpperCase() + segment.slice(1)
  }
  return props.field.name
})

const statusIcon = computed(() => {
  switch (props.field.status) {
    case 'mapped': return '🟩'
    case 'unmapped': return '🟥'
    case 'unconfirmed': return '🟨'
  }
})

const statusLabel = computed(() => {
  switch (props.field.status) {
    case 'mapped': return 'Mapeado'
    case 'unmapped': return 'Não mapeado'
    case 'unconfirmed': return 'Não confirmado'
  }
})

function handleClick() {
  if (props.field.isAmbiguous) {
    emit('open-ambiguous', props.field)
  } else {
    emit('select', props.field)
  }
}

function handleDragStart(event: DragEvent) {
  isDragging.value = true
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'copy'
    event.dataTransfer.setData('field-path', props.field.path)
    event.dataTransfer.setData('field-id', props.field.name)
    event.dataTransfer.setData('drag-type', 'field')
  }
}

function handleDragEnd() {
  isDragging.value = false
}
</script>

<style scoped>
.field-nav-item {
  display: flex;
  align-items: flex-start;
  gap: 0.375rem;
  padding: 0.3125rem 0.75rem;
  cursor: pointer;
  border-radius: 0.25rem;
  font-size: 0.8125rem;
  color: var(--color-neutral-300, #d1d5db);
  transition: background-color 0.1s;
  user-select: none;
}

.field-nav-item:hover {
  background-color: var(--color-neutral-700, #374151);
}

.field-nav-item--selected {
  background-color: var(--color-primary-900, #1e3a5f);
  color: var(--color-primary-200, #bfdbfe);
}

.field-nav-item:focus-visible {
  outline: 2px solid var(--color-primary-400, #60a5fa);
  outline-offset: -2px;
}

.field-nav-item__status {
  flex-shrink: 0;
  font-size: 0.625rem;
  margin-top: 2px;
}

.field-nav-item__content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.field-nav-item__primary {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow: hidden;
}

.field-nav-item__name {
  font-size: 0.8125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.field-nav-item__secondary {
  font-size: 0.6875rem;
  color: var(--color-neutral-500, #6b7280);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-nav-item__sep {
  color: var(--color-neutral-600, #4b5563);
}

.field-nav-item__xsd-path {
  font-family: monospace;
  font-size: 0.625rem;
  color: var(--color-neutral-500, #6b7280);
}

.field-nav-item__bind-btn {
  flex-shrink: 0;
  background: none;
  border: 1px solid var(--color-primary-400, #60a5fa);
  border-radius: 3px;
  color: var(--color-primary-400, #60a5fa);
  font-size: 0.625rem;
  padding: 1px 5px;
  cursor: pointer;
  white-space: nowrap;
  margin-top: 1px;
  transition: background 0.1s;
}

.field-nav-item__bind-btn:hover {
  background: rgba(96, 165, 250, 0.15);
}

.field-nav-item__optional {
  flex-shrink: 0;
  font-size: 0.6875rem;
  color: var(--color-yellow-400, #facc15);
}

.field-nav-item__ambiguous {
  flex-shrink: 0;
  font-size: 0.6875rem;
  color: var(--color-orange-400, #fb923c);
  cursor: pointer;
}

.field-nav-item--dragging {
  opacity: 0.5;
  cursor: grabbing;
}

.field-nav-item[draggable='true'] {
  cursor: grab;
}
</style>
