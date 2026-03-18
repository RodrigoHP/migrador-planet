import { ref } from 'vue'
import type { Ref } from 'vue'

export interface UseSyncReturn {
  scrollLocked: Ref<boolean>
  selectedElementId: Ref<string | null>
  syncScroll: (sourcePanel: HTMLElement, targetPanel: HTMLElement) => void
  syncSelection: (canvasElementId: string) => void
  toggleScrollLock: () => void
  clearSelection: () => void
}

/**
 * Composable for synchronizing scroll and selection between Canvas and PDF panels.
 * Uses proportional mapping: scrollRatio = scrollTop / (scrollHeight - clientHeight)
 */
export function useSync(): UseSyncReturn {
  const scrollLocked = ref<boolean>(true)
  const selectedElementId = ref<string | null>(null)

  // Guard to prevent recursive scroll sync
  let isSyncing = false

  /**
   * Maps proportional scroll position from source panel to target panel.
   * scrollRatio = scrollTop / max(1, scrollHeight - clientHeight)
   */
  function syncScroll(sourcePanel: HTMLElement, targetPanel: HTMLElement): void {
    if (!scrollLocked.value || isSyncing) return

    const sourceMax = sourcePanel.scrollHeight - sourcePanel.clientHeight
    if (sourceMax <= 0) return

    const ratio = sourcePanel.scrollTop / sourceMax

    const targetMax = targetPanel.scrollHeight - targetPanel.clientHeight
    if (targetMax <= 0) return

    isSyncing = true
    targetPanel.scrollTop = ratio * targetMax
    // Reset after the browser processes the scroll
    requestAnimationFrame(() => {
      isSyncing = false
    })
  }

  /**
   * Records which canvas element was clicked (for cross-panel highlight).
   * Consumers can watch selectedElementId to highlight corresponding PDF bounding box.
   */
  function syncSelection(canvasElementId: string): void {
    selectedElementId.value = canvasElementId
  }

  function toggleScrollLock(): void {
    scrollLocked.value = !scrollLocked.value
  }

  function clearSelection(): void {
    selectedElementId.value = null
  }

  return {
    scrollLocked,
    selectedElementId,
    syncScroll,
    syncSelection,
    toggleScrollLock,
    clearSelection,
  }
}
