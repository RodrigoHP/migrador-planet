<template>
  <div v-if="visible" ref="overlayRef" class="svc-failure-overlay">
    <div class="svc-failure-modal">
      <h2 class="svc-failure-modal__title">Falha de Servico — {{ checkpoint.service }}</h2>

      <div class="svc-failure-modal__details">
        <p class="svc-failure-modal__error"><strong>Erro:</strong> {{ checkpoint.error }}</p>
        <p class="svc-failure-modal__stage"><strong>Stage:</strong> {{ checkpoint.stage }}</p>
      </div>

      <div class="svc-failure-modal__fallback-info">
        <p class="svc-failure-modal__fallback-title">
          O que acontece se continuar sem {{ checkpoint.service }}:
        </p>
        <p
          v-for="(option, idx) in fallbackOptions"
          :key="idx"
          class="svc-failure-modal__fallback-desc"
        >
          {{ option.description }}
          <span v-if="option.warning" class="svc-failure-modal__warning">
            Impacto: {{ option.warning }}
          </span>
        </p>
      </div>

      <div class="svc-failure-modal__actions">
        <button
          class="svc-failure-modal__btn svc-failure-modal__btn--retry"
          @click="$emit('decide', 'retry')"
        >
          Tentar de novo
        </button>
        <button
          class="svc-failure-modal__btn svc-failure-modal__btn--fallback"
          @click="$emit('decide', 'fallback')"
        >
          Continuar sem {{ checkpoint.service }}
        </button>
        <button
          class="svc-failure-modal__btn svc-failure-modal__btn--abort"
          @click="$emit('decide', 'abort')"
        >
          Cancelar pipeline
        </button>
      </div>

      <p class="svc-failure-modal__timeout">
        Auto-continua sem {{ checkpoint.service }} em {{ formattedTimeout }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted, toRef } from 'vue'
import { useFocusTrap } from '@/composables/useFocusTrap'

export interface ServiceFailureCheckpoint {
  type: string
  service: string
  stage: string
  error: string
  options: Array<{
    action: string
    label: string
    description: string
    warning?: string
  }>
  timeout_seconds: number
  timeout_action: string
  message: string
}

const props = defineProps<{
  visible: boolean
  checkpoint: ServiceFailureCheckpoint
}>()

defineEmits<{
  decide: [action: 'retry' | 'fallback' | 'abort']
}>()

// Story 40.5 — A11Y-001: Focus trap
const overlayRef = ref<HTMLElement | null>(null)
useFocusTrap(overlayRef, toRef(props, 'visible'))

const remainingSeconds = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const fallbackOptions = computed(
  () => props.checkpoint.options?.filter((o) => o.action === 'fallback') ?? [],
)

const formattedTimeout = computed(() => {
  const mins = Math.floor(remainingSeconds.value / 60)
  const secs = remainingSeconds.value % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
})

watch(
  () => props.visible,
  (val) => {
    if (val) {
      remainingSeconds.value = props.checkpoint.timeout_seconds || 300
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
.svc-failure-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.svc-failure-modal {
  background: white;
  border-radius: 0.75rem;
  padding: 2rem;
  max-width: 36rem;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.svc-failure-modal__title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #b45309;
  margin-bottom: 1rem;
}

.svc-failure-modal__details {
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: #374151;
}

.svc-failure-modal__error,
.svc-failure-modal__stage {
  margin-bottom: 0.25rem;
}

.svc-failure-modal__fallback-info {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.svc-failure-modal__fallback-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: #92400e;
  margin-bottom: 0.5rem;
}

.svc-failure-modal__fallback-desc {
  font-size: 0.8125rem;
  color: #78350f;
  line-height: 1.5;
}

.svc-failure-modal__warning {
  display: block;
  margin-top: 0.25rem;
  font-style: italic;
  color: #b45309;
}

.svc-failure-modal__actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.svc-failure-modal__btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.svc-failure-modal__btn--retry {
  background: #2563eb;
  color: white;
}

.svc-failure-modal__btn--retry:hover {
  background: #1d4ed8;
}

.svc-failure-modal__btn--fallback {
  background: #f59e0b;
  color: white;
}

.svc-failure-modal__btn--fallback:hover {
  background: #d97706;
}

.svc-failure-modal__btn--abort {
  background: white;
  color: #dc2626;
  border-color: #dc2626;
}

.svc-failure-modal__btn--abort:hover {
  background: #fef2f2;
}

.svc-failure-modal__timeout {
  font-size: 0.75rem;
  color: #6b7280;
  text-align: center;
}
</style>
