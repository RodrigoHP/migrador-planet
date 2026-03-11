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
    eventSource.value = new EventSource(`${API_BASE}/progress/${id}`)

    eventSource.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEProgressEvent
        lastEvent.value = data

        session.processingStep = data.step
        session.processingPct = data.pct
        if (data.warning) options?.onWarning?.(data.warning)

        if (data.status === 'done') {
          options?.onDone?.(data)
          eventSource.value?.close()
          eventSource.value = null
        }
        if (data.status === 'error') {
          options?.onError?.(data)
          eventSource.value?.close()
          eventSource.value = null
        }
      } catch {
        // ignore parse errors
      }
    }

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
