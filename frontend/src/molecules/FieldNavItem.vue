<template>
  <div
    class="field-nav-item"
    :class="{ 'field-nav-item--selected': isSelected }"
    role="button"
    tabindex="0"
    :aria-selected="isSelected"
    @click="emit('select', field)"
    @keydown.enter="emit('select', field)"
    @keydown.space.prevent="emit('select', field)"
  >
    <!-- Type icon -->
    <span class="field-nav-item__type-icon" aria-hidden="true">{{ typeIcon }}</span>

    <!-- Field name -->
    <span class="field-nav-item__name">{{ field.name }}</span>

    <!-- Optional badge -->
    <span v-if="field.isOptional" class="field-nav-item__optional" title="Campo opcional">⚠</span>

    <!-- Status badge -->
    <span
      class="field-nav-item__status"
      :class="`field-nav-item__status--${field.status}`"
      :title="statusLabel"
      aria-hidden="true"
    >{{ statusIcon }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FieldNavItem } from '@/types/field-navigator.types'
import { TYPE_GROUPS } from '@/types/field-navigator.types'

const props = defineProps<{
  field: FieldNavItem
  isSelected: boolean
}>()

const emit = defineEmits<{
  select: [field: FieldNavItem]
}>()

const typeIcon = computed(() => TYPE_GROUPS[props.field.type]?.icon ?? '📋')

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
</script>

<style scoped>
.field-nav-item {
  display: flex;
  align-items: center;
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

.field-nav-item__type-icon {
  flex-shrink: 0;
  font-size: 0.75rem;
}

.field-nav-item__name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-nav-item__optional {
  flex-shrink: 0;
  font-size: 0.6875rem;
  color: var(--color-yellow-400, #facc15);
}

.field-nav-item__status {
  flex-shrink: 0;
  font-size: 0.625rem;
}
</style>
