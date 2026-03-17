<template>
  <button
    type="button"
    class="coverage-badge"
    :class="[`coverage-badge--${colorClass}`]"
    :aria-label="`Cobertura: ${displayPct}%`"
    @click="emit('click')"
  >
    <span class="coverage-badge__label">Cobertura</span>
    <span class="coverage-badge__value">{{ displayPct }}%</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  percentage: number | undefined
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()

const displayPct = computed(() => (props.percentage !== undefined ? Math.round(props.percentage) : '--'))

const colorClass = computed(() => {
  if (props.percentage === undefined) return 'unknown'
  if (props.percentage >= 95) return 'green'
  if (props.percentage >= 80) return 'yellow'
  return 'red'
})
</script>

<style scoped>
.coverage-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  border: none;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  transition: opacity 0.15s;
}

.coverage-badge:hover {
  opacity: 0.85;
}

.coverage-badge__label {
  opacity: 0.8;
}

.coverage-badge__value {
  font-weight: 700;
}

.coverage-badge--green {
  background: #dcfce7;
  color: #166534;
}

.coverage-badge--yellow {
  background: #fef9c3;
  color: #854d0e;
}

.coverage-badge--red {
  background: #fee2e2;
  color: #991b1b;
}

.coverage-badge--unknown {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-300, #d1d5db);
}
</style>
