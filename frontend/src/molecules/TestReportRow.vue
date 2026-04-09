<template>
  <tr
    class="test-report-row"
    :class="`test-report-row--${result.status}`"
    data-testid="test-report-row"
  >
    <td class="test-report-row__cell test-report-row__name">
      {{ result.datasetName }}
    </td>
    <td class="test-report-row__cell test-report-row__pages">
      {{ result.pageCount }}
    </td>
    <td class="test-report-row__cell test-report-row__coverage">
      <span class="test-report-row__coverage-bar">
        <span class="test-report-row__coverage-fill" :style="{ width: `${result.coveragePct}%` }" />
      </span>
      <span class="test-report-row__coverage-pct">{{ result.coveragePct }}%</span>
    </td>
    <td class="test-report-row__cell test-report-row__status">
      <span
        class="test-report-row__status-badge"
        :class="`test-report-row__status-badge--${result.status}`"
        :title="result.errorMessage"
      >
        {{ statusIcon }} {{ statusLabel }}
      </span>
    </td>
  </tr>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DatasetTestResult } from '@/stores/testReportStore'

const props = defineProps<{
  result: DatasetTestResult
}>()

const statusIcon = computed(() => {
  switch (props.result.status) {
    case 'ok':
      return '✓'
    case 'warning':
      return '⚠'
    case 'error':
      return '❌'
    case 'timeout':
      return '⚠'
    case 'cancelled':
      return '–'
    default:
      return '?'
  }
})

const statusLabel = computed(() => {
  switch (props.result.status) {
    case 'ok':
      return 'OK'
    case 'warning':
      return 'Aviso'
    case 'error':
      return 'Erro'
    case 'timeout':
      return 'Timeout'
    case 'cancelled':
      return 'Cancelado'
    default:
      return 'Pendente'
  }
})
</script>

<style scoped>
.test-report-row {
  transition: background 0.1s;
}

.test-report-row:hover {
  background: var(--color-neutral-700, #374151);
}

.test-report-row__cell {
  padding: 0.375rem 0.625rem;
  font-size: 0.8125rem;
  color: var(--color-neutral-200, #e5e7eb);
  white-space: nowrap;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.test-report-row__name {
  font-weight: 500;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.test-report-row__coverage {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.test-report-row__coverage-bar {
  flex: 1;
  height: 6px;
  background: var(--color-neutral-700, #374151);
  border-radius: 3px;
  overflow: hidden;
  min-width: 60px;
  display: inline-block;
}

.test-report-row__coverage-fill {
  display: block;
  height: 100%;
  background: var(--color-primary-500, #3b82f6);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.test-report-row__coverage-pct {
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
  min-width: 2.5rem;
  text-align: right;
}

/* Status badge */
.test-report-row__status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.test-report-row__status-badge--ok {
  background: var(--color-success-900, #14532d);
  color: var(--color-success-300, #86efac);
}

.test-report-row__status-badge--warning,
.test-report-row__status-badge--timeout {
  background: var(--color-warning-900, #78350f);
  color: var(--color-warning-300, #fcd34d);
}

.test-report-row__status-badge--error {
  background: var(--color-error-900, #7f1d1d);
  color: var(--color-error-300, #fca5a5);
}

.test-report-row__status-badge--cancelled,
.test-report-row__status-badge--pending {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-400, #9ca3af);
}
</style>
