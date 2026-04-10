import { onMounted, onUnmounted, watch, type Ref, nextTick } from 'vue'

/**
 * Story 40.5 — A11Y-001: Lightweight focus trap for modals.
 *
 * Traps Tab/Shift+Tab navigation within a container element.
 * Activates when `active` becomes true, deactivates when false.
 *
 * @param containerRef - Ref to the trap container element
 * @param active - Ref<boolean> controlling activation
 */
export function useFocusTrap(containerRef: Ref<HTMLElement | null>, active: Ref<boolean>) {
  let previouslyFocused: HTMLElement | null = null

  const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ')

  function getFocusableElements(): HTMLElement[] {
    if (!containerRef.value) return []
    return Array.from(containerRef.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key !== 'Tab') return

    const focusable = getFocusableElements()
    if (focusable.length === 0) return

    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
  }

  function activate() {
    previouslyFocused = document.activeElement as HTMLElement | null
    nextTick(() => {
      const focusable = getFocusableElements()
      if (focusable.length > 0) {
        focusable[0].focus()
      } else {
        containerRef.value?.focus()
      }
    })
    document.addEventListener('keydown', handleKeyDown)
  }

  function deactivate() {
    document.removeEventListener('keydown', handleKeyDown)
    if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
      previouslyFocused.focus()
    }
    previouslyFocused = null
  }

  watch(active, (isActive) => {
    if (isActive) {
      activate()
    } else {
      deactivate()
    }
  })

  onMounted(() => {
    if (active.value) activate()
  })

  onUnmounted(() => {
    deactivate()
  })
}
