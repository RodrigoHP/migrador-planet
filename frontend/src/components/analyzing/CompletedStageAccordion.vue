<template>
  <div class="completed-stages">
    <div class="completed-stages__label">{{ label }}</div>
    <div
      v-for="stage in stages"
      :key="stage.stage"
      class="accordion"
      :class="{ 'accordion--open': expandedStages.has(stage.stage) }"
      tabindex="0"
      role="button"
      :aria-expanded="expandedStages.has(stage.stage)"
      @click="toggle(stage.stage)"
      @keydown="handleKey($event, stage.stage)"
    >
      <div class="accordion__header">
        <div class="accordion__icon accordion__icon--done">&#x2713;</div>
        <span class="accordion__name">{{ stage.name }}</span>
        <span class="accordion__summary">{{ stage.shortSummary }}</span>
        <span class="accordion__time">{{ formatTime(stage.elapsedSeconds) }}</span>
        <span class="accordion__expand" :class="{ 'accordion__expand--open': expandedStages.has(stage.stage) }">&#x25B8;</span>
      </div>
      <div v-if="expandedStages.has(stage.stage)" class="accordion__body" @click.stop>
        <div class="accordion__detail-grid">
          <div v-for="(detail, idx) in stage.details" :key="idx" class="accordion__detail">
            <span class="accordion__detail-dot" />
            {{ detail }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { CompletedStageSummary } from '@/pages/analyzingPageConstantsV2'

defineProps<{
  stages: CompletedStageSummary[]
  label?: string
}>()

const expandedStages = ref<Set<number>>(new Set())

function toggle(stage: number) {
  if (expandedStages.value.has(stage)) {
    expandedStages.value.delete(stage)
  } else {
    expandedStages.value.add(stage)
  }
  // Force reactivity
  expandedStages.value = new Set(expandedStages.value)
}

function handleKey(event: KeyboardEvent, stage: number) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggle(stage)
  }
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}
</script>

<style scoped>
.completed-stages {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.completed-stages__label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 2px;
}

.accordion {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s;
  cursor: pointer;
}

.accordion:hover {
  border-color: #c7d2fe;
}

.accordion:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
  border-radius: 10px;
}

.accordion__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
}

.accordion__icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.accordion__icon--done {
  background: #dcfce7;
  color: #15803d;
}

.accordion__name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  flex: 1;
}

.accordion__summary {
  font-size: 12px;
  color: #64748b;
}

.accordion__time {
  font-size: 11px;
  color: #64748b;
}

.accordion__expand {
  font-size: 12px;
  color: #64748b;
  transition: transform 0.2s;
}

.accordion__expand--open {
  transform: rotate(90deg);
}

.accordion__body {
  padding: 0 20px 16px 58px;
}

.accordion__detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.accordion__detail {
  font-size: 12px;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 6px;
}

.accordion__detail-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #86efac;
  flex-shrink: 0;
}
</style>
