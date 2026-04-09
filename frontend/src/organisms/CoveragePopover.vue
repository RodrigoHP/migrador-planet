<template>
  <div
    v-if="visible"
    ref="popoverRef"
    class="coverage-popover"
    role="dialog"
    aria-label="Detalhamento de Cobertura"
    data-testid="coverage-popover"
  >
    <!-- Overall header -->
    <div class="coverage-popover__header">
      <span class="coverage-popover__overall-label">Cobertura Geral:</span>
      <span class="coverage-popover__overall-value" :class="overallColorClass">
        {{ overall !== undefined ? `${Math.round(overall)}%` : '--' }}
        {{ overallIcon }}
      </span>
    </div>

    <div class="coverage-popover__divider" aria-hidden="true" />

    <!-- 4 breakdown rows -->
    <div v-if="coverage" class="coverage-popover__breakdown">
      <CoverageBreakdown
        icon="📋"
        label="Campos"
        :mapped="coverage.fields.mapped"
        :total="coverage.fields.total"
      />
      <CoverageBreakdown
        icon="📊"
        label="Tabelas"
        :mapped="coverage.tables.mapped"
        :total="coverage.tables.total"
      />
      <CoverageBreakdown
        icon="🖼"
        label="Imagens"
        :mapped="coverage.images.mapped"
        :total="coverage.images.total"
      />
      <CoverageBreakdown
        icon="📈"
        label="Gráficos"
        :mapped="coverage.charts.mapped"
        :total="coverage.charts.total"
      />
    </div>
    <div v-else class="coverage-popover__empty">Nenhum dado de cobertura disponível.</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCoverageStore } from '@/stores/coverageStore'
import { useLayoutStore } from '@/stores/layout'
import { useClickOutside } from '@/composables/useClickOutside'
import CoverageBreakdown from '@/molecules/CoverageBreakdown.vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const popoverRef = ref<HTMLElement | null>(null)
const coverageStore = useCoverageStore()
const layoutStore = useLayoutStore()

const coverage = computed(() => {
  const id = layoutStore.activeLayoutId
  if (!id) return undefined
  return coverageStore.getForLayout(id)
})

const overall = computed(() => coverage.value?.percentage)

const overallIcon = computed(() => {
  if (overall.value === undefined) return ''
  if (overall.value >= 95) return '✅'
  if (overall.value >= 80) return '⚠️'
  return '🔴'
})

const overallColorClass = computed(() => {
  if (overall.value === undefined) return ''
  if (overall.value >= 95) return 'coverage-popover__overall-value--green'
  if (overall.value >= 80) return 'coverage-popover__overall-value--yellow'
  return 'coverage-popover__overall-value--red'
})

useClickOutside(popoverRef, () => {
  if (props.visible) {
    emit('close')
  }
})
</script>

<style scoped>
.coverage-popover {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  z-index: 100;
  min-width: 260px;
  background: #ffffff;
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  border-radius: 0.5rem;
  box-shadow:
    0 10px 15px -3px rgba(0, 0, 0, 0.1),
    0 4px 6px -4px rgba(0, 0, 0, 0.1);
  padding: 0.75rem;
}

.coverage-popover__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.coverage-popover__overall-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-800, #1f2937);
}

.coverage-popover__overall-value {
  font-size: 0.875rem;
  font-weight: 700;
}

.coverage-popover__overall-value--green {
  color: #166534;
}
.coverage-popover__overall-value--yellow {
  color: #854d0e;
}
.coverage-popover__overall-value--red {
  color: #991b1b;
}

.coverage-popover__divider {
  height: 1px;
  background: var(--color-neutral-200, #e5e7eb);
  margin-bottom: 0.625rem;
}

.coverage-popover__breakdown {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.coverage-popover__empty {
  font-size: 0.75rem;
  color: var(--color-neutral-500, #6b7280);
  text-align: center;
  padding: 0.5rem 0;
}
</style>
