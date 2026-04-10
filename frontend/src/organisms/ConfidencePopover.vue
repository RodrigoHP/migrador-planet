<template>
  <div
    v-if="visible"
    ref="popoverRef"
    class="confidence-popover"
    role="dialog"
    aria-label="Detalhamento de Confiança"
    data-testid="confidence-popover"
  >
    <!-- Overall header -->
    <div class="confidence-popover__header">
      <span class="confidence-popover__overall-label">Confiança Geral:</span>
      <span class="confidence-popover__overall-value" :class="overallColorClass">
        {{ overall !== undefined ? `${Math.round(overall)}%` : '--' }}
        {{ overallIcon }}
      </span>
    </div>

    <div class="confidence-popover__divider" aria-hidden="true" />

    <!-- 5 factors -->
    <div v-if="factors" class="confidence-popover__factors">
      <ConfidenceFactor label="Estabilidade de Layout" :value="factors.layout_stability" />
      <ConfidenceFactor label="Detecção de Âncoras" :value="factors.anchor_detection" />
      <ConfidenceFactor label="Qualidade do Grid" :value="factors.grid_quality" />
      <ConfidenceFactor label="Variabilidade de Campos" :value="factors.field_variability" />
      <ConfidenceFactor label="Concordância da Visão" :value="factors.vision_agreement" />
    </div>
    <div v-else class="confidence-popover__empty">Nenhum dado de confiança disponível.</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useLayoutStore } from '@/stores/layout'
import { useClickOutside } from '@/composables/useClickOutside'
import ConfidenceFactor from '@/molecules/ConfidenceFactor.vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const popoverRef = ref<HTMLElement | null>(null)
const confidenceStore = useConfidenceStore()
const layoutStore = useLayoutStore()

const factors = computed(() => {
  const id = layoutStore.activeLayoutId
  if (!id) return undefined
  return confidenceStore.getForLayout(id)
})

const overall = computed(() => factors.value?.overall)

const overallIcon = computed(() => {
  if (overall.value === undefined) return ''
  if (overall.value >= 95) return '✅'
  if (overall.value >= 80) return '⚠️'
  return '🔴'
})

const overallColorClass = computed(() => {
  if (overall.value === undefined) return ''
  if (overall.value >= 95) return 'confidence-popover__overall-value--green'
  if (overall.value >= 80) return 'confidence-popover__overall-value--yellow'
  return 'confidence-popover__overall-value--red'
})

useClickOutside(popoverRef, () => {
  if (props.visible) {
    emit('close')
  }
})
</script>

<style scoped>
.confidence-popover {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  z-index: 100;
  min-width: 280px;
  background: #ffffff;
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  border-radius: 0.5rem;
  box-shadow:
    0 10px 15px -3px rgba(0, 0, 0, 0.1),
    0 4px 6px -4px rgba(0, 0, 0, 0.1);
  padding: 0.75rem;
}

.confidence-popover__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.confidence-popover__overall-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-800, #1f2937);
}

.confidence-popover__overall-value {
  font-size: 0.875rem;
  font-weight: 700;
}

.confidence-popover__overall-value--green {
  color: #166534;
}
.confidence-popover__overall-value--yellow {
  color: #854d0e;
}
.confidence-popover__overall-value--red {
  color: #991b1b;
}

.confidence-popover__divider {
  height: 1px;
  background: var(--color-neutral-200, #e5e7eb);
  margin-bottom: 0.625rem;
}

.confidence-popover__factors {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.confidence-popover__empty {
  font-size: 0.75rem;
  color: var(--color-neutral-500, #525252);
  text-align: center;
  padding: 0.5rem 0;
}
</style>
