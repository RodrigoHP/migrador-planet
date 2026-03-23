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
    <span v-if="breakdownText" class="coverage-badge__breakdown">{{ breakdownText }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CoverageData } from '@/types/coverage.types'

const props = defineProps<{
  percentage: number | undefined
  breakdown?: CoverageData
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

function pct(mapped: number, total: number): string {
  if (total === 0) return '0'
  return String(Math.round((mapped / total) * 100))
}

const breakdownText = computed(() => {
  if (!props.breakdown) return ''
  const parts: string[] = []
  if (props.breakdown.fields.total > 0) parts.push(`campos ${pct(props.breakdown.fields.mapped, props.breakdown.fields.total)}%`)
  if (props.breakdown.tables.total > 0) parts.push(`tabelas ${pct(props.breakdown.tables.mapped, props.breakdown.tables.total)}%`)
  if (props.breakdown.images.total > 0) parts.push(`imagens ${pct(props.breakdown.images.mapped, props.breakdown.images.total)}%`)
  if (parts.length === 0) return ''
  return `(${parts.join(' | ')})`
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

.coverage-badge__breakdown {
  font-size: 0.625rem;
  font-weight: 500;
  opacity: 0.75;
}
</style>
