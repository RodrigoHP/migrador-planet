<template>
  <div class="detection-card" :class="`detection-card--${detection.type}`">
    <!-- Header row: type badge + confidence -->
    <div class="detection-card__header">
      <span class="detection-card__type-badge">{{ typeLabel }}</span>
      <span class="detection-card__confidence" :class="confidenceClass">
        {{ confidencePercent }}%
      </span>
    </div>

    <!-- Description -->
    <p class="detection-card__description">{{ detection.description }}</p>

    <!-- Actions -->
    <div class="detection-card__actions">
      <button
        type="button"
        class="detection-card__btn detection-card__btn--confirm"
        aria-label="Confirmar inferência"
        @click="emit('confirm', detection.id)"
      >
        ✅ Confirmar
      </button>
      <button
        type="button"
        class="detection-card__btn detection-card__btn--reject"
        aria-label="Rejeitar inferência"
        @click="emit('reject', detection.id)"
      >
        ❌ Rejeitar
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Detection } from '@/types/multi-doc.types'

const props = defineProps<{
  detection: Detection
}>()

const emit = defineEmits<{
  (e: 'confirm', id: string): void
  (e: 'reject', id: string): void
}>()

const typeLabels: Record<string, string> = {
  required: 'Obrigatório',
  optional_field: 'Campo Opcional',
  optional_section: 'Seção Opcional',
  conditional_section: 'Seção Condicional',
  dynamic_table: 'Tabela Dinâmica',
}

const typeLabel = computed(() => typeLabels[props.detection.type] ?? props.detection.type)

const confidencePercent = computed(() => Math.round(props.detection.confidence * 100))

const confidenceClass = computed(() => {
  const pct = confidencePercent.value
  if (pct >= 80) return 'detection-card__confidence--high'
  if (pct >= 50) return 'detection-card__confidence--medium'
  return 'detection-card__confidence--low'
})
</script>

<style scoped>
.detection-card {
  background: var(--color-neutral-750, #1c2533);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  padding: 0.625rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.detection-card--required {
  border-left: 3px solid #22c55e;
}

.detection-card--optional_field {
  border-left: 3px solid #60a5fa;
}

.detection-card--optional_section {
  border-left: 3px solid #a78bfa;
}

.detection-card--conditional_section {
  border-left: 3px solid #f59e0b;
}

.detection-card--dynamic_table {
  border-left: 3px solid #ec4899;
}

.detection-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.detection-card__type-badge {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-300, #d1d5db);
  background: var(--color-neutral-700, #374151);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
}

.detection-card__confidence {
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
}

.detection-card__confidence--high {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.detection-card__confidence--medium {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.detection-card__confidence--low {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.detection-card__description {
  font-size: 0.8125rem;
  color: var(--color-neutral-300, #d1d5db);
  margin: 0;
  line-height: 1.4;
}

.detection-card__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.125rem;
}

.detection-card__btn {
  flex: 1;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid transparent;
  border-radius: 0.25rem;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.detection-card__btn--confirm {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.3);
}

.detection-card__btn--confirm:hover {
  background: rgba(34, 197, 94, 0.25);
}

.detection-card__btn--reject {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}

.detection-card__btn--reject:hover {
  background: rgba(239, 68, 68, 0.25);
}
</style>
