<template>
  <Teleport to="body">
    <div
      v-if="autoFixStore.isOpen"
      class="auto-fix-panel__backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auto-fix-panel-title"
      data-testid="auto-fix-panel"
      @click.self="autoFixStore.closePanel()"
    >
      <div class="auto-fix-panel">
        <!-- Header -->
        <div class="auto-fix-panel__header">
          <h2 id="auto-fix-panel-title" class="auto-fix-panel__title">🔧 Auto Fix AI</h2>
          <button
            type="button"
            class="auto-fix-panel__close-btn"
            aria-label="Fechar painel"
            @click="autoFixStore.closePanel()"
          >
            ✕
          </button>
        </div>

        <!-- Loading state -->
        <div v-if="autoFixStore.isRunning" class="auto-fix-panel__loading" data-testid="auto-fix-loading">
          <div class="auto-fix-panel__spinner" aria-hidden="true" />
          <p class="auto-fix-panel__loading-text">Analisando template com IA…</p>
        </div>

        <!-- Error state -->
        <div v-else-if="autoFixStore.error" class="auto-fix-panel__error" data-testid="auto-fix-error">
          <p class="auto-fix-panel__error-text">⚠️ {{ autoFixStore.error }}</p>
          <button
            type="button"
            class="auto-fix-panel__btn auto-fix-panel__btn--secondary"
            @click="autoFixStore.closePanel()"
          >
            Fechar
          </button>
        </div>

        <!-- Empty state (no suggestions) -->
        <div
          v-else-if="!autoFixStore.isRunning && autoFixStore.suggestions.length === 0 && !autoFixStore.isFinished"
          class="auto-fix-panel__empty"
          data-testid="auto-fix-empty"
        >
          <p>Nenhuma sugestão de correção encontrada.</p>
          <button
            type="button"
            class="auto-fix-panel__btn auto-fix-panel__btn--secondary"
            @click="autoFixStore.closePanel()"
          >
            Fechar
          </button>
        </div>

        <!-- Finished state -->
        <div v-else-if="autoFixStore.isFinished" class="auto-fix-panel__summary" data-testid="auto-fix-summary">
          <h3 class="auto-fix-panel__summary-title">✅ Revisão concluída</h3>
          <ul class="auto-fix-panel__summary-list">
            <li>
              <span class="auto-fix-panel__summary-icon">✅</span>
              Aceitas: <strong>{{ autoFixStore.appliedFixes.length }}</strong>
            </li>
            <li>
              <span class="auto-fix-panel__summary-icon">❌</span>
              Rejeitadas: <strong>{{ autoFixStore.rejectedFixes.length }}</strong>
            </li>
            <li>
              <span class="auto-fix-panel__summary-icon">⏭️</span>
              Puladas: <strong>{{ autoFixStore.skippedFixes.length }}</strong>
            </li>
          </ul>
          <button
            type="button"
            class="auto-fix-panel__btn auto-fix-panel__btn--primary"
            @click="autoFixStore.closePanel()"
          >
            Concluir
          </button>
        </div>

        <!-- Active suggestion -->
        <template v-else-if="autoFixStore.currentSuggestion">
          <!-- Progress bar -->
          <div class="auto-fix-panel__progress" data-testid="auto-fix-progress">
            <div class="auto-fix-panel__progress-text">
              Sugestão {{ autoFixStore.progress.current }} de {{ autoFixStore.progress.total }}
            </div>
            <div class="auto-fix-panel__progress-bar" role="progressbar" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100">
              <div class="auto-fix-panel__progress-fill" :style="{ width: `${progressPercent}%` }" />
            </div>
          </div>

          <!-- Fix preview with type badge and confidence badge -->
          <div class="auto-fix-panel__suggestion-row">
            <span class="auto-fix-panel__type-badge" :data-type="autoFixStore.currentSuggestion.type" data-testid="fix-type-badge">
              {{ FIX_TYPE_ICONS[autoFixStore.currentSuggestion.type as FixType] ?? autoFixStore.currentSuggestion.type }}
            </span>
            <FixPreview :suggestion="autoFixStore.currentSuggestion" />
            <ConfidenceBadge :score="autoFixStore.currentSuggestion.confidence" />
          </div>

          <!-- Action buttons -->
          <div class="auto-fix-panel__actions" data-testid="auto-fix-actions">
            <button
              type="button"
              class="auto-fix-panel__btn auto-fix-panel__btn--accept"
              data-testid="btn-accept"
              @click="autoFixStore.acceptCurrent()"
            >
              ✅ Aceitar
            </button>
            <button
              type="button"
              class="auto-fix-panel__btn auto-fix-panel__btn--skip"
              data-testid="btn-skip"
              @click="autoFixStore.skipCurrent()"
            >
              ⏭️ Pular
            </button>
            <button
              type="button"
              class="auto-fix-panel__btn auto-fix-panel__btn--reject"
              data-testid="btn-reject"
              @click="autoFixStore.rejectCurrent()"
            >
              ❌ Rejeitar
            </button>
          </div>

          <!-- Batch actions (Story 14.11) -->
          <div class="auto-fix-panel__batch" data-testid="auto-fix-batch">
            <button
              type="button"
              class="auto-fix-panel__btn auto-fix-panel__btn--secondary"
              data-testid="btn-batch-all"
              @click="showBatchPreview = 'all'"
            >
              Aceitar Todas ({{ autoFixStore.pendingSuggestions.length }})
            </button>
            <div v-if="autoFixStore.suggestionTypes.length > 1" class="auto-fix-panel__batch-type">
              <select
                v-model="selectedBatchType"
                class="auto-fix-panel__type-select"
                data-testid="batch-type-select"
              >
                <option v-for="st in autoFixStore.suggestionTypes" :key="st.type" :value="st.type">
                  {{ st.type }} ({{ st.count }})
                </option>
              </select>
              <button
                type="button"
                class="auto-fix-panel__btn auto-fix-panel__btn--secondary"
                data-testid="btn-batch-type"
                @click="showBatchPreview = 'type'"
              >
                Aceitar Tipo
              </button>
            </div>
          </div>

          <!-- Batch preview modal (inline) -->
          <div v-if="showBatchPreview" class="auto-fix-panel__preview" data-testid="batch-preview">
            <h4 class="auto-fix-panel__preview-title">
              {{ showBatchPreview === 'all' ? 'Aceitar todas as sugestões' : `Aceitar sugestões de "${selectedBatchType}"` }}
            </h4>
            <ul class="auto-fix-panel__preview-list">
              <li v-for="s in previewList.slice(0, previewExpanded ? undefined : 5)" :key="s.id">
                <ConfidenceBadge :score="s.confidence" />
                {{ s.description }}
              </li>
            </ul>
            <button
              v-if="previewList.length > 5 && !previewExpanded"
              type="button"
              class="auto-fix-panel__preview-more"
              @click="previewExpanded = true"
            >
              + {{ previewList.length - 5 }} mais
            </button>
            <div class="auto-fix-panel__preview-actions">
              <button
                type="button"
                class="auto-fix-panel__btn auto-fix-panel__btn--accept"
                data-testid="btn-batch-confirm"
                @click="confirmBatch"
              >
                Confirmar ({{ previewList.length }})
              </button>
              <button
                type="button"
                class="auto-fix-panel__btn auto-fix-panel__btn--secondary"
                data-testid="btn-batch-cancel"
                @click="showBatchPreview = null; previewExpanded = false"
              >
                Cancelar
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAutoFixStore, type FixType } from '@/stores/autoFixStore'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useCoverageStore } from '@/stores/coverageStore'
import FixPreview from '@/molecules/FixPreview.vue'
import ConfidenceBadge from '@/molecules/ConfidenceBadge.vue'

const FIX_TYPE_ICONS: Record<FixType, string> = {
  spacing: 'Spacing',
  alignment: 'Align',
  font: 'Font',
  binding: 'Bind',
  position: 'Pos',
  'border-refine': 'Border',
  'background-refine': 'BG',
  'text-align': 'TxtAlign',
  'z-order': 'Z-Order',
}

const autoFixStore = useAutoFixStore()
const confidenceStore = useConfidenceStore()
const coverageStore = useCoverageStore()

const progressPercent = computed(() => {
  const { current, total } = autoFixStore.progress
  if (total === 0) return 0
  return Math.round(((current - 1) / total) * 100)
})

// ─── Batch state (Story 14.11) ──────────────────────────────────────────────
const showBatchPreview = ref<'all' | 'type' | null>(null)
const previewExpanded = ref(false)
const selectedBatchType = ref('')

// Auto-select first type when types change
watch(
  () => autoFixStore.suggestionTypes,
  (types) => {
    if (types.length > 0 && !selectedBatchType.value) {
      selectedBatchType.value = types[0]!.type
    }
  },
  { immediate: true },
)

const previewList = computed(() => {
  if (showBatchPreview.value === 'type') {
    return autoFixStore.pendingSuggestions.filter((s) => s.type === selectedBatchType.value)
  }
  return autoFixStore.pendingSuggestions
})

function confirmBatch() {
  if (showBatchPreview.value === 'type') {
    autoFixStore.batchAcceptByType(selectedBatchType.value)
  } else {
    autoFixStore.batchAcceptAll()
  }
  showBatchPreview.value = null
  previewExpanded.value = false
}

// Watch for finish to recalculate metrics
watch(
  () => autoFixStore.isFinished,
  (finished) => {
    if (!finished) return
    void confidenceStore
    void coverageStore
  },
)
</script>

<style scoped>
.auto-fix-panel__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.auto-fix-panel {
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.75rem;
  padding: 1.5rem;
  width: min(42rem, 95vw);
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  color: var(--color-neutral-100, #f3f4f6);
}

.auto-fix-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.auto-fix-panel__title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
}

.auto-fix-panel__close-btn {
  background: none;
  border: none;
  color: var(--color-neutral-400, #9ca3af);
  font-size: 1.125rem;
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
  border-radius: 0.25rem;
  transition: color 0.15s;
}

.auto-fix-panel__close-btn:hover {
  color: var(--color-neutral-100, #f3f4f6);
}

/* Loading */
.auto-fix-panel__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
}

.auto-fix-panel__spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid var(--color-neutral-700, #374151);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auto-fix-panel__loading-text {
  margin: 0;
  color: var(--color-neutral-300, #d1d5db);
  font-size: 0.875rem;
}

/* Error */
.auto-fix-panel__error {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: flex-start;
}

.auto-fix-panel__error-text {
  margin: 0;
  font-size: 0.875rem;
  color: #fca5a5;
}

/* Empty */
.auto-fix-panel__empty {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: flex-start;
  color: var(--color-neutral-300, #d1d5db);
  font-size: 0.875rem;
}

/* Summary */
.auto-fix-panel__summary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.auto-fix-panel__summary-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.auto-fix-panel__summary-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--color-neutral-300, #d1d5db);
}

.auto-fix-panel__summary-icon {
  margin-right: 0.375rem;
}

/* Progress */
.auto-fix-panel__progress {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.auto-fix-panel__progress-text {
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
}

.auto-fix-panel__progress-bar {
  height: 0.375rem;
  background: var(--color-neutral-700, #374151);
  border-radius: 9999px;
  overflow: hidden;
}

.auto-fix-panel__progress-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

/* Action buttons */
.auto-fix-panel__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.auto-fix-panel__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s, opacity 0.15s;
}

.auto-fix-panel__btn--accept {
  background: #065f46;
  border-color: #059669;
  color: #a7f3d0;
}

.auto-fix-panel__btn--accept:hover {
  background: #047857;
}

.auto-fix-panel__btn--reject {
  background: #7f1d1d;
  border-color: #b91c1c;
  color: #fecaca;
}

.auto-fix-panel__btn--reject:hover {
  background: #991b1b;
}

.auto-fix-panel__btn--skip {
  background: var(--color-neutral-700, #374151);
  border-color: var(--color-neutral-600, #4b5563);
  color: var(--color-neutral-200, #e5e7eb);
}

.auto-fix-panel__btn--skip:hover {
  background: var(--color-neutral-600, #4b5563);
}

.auto-fix-panel__btn--primary {
  background: #1d4ed8;
  border-color: #2563eb;
  color: #fff;
}

.auto-fix-panel__btn--primary:hover {
  background: #2563eb;
}

.auto-fix-panel__btn--secondary {
  background: var(--color-neutral-700, #374151);
  border-color: var(--color-neutral-600, #4b5563);
  color: var(--color-neutral-200, #e5e7eb);
}

.auto-fix-panel__btn--secondary:hover {
  background: var(--color-neutral-600, #4b5563);
}

/* Suggestion row with badge */
.auto-fix-panel__suggestion-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.auto-fix-panel__type-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.625rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  white-space: nowrap;
  flex-shrink: 0;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-200, #e5e7eb);
  border: 1px solid var(--color-neutral-600, #4b5563);
}

.auto-fix-panel__type-badge[data-type="border-refine"] {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.3);
}

.auto-fix-panel__type-badge[data-type="background-refine"] {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  border-color: rgba(139, 92, 246, 0.3);
}

.auto-fix-panel__type-badge[data-type="text-align"] {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  border-color: rgba(59, 130, 246, 0.3);
}

.auto-fix-panel__type-badge[data-type="z-order"] {
  background: rgba(236, 72, 153, 0.15);
  color: #f9a8d4;
  border-color: rgba(236, 72, 153, 0.3);
}

/* Batch actions */
.auto-fix-panel__batch {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-neutral-700, #374151);
}

.auto-fix-panel__batch-type {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.auto-fix-panel__type-select {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  color: var(--color-neutral-100, #f3f4f6);
  font-size: 0.8125rem;
  padding: 0.375rem 0.5rem;
  outline: none;
  cursor: pointer;
}

/* Batch preview */
.auto-fix-panel__preview {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.auto-fix-panel__preview-title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
}

.auto-fix-panel__preview-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--color-neutral-300, #d1d5db);
  max-height: 12rem;
  overflow-y: auto;
}

.auto-fix-panel__preview-list li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.auto-fix-panel__preview-more {
  background: none;
  border: none;
  color: var(--color-primary-400, #818cf8);
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0;
  text-align: left;
}

.auto-fix-panel__preview-actions {
  display: flex;
  gap: 0.5rem;
}
</style>
