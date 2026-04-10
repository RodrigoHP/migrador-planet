import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Story 40.5 — UX-007: Guard against losing unsaved changes.
 *
 * Tracks a dirty flag and installs a `beforeunload` handler
 * that warns the user when they try to close/reload the tab
 * with pending changes.
 *
 * Usage:
 *   const { markDirty, markClean, isDirty } = useUnsavedChanges()
 *   // After any edit: markDirty()
 *   // After save:     markClean()
 */
export function useUnsavedChanges() {
  const isDirty = ref(false)

  function markDirty() {
    isDirty.value = true
  }

  function markClean() {
    isDirty.value = false
  }

  function onBeforeUnload(e: BeforeUnloadEvent) {
    if (isDirty.value) {
      e.preventDefault()
      // Modern browsers ignore custom messages but still show a default prompt
      e.returnValue = 'Voce tem alteracoes nao salvas. Deseja sair?'
    }
  }

  onMounted(() => {
    window.addEventListener('beforeunload', onBeforeUnload)
  })

  onUnmounted(() => {
    window.removeEventListener('beforeunload', onBeforeUnload)
  })

  return { isDirty, markDirty, markClean }
}

/**
 * Shared dirty flag for router guard consumption.
 * This is a module-level singleton so the router guard (which runs
 * outside of component scope) can check if there are unsaved changes.
 */
export const globalDirtyFlag = ref(false)

export function setGlobalDirty(dirty: boolean) {
  globalDirtyFlag.value = dirty
}
