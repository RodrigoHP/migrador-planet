import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export type ToastType = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: string
  type: ToastType
  message: string
  /** Duration in ms. 0 = persistent (manual dismiss). Default: 5000 */
  duration: number
}

let _toastIdCounter = 0

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  const activeToasts = computed(() => toasts.value)

  function addToast(message: string, type: ToastType = 'info', duration = 5000): string {
    const id = `toast-${Date.now()}-${_toastIdCounter++}`
    const toast: Toast = { id, type, message, duration }
    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }

    return id
  }

  function removeToast(id: string) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function clearAll() {
    toasts.value = []
  }

  // Convenience methods
  function info(message: string, duration?: number) {
    return addToast(message, 'info', duration)
  }

  function success(message: string, duration?: number) {
    return addToast(message, 'success', duration)
  }

  function warning(message: string, duration?: number) {
    return addToast(message, 'warning', duration)
  }

  function error(message: string, duration?: number) {
    return addToast(message, 'error', duration ?? 8000)
  }

  return {
    toasts,
    activeToasts,
    addToast,
    removeToast,
    clearAll,
    info,
    success,
    warning,
    error,
  }
})
