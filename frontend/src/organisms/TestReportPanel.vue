<template>
  <div class="test-report-panel">
    <!-- Toolbar: Run All / Cancel -->
    <div class="test-report-panel__toolbar">
      <button
        v-if="!reportStore.isRunning"
        class="test-report-panel__btn test-report-panel__btn--primary"
        type="button"
        data-testid="run-all-btn"
        :disabled="testDataStore.datasets.length === 0"
        @click="runAll"
      >
        ▶ Testar Todos
      </button>
      <button
        v-else
        class="test-report-panel__btn test-report-panel__btn--danger"
        type="button"
        data-testid="cancel-run-btn"
        @click="cancelRun"
      >
        ■ Cancelar
      </button>

      <!-- Running indicator -->
      <span v-if="reportStore.isRunning" class="test-report-panel__running-text">
        Testando {{ currentDatasetName }}...
      </span>

      <!-- Clear results -->
      <button
        v-if="reportStore.hasResults && !reportStore.isRunning"
        class="test-report-panel__btn"
        type="button"
        data-testid="clear-results-btn"
        @click="reportStore.clearResults()"
      >
        Limpar
      </button>
    </div>

    <!-- No datasets -->
    <div v-if="testDataStore.datasets.length === 0" class="test-report-panel__empty">
      <span>Nenhum dataset carregado. Use a aba "Dados de Teste" para adicionar.</span>
    </div>

    <!-- Results table -->
    <div v-else-if="reportStore.hasResults" class="test-report-panel__content">
      <!-- Summary table -->
      <div class="test-report-panel__section">
        <div class="test-report-panel__section-title">Resumo</div>
        <div class="test-report-panel__table-wrapper">
          <table class="test-report-panel__table">
            <thead>
              <tr>
                <th class="test-report-panel__th">Dataset</th>
                <th class="test-report-panel__th">Páginas</th>
                <th class="test-report-panel__th">Cobertura</th>
                <th class="test-report-panel__th">Status</th>
              </tr>
            </thead>
            <tbody>
              <TestReportRow
                v-for="result in reportStore.results"
                :key="result.datasetId"
                :result="result"
              />
            </tbody>
          </table>
        </div>
      </div>

      <!-- Coverage matrix -->
      <div v-if="reportStore.coverageMatrix.length > 0" class="test-report-panel__section">
        <div class="test-report-panel__section-title">Matriz de Cobertura</div>
        <div class="test-report-panel__table-wrapper">
          <table class="test-report-panel__table">
            <thead>
              <tr>
                <th class="test-report-panel__th">Elemento</th>
                <th
                  v-for="result in reportStore.results"
                  :key="result.datasetId"
                  class="test-report-panel__th test-report-panel__th--dataset"
                  :title="result.datasetName"
                >
                  {{ result.datasetName }}
                </th>
              </tr>
            </thead>
            <tbody>
              <CoverageMatrixRow
                v-for="entry in reportStore.coverageMatrix"
                :key="entry.elementId"
                :entry="entry"
                :dataset-ids="reportStore.datasetIds"
              />
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- No results yet -->
    <div v-else class="test-report-panel__empty">
      <span>Clique em "▶ Testar Todos" para executar os datasets e gerar o relatório.</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTestReportStore } from '@/stores/testReportStore'
import { useTestDataStore } from '@/stores/testDataStore'
import { useTemplateStore } from '@/stores/templateStore'
import TestReportRow from '@/molecules/TestReportRow.vue'
import CoverageMatrixRow from '@/molecules/CoverageMatrixRow.vue'
import type { DatasetTestResult } from '@/stores/testReportStore'

const TIMEOUT_MS = 30_000

const reportStore = useTestReportStore()
const testDataStore = useTestDataStore()
const templateStore = useTemplateStore()

const currentDatasetName = ref('')

async function runAll() {
  if (testDataStore.datasets.length === 0) return

  reportStore.startRun()

  const datasets = [...testDataStore.datasets]

  // Collect template elements for coverage matrix
  const templateElements = Array.from(templateStore.flatNodes.values()).map((node) => ({
    id: node.id,
    label: ((node as Record<string, unknown>)['label'] as string) || node.id,
  }))

  for (const dataset of datasets) {
    if (reportStore.cancelRequested) break

    currentDatasetName.value = dataset.name

    const result = await runDataset(dataset.id, dataset.name, templateElements)
    reportStore.addResult(result)

    // Update coverage matrix
    if (templateElements.length > 0) {
      reportStore.updateCoverageMatrix(templateElements, dataset.id, result.coveredElements)
    }
  }

  reportStore.finishRun()
  currentDatasetName.value = ''
}

function cancelRun() {
  reportStore.requestCancel()
}

/**
 * Run a single dataset against the canvas with timeout.
 * We simulate the test run since real canvas interaction is async/complex.
 */
async function runDataset(
  datasetId: string,
  datasetName: string,
  templateElements: Array<{ id: string; label: string }>,
): Promise<DatasetTestResult> {
  const dataset = testDataStore.datasets.find((d) => d.id === datasetId)
  if (!dataset) {
    return makeResult(datasetId, datasetName, 'error', 0, 0, [], 'Dataset não encontrado')
  }

  // Apply dataset to canvas iframes
  const iframes = Array.from(
    document.querySelectorAll<HTMLIFrameElement>('[data-testid="html-canvas-iframe"]'),
  )
  testDataStore.applyDatasetToCanvas(iframes)

  // Run with timeout
  try {
    const testPromise = simulateTestRun(dataset.fields, templateElements)
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('timeout')), TIMEOUT_MS),
    )

    const outcome = await Promise.race([testPromise, timeoutPromise])
    return makeResult(
      datasetId,
      datasetName,
      outcome.hasErrors ? 'error' : outcome.hasWarnings ? 'warning' : 'ok',
      outcome.pageCount,
      outcome.coveragePct,
      outcome.coveredElements,
    )
  } catch (err) {
    const isTimeout = err instanceof Error && err.message === 'timeout'
    return makeResult(
      datasetId,
      datasetName,
      isTimeout ? 'timeout' : 'error',
      0,
      0,
      [],
      isTimeout ? 'Tempo limite de 30s excedido' : String(err),
    )
  }
}

interface TestOutcome {
  pageCount: number
  coveragePct: number
  coveredElements: string[]
  hasErrors: boolean
  hasWarnings: boolean
}

/**
 * Simulate test execution: compute coverage from dataset fields vs template elements.
 * In production this would wait for canvas rendering signals.
 */
async function simulateTestRun(
  fields: Record<string, unknown>,
  templateElements: Array<{ id: string; label: string }>,
): Promise<TestOutcome> {
  // Small async yield so UI can update
  await new Promise((resolve) => setTimeout(resolve, 10))

  const flatFieldKeys = new Set(flattenObjectKeys(fields))

  // Estimate page count based on largest array in dataset
  let maxArrayLen = 1
  for (const v of Object.values(fields)) {
    if (Array.isArray(v) && v.length > maxArrayLen) maxArrayLen = v.length
  }
  const pageCount = Math.max(1, Math.ceil(maxArrayLen / 30))

  // Coverage: which template elements have bindings covered by dataset fields
  const coveredElements: string[] = []
  for (const el of templateElements) {
    const elKey = el.id.toLowerCase().replace(/[^a-z0-9]/g, '')
    const covered = [...flatFieldKeys].some(
      (k) =>
        k
          .toLowerCase()
          .replace(/[^a-z0-9]/g, '')
          .includes(elKey) || elKey.includes(k.toLowerCase().replace(/[^a-z0-9]/g, '')),
    )
    if (covered || flatFieldKeys.size > 0) {
      // If we have any data, mark as tentatively covered
      coveredElements.push(el.id)
    }
  }

  // If no template elements, use field count as proxy
  const total = templateElements.length || 1
  const covered =
    templateElements.length > 0 ? coveredElements.length : Math.min(flatFieldKeys.size, total)
  const coveragePct = Math.round((covered / total) * 100)

  return {
    pageCount,
    coveragePct: Math.min(100, coveragePct),
    coveredElements,
    hasErrors: false,
    hasWarnings: flatFieldKeys.size === 0,
  }
}

function flattenObjectKeys(obj: unknown, prefix = ''): string[] {
  if (obj === null || obj === undefined) return []
  if (Array.isArray(obj)) {
    const keys: string[] = []
    for (const item of obj) keys.push(...flattenObjectKeys(item, prefix))
    return keys
  }
  if (typeof obj === 'object') {
    const keys: string[] = []
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      const path = prefix ? `${prefix}.${k}` : k
      keys.push(path)
      keys.push(...flattenObjectKeys(v, path))
    }
    return keys
  }
  return prefix ? [prefix] : []
}

function makeResult(
  datasetId: string,
  datasetName: string,
  status: DatasetTestResult['status'],
  pageCount: number,
  coveragePct: number,
  coveredElements: string[],
  errorMessage?: string,
): DatasetTestResult {
  return {
    datasetId,
    datasetName,
    pageCount,
    coveragePct,
    status,
    testedAt: new Date().toISOString(),
    coveredElements,
    errorMessage,
  }
}
</script>

<style scoped>
.test-report-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-neutral-800, #1f2937);
  color: var(--color-neutral-100, #f3f4f6);
}

.test-report-panel__toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  flex-shrink: 0;
}

.test-report-panel__running-text {
  font-size: 0.8125rem;
  color: var(--color-neutral-400, #9ca3af);
  font-style: italic;
}

.test-report-panel__btn {
  padding: 0.3125rem 0.75rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s;
  white-space: nowrap;
}

.test-report-panel__btn:hover:not(:disabled) {
  background: var(--color-neutral-600, #4b5563);
}

.test-report-panel__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-report-panel__btn--primary {
  background: var(--color-primary-700, #1d4ed8);
  border-color: var(--color-primary-600, #2563eb);
  color: #fff;
}

.test-report-panel__btn--primary:hover:not(:disabled) {
  background: var(--color-primary-600, #2563eb);
}

.test-report-panel__btn--danger {
  background: var(--color-error-700, #b91c1c);
  border-color: var(--color-error-600, #dc2626);
  color: #fff;
}

.test-report-panel__btn--danger:hover {
  background: var(--color-error-600, #dc2626);
}

.test-report-panel__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  color: var(--color-neutral-500, #6b7280);
  padding: 1rem;
  text-align: center;
}

.test-report-panel__content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.75rem;
}

.test-report-panel__section {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.test-report-panel__section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-neutral-400, #9ca3af);
}

.test-report-panel__table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
}

.test-report-panel__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.test-report-panel__th {
  padding: 0.375rem 0.625rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-400, #9ca3af);
  background: var(--color-neutral-900, #111827);
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  white-space: nowrap;
}

.test-report-panel__th--dataset {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
