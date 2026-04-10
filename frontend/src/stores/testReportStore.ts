/**
 * testReportStore — Story 8.4
 * Stores results from "Testar Todos" execution: per-dataset results + coverage matrix.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export type TestRunStatus = 'ok' | 'warning' | 'error' | 'timeout' | 'cancelled' | 'pending'

export interface DatasetTestResult {
  datasetId: string
  datasetName: string
  pageCount: number
  coveragePct: number
  status: TestRunStatus
  /** ISO timestamp when test completed */
  testedAt: string
  /** Error message if status is 'error' */
  errorMessage?: string
  /** Elements covered in this dataset (for coverage matrix) */
  coveredElements: string[]
}

export interface CoverageMatrixEntry {
  /** Template element id or path */
  elementId: string
  elementLabel: string
  /** Map from datasetId → covered (true/false) */
  coverageByDataset: Record<string, boolean>
}

export const useTestReportStore = defineStore('testReport', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const results = ref<DatasetTestResult[]>([])
  const isRunning = ref(false)
  const cancelRequested = ref(false)
  const coverageMatrix = ref<CoverageMatrixEntry[]>([])

  // ─── Getters ─────────────────────────────────────────────────────────────
  const hasResults = computed(() => results.value.length > 0)

  const overallStatus = computed<TestRunStatus>(() => {
    if (results.value.length === 0) return 'pending'
    if (results.value.some((r) => r.status === 'error')) return 'error'
    if (results.value.some((r) => r.status === 'timeout' || r.status === 'warning'))
      return 'warning'
    if (results.value.every((r) => r.status === 'ok')) return 'ok'
    return 'warning'
  })

  const datasetIds = computed(() => results.value.map((r) => r.datasetId))

  // ─── Actions ─────────────────────────────────────────────────────────────

  function startRun() {
    results.value = []
    coverageMatrix.value = []
    isRunning.value = true
    cancelRequested.value = false
  }

  function requestCancel() {
    cancelRequested.value = true
  }

  function finishRun() {
    isRunning.value = false
    cancelRequested.value = false
  }

  function addResult(result: DatasetTestResult) {
    const idx = results.value.findIndex((r) => r.datasetId === result.datasetId)
    if (idx !== -1) {
      results.value[idx] = result
    } else {
      results.value.push(result)
    }
  }

  function clearResults() {
    results.value = []
    coverageMatrix.value = []
    isRunning.value = false
    cancelRequested.value = false
  }

  function updateCoverageMatrix(
    elements: Array<{ id: string; label: string }>,
    datasetId: string,
    coveredElementIds: string[],
  ) {
    const coveredSet = new Set(coveredElementIds)

    for (const el of elements) {
      let entry = coverageMatrix.value.find((e) => e.elementId === el.id)
      if (!entry) {
        entry = {
          elementId: el.id,
          elementLabel: el.label,
          coverageByDataset: {},
        }
        coverageMatrix.value.push(entry)
      }
      entry.coverageByDataset[datasetId] = coveredSet.has(el.id)
    }
  }

  return {
    results,
    isRunning,
    cancelRequested,
    coverageMatrix,
    hasResults,
    overallStatus,
    datasetIds,
    startRun,
    requestCancel,
    finishRun,
    addResult,
    clearResults,
    updateCoverageMatrix,
  }
})
