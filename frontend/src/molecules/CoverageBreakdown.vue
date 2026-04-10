<template>
  <div class="coverage-breakdown">
    <div class="coverage-breakdown__header">
      <span class="coverage-breakdown__icon" aria-hidden="true">{{ icon }}</span>
      <span class="coverage-breakdown__label">{{ label }}</span>
      <span class="coverage-breakdown__count">{{ mapped }}/{{ total }}</span>
      <span class="coverage-breakdown__threshold" :class="valueColorClass">
        {{ thresholdIcon }}
      </span>
    </div>
    <div class="coverage-breakdown__bar-bg" aria-hidden="true">
      <div
        class="coverage-breakdown__bar-fill"
        :class="barColorClass"
        :style="{ width: `${percentage}%` }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  icon: string
  label: string
  mapped: number
  total: number
}>()

const percentage = computed(() => {
  if (props.total === 0) return 100
  return Math.round((props.mapped / props.total) * 100)
})

const thresholdIcon = computed(() => {
  if (percentage.value >= 95) return '✅'
  if (percentage.value >= 80) return '⚠️'
  return '🔴'
})

const valueColorClass = computed(() => {
  if (percentage.value >= 95) return 'coverage-breakdown__threshold--green'
  if (percentage.value >= 80) return 'coverage-breakdown__threshold--yellow'
  return 'coverage-breakdown__threshold--red'
})

const barColorClass = computed(() => {
  if (percentage.value >= 95) return 'coverage-breakdown__bar-fill--green'
  if (percentage.value >= 80) return 'coverage-breakdown__bar-fill--yellow'
  return 'coverage-breakdown__bar-fill--red'
})
</script>

<style scoped>
.coverage-breakdown {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.coverage-breakdown__header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
}

.coverage-breakdown__icon {
  flex-shrink: 0;
}

.coverage-breakdown__label {
  flex: 1;
  color: var(--color-neutral-700, #374151);
  font-weight: 500;
}

.coverage-breakdown__count {
  font-weight: 600;
  color: var(--color-neutral-800, #1f2937);
  white-space: nowrap;
}

.coverage-breakdown__threshold {
  font-size: 0.75rem;
  flex-shrink: 0;
}

.coverage-breakdown__threshold--green {
  color: #166534;
}
.coverage-breakdown__threshold--yellow {
  color: #854d0e;
}
.coverage-breakdown__threshold--red {
  color: #991b1b;
}

.coverage-breakdown__bar-bg {
  height: 5px;
  border-radius: 9999px;
  background: var(--color-neutral-200, #e5e7eb);
  overflow: hidden;
}

.coverage-breakdown__bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.coverage-breakdown__bar-fill--green {
  background: #22c55e;
}
.coverage-breakdown__bar-fill--yellow {
  background: #eab308;
}
.coverage-breakdown__bar-fill--red {
  background: #ef4444;
}
</style>
