<template>
  <div class="detail-card detail-card--warning" role="alert" aria-live="assertive">
    <div class="detail-card__header">
      <div class="detail-card__label detail-card__label--yellow">Ação necessária</div>
      <div class="detail-card__title-row">
        <div class="detail-card__pulse detail-card__pulse--yellow" aria-hidden="true" />
        <h2 class="detail-card__title">{{ checkpoint.stageName }} — Revisão</h2>
      </div>
      <p class="detail-card__subtitle">O sistema precisa da sua confirmação antes de continuar</p>
    </div>

    <div class="checkpoint-content">
      <p class="checkpoint-content__desc">{{ checkpoint.message }}</p>

      <!-- Thumbnails -->
      <div
        v-if="checkpoint.layouts && checkpoint.layouts.length > 0"
        class="checkpoint-thumbs"
        role="group"
        aria-label="Layouts detectados"
      >
        <div
          v-for="layout in checkpoint.layouts"
          :key="layout.id"
          class="thumb"
          :class="{ 'thumb--similar': layout.similar }"
          tabindex="0"
          role="button"
          :aria-label="`${layout.label} — ${layout.pageCount} páginas${layout.similar ? ', similar' : ''}`"
        >
          <div class="thumb__img" aria-hidden="true">&#x1F4C4;</div>
          <div class="thumb__label">{{ layout.label }}</div>
          <div class="thumb__sub">{{ layout.pageCount }} páginas</div>
        </div>
      </div>

      <!-- System suggestion -->
      <div v-if="checkpoint.suggestion" class="checkpoint-suggestion">
        <span aria-hidden="true">&#x1F4A1;</span>
        <span> <strong>Sugestão do sistema:</strong> {{ checkpoint.suggestion.text }} </span>
      </div>

      <!-- Actions -->
      <div class="checkpoint-actions">
        <button
          class="btn btn--primary"
          :disabled="isSubmitting"
          @click="$emit('action', 'fallback')"
        >
          <span v-if="isSubmitting" class="btn-spinner" aria-hidden="true" />
          <span v-else>&#x2713;</span>
          Aceitar sugestão
        </button>
        <button
          class="btn btn--secondary"
          :disabled="isSubmitting"
          @click="$emit('action', 'retry')"
        >
          Manter {{ checkpoint.layouts?.length ?? 0 }} layouts
        </button>
        <button class="btn btn--ghost" :disabled="isSubmitting" @click="$emit('action', 'abort')">
          Pular revisão
        </button>
        <span
          class="checkpoint-timeout"
          aria-live="polite"
          :aria-label="`Tempo restante para ação automática: ${formattedTime}`"
        >
          &#x23F1; Continua automaticamente em <strong>{{ formattedTime }}</strong>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import type { CheckpointData } from '@/pages/analyzingPageConstantsV2'

const props = defineProps<{
  checkpoint: CheckpointData
  visible: boolean
  isSubmitting?: boolean
}>()

defineEmits<{
  action: [action: 'retry' | 'fallback' | 'abort']
}>()

const remainingSeconds = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const formattedTime = computed(() => {
  const mins = Math.floor(remainingSeconds.value / 60)
  const secs = remainingSeconds.value % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
})

watch(
  () => props.visible,
  (val) => {
    if (val) {
      remainingSeconds.value = props.checkpoint.timeoutSeconds || 300
      countdownTimer = setInterval(() => {
        remainingSeconds.value--
        if (remainingSeconds.value <= 0 && countdownTimer) {
          clearInterval(countdownTimer)
          countdownTimer = null
        }
      }, 1000)
    } else if (countdownTimer) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.detail-card {
  background: #fff;
  border-radius: 14px;
  padding: 0;
  box-shadow: 0 2px 16px rgba(99, 102, 241, 0.06);
  margin-bottom: 20px;
  overflow: hidden;
}

.detail-card--warning {
  border: 1.5px solid #fcd34d;
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

.detail-card__label--yellow {
  color: #b45309;
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

.detail-card__pulse--yellow {
  background: #f59e0b;
  animation: pulse-dot-yellow 1.5s ease-in-out infinite;
}

@keyframes pulse-dot-yellow {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(245, 158, 11, 0);
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

.checkpoint-content {
  padding: 0 28px 24px;
}

.checkpoint-content__desc {
  font-size: 14px;
  color: #475569;
  margin-bottom: 18px;
  line-height: 1.6;
}

.checkpoint-thumbs {
  display: flex;
  gap: 14px;
  margin-bottom: 18px;
}

.thumb {
  background: #f1f5f9;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  text-align: center;
  flex: 1;
  transition: all 0.15s;
  cursor: pointer;
}

.thumb:hover {
  border-color: #818cf8;
  background: #f5f3ff;
}

.thumb:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
  border-radius: 10px;
}

.thumb--similar {
  border-color: #fbbf24;
}

.thumb__img {
  width: 100%;
  height: 80px;
  background: linear-gradient(135deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  border-radius: 6px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #64748b;
}

.thumb__label {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}

.thumb__sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.checkpoint-suggestion {
  background: #eff6ff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 18px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: #1e40af;
  line-height: 1.5;
}

.checkpoint-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.btn:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: btn-spin 0.7s linear infinite;
  vertical-align: middle;
}

@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
}

.btn--primary {
  background: #2563eb;
  color: #fff;
}

.btn--primary:hover {
  background: #1d4ed8;
}

.btn--secondary {
  background: #fff;
  color: #475569;
  border: 1.5px solid #e2e8f0;
}

.btn--secondary:hover {
  background: #f8fafc;
}

.btn--ghost {
  background: transparent;
  color: #64748b;
  padding: 10px 14px;
}

.btn--ghost:hover {
  color: #475569;
}

.checkpoint-timeout {
  font-size: 12px;
  color: #64748b;
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 5px;
}
</style>
