<template>
  <div class="summary-card">
    <div class="summary-card__header">
      <div class="summary-card__check" aria-hidden="true">&#x2713;</div>
      <div>
        <h2 class="summary-card__title">Análise concluída!</h2>
        <p class="summary-card__subtitle">
          Documento processado em {{ formatTotalTime(summary.totalTimeSeconds) }} — pronto para
          edição
        </p>
      </div>
    </div>

    <!-- 4-metric grid -->
    <div class="summary-grid">
      <div class="summary-stat">
        <div class="summary-stat__value">{{ formatTotalTime(summary.totalTimeSeconds) }}</div>
        <div class="summary-stat__label">Tempo Total</div>
      </div>
      <div class="summary-stat">
        <div
          class="summary-stat__value"
          :title="
            summary.visionAiUsed === false
              ? 'Vision AI desabilitado — análise em qualidade reduzida (~75%)'
              : undefined
          "
        >
          {{ summary.visionAiUsed === false ? 'N/A' : formatCostBRL(summary.apiCostEstimate ?? 0) }}
        </div>
        <div class="summary-stat__label">Custo API</div>
      </div>
      <div class="summary-stat">
        <div class="summary-stat__value">{{ summary.layoutCount }}</div>
        <div class="summary-stat__label">Layouts</div>
      </div>
      <div class="summary-stat">
        <div class="summary-stat__value">{{ summary.pageCount }}</div>
        <div class="summary-stat__label">Páginas</div>
      </div>
    </div>

    <!-- Coverage -->
    <div v-if="summary.coverageTotal != null" class="summary-coverage">
      <div class="summary-coverage__header">
        <span class="summary-coverage__title">Cobertura do Template</span>
        <span class="summary-coverage__total">{{ summary.coverageTotal }}%</span>
      </div>
      <div v-if="summary.coverageBreakdown" class="summary-coverage__breakdown">
        <div v-for="item in summary.coverageBreakdown" :key="item.label" class="coverage-item">
          {{ item.label }} {{ item.pct }}%
          <div class="coverage-bar-mini">
            <div class="coverage-bar-mini__fill" :style="{ width: `${item.pct}%` }" />
          </div>
        </div>
      </div>
    </div>

    <!-- Warnings -->
    <div
      v-if="summary.warnings && summary.warnings.length > 0"
      class="summary-warnings"
      role="alert"
    >
      <span aria-hidden="true">&#x26A0;&#xFE0F;</span>
      <div class="summary-warnings__text">
        <p v-for="(w, idx) in summary.warnings" :key="idx">{{ w }}</p>
      </div>
    </div>

    <!-- CTA Button -->
    <button class="btn-editor" @click="$emit('open-editor')">Abrir no Editor</button>
  </div>
</template>

<script setup lang="ts">
import type { CompletedSummaryData } from '@/pages/analyzingPageConstantsV2'
import { USD_TO_BRL_RATE } from '@/pages/analyzingPageConstantsV2'

defineProps<{
  summary: CompletedSummaryData
}>()

defineEmits<{
  'open-editor': []
}>()

function formatTotalTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (secs === 0) return `${mins} min`
  return `${mins} min ${secs} seg`
}

function formatCostBRL(usdValue: number): string {
  const brl = usdValue * USD_TO_BRL_RATE
  return `R$ ${brl.toFixed(2).replace('.', ',')}`
}
</script>

<style scoped>
.summary-card {
  background: #fff;
  border: 1.5px solid #bbf7d0;
  border-radius: 14px;
  padding: 28px;
  box-shadow: 0 2px 16px rgba(34, 197, 94, 0.06);
  margin-bottom: 20px;
}

.summary-card__header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.summary-card__check {
  width: 44px;
  height: 44px;
  background: #dcfce7;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
  color: #15803d;
}

.summary-card__title {
  font-size: 22px;
  font-weight: 700;
  color: #15803d;
  margin: 0;
}

.summary-card__subtitle {
  font-size: 14px;
  color: #64748b;
  margin-top: 2px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.summary-stat {
  background: #f8faf9;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.summary-stat__value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.summary-stat__label {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 4px;
}

.summary-coverage {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 24px;
}

.summary-coverage__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.summary-coverage__title {
  font-size: 14px;
  font-weight: 600;
  color: #15803d;
}

.summary-coverage__total {
  font-size: 22px;
  font-weight: 700;
  color: #15803d;
}

.summary-coverage__breakdown {
  display: flex;
  gap: 20px;
}

.coverage-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #475569;
}

.coverage-bar-mini {
  width: 40px;
  height: 5px;
  background: #dcfce7;
  border-radius: 99px;
  overflow: hidden;
}

.coverage-bar-mini__fill {
  height: 100%;
  background: #22c55e;
  border-radius: 99px;
}

.summary-warnings {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 24px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.summary-warnings__text {
  font-size: 13px;
  color: #92400e;
  line-height: 1.5;
}

.summary-warnings__text p {
  margin: 0 0 4px;
}

.btn-editor {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  color: #fff;
  background: linear-gradient(135deg, #16a34a, #22c55e);
  box-shadow: 0 4px 14px rgba(34, 197, 94, 0.25);
  transition: all 0.2s;
}

.btn-editor:hover {
  box-shadow: 0 6px 20px rgba(34, 197, 94, 0.35);
  transform: translateY(-1px);
}

.btn-editor:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}
</style>
