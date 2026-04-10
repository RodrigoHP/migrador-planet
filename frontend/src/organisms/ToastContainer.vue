<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast"
          :class="`toast--${toast.type}`"
          role="status"
        >
          <span class="toast__icon" aria-hidden="true">{{ iconFor(toast.type) }}</span>
          <span class="toast__message">{{ toast.message }}</span>
          <button
            class="toast__dismiss"
            aria-label="Fechar notificacao"
            @click="toastStore.removeToast(toast.id)"
          >
            &times;
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useToastStore } from '@/stores/toastStore'
import type { ToastType } from '@/stores/toastStore'

const toastStore = useToastStore()
const toasts = computed(() => toastStore.activeToasts)

function iconFor(type: ToastType): string {
  switch (type) {
    case 'success':
      return '\u2714'
    case 'error':
      return '\u2716'
    case 'warning':
      return '\u26A0'
    case 'info':
    default:
      return '\u2139'
  }
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 24rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  pointer-events: auto;
}

.toast--info {
  background: #eff6ff;
  border: 1px solid #93c5fd;
  color: #1e40af;
}

.toast--success {
  background: #f0fdf4;
  border: 1px solid #86efac;
  color: #166534;
}

.toast--warning {
  background: #fffbeb;
  border: 1px solid #fcd34d;
  color: #92400e;
}

.toast--error {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #991b1b;
}

.toast__icon {
  flex-shrink: 0;
  font-size: 1rem;
}

.toast__message {
  flex: 1;
  line-height: 1.4;
}

.toast__dismiss {
  flex-shrink: 0;
  background: none;
  border: none;
  font-size: 1.125rem;
  cursor: pointer;
  opacity: 0.6;
  padding: 0 0.25rem;
  color: inherit;
  line-height: 1;
}

.toast__dismiss:hover {
  opacity: 1;
}

/* Transitions */
.toast-enter-active {
  transition: all 0.3s ease;
}

.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
