<template>
  <FullWidthLayout>
    <!-- Topbar breadcrumb slot -->
    <template #stepper>
      <nav class="topbar-breadcrumb" aria-label="Breadcrumb">
        <span class="topbar-breadcrumb__item">Upload</span>
        <span class="topbar-breadcrumb__sep" aria-hidden="true">&#x203A;</span>
        <span class="topbar-breadcrumb__item topbar-breadcrumb__item--active" aria-current="page"
          >Analisando</span
        >
        <span class="topbar-breadcrumb__sep" aria-hidden="true">&#x203A;</span>
        <span class="topbar-breadcrumb__item topbar-breadcrumb__item--future">Editor</span>
      </nav>
      <button
        class="topbar-cancel"
        :disabled="sm.isCancelling.value"
        aria-label="Cancelar análise"
        @click="handleCancel"
      >
        &#x2715; Cancelar análise
      </button>
    </template>

    <div class="analyzing-page">
      <!-- Connection lost banner -->
      <div v-if="sm.connectionLost.value" class="banner banner--warning" role="alert">
        <p class="banner__title">Conexão perdida</p>
        <p class="banner__text">Não foi possível reconectar após 3 tentativas.</p>
        <button class="banner__btn banner__btn--warning" @click="sm.handleReconnect()">
          Reconectar
        </button>
      </div>

      <!-- Session lost banner -->
      <div v-if="sm.sessionLost.value" class="banner banner--orange" role="alert">
        <p class="banner__title">Sessão de análise perdida</p>
        <p class="banner__text">O servidor pode ter sido reiniciado. Faça o upload novamente.</p>
        <button class="banner__btn banner__btn--secondary" @click="handleBackToUpload">
          &#x2190; Voltar ao Upload
        </button>
      </div>

      <!-- V2 Full Redesign -->
      <template v-if="!sm.sessionLost.value && !sm.connectionLost.value">
        <!-- Stepper (always visible in v2) -->
        <AnalyzingStepper
          :stages="PIPELINE_V2_STAGES"
          :step-states="sm.stepperStates.value"
          :stage-times="sm.completedStageTimes.value"
        />

        <!-- STATE: Initializing -->
        <InitializingState
          v-if="sm.pageState.value === 'initializing'"
          :pdf-count="sm.summaryData.value.pdfCount"
        />

        <!-- STATE: Processing -->
        <template v-if="sm.pageState.value === 'processing'">
          <AnalyzingDetailCard
            :stage-number="sm.activeStageNumber.value"
            :total-stages="TOTAL_V2_STAGES"
            :stage-name="sm.activeStageInfo.value?.name ?? ''"
            :stage-description="sm.activeStageInfo.value?.description ?? ''"
            :sub-step="sm.v2SubStep.value"
            :progress-pct="sm.v2SubProgressPct.value"
            :sub-step-pill="sm.subStepPill.value"
            :estimated-time-label="sm.estimatedTimeLabel.value"
            :metrics="sm.activeMetrics.value"
          />

          <!-- Completed stage accordions -->
          <CompletedStageAccordion
            v-if="sm.completedStages.value.length > 0"
            :stages="sm.completedStages.value"
            label="Estágios concluídos"
          />

          <!-- Pending stages -->
          <div v-if="sm.pendingStages.value.length > 0" class="pending-section">
            <div class="pending-section__label">Próximos</div>
            <div class="pending-stages">
              <div v-for="s in sm.pendingStages.value" :key="s.stage" class="pending-stage">
                <div class="pending-stage__header">
                  <div class="pending-stage__icon">{{ s.stage }}</div>
                  <span class="pending-stage__name">{{ s.name }}</span>
                  <span class="pending-stage__desc">{{ s.pendingDesc }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Info cards -->
          <div class="info-row">
            <div class="info-card">
              <div class="info-card__label">PDFs</div>
              <div class="info-card__value">{{ sm.summaryData.value.pdfCount ?? '—' }}</div>
            </div>
            <div class="info-card">
              <div class="info-card__label">Páginas</div>
              <div
                class="info-card__value"
                :class="{ 'info-card__value--pending': sm.summaryData.value.pageCount == null }"
              >
                {{ sm.summaryData.value.pageCount ?? '—' }}
              </div>
            </div>
            <div class="info-card">
              <div class="info-card__label">Layouts</div>
              <div
                class="info-card__value"
                :class="{
                  'info-card__value--pending': sm.summaryData.value.layoutsDetected == null,
                }"
              >
                {{ sm.summaryData.value.layoutsDetected ?? '—' }}
              </div>
            </div>
          </div>
        </template>

        <!-- STATE: Checkpoint -->
        <template v-if="sm.pageState.value === 'checkpoint' && sm.checkpointData.value">
          <CheckpointCard
            :checkpoint="sm.checkpointData.value"
            :visible="sm.pageState.value === 'checkpoint'"
            :is-submitting="sm.isCheckpointSubmitting.value"
            @action="sm.handleCheckpointAction"
          />
          <div v-if="sm.checkpointActionError.value" class="banner banner--warning" role="alert">
            <p class="banner__title">Erro ao enviar ação</p>
            <p class="banner__text">{{ sm.checkpointActionError.value }}</p>
          </div>
        </template>

        <!-- STATE: Error -->
        <template v-if="sm.pageState.value === 'error' && sm.errorData.value">
          <ErrorCard :error="sm.errorData.value" @decide="handleErrorDecision" />

          <!-- Completed stage accordions (still visible on error) -->
          <CompletedStageAccordion
            v-if="sm.completedStages.value.length > 0"
            :stages="sm.completedStages.value"
            label="Estágios concluídos"
          />
        </template>

        <!-- STATE: Completed -->
        <template v-if="sm.pageState.value === 'completed'">
          <CompletedSummary :summary="sm.completedSummary.value" @open-editor="handleOpenEditor" />

          <!-- Pipeline degradation warnings banner -->
          <div
            v-if="sm.pipelineWarnings.value.length > 0 && !sm.warningsDismissed.value"
            class="pipeline-warnings-banner"
            role="alert"
          >
            <div class="pipeline-warnings-banner__header">
              <span class="pipeline-warnings-banner__title">Avisos do pipeline</span>
              <button
                class="pipeline-warnings-banner__close"
                aria-label="Fechar avisos"
                @click="sm.warningsDismissed.value = true"
              >
                &#x2715;
              </button>
            </div>
            <ul class="pipeline-warnings-banner__list">
              <li
                v-for="w in sm.pipelineWarnings.value"
                :key="w.code"
                class="pipeline-warnings-banner__item"
                :class="`pipeline-warnings-banner__item--${w.severity}`"
              >
                <span class="pipeline-warnings-banner__icon">{{
                  w.severity === 'warning' ? '⚠️' : 'ℹ️'
                }}</span>
                <span class="pipeline-warnings-banner__message">{{ w.message }}</span>
              </li>
            </ul>
          </div>

          <!-- All stages as accordions -->
          <CompletedStageAccordion
            v-if="sm.completedStages.value.length > 0"
            :stages="sm.completedStages.value"
            label="Detalhes por estágio"
          />
        </template>
      </template>
    </div>
  </FullWidthLayout>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import FullWidthLayout from '@/templates/FullWidthLayout.vue'
import AnalyzingStepper from '@/organisms/analyzing/AnalyzingStepper.vue'
import InitializingState from '@/organisms/analyzing/InitializingState.vue'
import AnalyzingDetailCard from '@/organisms/analyzing/AnalyzingDetailCard.vue'
import CompletedStageAccordion from '@/organisms/analyzing/CompletedStageAccordion.vue'
import CheckpointCard from '@/organisms/analyzing/CheckpointCard.vue'
import ErrorCard from '@/organisms/analyzing/ErrorCard.vue'
import CompletedSummary from '@/organisms/analyzing/CompletedSummary.vue'
import { useSessionStore } from '@/stores/session'
import { useAnalyzingStateMachine } from '@/composables/useAnalyzingStateMachine'
import { PIPELINE_V2_STAGES, TOTAL_V2_STAGES } from './analyzingPageConstantsV2'

const router = useRouter()
const session = useSessionStore()
const sm = useAnalyzingStateMachine()

// ─── Handlers ────────────────────────────────────────────────────────────────

async function handleCancel() {
  if (sm.isCancelling.value) return
  sm.isCancelling.value = true
  sm.closeSSE()
  try {
    const API_BASE = import.meta.env.VITE_API_URL ?? ''
    if (session.jobId) {
      const { apiFetch } = await import('@/services/apiFetch')
      await apiFetch(`${API_BASE}/api/v1/analyze/${session.jobId}/cancel`, { method: 'POST' })
    }
  } catch {
    // proceed regardless
  } finally {
    sm.isCancelling.value = false
    router.push('/upload')
  }
}

async function _handleRetry() {
  sm.resetState()
  if (session.jobId) {
    try {
      await sm.startPipeline(session.jobId)
    } catch {
      sm.errorData.value = {
        stage: 0,
        stageName: 'Inicialização',
        service: '',
        errorMessage: 'Erro ao iniciar pipeline de análise.',
        retriesAttempted: 0,
      }
      sm.pageState.value = 'error'
      return
    }
    sm.pipelineStartTime.value = Date.now()
    sm.connectSSE(session.jobId)
  }
}

async function handleErrorDecision(action: 'retry' | 'fallback' | 'abort') {
  if (action === 'abort') {
    handleCancel()
    return
  }
  await sm.handleErrorDecision(action)
}

async function handleOpenEditor() {
  const success = await sm.fetchAndLoadResult()
  if (success) router.push('/editor')
}

function handleBackToUpload() {
  sm.closeSSE()
  router.push('/upload')
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(async () => {
  if (session.jobId) {
    sm.pipelineStartTime.value = Date.now()
    try {
      await sm.startPipeline(session.jobId)
    } catch {
      sm.errorData.value = {
        stage: 0,
        stageName: 'Inicialização',
        service: '',
        errorMessage: 'Erro ao iniciar pipeline de análise.',
        retriesAttempted: 0,
      }
      sm.pageState.value = 'error'
      return
    }
    sm.connectSSE(session.jobId)
  }
})

onUnmounted(() => {
  sm.closeSSE()
})
</script>

<style scoped>
.analyzing-page {
  padding: 2rem 0;
}

/* --- Topbar breadcrumb --- */
.topbar-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
}

.topbar-breadcrumb__item {
  font-size: 14px;
  color: #64748b;
}

.topbar-breadcrumb__item--active {
  color: #1e293b;
  font-weight: 500;
}

.topbar-breadcrumb__item--future {
  color: #cbd5e1;
}

.topbar-breadcrumb__sep {
  color: #cbd5e1;
  font-size: 14px;
}

.topbar-cancel {
  font-size: 13px;
  color: #ef4444;
  cursor: pointer;
  padding: 6px 14px;
  border: 1px solid #fecaca;
  border-radius: 6px;
  background: #fff;
  transition: all 0.15s;
  margin-left: auto;
}

.topbar-cancel:hover {
  background: #fef2f2;
}

.topbar-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.topbar-cancel:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

/* --- Banners --- */
.banner {
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 20px;
}

.banner--warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.banner--orange {
  background: #fff7ed;
  border: 1px solid #fed7aa;
}

.banner--error {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.banner__title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.banner--warning .banner__title {
  color: #b45309;
}
.banner--orange .banner__title {
  color: #c2410c;
}
.banner--error .banner__title {
  color: #dc2626;
}

.banner__text {
  font-size: 13px;
  margin-bottom: 12px;
}

.banner--warning .banner__text {
  color: #92400e;
}
.banner--orange .banner__text {
  color: #9a3412;
}
.banner--error .banner__text {
  color: #b91c1c;
}

.banner__actions {
  display: flex;
  gap: 10px;
}

.banner__btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.banner__btn:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

.banner__btn--primary {
  background: #2563eb;
  color: #fff;
}
.banner__btn--primary:hover {
  background: #1d4ed8;
}
.banner__btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.banner__btn--secondary {
  background: #fff;
  color: #475569;
  border: 1px solid #e2e8f0;
}
.banner__btn--secondary:hover {
  background: #f8fafc;
}

.banner__btn--warning {
  background: #f59e0b;
  color: #fff;
}
.banner__btn--warning:hover {
  background: #d97706;
}

/* --- Pipeline Warnings Banner --- */
.pipeline-warnings-banner {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 20px;
}

.pipeline-warnings-banner__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.pipeline-warnings-banner__title {
  font-size: 13px;
  font-weight: 600;
  color: #92400e;
}

.pipeline-warnings-banner__close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #92400e;
  line-height: 1;
  padding: 2px 4px;
  border-radius: 4px;
}

.pipeline-warnings-banner__close:hover {
  background: #fde68a;
}

.pipeline-warnings-banner__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pipeline-warnings-banner__item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}

.pipeline-warnings-banner__item--info .pipeline-warnings-banner__message {
  color: #1e40af;
}
.pipeline-warnings-banner__item--warning .pipeline-warnings-banner__message {
  color: #92400e;
}
.pipeline-warnings-banner__item--error .pipeline-warnings-banner__message {
  color: #b91c1c;
}

.pipeline-warnings-banner__icon {
  flex-shrink: 0;
  line-height: 1.4;
}

.pipeline-warnings-banner__message {
  line-height: 1.4;
}

/* --- V2 Sections --- */
.pending-section {
  margin-top: 20px;
}

.pending-section__label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}

.pending-stages {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.pending-stage {
  background: #fff;
  border: 1px solid #f1f5f9;
  border-radius: 10px;
}

.pending-stage__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  opacity: 0.6;
}

.pending-stage__icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
  background: #f1f5f9;
  color: #64748b;
}

.pending-stage__name {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

.pending-stage__desc {
  font-size: 12px;
  color: #cbd5e1;
  margin-left: auto;
}

/* --- Info Cards --- */
.info-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 20px;
  margin-bottom: 20px;
}

.info-card {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 16px 18px;
}

.info-card__label {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}

.info-card__value {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
}

.info-card__value--pending {
  color: #cbd5e1;
}

/* --- A11y Focus --- */
*:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}
</style>
