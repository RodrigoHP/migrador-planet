<template>
  <tr class="coverage-matrix-row" data-testid="coverage-matrix-row">
    <td class="coverage-matrix-row__cell coverage-matrix-row__element">
      {{ entry.elementLabel }}
    </td>
    <td
      v-for="datasetId in datasetIds"
      :key="datasetId"
      class="coverage-matrix-row__cell coverage-matrix-row__check"
      :class="entry.coverageByDataset[datasetId] ? 'coverage-matrix-row__check--yes' : 'coverage-matrix-row__check--no'"
    >
      <span
        :title="entry.coverageByDataset[datasetId] ? 'Coberto' : 'Não coberto'"
        :data-testid="entry.coverageByDataset[datasetId] ? 'coverage-yes' : 'coverage-no'"
      >
        {{ entry.coverageByDataset[datasetId] ? '✓' : '✕' }}
      </span>
    </td>
  </tr>
</template>

<script setup lang="ts">
import type { CoverageMatrixEntry } from '@/stores/testReportStore'

defineProps<{
  entry: CoverageMatrixEntry
  datasetIds: string[]
}>()
</script>

<style scoped>
.coverage-matrix-row:hover {
  background: var(--color-neutral-700, #374151);
}

.coverage-matrix-row__cell {
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  color: var(--color-neutral-300, #d1d5db);
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  white-space: nowrap;
}

.coverage-matrix-row__element {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
  color: var(--color-neutral-200, #e5e7eb);
}

.coverage-matrix-row__check {
  text-align: center;
  font-weight: 700;
  font-size: 0.875rem;
}

.coverage-matrix-row__check--yes {
  color: var(--color-success-400, #4ade80);
}

.coverage-matrix-row__check--no {
  color: var(--color-error-400, #f87171);
}
</style>
