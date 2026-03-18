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
      store.sessionRunCount = 3
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
    it('becomes true at 3 runs', async () => {
      const store = useAutoFixStore()

      mockApiSuccess([])
      await store.runAutoFix()
      mockApiSuccess([])
      await store.runAutoFix()
      mockApiSuccess([])
      await store.runAutoFix()

      expect(store.isLimitReached).toBe(true)
    })

    it('is false at 2 runs', async () => {
      const store = useAutoFixStore()

      mockApiSuccess([])
      await store.runAutoFix()
      mockApiSuccess([])
      await store.runAutoFix()

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
})
