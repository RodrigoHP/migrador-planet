/**
 * Story 40.6 — FE-002: Canvas zoom wheel handler.
 *
 * Wraps useCanvas zoom operations with the wheel event handler
 * that was previously inline in HTMLCanvas.vue.
 */
import { useCanvas } from '@/composables/useCanvas'

export function useCanvasZoom() {
  const {
    zoomLevel,
    visiblePages,
    scrollToPage,
    setupObserver,
    observePage,
    unobservePage,
    teardownObserver,
    isPageVisible,
    setZoom,
    ZOOM_STEP,
    ZOOM_MAX,
    ZOOM_MIN,
  } = useCanvas()

  /** Ctrl+Wheel zoom handler for canvas container */
  function onWheel(event: WheelEvent) {
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault()
      const delta = event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP
      setZoom(zoomLevel.value + delta)
    }
  }

  return {
    zoomLevel,
    visiblePages,
    scrollToPage,
    setupObserver,
    observePage,
    unobservePage,
    teardownObserver,
    isPageVisible,
    setZoom,
    onWheel,
    ZOOM_STEP,
    ZOOM_MAX,
    ZOOM_MIN,
  }
}
