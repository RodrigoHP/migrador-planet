import { onUnmounted } from 'vue'
import type { Ref } from 'vue'

/**
 * Composable that calls `callback` whenever a click event occurs outside
 * the element referenced by `elementRef`.
 *
 * Cleanup happens automatically on component unmount.
 */
export function useClickOutside(elementRef: Ref<HTMLElement | null>, callback: () => void): void {
  function handleClick(event: MouseEvent) {
    if (!elementRef.value) return
    if (!elementRef.value.contains(event.target as Node)) {
      callback()
    }
  }

  document.addEventListener('mousedown', handleClick)

  onUnmounted(() => {
    document.removeEventListener('mousedown', handleClick)
  })
}
