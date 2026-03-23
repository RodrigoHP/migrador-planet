<template>
  <div class="step-circle" :class="stateClass" :aria-label="ariaLabel">
    <div v-if="state === 'active'" class="step-circle__spinner" aria-hidden="true" />
    <span v-else-if="state === 'done'">&#x2713;</span>
    <span v-else-if="state === 'error'">&#x2717;</span>
    <span v-else-if="state === 'warning'">&#x26A0;</span>
    <span v-else class="step-circle__number">{{ stageNumber }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StepCircleState } from '@/pages/analyzingPageConstantsV2'

const props = defineProps<{
  state: StepCircleState
  stageNumber: number
}>()

const stateClass = computed(() => `step-circle--${props.state}`)

const ariaLabel = computed(() => {
  switch (props.state) {
    case 'done': return 'Concluído'
    case 'active': return 'Em andamento'
    case 'error': return 'Erro'
    case 'warning': return 'Ação necessária'
    default: return 'Pendente'
  }
})
</script>

<style scoped>
.step-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  position: relative;
  transition: all 0.3s;
  flex-shrink: 0;
}

.step-circle--done {
  background: #dcfce7;
  color: #15803d;
  border: 2px solid #86efac;
}

.step-circle--active {
  background: #2563eb;
  color: #fff;
  border: 2px solid #2563eb;
  animation: pulse-ring 2s ease-in-out infinite;
}

.step-circle--pending {
  background: #f1f5f9;
  color: #64748b;
  border: 2px solid #cbd5e1;
}

.step-circle--error {
  background: #fef2f2;
  color: #ef4444;
  border: 2px solid #fca5a5;
}

.step-circle--warning {
  background: #fffbeb;
  color: #f59e0b;
  border: 2px solid #fcd34d;
  animation: pulse-warning 2s ease-in-out infinite;
}

.step-circle__number {
  color: #64748b;
}

.step-circle__spinner {
  width: 18px;
  height: 18px;
  border: 2.5px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes pulse-ring {
  0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.3); }
  70% { box-shadow: 0 0 0 8px rgba(37, 99, 235, 0); }
  100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
}

@keyframes pulse-warning {
  0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.3); }
  70% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
  100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
