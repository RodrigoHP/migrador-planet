<template>
  <div class="fix-preview" data-testid="fix-preview">
    <!-- Type badge -->
    <div class="fix-preview__header">
      <span class="fix-preview__type-badge" :class="`fix-preview__type-badge--${suggestion.type}`">
        {{ typeLabel }}
      </span>
      <span class="fix-preview__confidence">{{ suggestion.confidence }}% confiança</span>
    </div>

    <!-- Problem description -->
    <p class="fix-preview__description" data-testid="fix-description">
      {{ suggestion.description }}
    </p>

    <!-- Element ID reference -->
    <p v-if="suggestion.element_id" class="fix-preview__element-id">
      Elemento: <code>{{ suggestion.element_id }}</code>
    </p>

    <!-- Before / After comparison -->
    <div class="fix-preview__diff" data-testid="fix-diff">
      <div class="fix-preview__diff-side fix-preview__diff-side--before">
        <span class="fix-preview__diff-label">Antes</span>
        <code class="fix-preview__diff-value fix-preview__diff-value--old" data-testid="fix-before">
          {{ suggestion.current_value || '(vazio)' }}
        </code>
      </div>
      <span class="fix-preview__diff-arrow" aria-hidden="true">→</span>
      <div class="fix-preview__diff-side fix-preview__diff-side--after">
        <span class="fix-preview__diff-label">Depois</span>
        <code class="fix-preview__diff-value fix-preview__diff-value--new" data-testid="fix-after">
          {{ suggestion.suggested_value || '(vazio)' }}
        </code>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FixSuggestion, FixType } from '@/stores/autoFixStore'

const props = defineProps<{
  suggestion: FixSuggestion
}>()

const TYPE_LABELS: Record<FixType, string> = {
  spacing: 'Espaçamento',
  alignment: 'Alinhamento',
  font: 'Fonte',
  binding: 'Binding',
  position: 'Posição',
  'text-align': 'Alinhamento de texto',
  'border-refine': 'Borda',
  'background-refine': 'Fundo',
  'z-order': 'Ordem Z',
}

const typeLabel = computed(() => TYPE_LABELS[props.suggestion.type] ?? props.suggestion.type)
</script>

<style scoped>
.fix-preview {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--color-neutral-800, #1f2937);
  border-radius: 0.5rem;
  color: var(--color-neutral-100, #f3f4f6);
}

.fix-preview__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.fix-preview__type-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.fix-preview__type-badge--spacing {
  background: #1e40af;
  color: #bfdbfe;
}

.fix-preview__type-badge--alignment {
  background: #065f46;
  color: #a7f3d0;
}

.fix-preview__type-badge--font {
  background: #581c87;
  color: #e9d5ff;
}

.fix-preview__type-badge--binding {
  background: #92400e;
  color: #fde68a;
}

.fix-preview__type-badge--position {
  background: #7f1d1d;
  color: #fecaca;
}

.fix-preview__confidence {
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
}

.fix-preview__description {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--color-neutral-200, #e5e7eb);
}

.fix-preview__element-id {
  margin: 0;
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
}

.fix-preview__element-id code {
  background: var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
  padding: 0 0.25rem;
  font-family: monospace;
}

.fix-preview__diff {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.fix-preview__diff-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.fix-preview__diff-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-neutral-400, #9ca3af);
}

.fix-preview__diff-arrow {
  font-size: 1.25rem;
  color: var(--color-neutral-400, #9ca3af);
  flex-shrink: 0;
}

.fix-preview__diff-value {
  display: block;
  padding: 0.375rem 0.5rem;
  border-radius: 0.25rem;
  font-family: monospace;
  font-size: 0.8125rem;
  word-break: break-all;
  border: 1px solid transparent;
}

.fix-preview__diff-value--old {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.4);
  color: #fca5a5;
}

.fix-preview__diff-value--new {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.4);
  color: #86efac;
}
</style>
