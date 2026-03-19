<template>
  <FullWidthLayout>
    <div class="analyzing-page">
      <!-- Título -->
      <h1 class="text-2xl font-bold text-center mb-8 text-gray-800">
        Analisando documentos...
      </h1>

      <!-- Erro -->
      <div v-if="hasError" class="max-w-2xl mx-auto mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
        <p class="text-red-700 font-semibold mb-1">Erro na análise</p>
        <p class="text-red-600 text-sm mb-4">{{ errorMessage }}</p>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            @click="handleRetry"
          >
            Tentar novamente
          </button>
          <button
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
            @click="handleBackToUpload"
          >
            ← Voltar ao Upload
          </button>
        </div>
      </div>

      <!-- Conexão perdida -->
      <div v-if="connectionLost" class="max-w-2xl mx-auto mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p class="text-yellow-700 font-semibold mb-1">Conexão perdida</p>
        <p class="text-yellow-600 text-sm mb-3">Não foi possível reconectar após 3 tentativas.</p>
        <button
          class="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors text-sm font-medium"
          @click="handleReconnect"
        >
          Reconectar
        </button>
      </div>

      <!-- Sessão perdida (backend reiniciou) -->
      <div v-if="sessionLost" class="max-w-2xl mx-auto mb-6 bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-orange-700 font-semibold mb-1">Sessão de análise perdida</p>
        <p class="text-orange-600 text-sm mb-4">O servidor pode ter sido reiniciado. Faça o upload novamente para reiniciar a análise.</p>
        <button
          class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
          @click="handleBackToUpload"
        >
          ← Voltar ao Upload
        </button>
      </div>

      <!-- Lista de blocos -->
      <div class="space-y-3 max-w-2xl mx-auto">
        <div
          v-for="block in PIPELINE_BLOCKS"
          :key="block.id"
          class="bg-white rounded-lg p-4 shadow-sm border border-gray-100"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="text-lg" :class="getBlockIconClass(block)">
              {{ getBlockIcon(block) }}
            </span>
            <span class="font-semibold text-gray-800 text-sm">
              {{ block.id }}. {{ block.name }}
            </span>
          </div>
          <div class="flex flex-wrap gap-2 ml-7">
            <div
              v-for="(stage, idx) in block.stages"
              :key="idx"
              class="flex items-center gap-1 text-xs px-2 py-1 rounded-full"
              :class="getStageClass(getStageIndex(block, idx))"
            >
              <span v-if="getStageStatus(getStageIndex(block, idx)) === 'running'" class="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span v-else-if="getStageStatus(getStageIndex(block, idx)) === 'completed'">✓</span>
              <span v-else-if="getStageStatus(getStageIndex(block, idx)) === 'failed'">✗</span>
              <span v-else class="inline-block w-2 h-2 rounded-full border border-gray-400" />
              <span>{{ stage }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Barra de progresso -->
      <div class="max-w-2xl mx-auto mt-6">
        <div class="flex justify-between items-center mb-2">
          <span class="text-sm font-medium text-gray-700">Progresso</span>
          <span class="text-sm font-semibold text-blue-600">{{ Math.round(progressPct) }}%</span>
        </div>
        <ProgressBar :value="progressPct" :animated="hasRunningStages" />
      </div>

      <!-- Resumo parcial -->
      <div class="max-w-2xl mx-auto mt-5 bg-white rounded-lg p-4 shadow-sm border border-gray-100">
        <p class="text-sm font-semibold text-gray-700 mb-2">Resumo parcial</p>
        <div class="flex flex-wrap gap-6 text-sm text-gray-600">
          <span>PDFs: <span class="font-semibold text-gray-800">{{ summary.pdfCount !== null ? `${summary.pdfCount} documentos` : '—' }}</span></span>
          <span>Páginas: <span class="font-semibold text-gray-800">{{ summary.pageCount !== null ? summary.pageCount : '—' }}</span></span>
          <span>Layouts detectados: <span class="font-semibold text-gray-800">{{ summary.layoutsDetected !== null ? summary.layoutsDetected : '—' }}</span></span>
        </div>
      </div>

      <!-- Tempo estimado -->
      <div class="max-w-2xl mx-auto mt-3 text-center">
        <span class="text-sm text-gray-500">{{ estimatedTime }}</span>
      </div>

      <!-- Botão cancelar -->
      <div class="max-w-2xl mx-auto mt-8 flex justify-center">
        <button
          :disabled="isCancelling"
          class="px-6 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          @click="handleCancel"
        >
          {{ isCancelling ? 'Cancelando...' : '← Cancelar' }}
        </button>
      </div>
    </div>
  </FullWidthLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import FullWidthLayout from '@/templates/FullWidthLayout.vue'
import ProgressBar from '@/atoms/ProgressBar.vue'
import { useSessionStore } from '@/stores/session'
import { PIPELINE_BLOCKS, TOTAL_STAGES, getStageIndex } from './analyzingPageConstants'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ─── Types ────────────────────────────────────────────────────────────────────

type StageStatus = 'pending' | 'running' | 'completed' | 'failed'

interface SummaryData {
  pdfCount: number | null
  pageCount: number | null
  layoutsDetected: number | null
}

// ─── State ────────────────────────────────────────────────────────────────────

const router = useRouter()
const session = useSessionStore()

// stagesStatus: 0-indexed map of stage index → status
const stagesStatus = ref<Map<number, StageStatus>>(new Map())
const hasError = ref(false)
const errorMessage = ref('')
const isCancelling = ref(false)
const connectionLost = ref(false)
const sessionLost = ref(false)

const summary = ref<SummaryData>({
  pdfCount: null,
  pageCount: null,
  layoutsDetected: null,
})

// Timing for estimation
const stageStartTimes = ref<Map<number, number>>(new Map())
const stageCompleteTimes = ref<number[]>([])

// SSE reconnect state
let eventSource: EventSource | null = null
let reconnectAttempts = 0
const MAX_RECONNECT = 3
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

// Pipeline failure tracking (Bug 3)
const pipelineFailed = ref(false)
const pipelineFailedStage = ref('')

// ─── Computed ─────────────────────────────────────────────────────────────────

function getStageStatus(stageIdx: number): StageStatus {
  return stagesStatus.value.get(stageIdx) ?? 'pending'
}

function getStageClass(stageIdx: number): string {
  const status = getStageStatus(stageIdx)
  switch (status) {
    case 'completed': return 'bg-green-100 text-green-700'
    case 'running':   return 'bg-blue-100 text-blue-700'
    case 'failed':    return 'bg-red-100 text-red-700'
    default:          return 'bg-gray-100 text-gray-500'
  }
}

type PipelineBlock = typeof PIPELINE_BLOCKS[number]

function getBlockStatus(block: PipelineBlock): StageStatus {
  const statuses = block.stages.map((_, idx) => getStageStatus(getStageIndex(block, idx)))
  if (statuses.every(s => s === 'completed')) return 'completed'
  if (statuses.some(s => s === 'failed')) return 'failed'
  if (statuses.some(s => s === 'running')) return 'running'
  return 'pending'
}

function getBlockIcon(block: PipelineBlock): string {
  const status = getBlockStatus(block)
  switch (status) {
    case 'completed': return '✓'
    case 'running':   return '⟳'
    case 'failed':    return '✗'
    default:          return '○'
  }
}

function getBlockIconClass(block: PipelineBlock): string {
  const status = getBlockStatus(block)
  switch (status) {
    case 'completed': return 'text-green-600'
    case 'running':   return 'text-blue-600'
    case 'failed':    return 'text-red-500'
    default:          return 'text-gray-400'
  }
}

const completedCount = computed(() => {
  let count = 0
  for (const [, status] of stagesStatus.value) {
    if (status === 'completed') count++
  }
  return count
})

const progressPct = computed(() => {
  return (completedCount.value / TOTAL_STAGES) * 100
})

const hasRunningStages = computed(() => {
  for (const [, status] of stagesStatus.value) {
    if (status === 'running') return true
  }
  return false
})

const estimatedTime = computed(() => {
  const completed = completedCount.value
  const remaining = TOTAL_STAGES - completed

  if (remaining === 0) return 'Concluído!'

  // Check if we're on the last block
  const lastBlock = PIPELINE_BLOCKS[PIPELINE_BLOCKS.length - 1]
  const lastBlockFirstIdx = TOTAL_STAGES - (lastBlock?.stages.length ?? 3)
  if (completed >= lastBlockFirstIdx) return 'Finalizando...'

  if (stageCompleteTimes.value.length < 2) return 'Calculando...'

  // Average time per stage based on completed stages
  const avgMs = stageCompleteTimes.value.reduce((a, b) => a + b, 0) / stageCompleteTimes.value.length
  const totalRemainingMs = avgMs * remaining
  const secs = Math.round(totalRemainingMs / 1000)
  const mins = Math.floor(secs / 60)
  const secsRemainder = secs % 60

  if (mins > 0) return `~${mins}m ${secsRemainder}s restantes`
  return `~${secsRemainder}s restantes`
})

// ─── SSE Logic ────────────────────────────────────────────────────────────────

function connectSSE(jobId: string) {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }

  const url = `${API_BASE}/api/analyze/${jobId}/progress`
  eventSource = new EventSource(url)

  eventSource.addEventListener('message', async (ev: Event) => {
    try {
      const data = JSON.parse((ev as MessageEvent).data) as {
        event?: string
        step?: string
        pct?: number
        block?: number
        stage?: number
        stage_name?: string
        status?: 'running' | 'completed' | 'failed'
        summary?: {
          pdf_count?: number
          page_count?: number
          layouts_detected?: number
        }
      }

      // Update stage status if block+stage present (1-indexed from backend)
      if (data.block !== undefined && data.stage !== undefined) {
        const blockObj = PIPELINE_BLOCKS[data.block - 1]
        if (blockObj) {
          // data.stage is the global 1-indexed stage number
          const flatIdx = data.stage - 1
          if (data.status === 'running') {
            stagesStatus.value.set(flatIdx, 'running')
            stageStartTimes.value.set(flatIdx, Date.now())
          } else if (data.status === 'completed') {
            stagesStatus.value.set(flatIdx, 'completed')
            const startTime = stageStartTimes.value.get(flatIdx)
            if (startTime) {
              stageCompleteTimes.value.push(Date.now() - startTime)
            }
          } else if (data.status === 'failed') {
            // Bug 3: track pipeline failure stage
            stagesStatus.value.set(flatIdx, 'failed')
            pipelineFailed.value = true
            pipelineFailedStage.value = data.stage_name ?? `Stage ${data.stage}`
          }
        }
      }

      // Update summary
      if (data.summary) {
        if (data.summary.pdf_count !== undefined) summary.value.pdfCount = data.summary.pdf_count
        if (data.summary.page_count !== undefined) summary.value.pageCount = data.summary.page_count
        if (data.summary.layouts_detected !== undefined) summary.value.layoutsDetected = data.summary.layouts_detected
      }

      // Reset reconnect counter on successful message
      reconnectAttempts = 0

      // Detect pipeline completion — via explicit event (Bug 6) OR via TOTAL_STAGES (fallback)
      const isPipelineCompleted =
        data.event === 'pipeline_completed' ||
        (data.stage === TOTAL_STAGES && data.status === 'completed')

      if (isPipelineCompleted) {
        // Mark any remaining running stages as completed
        for (const [idx, st] of stagesStatus.value) {
          if (st === 'running') stagesStatus.value.set(idx, 'completed')
        }
        eventSource?.close()
        eventSource = null
        await fetchAndLoadResult()
      }
    } catch {
      // ignore parse errors
    }
  })

  // Bug 3: onerror distinguishes pipeline failure from network failure
  // - pipelineFailed === true → pipeline emitted a 'failed' stage event, don't reconnect
  // - pipelineFailed === false + first attempt → check if job still exists (Bug 4/10.5)
  // - pipelineFailed === false + network drop → attempt reconnect with backoff
  eventSource.onerror = () => {
    eventSource?.close()
    eventSource = null

    if (pipelineFailed.value) {
      // Pipeline failed — show stage-specific error, do not reconnect
      showError(`Pipeline falhou na ${pipelineFailedStage.value}. Verifique os logs do servidor.`)
      return
    }

    // Bug 4 (10.5): On first error, verify the job still exists before reconnecting.
    // EventSource does not expose HTTP status codes — we probe /status to distinguish
    // "job not found (server restarted)" from "transient network error".
    if (reconnectAttempts === 0 && session.jobId) {
      fetch(`${API_BASE}/api/analyze/${session.jobId}/status`)
        .then(r => r.json())
        .then((s: { exists: boolean }) => {
          if (!s.exists) {
            sessionLost.value = true
            return
          }
          // Job exists, reconnect normally
          reconnectAttempts++
          reconnectTimer = setTimeout(() => {
            if (session.jobId) connectSSE(session.jobId)
          }, 1000)
        })
        .catch(() => {
          // No server access — try reconnecting anyway
          reconnectAttempts++
          reconnectTimer = setTimeout(() => {
            if (session.jobId) connectSSE(session.jobId)
          }, 1000)
        })
      return
    }

    if (reconnectAttempts < MAX_RECONNECT) {
      const backoffMs = Math.pow(2, reconnectAttempts) * 1000 // 1s, 2s, 4s
      reconnectAttempts++
      reconnectTimer = setTimeout(() => {
        if (session.jobId) connectSSE(session.jobId)
      }, backoffMs)
    } else {
      connectionLost.value = true
    }
  }
}

async function fetchAndLoadResult() {
  let resp: Response | undefined
  try {
    resp = await fetch(`${API_BASE}/api/analyze/${session.jobId}/result`)
    if (!resp.ok) {
      if (resp.status === 404) {
        sessionLost.value = true
        return
      }
      showError(`Erro ao buscar resultado: Erro HTTP ${resp.status}`)
      return
    }
    const data = await resp.json() as { status: string; result: unknown; error?: string }
    if (data.status === 'failed') {
      showError(data.error ?? 'Pipeline falhou sem mensagem de erro.')
      return
    }
    if (data.result) {
      await session.loadFromPipelineResult(data.result as Parameters<typeof session.loadFromPipelineResult>[0])
    }
    router.push('/editor')
  } catch (e) {
    console.error('[AnalyzingPage] fetchAndLoadResult error:', e)
    if (resp && !resp.ok) {
      showError(`Erro ao carregar resultado da análise: Erro HTTP ${resp.status}`)
    } else {
      showError('Erro ao carregar resultado da análise.')
    }
  }
}

function showError(msg: string) {
  hasError.value = true
  errorMessage.value = msg
}

function closeSSE() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  eventSource?.close()
  eventSource = null
}

// ─── Handlers ─────────────────────────────────────────────────────────────────

async function handleCancel() {
  if (isCancelling.value) return
  isCancelling.value = true
  closeSSE()

  try {
    if (session.jobId) {
      await fetch(`${API_BASE}/api/analyze/${session.jobId}/cancel`, { method: 'POST' })
    }
  } catch {
    // proceed regardless
  } finally {
    isCancelling.value = false
    router.push('/upload')
  }
}

async function startPipeline(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId }),
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
}

async function handleRetry() {
  hasError.value = false
  errorMessage.value = ''
  stagesStatus.value.clear()
  stageStartTimes.value.clear()
  stageCompleteTimes.value = []
  summary.value = { pdfCount: null, pageCount: null, layoutsDetected: null }

  if (session.jobId) {
    try {
      await startPipeline(session.jobId)
    } catch {
      hasError.value = true
      errorMessage.value = 'Erro ao iniciar pipeline de análise.'
      return
    }
    connectSSE(session.jobId)
  }
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
    try {
      await startPipeline(session.jobId)
    } catch {
      hasError.value = true
      errorMessage.value = 'Erro ao iniciar pipeline de análise.'
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
</style>
