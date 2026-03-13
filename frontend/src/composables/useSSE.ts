import { ref, onUnmounted, watch } from 'vue'
import type { Ref } from 'vue'
import { useSessionStore } from '@/stores/session'
import type { ExtractionResult } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export interface SSEProgressEvent {
  step: string
  pct: number
  status: 'processing' | 'done' | 'error'
  extraction?: ExtractionResult
  warning?: string
  error?: string
}

interface SSEOptions {
  onDone?: (event: SSEProgressEvent) => void
  onError?: (event: SSEProgressEvent) => void
  onWarning?: (message: string) => void
}

export function useSSE(jobId: Ref<string | null>, options?: SSEOptions) {
  const session = useSessionStore()
  const eventSource = ref<EventSource | null>(null)
  const lastEvent = ref<SSEProgressEvent | null>(null)

  function connect(id: string) {
    if (eventSource.value) {
      eventSource.value.close()
    }
    // Fix G4: add /api/ prefix so Vite proxy routes to backend
    eventSource.value = new EventSource(`${API_BASE}/api/progress/${id}`)

    // Backend emits named SSE events: 'step', 'done', 'error', 'warning'
    // onmessage only handles unnamed events — use addEventListener for named events

    eventSource.value.addEventListener('step', (event: Event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as { step?: string; pct?: number; warning?: string }
        const synthetic: SSEProgressEvent = {
          step: data.step ?? '',
          pct: data.pct ?? 0,
          status: 'processing',
          warning: data.warning,
        }
        lastEvent.value = synthetic
        if (data.step !== undefined) session.processingStep = data.step
        if (data.pct !== undefined) session.processingPct = data.pct
        if (data.warning) options?.onWarning?.(data.warning)
      } catch {
        // ignore parse errors
      }
    })

    eventSource.value.addEventListener('done', (_event: Event) => {
      const synthetic: SSEProgressEvent = {
        step: session.processingStep,
        pct: 100,
        status: 'done',
      }
      lastEvent.value = synthetic
      session.processingPct = 100
      options?.onDone?.(synthetic)
      eventSource.value?.close()
      eventSource.value = null
    })

    eventSource.value.addEventListener('error', (event: Event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as { message?: string }
        const synthetic: SSEProgressEvent = {
          step: session.processingStep,
          pct: session.processingPct,
          status: 'error',
          error: data.message,
        }
        lastEvent.value = synthetic
        options?.onError?.(synthetic)
      } catch {
        options?.onError?.({
          step: session.processingStep,
          pct: session.processingPct,
          status: 'error',
          error: 'Falha ao processar evento de erro SSE.',
        })
      }
      eventSource.value?.close()
      eventSource.value = null
    })

    eventSource.value.addEventListener('warning', (event: Event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as { message?: string }
        if (data.message) options?.onWarning?.(data.message)
      } catch {
        // ignore
      }
    })

    // Connection-level error (network failure, server unreachable)
    eventSource.value.onerror = () => {
      options?.onError?.({
        step: session.processingStep || 'SSE',
        pct: session.processingPct,
        status: 'error',
        error: 'Falha de conexao com canal de progresso (SSE).',
      })
      eventSource.value?.close()
      eventSource.value = null
    }
  }

  const stop = watch(jobId, (id) => {
    if (id) connect(id)
    else if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
  }, { immediate: true })

  onUnmounted(() => {
    stop()
    eventSource.value?.close()
  })

  return { eventSource, lastEvent }
}
