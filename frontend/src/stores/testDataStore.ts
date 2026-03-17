import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Dataset, ValidationResult } from '@/types/test-data.types'

export const useTestDataStore = defineStore('testData', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const datasets = ref<Dataset[]>([])
  const activeDatasetId = ref<string | null>(null)
  const validationResults = ref<ValidationResult[]>([])

  // ─── Getters ─────────────────────────────────────────────────────────────
  const activeDataset = computed<Dataset | undefined>(() =>
    datasets.value.find((d) => d.id === activeDatasetId.value),
  )

  // ─── Actions ─────────────────────────────────────────────────────────────
  function setActiveDataset(id: string) {
    activeDatasetId.value = id
  }

  function addDataset(dataset: Dataset) {
    datasets.value.push(dataset)
  }

  function removeDataset(id: string) {
    datasets.value = datasets.value.filter((d) => d.id !== id)
    if (activeDatasetId.value === id) {
      activeDatasetId.value = datasets.value[0]?.id ?? null
    }
  }

  // Placeholder for Epic 8 — test execution engine
  function runValidation(_datasetId: string): Promise<void> {
    return Promise.resolve()
  }

  function setValidationResults(results: ValidationResult[]) {
    validationResults.value = results
  }

  return {
    datasets,
    activeDatasetId,
    validationResults,
    activeDataset,
    setActiveDataset,
    addDataset,
    removeDataset,
    runValidation,
    setValidationResults,
  }
})
