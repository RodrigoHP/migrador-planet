<template>
  <div
    class="dataset-item"
    :class="{
      'dataset-item--active': isActive,
      'dataset-item--valid': dataset.status === 'valid',
      'dataset-item--warning': dataset.status === 'warning',
      'dataset-item--invalid': dataset.status === 'invalid',
    }"
    role="option"
    :aria-selected="isActive"
    data-testid="dataset-item"
    @click="emit('select', dataset.id)"
  >
    <!-- Active indicator -->
    <span
      class="dataset-item__active-dot"
      :class="{ 'dataset-item__active-dot--visible': isActive }"
      aria-hidden="true"
      >&#9679;</span
    >

    <!-- Dataset name -->
    <span class="dataset-item__name">{{ dataset.name }}</span>

    <!-- Status badge -->
    <span
      class="dataset-item__badge"
      :class="`dataset-item__badge--${dataset.status}`"
      :title="statusLabel"
      >{{ statusIcon }}</span
    >

    <!-- Delete button -->
    <button
      class="dataset-item__delete"
      type="button"
      :aria-label="`Excluir dataset ${dataset.name}`"
      title="Excluir dataset"
      data-testid="dataset-item-delete"
      @click.stop="emit('delete', dataset.id)"
    >
      🗑️
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Dataset } from '@/types/test-data.types'

const props = defineProps<{
  dataset: Dataset
  isActive: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  delete: [id: string]
}>()

const statusIcon = computed(() => {
  switch (props.dataset.status) {
    case 'valid':
      return '✓'
    case 'warning':
      return '⚠'
    case 'invalid':
      return '✕'
    default:
      return '?'
  }
})

const statusLabel = computed(() => {
  switch (props.dataset.status) {
    case 'valid':
      return 'Validado'
    case 'warning':
      return 'Aviso: campos opcionais ausentes'
    case 'invalid':
      return 'Inválido: campos obrigatórios ausentes ou tipo incompatível'
    default:
      return 'Não validado'
  }
})
</script>

<style scoped>
.dataset-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.5rem;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background 0.12s;
  user-select: none;
  border: 1px solid transparent;
}

.dataset-item:hover {
  background: var(--color-neutral-700, #374151);
}

.dataset-item--active {
  background: var(--color-neutral-700, #374151);
  border-color: var(--color-primary-600, #2563eb);
}

.dataset-item__active-dot {
  font-size: 0.5rem;
  color: transparent;
  flex-shrink: 0;
  line-height: 1;
}

.dataset-item__active-dot--visible {
  color: var(--color-primary-400, #60a5fa);
}

.dataset-item__name {
  flex: 1;
  font-size: 0.8125rem;
  color: var(--color-neutral-100, #f3f4f6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.dataset-item__badge {
  flex-shrink: 0;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.0625rem 0.3125rem;
  border-radius: 0.1875rem;
  line-height: 1.4;
}

.dataset-item__badge--valid {
  background: var(--color-success-900, #14532d);
  color: var(--color-success-300, #86efac);
}

.dataset-item__badge--warning {
  background: var(--color-warning-900, #78350f);
  color: var(--color-warning-300, #fcd34d);
}

.dataset-item__badge--invalid {
  background: var(--color-error-900, #7f1d1d);
  color: var(--color-error-300, #fca5a5);
}

.dataset-item__badge--unvalidated {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-400, #9ca3af);
}

.dataset-item__delete {
  flex-shrink: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  padding: 0.125rem;
  border-radius: 0.25rem;
  line-height: 1;
  opacity: 0.6;
  transition: opacity 0.12s;
}

.dataset-item__delete:hover {
  opacity: 1;
}
</style>
