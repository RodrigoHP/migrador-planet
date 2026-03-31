<template>
  <FullWidthLayout>
    <!-- Topbar breadcrumb slot -->
    <template #stepper>
      <nav class="topbar-breadcrumb" aria-label="Breadcrumb">
        <span class="topbar-breadcrumb__item">Upload</span>
        <span class="topbar-breadcrumb__sep" aria-hidden="true">&#x203A;</span>
        <span class="topbar-breadcrumb__item topbar-breadcrumb__item--active" aria-current="page">Analisando</span>
        <span class="topbar-breadcrumb__sep" aria-hidden="true">&#x203A;</span>
        <span class="topbar-breadcrumb__item topbar-breadcrumb__item--future">Editor</span>
      </nav>
      <button
        class="topbar-cancel"
        :disabled="isCancelling"
        aria-label="Cancelar análise"
        @click="handleCancel"
      >
        &#x2715; Cancelar análise
      </button>
    </template>

    <div class="analyzing-page">
      <!-- Connection lost banner -->
      <div v-if="connectionLost" class="banner banner--warning" role="alert">
        <p class="banner__title">Conexão perdida</p>
        <p class="banner__text">Não foi possível reconectar após 3 tentativas.</p>
        <button class="banner__btn banner__btn--warning" @click="handleReconnect">Reconectar</button>
      </div>

      <!-- Session lost banner -->
      <div v-if="sessionLost" class="banner banner--orange" role="alert">
        <p class="banner__title">Sessão de análise perdida</p>
        <p class="banner__text">O servidor pode ter sido reiniciado. Faça o upload novamente.</p>
        <button class="banner__btn banner__btn--secondary" @click="handleBackToUpload">&#x2190; Voltar ao Upload</button>
      </div>

      <!-- V2 Full Redesign -->
      <template v-if="!sessionLost && !connectionLost">
        <!-- Stepper (always visible in v2) -->
        <AnalyzingStepper
          :stages="PIPELINE_V2_STAGES"
          :step-states="stepperStates"
          :stage-times="completedStageTimes"
        />

        <!-- STATE: Initializing -->
        <InitializingState
          v-if="pageState === 'initializing'"
          :pdf-count="summaryData.pdfCount"
        />

        <!-- STATE: Processing -->
        <template v-if="pageState === 'processing'">
          <AnalyzingDetailCard
            :stage-number="activeStageNumber"
            :total-stages="TOTAL_V2_STAGES"
            :stage-name="activeStageInfo?.name ?? ''"
            :stage-description="activeStageInfo?.description ?? ''"
            :sub-step="v2SubStep"
            :progress-pct="v2SubProgressPct"
            :sub-step-pill="subStepPill"
            :estimated-time-label="estimatedTimeLabel"
            :metrics="activeMetrics"
          />

          <!-- Completed stage accordions -->
          <CompletedStageAccordion
            v-if="completedStages.length > 0"
            :stages="completedStages"
            label="Estágios concluídos"
          />

          <!-- Pending stages -->
          <div v-if="pendingStages.length > 0" class="pending-section">
            <div class="pending-section__label">Próximos</div>
            <div class="pending-stages">
              <div v-for="s in pendingStages" :key="s.stage" class="pending-stage">
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
              <div class="info-card__value">{{ summaryData.pdfCount ?? '—' }}</div>
            </div>
            <div class="info-card">
              <div class="info-card__label">Páginas</div>
              <div class="info-card__value" :class="{ 'info-card__value--pending': summaryData.pageCount == null }">
                {{ summaryData.pageCount ?? '—' }}
              </div>
            </div>
            <div class="info-card">
              <div class="info-card__label">Layouts</div>
              <div class="info-card__value" :class="{ 'info-card__value--pending': summaryData.layoutsDetected == null }">
                {{ summaryData.layoutsDetected ?? '—' }}
              </div>
            </div>
          </div>
        </template>

        <!-- STATE: Checkpoint -->
        <template v-if="pageState === 'checkpoint' && checkpointData">
          <CheckpointCard
            :checkpoint="checkpointData"
            :visible="pageState === 'checkpoint'"
            :is-submitting="isCheckpointSubmitting"
            @action="handleCheckpointAction"
          />
          <div v-if="checkpointActionError" class="banner banner--warning" role="alert">
            <p class="banner__title">Erro ao enviar ação</p>
            <p class="banner__text">{{ checkpointActionError }}</p>
          </div>
        </template>

        <!-- STATE: Error -->
        <template v-if="pageState === 'error' && errorData">
          <ErrorCard
            :error="errorData"
            @decide="handleErrorDecision"
          />

          <!-- Completed stage accordions (still visible on error) -->
          <CompletedStageAccordion
            v-if="completedStages.length > 0"
            :stages="completedStages"
            label="Estágios concluídos"
          />
        </template>

        <!-- STATE: Completed -->
        <template v-if="pageState === 'completed'">
          <CompletedSummary
            :summary="completedSummary"
            @open-editor="handleOpenEditor"
          />

          <!-- All stages as accordions -->
          <CompletedStageAccordion
            v-if="completedStages.length > 0"
            :stages="completedStages"
            label="Detalhes por estágio"
          />
        </template>
      </template>
    </div>
  </FullWidthLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import FullWidthLayout from '@/templates/FullWidthLayout.vue'
import AnalyzingStepper from '@/components/analyzing/AnalyzingStepper.vue'
import InitializingState from '@/components/analyzing/InitializingState.vue'
import AnalyzingDetailCard from '@/components/analyzing/AnalyzingDetailCard.vue'
import CompletedStageAccordion from '@/components/analyzing/CompletedStageAccordion.vue'
import CheckpointCard from '@/components/analyzing/CheckpointCard.vue'
import ErrorCard from '@/components/analyzing/ErrorCard.vue'
import CompletedSummary from '@/components/analyzing/CompletedSummary.vue'
import type { MetricItem } from '@/components/analyzing/AnalyzingDetailCard.vue'
import { useSessionStore } from '@/stores/session'
import { apiFetch } from '@/services/apiFetch'
import {
  PIPELINE_V2_STAGES,
  TOTAL_V2_STAGES,
  SUB_STEP_LABELS,
  METRIC_LABELS,
  type AnalyzingPageState,
  type StepCircleState,
  type CompletedStageSummary,
  type CheckpointData,
  type ErrorData,
  type CompletedSummaryData,
} from './analyzingPageConstantsV2'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ─── Types ────────────────────────────────────────────────────────────────────

type V2Status = 'pending' | 'running' | 'completed' | 'failed' | 'service_failure' | 'checkpoint'

interface RawSSEData {
  event?: string
  stage?: number
  stage_name?: string
  status?: string
  progress_pct?: number
  sub_step?: string
  sub_progress_pct?: number
  summary?: Record<string, unknown>
  checkpoint?: {
    type: string
    service?: string
    stage?: string
    error?: string
    message?: string
    confidence?: number
    layouts?: Array<{ id: string; label: string; page_count: number; similar?: boolean }>
    suggestion?: { text: string; result_layouts?: number; result_confidence?: number }
    options?: Array<{ action: string; label: string; description: string; warning?: string }>
    timeout_seconds?: number
    timeout_action?: string
  }
}

// ─── State ────────────────────────────────────────────────────────────────────

const router = useRouter()
const session = useSessionStore()

// V2 State
const pageState = ref<AnalyzingPageState>('initializing')
const v2StageStatuses = ref<Map<number, V2Status>>(new Map())
const v2SubStep = ref('')
const v2SubStepRaw = ref('')  // raw SSE sub_step (e.g. "1.1 Page Classification") for subStepPill
const v2SubProgressPct = ref(0)
const v2ProgressPct = ref(0)
const stageStartTimes = ref<Map<number, number>>(new Map())
const stageElapsedTimes = ref<Map<number, number>>(new Map())
const stageSummaries = ref<Map<number, Record<string, unknown>>>(new Map())
const checkpointData = ref<CheckpointData | null>(null)
const errorData = ref<ErrorData | null>(null)
const pipelineStartTime = ref<number>(0)

// Shared state
const isCancelling = ref(false)
const isStarting = ref(false)
const isCheckpointSubmitting = ref(false)
const checkpointActionError = ref<string | null>(null)
const connectionLost = ref(false)
const sessionLost = ref(false)

const summaryData = ref<{
  pdfCount: number | null
  pageCount: number | null
  layoutsDetected: number | null
  fieldsMapped: number | null
  apiCost: number | null
  coverageTotal: number | null
  coverageBreakdown: Array<{ label: string; pct: number }> | null
  warnings: string[] | null
}>({
  pdfCount: null,
  pageCount: null,
  layoutsDetected: null,
  fieldsMapped: null,
  apiCost: null,
  coverageTotal: null,
  coverageBreakdown: null,
  warnings: null,
})

// SSE state (fetch+ReadableStream — no token in URL)
let sseAbortController: AbortController | null = null
let reconnectAttempts = 0
const MAX_RECONNECT = 3
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

// Event queue (60ms drain for visual staggering)
const _eventQueue: RawSSEData[] = []
let _drainingQueue = false

// ─── Computed: Stepper States ─────────────────────────────────────────────────

const stepperStates = computed<StepCircleState[]>(() => {
  return PIPELINE_V2_STAGES.map((s) => {
    const status = v2StageStatuses.value.get(s.stage) ?? 'pending'
    switch (status) {
      case 'completed': return 'done'
      case 'running': return 'active'
      case 'failed': return 'error'
      case 'service_failure':
      case 'checkpoint': return 'warning'
      default: return 'pending'
    }
  })
})

const completedStageTimes = computed<Record<number, number>>(() => {
  const result: Record<number, number> = {}
  for (const [stage, elapsed] of stageElapsedTimes.value) {
    result[stage] = elapsed
  }
  return result
})

const activeStageNumber = computed(() => {
  for (const s of PIPELINE_V2_STAGES) {
    if (v2StageStatuses.value.get(s.stage) === 'running') return s.stage
  }
  return 1
})

const activeStageInfo = computed(() => {
  return PIPELINE_V2_STAGES.find((s) => s.stage === activeStageNumber.value)
})

const subStepPill = computed(() => {
  if (!v2SubStepRaw.value) return undefined
  // Extract sub-step like "3.3" from raw SSE sub_step "3.3 Image Extraction"
  const match = v2SubStepRaw.value.match(/^(\d+\.\d+)/)
  if (match) {
    const current = match[1]
    const stageNum = parseInt(current.split('.')[0])
    const lastKey = Object.keys(SUB_STEP_LABELS)
      .filter((k) => k.startsWith(`${stageNum}.`))
      .sort((a, b) => parseFloat(a) - parseFloat(b))
      .at(-1)
    return lastKey ? `Sub-etapa ${current} de ${lastKey}` : `Sub-etapa ${current}`
  }
  return undefined
})

const estimatedTimeLabel = computed(() => {
  if (stageElapsedTimes.value.size < 1) return '⏱ Calculando...'
  // Rough estimation: average completed stage time * remaining
  const completed = stageElapsedTimes.value.size
  const remaining = TOTAL_V2_STAGES - completed - 1 // -1 for current running
  if (remaining <= 0) return '⏱ Finalizando...'
  let total = 0
  for (const [, t] of stageElapsedTimes.value) total += t
  const avg = total / completed
  const estSecs = Math.round(avg * remaining)
  if (estSecs < 60) return `⏱ ~${estSecs}s restantes`
  const mins = Math.floor(estSecs / 60)
  const secs = estSecs % 60
  return `⏱ ~${mins}m ${secs}s restantes`
})

const activeMetrics = computed<MetricItem[]>(() => {
  const summary = stageSummaries.value.get(activeStageNumber.value)
  if (!summary) return []
  const result: MetricItem[] = []
  for (const [key, val] of Object.entries(summary)) {
    if (typeof val === 'number') {
      result.push({ value: val, label: translateMetric(key) })
    }
  }
  return result.slice(0, 5)
})

// ─── Computed: Completed Stages ───────────────────────────────────────────────

const completedStages = computed<CompletedStageSummary[]>(() => {
  const result: CompletedStageSummary[] = []
  for (const s of PIPELINE_V2_STAGES) {
    if (v2StageStatuses.value.get(s.stage) === 'completed') {
      const summary = stageSummaries.value.get(s.stage)
      const details: string[] = []
      if (summary) {
        for (const [key, val] of Object.entries(summary)) {
          details.push(`${val} ${translateMetric(key)}`)
        }
      }
      result.push({
        stage: s.stage,
        name: s.name,
        shortSummary: details.slice(0, 3).join(' · ') || 'Concluído',
        elapsedSeconds: stageElapsedTimes.value.get(s.stage) ?? 0,
        details: details.length > 0 ? details : ['Concluído com sucesso'],
      })
    }
  }
  return result
})

const pendingStages = computed(() => {
  return PIPELINE_V2_STAGES.filter((s) => {
    const status = v2StageStatuses.value.get(s.stage)
    return !status || status === 'pending'
  })
})

// ─── Computed: Completed Summary ──────────────────────────────────────────────

const completedSummary = computed<CompletedSummaryData>(() => {
  const totalTime = pipelineStartTime.value > 0
    ? Math.round((Date.now() - pipelineStartTime.value) / 1000)
    : 0
  return {
    totalTimeSeconds: totalTime,
    layoutCount: summaryData.value.layoutsDetected ?? 0,
    pageCount: summaryData.value.pageCount ?? 0,
    fieldsMapped: summaryData.value.fieldsMapped ?? undefined,
    apiCostEstimate: summaryData.value.apiCost ?? undefined,
    coverageTotal: summaryData.value.coverageTotal ?? undefined,
    coverageBreakdown: summaryData.value.coverageBreakdown ?? undefined,
    warnings: summaryData.value.warnings ?? undefined,
  }
})

// ─── Translation Helpers ──────────────────────────────────────────────────────

function translateSubStep(raw: string): string {
  const match = raw.match(/^(\d+\.\d+)/)
  if (!match) return raw
  const key = match[1]
  const label = SUB_STEP_LABELS[key]
  if (!label) {
    if (import.meta.env.DEV) console.warn(`[AnalyzingPage] SUB_STEP_LABELS missing key: "${key}"`)
    return raw
  }
  return label
}

function translateMetric(key: string): string {
  const label = METRIC_LABELS[key]
  if (!label) {
    if (import.meta.env.DEV) console.warn(`[AnalyzingPage] METRIC_LABELS missing key: "${key}"`)
    return key.replace(/_/g, ' ')
  }
  return label
}

// ─── SSE Event Processing ─────────────────────────────────────────────────────

async function _applyEvent(data: RawSSEData): Promise<boolean> {
  if (data.stage !== undefined) {
    const stageNum = data.stage

    // Handle checkpoint (service_failure with checkpoint data)
    if (data.status === 'service_failure' && data.checkpoint) {
      v2StageStatuses.value.set(stageNum, 'checkpoint')
      const cp = data.checkpoint
      checkpointData.value = {
        stage: stageNum,
        stageName: PIPELINE_V2_STAGES.find((s) => s.stage === stageNum)?.name ?? `Estágio ${stageNum}`,
        message: cp.message ?? cp.error ?? 'Ação necessária',
        confidence: cp.confidence,
        layouts: cp.layouts?.map((l) => ({
          id: l.id,
          label: l.label,
          pageCount: l.page_count,
          similar: l.similar,
        })),
        suggestion: cp.suggestion ? {
          text: cp.suggestion.text,
          resultLayouts: cp.suggestion.result_layouts,
          resultConfidence: cp.suggestion.result_confidence,
        } : undefined,
        timeoutSeconds: cp.timeout_seconds ?? 300,
        timeoutAction: (cp.timeout_action as 'confirm' | 'fallback' | 'skip') ?? 'fallback',
      }
      pageState.value = 'checkpoint'
      return false
    }

    // Handle error/failure
    if (data.status === 'failed' || (data.status === 'service_failure' && !data.checkpoint)) {
      v2StageStatuses.value.set(stageNum, 'failed')
      const startT = stageStartTimes.value.get(stageNum)
      if (startT) {
        stageElapsedTimes.value.set(stageNum, Math.round((Date.now() - startT) / 1000))
      }
      errorData.value = {
        stage: stageNum,
        stageName: PIPELINE_V2_STAGES.find((s) => s.stage === stageNum)?.name ?? `Estágio ${stageNum}`,
        service: (data.checkpoint?.service || data.summary?.service as string) ?? '',
        errorMessage: (data.checkpoint?.error || data.summary?.error as string) ?? 'Erro desconhecido no pipeline.',
        retriesAttempted: (data.summary?.retries as number) ?? 1,
      }
      pageState.value = 'error'
      return false
    }

    // Running
    if (data.status === 'running') {
      v2StageStatuses.value.set(stageNum, 'running')
      if (!stageStartTimes.value.has(stageNum)) {
        stageStartTimes.value.set(stageNum, Date.now())
      }
      if (pageState.value === 'initializing' || pageState.value === 'checkpoint') {
        pageState.value = 'processing'
      }
    }

    // Completed
    if (data.status === 'completed') {
      v2StageStatuses.value.set(stageNum, 'completed')
      const startT = stageStartTimes.value.get(stageNum)
      if (startT) {
        stageElapsedTimes.value.set(stageNum, Math.round((Date.now() - startT) / 1000))
      }
    }

    // Cancelled
    if (data.status === 'cancelled') {
      v2StageStatuses.value.set(stageNum, 'pending')
    }

    // Update sub-progress
    if (data.sub_step) {
      v2SubStepRaw.value = data.sub_step
      v2SubStep.value = translateSubStep(data.sub_step)
    }
    if (data.sub_progress_pct !== undefined) v2SubProgressPct.value = data.sub_progress_pct
    if (data.progress_pct !== undefined) v2ProgressPct.value = data.progress_pct

    // Stage-level summary
    if (data.summary) {
      const current = stageSummaries.value.get(stageNum) ?? {}
      stageSummaries.value.set(stageNum, { ...current, ...data.summary })
    }
  }

  // Update global summary
  if (data.summary) {
    const s = data.summary
    if (s.pdf_count !== undefined) summaryData.value.pdfCount = s.pdf_count as number
    if (s.page_count !== undefined) summaryData.value.pageCount = s.page_count as number
    else if (s.pages_processed !== undefined) summaryData.value.pageCount = s.pages_processed as number
    if (s.layouts_detected !== undefined) summaryData.value.layoutsDetected = s.layouts_detected as number
    if (s.fields_mapped !== undefined) summaryData.value.fieldsMapped = s.fields_mapped as number
    if (s.api_cost !== undefined) summaryData.value.apiCost = s.api_cost as number
    if (s.coverage !== undefined) {
      const cov = s.coverage as Record<string, unknown>
      if (cov.total !== undefined) summaryData.value.coverageTotal = cov.total as number
      if (Array.isArray(cov.breakdown)) summaryData.value.coverageBreakdown = cov.breakdown as Array<{ label: string; pct: number }>
    }
    if (Array.isArray(s.warnings)) summaryData.value.warnings = s.warnings as string[]
  }

  reconnectAttempts = 0

  // Detect completion
  const isComplete =
    data.event === 'pipeline_completed' ||
    (data.stage === TOTAL_V2_STAGES && data.status === 'completed')

  if (isComplete) {
    for (const s of PIPELINE_V2_STAGES) {
      if (v2StageStatuses.value.get(s.stage) === 'running') {
        v2StageStatuses.value.set(s.stage, 'completed')
      }
    }
    pageState.value = 'completed'
    closeSSE()
    return true
  }

  return false
}

async function _drainEventQueue(): Promise<void> {
  if (_drainingQueue) return
  _drainingQueue = true

  while (_eventQueue.length > 0) {
    const data = _eventQueue.shift()!
    const done = await _applyEvent(data)
    if (done) break

    if (_eventQueue.length > 0) {
      await new Promise<void>((resolve) => setTimeout(resolve, 60))
    }
  }

  _drainingQueue = false
}

async function connectSSE(jobId: string) {
  // Abort any existing SSE connection
  if (sseAbortController) {
    sseAbortController.abort()
    sseAbortController = null
  }

  sseAbortController = new AbortController()
  const { signal } = sseAbortController
  const url = `${API_BASE}/api/analyze/${jobId}/progress`

  let response: Response
  try {
    response = await apiFetch(url, { signal })
    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`)
    }
  } catch (err) {
    if ((err as Error).name === 'AbortError') return
    _handleSSEError(jobId)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6)) as RawSSEData
            _eventQueue.push(data)
            _drainEventQueue()
          } catch {
            // ignore parse errors
          }
        }
      }
    }
  } catch (err) {
    if ((err as Error).name === 'AbortError') return

    if (_eventQueue.length > 0 || _drainingQueue) return
    if (pageState.value === 'error' || pageState.value === 'completed') return

    _handleSSEError(jobId)
  }
}

async function _handleSSEError(jobId: string) {
  if (reconnectAttempts === 0 && session.jobId) {
    try {
      const r = await apiFetch(`${API_BASE}/api/analyze/${session.jobId}/status`)
      const s = (await r.json()) as { exists: boolean }
      if (!s.exists) {
        sessionLost.value = true
        return
      }
    } catch {
      // proceed to reconnect
    }
  }

  if (reconnectAttempts < MAX_RECONNECT) {
    const backoffMs = Math.pow(2, reconnectAttempts) * 1000
    reconnectAttempts++
    reconnectTimer = setTimeout(() => {
      if (session.jobId) connectSSE(session.jobId)
    }, backoffMs)
  } else {
    connectionLost.value = true
  }
}

async function fetchAndLoadResult() {
  let resp: Response | undefined
  try {
    resp = await apiFetch(`${API_BASE}/api/analyze/${session.jobId}/result`)
    if (!resp.ok) {
      if (resp.status === 404) {
        sessionLost.value = true
        return
      }
      errorData.value = { stage: 0, stageName: 'Carregamento', service: '', errorMessage: `Erro ao buscar resultado: HTTP ${resp.status}`, retriesAttempted: 0 }
      pageState.value = 'error'
      return
    }
    const data = (await resp.json()) as { status: string; result: unknown; error?: string }
    if (data.status === 'failed') {
      errorData.value = { stage: 0, stageName: 'Pipeline', service: '', errorMessage: data.error ?? 'Pipeline falhou sem mensagem de erro.', retriesAttempted: 0 }
      pageState.value = 'error'
      return
    }
    if (data.result) {
      await session.loadFromPipelineResult(data.result as Parameters<typeof session.loadFromPipelineResult>[0])
      if (session.error) {
        errorData.value = { stage: 0, stageName: 'Carregamento', service: '', errorMessage: session.error, retriesAttempted: 0 }
        pageState.value = 'error'
        return
      }
    }
    router.push('/editor')
  } catch (e) {
    console.error('[AnalyzingPage] fetchAndLoadResult error:', e)
    errorData.value = { stage: 0, stageName: 'Carregamento', service: '', errorMessage: 'Erro ao carregar resultado da análise.', retriesAttempted: 0 }
    pageState.value = 'error'
  }
}

function closeSSE() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  sseAbortController?.abort()
  sseAbortController = null
}

// ─── Handlers ─────────────────────────────────────────────────────────────────

async function handleCancel() {
  if (isCancelling.value) return
  isCancelling.value = true
  closeSSE()
  try {
    if (session.jobId) {
      await apiFetch(`${API_BASE}/api/analyze/${session.jobId}/cancel`, { method: 'POST' })
    }
  } catch {
    // proceed regardless
  } finally {
    isCancelling.value = false
    router.push('/upload')
  }
}

async function startPipeline(jobId: string): Promise<void> {
  if (isStarting.value) return
  isStarting.value = true
  try {
    const response = await apiFetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId }),
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
  } finally {
    isStarting.value = false
  }
}

async function handleRetry() {
  v2StageStatuses.value.clear()
  v2SubStep.value = ''
  v2SubStepRaw.value = ''
  v2SubProgressPct.value = 0
  v2ProgressPct.value = 0
  stageStartTimes.value.clear()
  stageElapsedTimes.value.clear()
  stageSummaries.value.clear()
  checkpointData.value = null
  errorData.value = null
  pageState.value = 'initializing'
  summaryData.value = { pdfCount: null, pageCount: null, layoutsDetected: null, fieldsMapped: null, apiCost: null, coverageTotal: null, coverageBreakdown: null, warnings: null }
  _eventQueue.length = 0
  _drainingQueue = false

  if (session.jobId) {
    try {
      await startPipeline(session.jobId)
    } catch {
      errorData.value = { stage: 0, stageName: 'Inicialização', service: '', errorMessage: 'Erro ao iniciar pipeline de análise.', retriesAttempted: 0 }
      pageState.value = 'error'
      return
    }
    pipelineStartTime.value = Date.now()
    connectSSE(session.jobId)
  }
}

async function handleCheckpointAction(action: 'retry' | 'fallback' | 'abort') {
  if (!session.jobId) return
  isCheckpointSubmitting.value = true
  checkpointActionError.value = null
  try {
    const response = await apiFetch(`${API_BASE}/api/jobs/${session.jobId}/handle-failure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    // Reset to processing — SSE will send the next event
    checkpointData.value = null
    pageState.value = 'processing'
  } catch {
    // Non-blocking: show error inline, keep checkpoint state so operator can retry
    checkpointActionError.value = 'Erro ao enviar ação ao servidor. Tente novamente.'
  } finally {
    isCheckpointSubmitting.value = false
  }
}

async function handleErrorDecision(action: 'retry' | 'fallback' | 'abort') {
  if (!session.jobId) return
  if (action === 'abort') {
    handleCancel()
    return
  }
  try {
    await apiFetch(`${API_BASE}/api/jobs/${session.jobId}/handle-failure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    })
    // Reset to processing
    pageState.value = 'processing'
    errorData.value = null
  } catch {
    // Keep error state, user can try again
  }
}

async function handleOpenEditor() {
  await fetchAndLoadResult()
}

function handleBackToUpload() {
  closeSSE()
  router.push('/upload')
}

function handleReconnect() {
  connectionLost.value = false
  reconnectAttempts = 0
  if (session.jobId) connectSSE(session.jobId)
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  if (session.jobId) {
    pipelineStartTime.value = Date.now()
    try {
      await startPipeline(session.jobId)
    } catch {
      errorData.value = { stage: 0, stageName: 'Inicialização', service: '', errorMessage: 'Erro ao iniciar pipeline de análise.', retriesAttempted: 0 }
      pageState.value = 'error'
      return
    }
    connectSSE(session.jobId)
  }
})

onUnmounted(() => {
  closeSSE()
})
</script>

<style scoped>
.analyzing-page {
  padding: 2rem 0;
}

/* ─── Topbar breadcrumb ───────────────────────────────────────────────────── */
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

/* ─── Banners ─────────────────────────────────────────────────────────────── */
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

.banner--warning .banner__title { color: #b45309; }
.banner--orange .banner__title { color: #c2410c; }
.banner--error .banner__title { color: #dc2626; }

.banner__text {
  font-size: 13px;
  margin-bottom: 12px;
}

.banner--warning .banner__text { color: #92400e; }
.banner--orange .banner__text { color: #9a3412; }
.banner--error .banner__text { color: #b91c1c; }

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

.banner__btn--primary { background: #2563eb; color: #fff; }
.banner__btn--primary:hover { background: #1d4ed8; }
.banner__btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }

.banner__btn--secondary { background: #fff; color: #475569; border: 1px solid #e2e8f0; }
.banner__btn--secondary:hover { background: #f8fafc; }

.banner__btn--warning { background: #f59e0b; color: #fff; }
.banner__btn--warning:hover { background: #d97706; }

/* ─── V2 Sections ─────────────────────────────────────────────────────────── */
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

/* ─── Info Cards ──────────────────────────────────────────────────────────── */
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

/* ─── A11y Focus ──────────────────────────────────────────────────────────── */
*:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}
</style>
