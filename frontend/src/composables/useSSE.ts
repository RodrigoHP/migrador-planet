import { ref, onUnmounted, watch } from 'vue'
import type { Ref } from 'vue'
import { useSessionStore } from '@/stores/session'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export function useSSE(jobId: Ref<string | null>) {
  const session = useSessionStore()
  let eventSource: EventSource | null = null

  function connect(id: string) {
    if (eventSource) {
      eventSource.close()
    }
    eventSource = new EventSource(`${API_BASE}/progress/${id}`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as {
          step: string
          pct: number
          status: 'processing' | 'done' | 'error'
        }
        session.processingStep = data.step
        session.processingPct = data.pct

        if (data.status === 'done' || data.status === 'error') {
          eventSource?.close()
          eventSource = null
        }
      } catch {
        // ignore parse errors
      }
    }

    eventSource.onerror = () => {
      eventSource?.close()
      eventSource = null
    }
  }

  const stop = watch(jobId, (id) => {
    if (id) connect(id)
    else if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }, { immediate: true })

  onUnmounted(() => {
    stop()
    eventSource?.close()
  })

  return { eventSource: ref(eventSource) }
}
