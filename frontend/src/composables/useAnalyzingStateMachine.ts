/**
 * Story 40.6 — FE-001: State machine composable for AnalyzingPage.
 *
 * Extracts all state transitions, computed derivations, and pipeline actions
 * from AnalyzingPage.vue into a testable composable.
 * SSE connection logic is delegated to useAnalyzingSSE.
 */
import { ref, computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { apiFetch } from '@/services/apiFetch'
import { useAnalyzingSSE } from './useAnalyzingSSE'
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
} from '@/pages/analyzingPageConstantsV2'
import type { MetricItem } from '@/components/analyzing/AnalyzingDetailCard.vue'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

type V2Status = 'pending' | 'running' | 'completed' | 'failed' | 'service_failure' | 'checkpoint'

export interface PipelineWarning {
  code: string
  severity: 'info' | 'warning' | 'error'
  message: string
  stage?: number
}

export interface RawSSEData {
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

export interface SummaryData {
  pdfCount: number | null
  pageCount: number | null
  layoutsDetected: number | null
  fieldsMapped: number | null
  apiCost: number | null
  visionAiUsed: boolean | null
  coverageTotal: number | null
  coverageBreakdown: Array<{ label: string; pct: number }> | null
  warnings: string[] | null
}

// ─── Translation Helpers ────────────────────────────────────────────────────

export function translateSubStep(raw: string): string {
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

export function translateMetric(key: string): string {
  const label = METRIC_LABELS[key]
  if (!label) {
    if (import.meta.env.DEV) console.warn(`[AnalyzingPage] METRIC_LABELS missing key: "${key}"`)
    return key.replace(/_/g, ' ')
  }
  return label
}

// ─── Composable ─────────────────────────────────────────────────────────────

export function useAnalyzingStateMachine() {
  const session = useSessionStore()

  // ─── Reactive State ─────────────────────────────────────────────────────
  const pageState = ref<AnalyzingPageState>('initializing')
  const v2StageStatuses = ref<Map<number, V2Status>>(new Map())
  const v2SubStep = ref('')
  const v2SubStepRaw = ref('')
  const v2SubProgressPct = ref(0)
  const stageStartTimes = ref<Map<number, number>>(new Map())
  const stageElapsedTimes = ref<Map<number, number>>(new Map())
  const stageSummaries = ref<Map<number, Record<string, unknown>>>(new Map())
  const checkpointData = ref<CheckpointData | null>(null)
  const errorData = ref<ErrorData | null>(null)
  const pipelineStartTime = ref<number>(0)
  const pipelineWarnings = ref<PipelineWarning[]>([])
  const warningsDismissed = ref(false)
  const isCancelling = ref(false)
  const isCheckpointSubmitting = ref(false)
  const checkpointActionError = ref<string | null>(null)

  const summaryData = ref<SummaryData>({
    pdfCount: null,
    pageCount: null,
    layoutsDetected: null,
    fieldsMapped: null,
    apiCost: null,
    visionAiUsed: null,
    coverageTotal: null,
    coverageBreakdown: null,
    warnings: null,
  })

  // SSE event processor — defined before SSE so it can be passed as callback
  let reconnectAttempts = 0

  async function applyEvent(data: RawSSEData): Promise<boolean> {
    if (data.stage !== undefined) {
      const stageNum = data.stage

      if (data.status === 'service_failure' && data.checkpoint) {
        _applyCheckpoint(stageNum, data)
        return false
      }
      if (data.status === 'failed' || (data.status === 'service_failure' && !data.checkpoint)) {
        _applyStageFailure(stageNum, data)
        return false
      }
      if (data.status === 'running') {
        v2StageStatuses.value.set(stageNum, 'running')
        if (!stageStartTimes.value.has(stageNum)) stageStartTimes.value.set(stageNum, Date.now())
        if (pageState.value === 'initializing' || pageState.value === 'checkpoint') {
          pageState.value = 'processing'
        }
      }
      if (data.status === 'completed') {
        v2StageStatuses.value.set(stageNum, 'completed')
        const startT = stageStartTimes.value.get(stageNum)
        if (startT) stageElapsedTimes.value.set(stageNum, Math.round((Date.now() - startT) / 1000))
      }
      if (data.status === 'cancelled') v2StageStatuses.value.set(stageNum, 'pending')
      if (data.sub_step) {
        v2SubStepRaw.value = data.sub_step
        v2SubStep.value = translateSubStep(data.sub_step)
      }
      if (data.sub_progress_pct !== undefined) v2SubProgressPct.value = data.sub_progress_pct
      if (data.summary) {
        const current = stageSummaries.value.get(stageNum) ?? {}
        stageSummaries.value.set(stageNum, { ...current, ...data.summary })
      }
    }
    if (data.summary) _updateSummaryFromEvent(data.summary)
    reconnectAttempts = 0

    const isComplete =
      data.event === 'pipeline_completed' ||
      (data.stage === TOTAL_V2_STAGES && data.status === 'completed')
    if (isComplete) {
      for (const s of PIPELINE_V2_STAGES) {
        if (v2StageStatuses.value.get(s.stage) === 'running')
          v2StageStatuses.value.set(s.stage, 'completed')
      }
      pageState.value = 'completed'
      sse.closeSSE()
      return true
    }
    return false
  }

  // SSE composable
  const sse = useAnalyzingSSE(pageState, applyEvent)

  // ─── Computed ───────────────────────────────────────────────────────────
  const stepperStates = computed<StepCircleState[]>(() =>
    PIPELINE_V2_STAGES.map((s) => {
      const status = v2StageStatuses.value.get(s.stage) ?? 'pending'
      switch (status) {
        case 'completed':
          return 'done'
        case 'running':
          return 'active'
        case 'failed':
          return 'error'
        case 'service_failure':
        case 'checkpoint':
          return 'warning'
        default:
          return 'pending'
      }
    }),
  )

  const completedStageTimes = computed<Record<number, number>>(() => {
    const result: Record<number, number> = {}
    for (const [stage, elapsed] of stageElapsedTimes.value) result[stage] = elapsed
    return result
  })

  const activeStageNumber = computed(() => {
    for (const s of PIPELINE_V2_STAGES) {
      if (v2StageStatuses.value.get(s.stage) === 'running') return s.stage
    }
    return 1
  })

  const activeStageInfo = computed(() =>
    PIPELINE_V2_STAGES.find((s) => s.stage === activeStageNumber.value),
  )

  const subStepPill = computed(() => {
    if (!v2SubStepRaw.value) return undefined
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
    if (stageElapsedTimes.value.size < 1) return 'Calculando...'
    const completed = stageElapsedTimes.value.size
    const remaining = TOTAL_V2_STAGES - completed - 1
    if (remaining <= 0) return 'Finalizando...'
    let total = 0
    for (const [, t] of stageElapsedTimes.value) total += t
    const avg = total / completed
    const estSecs = Math.round(avg * remaining)
    if (estSecs < 60) return `~${estSecs}s restantes`
    const mins = Math.floor(estSecs / 60)
    const secs = estSecs % 60
    return `~${mins}m ${secs}s restantes`
  })

  const activeMetrics = computed<MetricItem[]>(() => {
    const summary = stageSummaries.value.get(activeStageNumber.value)
    if (!summary) return []
    const result: MetricItem[] = []
    for (const [key, val] of Object.entries(summary)) {
      if (typeof val === 'number') result.push({ value: val, label: translateMetric(key) })
    }
    return result.slice(0, 5)
  })

  const completedStages = computed<CompletedStageSummary[]>(() => {
    const result: CompletedStageSummary[] = []
    for (const s of PIPELINE_V2_STAGES) {
      if (v2StageStatuses.value.get(s.stage) !== 'completed') continue
      const summary = stageSummaries.value.get(s.stage)
      const details: string[] = []
      if (summary) {
        for (const [key, val] of Object.entries(summary))
          details.push(`${val} ${translateMetric(key)}`)
      }
      result.push({
        stage: s.stage,
        name: s.name,
        shortSummary: details.slice(0, 3).join(' . ') || 'Concluido',
        elapsedSeconds: stageElapsedTimes.value.get(s.stage) ?? 0,
        details: details.length > 0 ? details : ['Concluido com sucesso'],
      })
    }
    return result
  })

  const pendingStages = computed(() =>
    PIPELINE_V2_STAGES.filter((s) => {
      const status = v2StageStatuses.value.get(s.stage)
      return !status || status === 'pending'
    }),
  )

  const completedSummary = computed<CompletedSummaryData>(() => ({
    totalTimeSeconds:
      pipelineStartTime.value > 0 ? Math.round((Date.now() - pipelineStartTime.value) / 1000) : 0,
    layoutCount: summaryData.value.layoutsDetected ?? 0,
    pageCount: summaryData.value.pageCount ?? 0,
    fieldsMapped: summaryData.value.fieldsMapped ?? undefined,
    apiCostEstimate: summaryData.value.apiCost ?? undefined,
    visionAiUsed: summaryData.value.visionAiUsed ?? undefined,
    coverageTotal: summaryData.value.coverageTotal ?? undefined,
    coverageBreakdown: summaryData.value.coverageBreakdown ?? undefined,
    warnings: summaryData.value.warnings ?? undefined,
  }))

  // ─── Internal Helpers ─────────────────────────────────────────────────

  function _applyCheckpoint(stageNum: number, data: RawSSEData): void {
    v2StageStatuses.value.set(stageNum, 'checkpoint')
    const cp = data.checkpoint!
    checkpointData.value = {
      stage: stageNum,
      stageName:
        PIPELINE_V2_STAGES.find((s) => s.stage === stageNum)?.name ?? `Estagio ${stageNum}`,
      message: cp.message ?? cp.error ?? 'Acao necessaria',
      confidence: cp.confidence,
      layouts: cp.layouts?.map((l) => ({
        id: l.id,
        label: l.label,
        pageCount: l.page_count,
        similar: l.similar,
      })),
      suggestion: cp.suggestion
        ? {
            text: cp.suggestion.text,
            resultLayouts: cp.suggestion.result_layouts,
            resultConfidence: cp.suggestion.result_confidence,
          }
        : undefined,
      timeoutSeconds: cp.timeout_seconds ?? 300,
      timeoutAction: (cp.timeout_action as 'confirm' | 'fallback' | 'skip') ?? 'fallback',
    }
    pageState.value = 'checkpoint'
  }

  function _applyStageFailure(stageNum: number, data: RawSSEData): void {
    v2StageStatuses.value.set(stageNum, 'failed')
    const startT = stageStartTimes.value.get(stageNum)
    if (startT) stageElapsedTimes.value.set(stageNum, Math.round((Date.now() - startT) / 1000))
    errorData.value = {
      stage: stageNum,
      stageName:
        PIPELINE_V2_STAGES.find((s) => s.stage === stageNum)?.name ?? `Estagio ${stageNum}`,
      service: (data.checkpoint?.service || (data.summary?.service as string)) ?? '',
      errorMessage:
        (data.checkpoint?.error || (data.summary?.error as string)) ?? 'Erro desconhecido.',
      retriesAttempted: (data.summary?.retries as number) ?? 1,
    }
    pageState.value = 'error'
  }

  function _updateSummaryFromEvent(s: Record<string, unknown>): void {
    if (s.pdf_count !== undefined) summaryData.value.pdfCount = s.pdf_count as number
    if (s.page_count !== undefined) summaryData.value.pageCount = s.page_count as number
    else if (s.pages_processed !== undefined)
      summaryData.value.pageCount = s.pages_processed as number
    if (s.layouts_detected !== undefined)
      summaryData.value.layoutsDetected = s.layouts_detected as number
    if (s.fields_mapped !== undefined) summaryData.value.fieldsMapped = s.fields_mapped as number
    if (s.api_cost !== undefined) summaryData.value.apiCost = s.api_cost as number
    if (s.vision_ai_used !== undefined) summaryData.value.visionAiUsed = s.vision_ai_used as boolean
    if (s.coverage !== undefined) {
      const cov = s.coverage as Record<string, unknown>
      if (cov.total !== undefined) summaryData.value.coverageTotal = cov.total as number
      if (Array.isArray(cov.breakdown))
        summaryData.value.coverageBreakdown = cov.breakdown as Array<{ label: string; pct: number }>
    }
    if (Array.isArray(s.warnings) && s.warnings.length > 0) {
      summaryData.value.warnings = s.warnings as string[]
      const structured = (s.warnings as unknown[]).filter(
        (w): w is PipelineWarning =>
          typeof w === 'object' && w !== null && 'code' in w && 'severity' in w && 'message' in w,
      )
      if (structured.length > 0) {
        pipelineWarnings.value = structured
        warningsDismissed.value = false
      }
    }
  }

  // ─── Pipeline Actions ─────────────────────────────────────────────────

  async function startPipeline(jobId: string): Promise<void> {
    const response = await apiFetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
  }

  async function fetchAndLoadResult() {
    try {
      const resp = await apiFetch(`${API_BASE}/api/analyze/${session.jobId}/result`)
      if (!resp.ok) {
        if (resp.status === 404) {
          sse.sessionLost.value = true
          return
        }
        errorData.value = {
          stage: 0,
          stageName: 'Carregamento',
          service: '',
          errorMessage: `Erro ao buscar resultado: HTTP ${resp.status}`,
          retriesAttempted: 0,
        }
        pageState.value = 'error'
        return
      }
      const data = (await resp.json()) as { status: string; result: unknown; error?: string }
      if (data.status === 'failed') {
        errorData.value = {
          stage: 0,
          stageName: 'Pipeline',
          service: '',
          errorMessage: data.error ?? 'Pipeline falhou sem mensagem de erro.',
          retriesAttempted: 0,
        }
        pageState.value = 'error'
        return
      }
      if (data.result) {
        await session.loadFromPipelineResult(
          data.result as Parameters<typeof session.loadFromPipelineResult>[0],
        )
        if (session.error) {
          errorData.value = {
            stage: 0,
            stageName: 'Carregamento',
            service: '',
            errorMessage: session.error,
            retriesAttempted: 0,
          }
          pageState.value = 'error'
          return
        }
      }
      return true
    } catch (e) {
      console.error('[AnalyzingPage] fetchAndLoadResult error:', e)
      errorData.value = {
        stage: 0,
        stageName: 'Carregamento',
        service: '',
        errorMessage: 'Erro ao carregar resultado da analise.',
        retriesAttempted: 0,
      }
      pageState.value = 'error'
    }
  }

  function resetState() {
    v2StageStatuses.value.clear()
    v2SubStep.value = ''
    v2SubStepRaw.value = ''
    v2SubProgressPct.value = 0
    stageStartTimes.value.clear()
    stageElapsedTimes.value.clear()
    stageSummaries.value.clear()
    checkpointData.value = null
    errorData.value = null
    pageState.value = 'initializing'
    summaryData.value = {
      pdfCount: null,
      pageCount: null,
      layoutsDetected: null,
      fieldsMapped: null,
      apiCost: null,
      visionAiUsed: null,
      coverageTotal: null,
      coverageBreakdown: null,
      warnings: null,
    }
    pipelineWarnings.value = []
    warningsDismissed.value = false
    sse.resetSSE()
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
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      checkpointData.value = null
      pageState.value = 'processing'
    } catch {
      checkpointActionError.value = 'Erro ao enviar acao ao servidor. Tente novamente.'
    } finally {
      isCheckpointSubmitting.value = false
    }
  }

  async function handleErrorDecision(action: 'retry' | 'fallback' | 'abort') {
    if (!session.jobId) return
    if (action === 'abort') return
    if (errorData.value?.stage === 0) {
      if (action === 'retry' || action === 'fallback') {
        errorData.value = null
        pageState.value = 'completed'
        await fetchAndLoadResult()
      }
      return
    }
    try {
      await apiFetch(`${API_BASE}/api/jobs/${session.jobId}/handle-failure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      pageState.value = 'processing'
      errorData.value = null
    } catch {
      /* Keep error state */
    }
  }

  return {
    // State
    pageState,
    v2SubStep,
    v2SubProgressPct,
    checkpointData,
    errorData,
    pipelineStartTime,
    pipelineWarnings,
    warningsDismissed,
    isCancelling,
    isCheckpointSubmitting,
    checkpointActionError,
    connectionLost: sse.connectionLost,
    sessionLost: sse.sessionLost,
    summaryData,
    // Computed
    stepperStates,
    completedStageTimes,
    activeStageNumber,
    activeStageInfo,
    subStepPill,
    estimatedTimeLabel,
    activeMetrics,
    completedStages,
    pendingStages,
    completedSummary,
    // Actions
    connectSSE: sse.connectSSE,
    closeSSE: sse.closeSSE,
    startPipeline,
    fetchAndLoadResult,
    resetState,
    handleCheckpointAction,
    handleErrorDecision,
    handleReconnect: sse.handleReconnect,
    // Testing
    applyEvent,
  }
}
