<template>
  <div class="stepper" role="list" aria-label="Progresso do pipeline">
    <div
      v-for="(stage, idx) in stages"
      :key="stage.stage"
      class="stepper__step"
      role="listitem"
      :aria-current="stepStates[idx] === 'active' ? 'step' : undefined"
    >
      <!-- Connector line (not on last step) -->
      <div v-if="idx < stages.length - 1" class="stepper__connector" :class="connectorClass(idx)" />

      <StepCircle :state="stepStates[idx]" :stage-number="stage.stage" />

      <span class="stepper__name" :class="`stepper__name--${stepStates[idx]}`">
        {{ stage.name }}
      </span>

      <span v-if="stage.stage in stageTimes" class="stepper__time">
        {{ formatTime(stageTimes[stage.stage]) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import StepCircle from './StepCircle.vue'
import type { StepCircleState, PipelineV2StageInfo } from '@/pages/analyzingPageConstantsV2'

const props = defineProps<{
  stages: readonly PipelineV2StageInfo[]
  stepStates: StepCircleState[]
  stageTimes: Record<number, number> // stage number -> elapsed seconds
}>()

function connectorClass(idx: number): string {
  const current = props.stepStates[idx]
  const next = props.stepStates[idx + 1]
  if (current === 'done' && (next === 'done' || next === 'active'))
    return 'stepper__connector--done'
  if (current === 'done' && next === 'error') return 'stepper__connector--error-transition'
  if (current === 'active') return 'stepper__connector--active'
  if (current === 'warning') return 'stepper__connector--warning'
  return ''
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}
</script>

<style scoped>
.stepper {
  display: flex;
  align-items: flex-start;
  margin-bottom: 32px;
  position: relative;
}

.stepper__step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
}

.stepper__connector {
  position: absolute;
  top: 20px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: #e2e8f0;
  z-index: 0;
}

.stepper__connector--done {
  background: #86efac;
}

.stepper__connector--active {
  background: linear-gradient(90deg, #86efac, #93c5fd);
}

.stepper__connector--error-transition {
  background: linear-gradient(90deg, #86efac, #fca5a5);
}

.stepper__connector--warning {
  background: linear-gradient(90deg, #fcd34d, #fcd34d);
}

.stepper__name {
  font-size: 11px;
  font-weight: 500;
  text-align: center;
  max-width: 110px;
  line-height: 1.3;
  margin-top: 10px;
}

.stepper__name--done {
  color: #15803d;
}
.stepper__name--active {
  color: #1d4ed8;
  font-weight: 600;
}
.stepper__name--pending {
  color: #64748b;
}
.stepper__name--error {
  color: #dc2626;
}
.stepper__name--warning {
  color: #b45309;
  font-weight: 600;
}

.stepper__time {
  font-size: 10px;
  color: #64748b;
  margin-top: 3px;
}
</style>
