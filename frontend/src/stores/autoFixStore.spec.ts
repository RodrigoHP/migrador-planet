import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAutoFixStore } from './autoFixStore'
import type { FixSuggestion } from './autoFixStore'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function makeSuggestion(overrides: Partial<FixSuggestion> = {}): FixSuggestion {
  return {
    id: 'fix-001',
    type: 'spacing',
    description: 'Espaçamento inconsistente',
    element_id: 'node-1',
    current_value: '8px',
    suggested_value: '16px',
    confidence: 85,
    ...overrides,
  }
}

function mockApiSuccess(suggestions: FixSuggestion[]) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ suggestions, total: suggestions.length }),
  })
}

function mockApiError(status = 500) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    text: () => Promise.resolve('Internal Server Error'),
  })
}

describe('autoFixStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('starts not running', () => {
      const store = useAutoFixStore()
      expect(store.isRunning).toBe(false)
    })

    it('starts with empty suggestions', () => {
      const store = useAutoFixStore()
      expect(store.suggestions).toEqual([])
    })

    it('starts at index 0', () => {
      const store = useAutoFixStore()
      expect(store.currentIndex).toBe(0)
    })

    it('starts with zero session run count', () => {
      const store = useAutoFixStore()
      expect(store.sessionRunCount).toBe(0)
    })

    it('isLimitReached is false initially', () => {
      const store = useAutoFixStore()
      expect(store.isLimitReached).toBe(false)
    })

    it('currentSuggestion is null initially', () => {
      const store = useAutoFixStore()
      expect(store.currentSuggestion).toBeNull()
    })

    it('progress starts at 0/0', () => {
      const store = useAutoFixStore()
      expect(store.progress.total).toBe(0)
      expect(store.progress.applied).toBe(0)
      expect(store.progress.rejected).toBe(0)
      expect(store.progress.skipped).toBe(0)
    })
  })

  describe('runAutoFix', () => {
    it('increments sessionRunCount after successful run', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      expect(store.sessionRunCount).toBe(1)
    })

    it('populates suggestions after run', async () => {
      const store = useAutoFixStore()
      const suggestion = makeSuggestion()
      mockApiSuccess([suggestion])
      await store.runAutoFix()
      expect(store.suggestions).toHaveLength(1)
      expect(store.suggestions[0]!.id).toBe('fix-001')
    })

    it('opens the panel after run', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([])
      await store.runAutoFix()
      expect(store.isOpen).toBe(true)
    })

    it('sets error on API failure', async () => {
      const store = useAutoFixStore()
      mockApiError()
      await store.runAutoFix()
      expect(store.error).toContain('Auto Fix failed')
    })

    it('does not run when limit is reached', async () => {
      const store = useAutoFixStore()
      store.sessionRunCount = 5
      await store.runAutoFix()
      expect(mockFetch).not.toHaveBeenCalled()
    })

    it('does not run while already running', async () => {
      const store = useAutoFixStore()
      store.isRunning = true
      await store.runAutoFix()
      expect(mockFetch).not.toHaveBeenCalled()
    })

    it('resets previous suggestions at start of new run', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      expect(store.appliedFixes).toHaveLength(0)
      expect(store.rejectedFixes).toHaveLength(0)
      expect(store.skippedFixes).toHaveLength(0)
    })
  })

  describe('acceptCurrent', () => {
    it('moves suggestion to appliedFixes', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.acceptCurrent()
      expect(store.appliedFixes).toHaveLength(1)
    })

    it('advances currentIndex', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion(), makeSuggestion({ id: 'fix-002' })])
      await store.runAutoFix()
      store.acceptCurrent()
      expect(store.currentIndex).toBe(1)
    })

    it('does nothing when no current suggestion', () => {
      const store = useAutoFixStore()
      store.acceptCurrent()
      expect(store.appliedFixes).toHaveLength(0)
    })
  })

  describe('rejectCurrent', () => {
    it('moves suggestion to rejectedFixes', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.rejectCurrent()
      expect(store.rejectedFixes).toHaveLength(1)
    })

    it('advances currentIndex', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.rejectCurrent()
      expect(store.currentIndex).toBe(1)
    })

    it('does nothing when no current suggestion', () => {
      const store = useAutoFixStore()
      store.rejectCurrent()
      expect(store.rejectedFixes).toHaveLength(0)
    })
  })

  describe('skipCurrent', () => {
    it('moves suggestion to skippedFixes', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.skipCurrent()
      expect(store.skippedFixes).toHaveLength(1)
    })

    it('advances currentIndex', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.skipCurrent()
      expect(store.currentIndex).toBe(1)
    })
  })

  describe('progress getter', () => {
    it('reflects accepted/rejected/skipped counts correctly', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([
        makeSuggestion({ id: 'fix-001' }),
        makeSuggestion({ id: 'fix-002' }),
        makeSuggestion({ id: 'fix-003' }),
      ])
      await store.runAutoFix()

      store.acceptCurrent()
      store.rejectCurrent()
      store.skipCurrent()

      expect(store.progress.applied).toBe(1)
      expect(store.progress.rejected).toBe(1)
      expect(store.progress.skipped).toBe(1)
    })

    it('total reflects suggestion count', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion(), makeSuggestion({ id: 'fix-002' })])
      await store.runAutoFix()
      expect(store.progress.total).toBe(2)
    })
  })

  describe('isLimitReached', () => {
    it('becomes true at limit runs (default 5)', async () => {
      const store = useAutoFixStore()

      for (let i = 0; i < 5; i++) {
        mockApiSuccess([])
        await store.runAutoFix()
      }

      expect(store.isLimitReached).toBe(true)
    })

    it('is false below limit', async () => {
      const store = useAutoFixStore()

      for (let i = 0; i < 4; i++) {
        mockApiSuccess([])
        await store.runAutoFix()
      }

      expect(store.isLimitReached).toBe(false)
    })
  })

  describe('isFinished', () => {
    it('is false when no suggestions', () => {
      const store = useAutoFixStore()
      expect(store.isFinished).toBe(false)
    })

    it('is true when all suggestions processed', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.rejectCurrent()
      expect(store.isFinished).toBe(true)
    })
  })

  describe('reset', () => {
    it('resets all state including sessionRunCount', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.reset()
      expect(store.sessionRunCount).toBe(0)
      expect(store.suggestions).toHaveLength(0)
      expect(store.isOpen).toBe(false)
    })
  })

  describe('closePanel', () => {
    it('sets isOpen to false', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([])
      await store.runAutoFix()
      store.closePanel()
      expect(store.isOpen).toBe(false)
    })
  })

  // ─── Story 14.11 — Batch Actions ──────────────────────────────────────────

  describe('batchAcceptAll', () => {
    it('applies all pending suggestions', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([
        makeSuggestion({ id: 'fix-001' }),
        makeSuggestion({ id: 'fix-002' }),
        makeSuggestion({ id: 'fix-003' }),
      ])
      await store.runAutoFix()
      const count = store.batchAcceptAll()
      expect(count).toBe(3)
      expect(store.appliedFixes).toHaveLength(3)
      expect(store.isFinished).toBe(true)
    })

    it('returns 0 when no pending suggestions', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion()])
      await store.runAutoFix()
      store.acceptCurrent() // process the only one
      const count = store.batchAcceptAll()
      expect(count).toBe(0)
    })

    it('only applies remaining pending suggestions', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([
        makeSuggestion({ id: 'fix-001' }),
        makeSuggestion({ id: 'fix-002' }),
        makeSuggestion({ id: 'fix-003' }),
      ])
      await store.runAutoFix()
      store.skipCurrent() // skip first
      const count = store.batchAcceptAll()
      expect(count).toBe(2)
      expect(store.appliedFixes).toHaveLength(2)
      expect(store.skippedFixes).toHaveLength(1)
    })
  })

  describe('batchAcceptByType', () => {
    it('applies only suggestions of specified type', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([
        makeSuggestion({ id: 'fix-001', type: 'spacing' }),
        makeSuggestion({ id: 'fix-002', type: 'font' }),
        makeSuggestion({ id: 'fix-003', type: 'spacing' }),
      ])
      await store.runAutoFix()
      const count = store.batchAcceptByType('spacing')
      expect(count).toBe(2)
      expect(store.appliedFixes).toHaveLength(2)
      expect(store.skippedFixes).toHaveLength(1)
      expect(store.isFinished).toBe(true)
    })

    it('returns 0 for non-existent type', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion({ type: 'spacing' })])
      await store.runAutoFix()
      const count = store.batchAcceptByType('nonexistent')
      expect(count).toBe(0)
    })
  })

  describe('pendingSuggestions', () => {
    it('returns all suggestions before any action', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion(), makeSuggestion({ id: 'fix-002' })])
      await store.runAutoFix()
      expect(store.pendingSuggestions).toHaveLength(2)
    })

    it('decreases as suggestions are processed', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion(), makeSuggestion({ id: 'fix-002' })])
      await store.runAutoFix()
      store.acceptCurrent()
      expect(store.pendingSuggestions).toHaveLength(1)
    })
  })

  describe('suggestionTypes', () => {
    it('groups by type with count', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([
        makeSuggestion({ id: 'fix-001', type: 'spacing' }),
        makeSuggestion({ id: 'fix-002', type: 'font' }),
        makeSuggestion({ id: 'fix-003', type: 'spacing' }),
      ])
      await store.runAutoFix()
      const types = store.suggestionTypes
      expect(types).toEqual(
        expect.arrayContaining([
          { type: 'spacing', count: 2 },
          { type: 'font', count: 1 },
        ]),
      )
    })
  })

  // ─── Story 14.10 — New Fix Types ──────────────────────────────────────────

  describe('new fix types (14.10)', () => {
    it('accepts border-refine suggestion', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion({ id: 'fix-br', type: 'border-refine' })])
      await store.runAutoFix()
      store.acceptCurrent()
      expect(store.appliedFixes).toHaveLength(1)
      expect(store.appliedFixes[0]!.type).toBe('border-refine')
    })

    it('accepts background-refine suggestion', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion({ id: 'fix-bg', type: 'background-refine' })])
      await store.runAutoFix()
      store.acceptCurrent()
      expect(store.appliedFixes).toHaveLength(1)
      expect(store.appliedFixes[0]!.type).toBe('background-refine')
    })

    it('accepts text-align suggestion', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion({ id: 'fix-ta', type: 'text-align' })])
      await store.runAutoFix()
      store.acceptCurrent()
      expect(store.appliedFixes).toHaveLength(1)
    })

    it('accepts z-order suggestion', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([makeSuggestion({ id: 'fix-zo', type: 'z-order' })])
      await store.runAutoFix()
      store.acceptCurrent()
      expect(store.appliedFixes).toHaveLength(1)
    })

    it('handles mixed old and new types', async () => {
      const store = useAutoFixStore()
      mockApiSuccess([
        makeSuggestion({ id: 'fix-001', type: 'spacing' }),
        makeSuggestion({ id: 'fix-002', type: 'border-refine' }),
        makeSuggestion({ id: 'fix-003', type: 'z-order' }),
      ])
      await store.runAutoFix()
      expect(store.suggestions).toHaveLength(3)
      store.batchAcceptAll()
      expect(store.appliedFixes).toHaveLength(3)
      expect(store.isFinished).toBe(true)
    })
  })
})
