import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useTemplateStore } from './templateStore'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const SESSION_RUN_LIMIT = 3

// ─── Types ────────────────────────────────────────────────────────────────────

export type FixType = 'spacing' | 'alignment' | 'font' | 'binding' | 'position'

export interface FixSuggestion {
  id: string
  type: FixType
  description: string
  element_id: string
  current_value: string
  suggested_value: string
  confidence: number
}

export interface AutoFixProgress {
  current: number
  total: number
  applied: number
  rejected: number
  skipped: number
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useAutoFixStore = defineStore('autoFix', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const isRunning = ref(false)
  const suggestions = ref<FixSuggestion[]>([])
  const currentIndex = ref(0)
  const appliedFixes = ref<FixSuggestion[]>([])
  const rejectedFixes = ref<FixSuggestion[]>([])
  const skippedFixes = ref<FixSuggestion[]>([])
  const sessionRunCount = ref(0)
  const isOpen = ref(false)
  const error = ref<string | null>(null)

  // ─── Getters ─────────────────────────────────────────────────────────────

  const currentSuggestion = computed<FixSuggestion | null>(() => {
    return suggestions.value[currentIndex.value] ?? null
  })

  const progress = computed<AutoFixProgress>(() => ({
    current: currentIndex.value + (suggestions.value.length > 0 ? 1 : 0),
    total: suggestions.value.length,
    applied: appliedFixes.value.length,
    rejected: rejectedFixes.value.length,
    skipped: skippedFixes.value.length,
  }))

  const isLimitReached = computed(() => sessionRunCount.value >= SESSION_RUN_LIMIT)

  const isFinished = computed(
    () =>
      suggestions.value.length > 0 &&
      currentIndex.value >= suggestions.value.length,
  )

  // ─── Actions ─────────────────────────────────────────────────────────────

  /** Call backend to get fix suggestions for current template state */
  async function runAutoFix(): Promise<void> {
    if (isRunning.value) return
    if (isLimitReached.value) return

    const templateStore = useTemplateStore()
    isRunning.value = true
    error.value = null

    // Reset state for new run
    suggestions.value = []
    currentIndex.value = 0
    appliedFixes.value = []
    rejectedFixes.value = []
    skippedFixes.value = []
    isOpen.value = true

    try {
      const templateState = {
        documentTree: templateStore.documentTree,
      }

      const response = await fetch(`${API_BASE}/api/auto-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_state: templateState }),
      })

      if (!response.ok) {
        const detail = await response.text()
        throw new Error(`Auto Fix failed: ${response.status} ${detail}`)
      }

      const data = (await response.json()) as { suggestions: FixSuggestion[]; total: number }
      suggestions.value = data.suggestions
      sessionRunCount.value++
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      isRunning.value = false
    }
  }

  /** Accept current suggestion — apply fix to templateStore, create undo snapshot */
  function acceptCurrent(): void {
    const suggestion = currentSuggestion.value
    if (!suggestion) return

    const templateStore = useTemplateStore()

    // Push undo snapshot before applying fix (Story 7.2 undo stack integration)
    templateStore.pushUndoSnapshot()

    // Apply fix: update the element property based on fix type
    if (suggestion.element_id) {
      const propMap: Record<FixType, string> = {
        spacing: 'padding',
        alignment: 'textAlign',
        font: 'fontFamily',
        binding: 'binding',
        position: 'x',
      }
      const propKey = propMap[suggestion.type] ?? suggestion.type
      templateStore.updateNodeProperty(suggestion.element_id, propKey, suggestion.suggested_value)
    }

    appliedFixes.value.push(suggestion)
    _advance()
  }

  /** Reject current suggestion — mark as rejected, advance */
  function rejectCurrent(): void {
    const suggestion = currentSuggestion.value
    if (!suggestion) return
    rejectedFixes.value.push(suggestion)
    _advance()
  }

  /** Skip current suggestion — mark as skipped, advance */
  function skipCurrent(): void {
    const suggestion = currentSuggestion.value
    if (!suggestion) return
    skippedFixes.value.push(suggestion)
    _advance()
  }

  /** Close the panel */
  function closePanel(): void {
    isOpen.value = false
  }

  /** Reset entire store state (for testing / new session) */
  function reset(): void {
    isRunning.value = false
    suggestions.value = []
    currentIndex.value = 0
    appliedFixes.value = []
    rejectedFixes.value = []
    skippedFixes.value = []
    sessionRunCount.value = 0
    isOpen.value = false
    error.value = null
  }

  // ─── Private helpers ─────────────────────────────────────────────────────

  function _advance(): void {
    currentIndex.value++
  }

  return {
    // state
    isRunning,
    suggestions,
    currentIndex,
    appliedFixes,
    rejectedFixes,
    skippedFixes,
    sessionRunCount,
    isOpen,
    error,
    // getters
    currentSuggestion,
    progress,
    isLimitReached,
    isFinished,
    // actions
    runAutoFix,
    acceptCurrent,
    rejectCurrent,
    skipCurrent,
    closePanel,
    reset,
  }
})
