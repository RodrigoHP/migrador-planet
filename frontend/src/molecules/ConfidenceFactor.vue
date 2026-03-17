<template>
  <div class="confidence-factor">
    <div class="confidence-factor__header">
      <span class="confidence-factor__label">{{ label }}</span>
      <span class="confidence-factor__value" :class="valueColorClass">
        {{ value }}% {{ thresholdIcon }}
      </span>
    </div>
    <div class="confidence-factor__bar-bg" aria-hidden="true">
      <div
        class="confidence-factor__bar-fill"
        :class="barColorClass"
        :style="{ width: `${clampedValue}%` }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value: number
}>()

const clampedValue = computed(() => Math.min(100, Math.max(0, props.value)))

const thresholdIcon = computed(() => {
  if (props.value >= 95) return '✅'
  if (props.value >= 80) return '⚠️'
  return '🔴'
})

const valueColorClass = computed(() => {
  if (props.value >= 95) return 'confidence-factor__value--green'
  if (props.value >= 80) return 'confidence-factor__value--yellow'
  return 'confidence-factor__value--red'
})

const barColorClass = computed(() => {
  if (props.value >= 95) return 'confidence-factor__bar-fill--green'
  if (props.value >= 80) return 'confidence-factor__bar-fill--yellow'
  return 'confidence-factor__bar-fill--red'
})
</script>

<style scoped>
.confidence-factor {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.confidence-factor__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
}

.confidence-factor__label {
  color: var(--color-neutral-700, #374151);
  font-weight: 500;
}

.confidence-factor__value {
  font-weight: 600;
  font-size: 0.75rem;
  white-space: nowrap;
}

.confidence-factor__value--green {
  color: #166534;
}

.confidence-factor__value--yellow {
  color: #854d0e;
}

.confidence-factor__value--red {
  color: #991b1b;
}

.confidence-factor__bar-bg {
  height: 6px;
  border-radius: 9999px;
  background: var(--color-neutral-200, #e5e7eb);
  overflow: hidden;
}

.confidence-factor__bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.confidence-factor__bar-fill--green {
  background: #22c55e;
}

.confidence-factor__bar-fill--yellow {
  background: #eab308;
}

.confidence-factor__bar-fill--red {
  background: #ef4444;
}
</style>
