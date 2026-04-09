import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTestReportStore } from './testReportStore'
import type { DatasetTestResult } from './testReportStore'

function makeResult(overrides: Partial<DatasetTestResult> = {}): DatasetTestResult {
  return {
    datasetId: 'ds-1',
    datasetName: 'synthetic_small',
    pageCount: 1,
    coveragePct: 80,
    status: 'ok',
    testedAt: new Date().toISOString(),
    coveredElements: ['el-1', 'el-2'],
    ...overrides,
  }
}

describe('testReportStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('starts with empty results', () => {
      const store = useTestReportStore()
      expect(store.results).toEqual([])
    })

    it('starts not running', () => {
      const store = useTestReportStore()
      expect(store.isRunning).toBe(false)
    })

    it('cancelRequested starts false', () => {
      const store = useTestReportStore()
      expect(store.cancelRequested).toBe(false)
    })

    it('hasResults starts false', () => {
      const store = useTestReportStore()
      expect(store.hasResults).toBe(false)
    })

    it('overallStatus starts as pending', () => {
      const store = useTestReportStore()
      expect(store.overallStatus).toBe('pending')
    })
  })

  describe('startRun', () => {
    it('sets isRunning to true', () => {
      const store = useTestReportStore()
      store.startRun()
      expect(store.isRunning).toBe(true)
    })

    it('clears existing results', () => {
      const store = useTestReportStore()
      store.addResult(makeResult())
      store.startRun()
      expect(store.results).toEqual([])
    })

    it('resets cancelRequested', () => {
      const store = useTestReportStore()
      store.requestCancel()
      store.startRun()
      expect(store.cancelRequested).toBe(false)
    })
  })

  describe('requestCancel', () => {
    it('sets cancelRequested to true', () => {
      const store = useTestReportStore()
      store.startRun()
      store.requestCancel()
      expect(store.cancelRequested).toBe(true)
    })
  })

  describe('finishRun', () => {
    it('sets isRunning to false', () => {
      const store = useTestReportStore()
      store.startRun()
      store.finishRun()
      expect(store.isRunning).toBe(false)
    })

    it('resets cancelRequested', () => {
      const store = useTestReportStore()
      store.startRun()
      store.requestCancel()
      store.finishRun()
      expect(store.cancelRequested).toBe(false)
    })
  })

  describe('addResult', () => {
    it('adds a new result', () => {
      const store = useTestReportStore()
      store.addResult(makeResult())
      expect(store.results.length).toBe(1)
      expect(store.results[0]!.datasetId).toBe('ds-1')
    })

    it('updates existing result with same datasetId', () => {
      const store = useTestReportStore()
      store.addResult(makeResult({ status: 'ok' }))
      store.addResult(makeResult({ status: 'error' }))
      expect(store.results.length).toBe(1)
      expect(store.results[0]!.status).toBe('error')
    })

    it('adds multiple different results', () => {
      const store = useTestReportStore()
      store.addResult(makeResult({ datasetId: 'ds-1' }))
      store.addResult(makeResult({ datasetId: 'ds-2' }))
      expect(store.results.length).toBe(2)
    })
  })

  describe('clearResults', () => {
    it('clears all results', () => {
      const store = useTestReportStore()
      store.addResult(makeResult())
      store.clearResults()
      expect(store.results).toEqual([])
    })

    it('resets isRunning', () => {
      const store = useTestReportStore()
      store.startRun()
      store.clearResults()
      expect(store.isRunning).toBe(false)
    })

    it('clears coverage matrix', () => {
      const store = useTestReportStore()
      store.updateCoverageMatrix([{ id: 'el-1', label: 'Element 1' }], 'ds-1', ['el-1'])
      store.clearResults()
      expect(store.coverageMatrix).toEqual([])
    })
  })

  describe('overallStatus computed', () => {
    it('returns ok when all results are ok', () => {
      const store = useTestReportStore()
      store.addResult(makeResult({ status: 'ok' }))
      store.addResult(makeResult({ datasetId: 'ds-2', status: 'ok' }))
      expect(store.overallStatus).toBe('ok')
    })

    it('returns error when any result is error', () => {
      const store = useTestReportStore()
      store.addResult(makeResult({ status: 'ok' }))
      store.addResult(makeResult({ datasetId: 'ds-2', status: 'error' }))
      expect(store.overallStatus).toBe('error')
    })

    it('returns warning when any result is timeout', () => {
      const store = useTestReportStore()
      store.addResult(makeResult({ status: 'ok' }))
      store.addResult(makeResult({ datasetId: 'ds-2', status: 'timeout' }))
      expect(store.overallStatus).toBe('warning')
    })
  })

  describe('datasetIds computed', () => {
    it('returns ids of all results', () => {
      const store = useTestReportStore()
      store.addResult(makeResult({ datasetId: 'ds-1' }))
      store.addResult(makeResult({ datasetId: 'ds-2' }))
      expect(store.datasetIds).toEqual(['ds-1', 'ds-2'])
    })
  })

  describe('updateCoverageMatrix', () => {
    it('adds entries for new elements', () => {
      const store = useTestReportStore()
      store.updateCoverageMatrix(
        [
          { id: 'el-1', label: 'Element 1' },
          { id: 'el-2', label: 'Element 2' },
        ],
        'ds-1',
        ['el-1'],
      )
      expect(store.coverageMatrix.length).toBe(2)
    })

    it('marks covered elements correctly', () => {
      const store = useTestReportStore()
      store.updateCoverageMatrix(
        [
          { id: 'el-1', label: 'Element 1' },
          { id: 'el-2', label: 'Element 2' },
        ],
        'ds-1',
        ['el-1'],
      )
      const el1 = store.coverageMatrix.find((e) => e.elementId === 'el-1')
      const el2 = store.coverageMatrix.find((e) => e.elementId === 'el-2')
      expect(el1?.coverageByDataset['ds-1']).toBe(true)
      expect(el2?.coverageByDataset['ds-1']).toBe(false)
    })

    it('accumulates coverage for multiple datasets', () => {
      const store = useTestReportStore()
      store.updateCoverageMatrix([{ id: 'el-1', label: 'Element 1' }], 'ds-1', ['el-1'])
      store.updateCoverageMatrix([{ id: 'el-1', label: 'Element 1' }], 'ds-2', [])
      const el1 = store.coverageMatrix.find((e) => e.elementId === 'el-1')
      expect(el1?.coverageByDataset['ds-1']).toBe(true)
      expect(el1?.coverageByDataset['ds-2']).toBe(false)
    })
  })
})
