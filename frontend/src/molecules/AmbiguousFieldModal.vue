<template>
  <Teleport to="body">
    <!-- Overlay -->
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ambiguous-modal-title"
      tabindex="-1"
      @click.self="cancel"
      @keydown.escape="cancel"
    >
      <div class="ambiguous-modal">
        <!-- Header -->
        <div class="ambiguous-modal__header">
          <h2 id="ambiguous-modal-title" class="ambiguous-modal__title">
            ⚡ Resolver Ambiguidade
          </h2>
          <button class="ambiguous-modal__close" @click="cancel" aria-label="Fechar modal">✕</button>
        </div>

        <!-- Field info -->
        <div class="ambiguous-modal__info">
          <span class="ambiguous-modal__info-label">Campo PDF:</span>
          <span class="ambiguous-modal__info-value">"{{ fieldDisplayName }}"</span>
        </div>
        <p class="ambiguous-modal__subtitle">Selecione o campo XSD correto:</p>

        <!-- Candidates -->
        <ul class="ambiguous-modal__candidates" role="radiogroup" aria-label="Candidatos XSD">
          <li
            v-for="candidate in sortedCandidates"
            :key="candidate.path"
            class="ambiguous-modal__candidate"
            :class="{ 'ambiguous-modal__candidate--selected': selected === candidate.path }"
            @click="selected = candidate.path"
          >
            <input
              type="radio"
              :id="`cand-${candidate.path}`"
              :value="candidate.path"
              v-model="selected"
              class="ambiguous-modal__radio"
            />
            <label :for="`cand-${candidate.path}`" class="ambiguous-modal__candidate-label">
              <span class="candidate-path">{{ candidate.path }}</span>
              <span class="candidate-semantic">{{ semanticLabel(candidate.path) }}</span>
            </label>
            <div class="candidate-score">
              <div
                class="candidate-score__bar"
                :style="{ '--score-pct': (scoreValue(candidate) * 100) + '%' }"
              >
                <div
                  class="candidate-score__fill"
                  :class="scoreBarClass(candidate)"
                  :style="{ width: (scoreValue(candidate) * 100) + '%' }"
                />
              </div>
              <span class="candidate-score__value">{{ Math.round(scoreValue(candidate) * 100) }}%</span>
            </div>
          </li>
        </ul>

        <!-- None of the above -->
        <div class="ambiguous-modal__none">
          <label class="ambiguous-modal__none-label">
            <input
              type="radio"
              :value="null"
              v-model="selected"
              class="ambiguous-modal__radio"
            />
            Nenhum dos anteriores — deixar sem mapeamento
          </label>
        </div>

        <!-- Actions -->
        <div class="ambiguous-modal__actions">
          <button class="ambiguous-modal__btn ambiguous-modal__btn--secondary" @click="cancel">
            Cancelar
          </button>
          <button
            class="ambiguous-modal__btn ambiguous-modal__btn--primary"
            :disabled="selected === undefined"
            @click="confirm"
          >
            Confirmar →
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FieldNavItem } from '@/types/field-navigator.types'

interface Candidate {
  path: string
  confidence?: number
  score?: number
}

interface Props {
  field: FieldNavItem
}

interface Emits {
  resolve: [chosenPath: string | null]
  cancel: []
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// undefined = nothing selected yet; null = "none of the above"
const selected = ref<string | null | undefined>(undefined)

const fieldDisplayName = computed<string>(() => {
  // Use rawPdfText, name, or path as display
  return (props.field as unknown as Record<string, string>)['rawPdfText']
    ?? props.field.name
    ?? props.field.path
})

/** Candidates sorted by score/confidence descending */
const sortedCandidates = computed<Candidate[]>(() => {
  const cands = (props.field.candidates ?? []) as Candidate[]
  return [...cands].sort((a, b) => scoreValue(b) - scoreValue(a))
})

function scoreValue(c: Candidate): number {
  return c.confidence ?? c.score ?? 0
}

function semanticLabel(path: string): string {
  const segment = path.split('.').pop() ?? path
  return segment.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase())
}

function scoreBarClass(c: Candidate): string {
  const pct = scoreValue(c) * 100
  if (pct >= 70) return 'candidate-score__fill--high'
  if (pct >= 50) return 'candidate-score__fill--mid'
  return 'candidate-score__fill--low'
}

function confirm() {
  if (selected.value !== undefined) {
    emit('resolve', selected.value)
  }
}

function cancel() {
  emit('cancel')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.ambiguous-modal {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 8px;
  padding: 20px;
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
}

.ambiguous-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.ambiguous-modal__title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
}

.ambiguous-modal__close {
  background: none;
  border: none;
  color: var(--color-neutral-400, #9ca3af);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 3px;
}

.ambiguous-modal__close:hover {
  color: var(--color-neutral-100, #f3f4f6);
  background: var(--color-neutral-700, #374151);
}

.ambiguous-modal__info {
  font-size: 0.8125rem;
  color: var(--color-neutral-300, #d1d5db);
  margin-bottom: 4px;
}

.ambiguous-modal__info-label {
  color: var(--color-neutral-500, #6b7280);
  margin-right: 4px;
}

.ambiguous-modal__info-value {
  font-weight: 500;
}

.ambiguous-modal__subtitle {
  margin: 0 0 12px;
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
}

/* Candidates list */
.ambiguous-modal__candidates {
  list-style: none;
  margin: 0 0 8px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ambiguous-modal__candidate {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid var(--color-neutral-700, #374151);
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s;
}

.ambiguous-modal__candidate:hover {
  background: var(--color-neutral-700, #374151);
}

.ambiguous-modal__candidate--selected {
  background: var(--color-primary-900, #1e3a5f);
  border-color: var(--color-primary-500, #3b82f6);
}

.ambiguous-modal__radio {
  flex-shrink: 0;
  cursor: pointer;
  /* Tailwind v4 @tailwindcss/forms aplica appearance:none + currentColor para :checked.
     No contexto dark do modal, currentColor herda para #171717 (invisível em #262626).
     Forçar azul como currentColor garante visibilidade do estado selecionado. */
  color: var(--color-primary-500, #3b82f6);
}

.ambiguous-modal__radio:checked {
  /* Fallback explícito caso o plugin não aplique :checked via currentColor */
  background-color: var(--color-primary-500, #3b82f6);
  border-color: var(--color-primary-500, #3b82f6);
}

.ambiguous-modal__candidate-label {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  cursor: pointer;
}

.candidate-path {
  font-size: 0.8125rem;
  font-family: monospace;
  color: var(--color-neutral-200, #e5e7eb);
}

.candidate-semantic {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
}

/* Score bar */
.candidate-score {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  width: 90px;
}

.candidate-score__bar {
  flex: 1;
  height: 5px;
  background: var(--color-neutral-700, #374151);
  border-radius: 2.5px;
  overflow: hidden;
}

.candidate-score__fill {
  height: 100%;
  border-radius: 2.5px;
  transition: width 0.2s;
}

.candidate-score__fill--high {
  background: var(--color-green-500, #22c55e);
}

.candidate-score__fill--mid {
  background: var(--color-yellow-400, #facc15);
}

.candidate-score__fill--low {
  background: var(--color-neutral-500, #6b7280);
}

.candidate-score__value {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  width: 30px;
  text-align: right;
}

/* None option */
.ambiguous-modal__none {
  padding: 8px 10px;
  border-top: 1px solid var(--color-neutral-700, #374151);
  margin-top: 8px;
}

.ambiguous-modal__none-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--color-neutral-300, #d1d5db);
  cursor: pointer;
}

/* Actions */
.ambiguous-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--color-neutral-700, #374151);
}

.ambiguous-modal__btn {
  padding: 6px 16px;
  border-radius: 5px;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: background 0.1s;
}

.ambiguous-modal__btn--secondary {
  background: none;
  border: 1px solid var(--color-neutral-600, #4b5563);
  color: var(--color-neutral-300, #d1d5db);
}

.ambiguous-modal__btn--secondary:hover {
  background: var(--color-neutral-700, #374151);
}

.ambiguous-modal__btn--primary {
  background: var(--color-primary-600, #2563eb);
  border: none;
  color: white;
  font-weight: 500;
}

.ambiguous-modal__btn--primary:hover:not(:disabled) {
  background: var(--color-primary-500, #3b82f6);
}

.ambiguous-modal__btn--primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
