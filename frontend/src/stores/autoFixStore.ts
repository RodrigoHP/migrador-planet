import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useTemplateStore } from './templateStore'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const _rawLimit = import.meta.env.VITE_AUTOFIX_LIMIT ?? '5'
const _parsedLimit = parseInt(_rawLimit, 10)
const SESSION_RUN_LIMIT = isNaN(_parsedLimit) ? 5 : _parsedLimit

// ─── Types ────────────────────────────────────────────────────────────────────

export type FixType =
  | 'spacing'
  | 'alignment'
  | 'font'
  | 'binding'
  | 'position'
  | 'border-refine'
  | 'background-refine'
  | 'text-align'
  | 'z-order'

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
    () => suggestions.value.length > 0 && currentIndex.value >= suggestions.value.length,
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

      // Include PDF extraction data when available (Story 14.10)
      const pdfExtraction =
        'pdfExtraction' in templateStore
          ? (templateStore as unknown as Record<string, unknown>).pdfExtraction
          : null

      const response = await fetch(`${API_BASE}/api/v1/auto-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_state: templateState,
          ...(pdfExtraction ? { pdf_extraction: pdfExtraction } : {}),
        }),
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
    templateStore.pushUndoSnapshot()
    _applySuggestion(templateStore, suggestion)
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

  // ─── Getters for batch (Story 14.11) ────────────────────────────────────────

  /** Pending suggestions that haven't been processed yet */
  const pendingSuggestions = computed(() => suggestions.value.slice(currentIndex.value))

  /** Unique suggestion types with counts */
  const suggestionTypes = computed(() => {
    const map = new Map<string, number>()
    for (const s of pendingSuggestions.value) {
      map.set(s.type, (map.get(s.type) ?? 0) + 1)
    }
    return [...map.entries()].map(([type, count]) => ({ type, count }))
  })

  // ─── Batch Actions (Story 14.11) ──────────────────────────────────────────

  /** Accept ALL pending suggestions in one batch */
  function batchAcceptAll(): number {
    const pending = pendingSuggestions.value
    if (pending.length === 0) return 0

    const templateStore = useTemplateStore()
    templateStore.pushUndoSnapshot()

    for (const suggestion of pending) {
      _applySuggestion(templateStore, suggestion)
      appliedFixes.value.push(suggestion)
    }
    currentIndex.value = suggestions.value.length
    return pending.length
  }

  /** Accept all pending suggestions of a specific type */
  function batchAcceptByType(type: string): number {
    const pending = pendingSuggestions.value
    const matching = pending.filter((s) => s.type === type)
    if (matching.length === 0) return 0

    const templateStore = useTemplateStore()
    templateStore.pushUndoSnapshot()

    const matchIds = new Set(matching.map((s) => s.id))
    // Process all pending: matching ones get applied, others get skipped
    for (const suggestion of pending) {
      if (matchIds.has(suggestion.id)) {
        _applySuggestion(templateStore, suggestion)
        appliedFixes.value.push(suggestion)
      } else {
        skippedFixes.value.push(suggestion)
      }
    }
    currentIndex.value = suggestions.value.length
    return matching.length
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

  function _applySuggestion(
    templateStore: ReturnType<typeof useTemplateStore>,
    suggestion: FixSuggestion,
  ): void {
    if (suggestion.element_id) {
      const propMap: Record<FixType, string> = {
        spacing: 'padding',
        alignment: 'textAlign',
        font: 'fontFamily',
        binding: 'binding',
        position: 'x',
        'border-refine': 'border',
        'background-refine': 'backgroundColor',
        'text-align': 'textAlign',
        'z-order': 'zIndex',
      }
      const propKey = propMap[suggestion.type] ?? suggestion.type
      templateStore.updateNodeProperty(suggestion.element_id, propKey, suggestion.suggested_value)
    }
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
    pendingSuggestions,
    suggestionTypes,
    // actions
    runAutoFix,
    acceptCurrent,
    rejectCurrent,
    skipCurrent,
    batchAcceptAll,
    batchAcceptByType,
    closePanel,
    reset,
  }
})
