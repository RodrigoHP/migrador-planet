<template>
  <Transition name="toast">
    <div
      v-if="visible"
      class="app-toast"
      :class="`app-toast--${variant}`"
      role="alert"
      aria-live="polite"
    >
      <span class="app-toast__icon" aria-hidden="true">{{ icon }}</span>
      <span class="app-toast__message">{{ message }}</span>
      <button
        class="app-toast__close"
        type="button"
        aria-label="Fechar notificação"
        @click="dismiss"
      >
        ✕
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'

const props = withDefaults(
  defineProps<{
    message: string
    variant?: 'success' | 'warning' | 'error' | 'neutral'
    duration?: number
  }>(),
  {
    variant: 'neutral',
    duration: 4000,
  },
)

const emit = defineEmits<{
  dismiss: []
}>()

const visible = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

const icon = computed(() => {
  const icons = { success: '✓', warning: '⚠', error: '✕', neutral: 'ℹ' }
  return icons[props.variant]
})

function show() {
  visible.value = true
  scheduleAutoDismiss()
}

function dismiss() {
  visible.value = false
  emit('dismiss')
  clearTimeout(timer!)
}

function scheduleAutoDismiss() {
  clearTimeout(timer!)
  timer = setTimeout(dismiss, props.duration)
}

watch(() => props.message, (msg) => {
  if (msg) show()
}, { immediate: true })

onUnmounted(() => clearTimeout(timer!))

defineExpose({ show, dismiss })
</script>

<style scoped>
.app-toast {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  font-size: 0.875rem;
  font-weight: 500;
  z-index: 100;
  min-width: 280px;
  max-width: 400px;
}

.app-toast--success { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.app-toast--warning { background: #fefce8; color: #a16207; border: 1px solid #fef08a; }
.app-toast--error   { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.app-toast--neutral { background: #f5f5f5; color: #404040; border: 1px solid #e5e5e5; }

.app-toast__icon { font-size: 1rem; flex-shrink: 0; }
.app-toast__message { flex: 1; }

.app-toast__close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.6;
  padding: 0;
  font-size: 0.875rem;
  line-height: 1;
  flex-shrink: 0;
}
.app-toast__close:hover { opacity: 1; }

.toast-enter-active,
.toast-leave-active { transition: all 150ms ease; }
.toast-enter-from,
.toast-leave-to { opacity: 0; transform: translateY(0.5rem); }
</style>
