<template>
  <div
    class="xsd-only-field"
    :class="{ 'xsd-only-field--selected': isSelected }"
    role="button"
    tabindex="0"
    :aria-selected="isSelected"
    @click="emit('select', field)"
    @keydown.enter="emit('select', field)"
    @keydown.space.prevent="emit('select', field)"
  >
    <span class="xsd-only-field__badge">🔴</span>
    <div class="xsd-only-field__content">
      <span class="xsd-only-field__name">{{ semanticName }}</span>
      <span class="xsd-only-field__path">{{ field.xsd_path }}</span>
    </div>
    <span class="xsd-only-field__label">XSD obrigatório</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UnmappedXsdField } from '@/types/pipeline.types'

interface Props {
  field: UnmappedXsdField
  isSelected?: boolean
}

const props = withDefaults(defineProps<Props>(), { isSelected: false })

const emit = defineEmits<{
  select: [field: UnmappedXsdField]
}>()

/** Derive readable name from XSD path: last segment, capitalized */
const semanticName = computed<string>(() => {
  const segment = props.field.xsd_path.split('.').pop() ?? props.field.xsd_path
  return segment.charAt(0).toUpperCase() + segment.slice(1)
})
</script>

<style scoped>
.xsd-only-field {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px 12px;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--color-neutral-400, #9ca3af);
  border-left: 2px solid var(--color-red-500, #ef4444);
  margin: 1px 0;
  transition: background-color 0.1s;
}

.xsd-only-field:hover {
  background-color: var(--color-neutral-700, #374151);
}

.xsd-only-field:focus-visible {
  outline: 2px solid var(--color-red-400, #f87171);
  outline-offset: -2px;
}

.xsd-only-field--selected {
  background-color: rgba(239, 68, 68, 0.12);
  color: var(--color-neutral-300, #d1d5db);
}

.xsd-only-field__badge {
  flex-shrink: 0;
  font-size: 0.625rem;
  margin-top: 2px;
}

.xsd-only-field__content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.xsd-only-field__name {
  font-size: 0.8125rem;
  color: var(--color-neutral-300, #d1d5db);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.xsd-only-field__path {
  font-size: 0.625rem;
  font-family: monospace;
  color: var(--color-neutral-500, #525252);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.xsd-only-field__label {
  flex-shrink: 0;
  font-size: 0.5625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-red-400, #f87171);
  white-space: nowrap;
}
</style>
