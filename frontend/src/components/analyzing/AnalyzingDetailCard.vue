<template>
  <div class="detail-card" aria-live="polite">
    <div class="detail-card__header">
      <div class="detail-card__label detail-card__label--blue">
        Estágio {{ stageNumber }} de {{ totalStages }}
      </div>
      <div class="detail-card__title-row">
        <div class="detail-card__pulse detail-card__pulse--blue" aria-hidden="true" />
        <h2 class="detail-card__title">{{ stageName }}</h2>
      </div>
      <p class="detail-card__subtitle">{{ stageDescription }}</p>
    </div>

    <div class="detail-card__progress">
      <div class="progress-top">
        <span :id="progressLabelId" class="progress-top__sub">{{
          subStep || 'Processando...'
        }}</span>
        <span class="progress-top__pct">{{ Math.round(progressPct * 100) }}%</span>
      </div>
      <div
        class="progress-bar-bg"
        role="progressbar"
        :aria-valuenow="Math.round(progressPct * 100)"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-labelledby="progressLabelId"
      >
        <div class="progress-fill" :style="{ width: `${progressPct * 100}%` }" />
      </div>
      <div class="progress-footer">
        <span class="progress-footer__time">{{ estimatedTimeLabel }}</span>
        <span v-if="subStepPill" class="progress-footer__pill">{{ subStepPill }}</span>
      </div>
    </div>

    <!-- Contextual metrics -->
    <div v-if="metrics && metrics.length > 0" class="detail-card__metrics">
      <div v-for="m in metrics" :key="m.label" class="metric">
        <span class="metric__value">{{ m.value }}</span>
        <span class="metric__label">{{ m.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface MetricItem {
  value: string | number
  label: string
}

const props = defineProps<{
  stageNumber: number
  totalStages: number
  stageName: string
  stageDescription: string
  subStep: string
  progressPct: number
  subStepPill?: string
  estimatedTimeLabel?: string
  metrics?: MetricItem[]
}>()

const progressLabelId = computed(() => `progress-label-stage-${props.stageNumber}`)
</script>

<style scoped>
.detail-card {
  background: #fff;
  border-radius: 14px;
  border: 1.5px solid #e0e7ff;
  padding: 0;
  box-shadow: 0 2px 16px rgba(99, 102, 241, 0.06);
  margin-bottom: 20px;
  overflow: hidden;
}

.detail-card__header {
  padding: 22px 28px 0;
}

.detail-card__label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}

.detail-card__label--blue {
  color: #6366f1;
}

.detail-card__title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.detail-card__pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.detail-card__pulse--blue {
  background: #3b82f6;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(59, 130, 246, 0);
  }
}

.detail-card__title {
  font-size: 19px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.detail-card__subtitle {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 18px;
  padding-left: 24px;
}

.detail-card__progress {
  padding: 0 28px 20px;
}

.progress-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-top__sub {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.progress-top__pct {
  font-size: 14px;
  font-weight: 700;
  color: #6366f1;
}

.progress-bar-bg {
  background: #e0e7ff;
  border-radius: 99px;
  height: 7px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #818cf8);
  border-radius: 99px;
  transition: width 0.5s ease;
  animation: progress-glow 2s ease-in-out infinite;
}

@keyframes progress-glow {
  0% {
    opacity: 0.7;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.7;
  }
}

.progress-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.progress-footer__time {
  font-size: 12px;
  color: #64748b;
}

.progress-footer__pill {
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 16px;
}

.detail-card__metrics {
  padding: 0 28px 22px;
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric__value {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.metric__label {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
</style>
