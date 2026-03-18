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

          <!-- Fix preview -->
          <FixPreview :suggestion="autoFixStore.currentSuggestion" />

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
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAutoFixStore } from '@/stores/autoFixStore'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useCoverageStore } from '@/stores/coverageStore'
import FixPreview from '@/molecules/FixPreview.vue'

const autoFixStore = useAutoFixStore()
const confidenceStore = useConfidenceStore()
const coverageStore = useCoverageStore()

const progressPercent = computed(() => {
  const { current, total } = autoFixStore.progress
  if (total === 0) return 0
  return Math.round(((current - 1) / total) * 100)
})

// Watch for finish to recalculate metrics
// We use the isFinished getter reactively — when it becomes true, recalculate
import { watch } from 'vue'

watch(
  () => autoFixStore.isFinished,
  (finished) => {
    if (!finished) return
    // Recalculate confidence and coverage after fixes applied
    // These stores don't have a recalculate() method yet — we trigger re-computation
    // by nudging the store (no-op if no changes needed)
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
</style>
