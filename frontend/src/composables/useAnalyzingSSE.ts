/**
 * Story 40.6 — FE-001: SSE connection management for AnalyzingPage.
 *
 * Extracted from useAnalyzingStateMachine to keep files under 500 LOC.
 * Handles SSE connection, reconnection, and stream parsing.
 */
import { ref } from 'vue'
import { useSessionStore } from '@/stores/session'
import { apiFetch } from '@/services/apiFetch'
import type { RawSSEData } from './useAnalyzingStateMachine'
import type { AnalyzingPageState } from '@/pages/analyzingPageConstantsV2'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export function useAnalyzingSSE(
  pageState: ReturnType<typeof ref<AnalyzingPageState>>,
  applyEventFn: (data: RawSSEData) => Promise<boolean>,
) {
  const session = useSessionStore()

  const connectionLost = ref(false)
  const sessionLost = ref(false)

  let sseAbortController: AbortController | null = null
  let reconnectAttempts = 0
  const MAX_RECONNECT = 3
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  const _eventQueue: RawSSEData[] = []
  let _drainingQueue = false

  async function drainEventQueue(): Promise<void> {
    if (_drainingQueue) return
    _drainingQueue = true
    while (_eventQueue.length > 0) {
      const data = _eventQueue.shift()!
      const done = await applyEventFn(data)
      if (done) break
      if (_eventQueue.length > 0) {
        await new Promise<void>((resolve) => setTimeout(resolve, 60))
      }
    }
    _drainingQueue = false
  }

  async function connectSSE(jobId: string) {
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
              drainEventQueue()
            } catch {
              /* ignore parse errors */
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
        /* proceed to reconnect */
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

  function closeSSE() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    sseAbortController?.abort()
    sseAbortController = null
  }

  function handleReconnect() {
    connectionLost.value = false
    reconnectAttempts = 0
    if (session.jobId) connectSSE(session.jobId)
  }

  function resetSSE() {
    _eventQueue.length = 0
    _drainingQueue = false
  }

  return {
    connectionLost,
    sessionLost,
    connectSSE,
    closeSSE,
    handleReconnect,
    resetSSE,
  }
}
