import { ref } from 'vue'
import type { Ref } from 'vue'

const ZOOM_MIN = 50
const ZOOM_MAX = 200
const ZOOM_STEP = 10

export interface UseZoomReturn {
  zoomLevel: Ref<number>
  zoomIn: () => void
  zoomOut: () => void
  setZoom: (level: number) => void
  ZOOM_MIN: number
  ZOOM_MAX: number
  ZOOM_STEP: number
}

/**
 * Independent zoom composable — each call creates its own isolated zoom state.
 * Use separately for each panel requiring independent zoom control.
 */
export function useZoom(initialZoom = 100): UseZoomReturn {
  const zoomLevel = ref<number>(initialZoom)

  function zoomIn() {
    zoomLevel.value = Math.min(zoomLevel.value + ZOOM_STEP, ZOOM_MAX)
  }

  function zoomOut() {
    zoomLevel.value = Math.max(zoomLevel.value - ZOOM_STEP, ZOOM_MIN)
  }

  function setZoom(level: number) {
    zoomLevel.value = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, level))
  }

  return {
    zoomLevel,
    zoomIn,
    zoomOut,
    setZoom,
    ZOOM_MIN,
    ZOOM_MAX,
    ZOOM_STEP,
  }
}
