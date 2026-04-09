import { ref, computed, onUnmounted } from 'vue'
import { useEditorStore } from '@/stores/editorStore'

export const ZOOM_MIN = 50
export const ZOOM_MAX = 125
export const ZOOM_STEP = 10
const MAX_VISIBLE_PAGES = 5

export function useCanvas() {
  const editorStore = useEditorStore()

  // ─── State ──────────────────────────────────────────────────────────────
  const scrollPosition = ref<number>(0)
  const visiblePages = ref<Set<number>>(new Set())

  // ─── Zoom (synced with editorStore) ──────────────────────────────────────
  const zoomLevel = computed({
    get: () => editorStore.zoomLevel,
    set: (value: number) => editorStore.setZoom(value),
  })

  // ─── Zoom Actions ─────────────────────────────────────────────────────────
  function zoomIn() {
    const next = Math.min(zoomLevel.value + ZOOM_STEP, ZOOM_MAX)
    editorStore.setZoom(next)
  }

  function zoomOut() {
    const next = Math.max(zoomLevel.value - ZOOM_STEP, ZOOM_MIN)
    editorStore.setZoom(next)
  }

  function setZoom(level: number) {
    const clamped = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, level))
    editorStore.setZoom(clamped)
  }

  function scrollToPage(pageNum: number) {
    // Emits an event for HTMLCanvas to handle scrolling
    const el = document.querySelector(`[data-page-wrapper="${pageNum}"]`) as HTMLElement | null
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  // ─── Lazy Rendering ───────────────────────────────────────────────────────
  let observer: IntersectionObserver | null = null

  function setupObserver(containerEl: HTMLElement) {
    observer = new IntersectionObserver(
      (entries) => {
        const updatedVisible = new Set(visiblePages.value)
        entries.forEach((entry) => {
          const pageNum = Number((entry.target as HTMLElement).dataset.pageWrapper)
          if (isNaN(pageNum)) return

          if (entry.isIntersecting) {
            updatedVisible.add(pageNum)
            // Enforce max visible pages
            if (updatedVisible.size > MAX_VISIBLE_PAGES) {
              // Remove the farthest page from scroll position
              const sorted = [...updatedVisible].sort((a, b) => a - b)
              const midIndex = sorted.indexOf(pageNum)
              if (midIndex > MAX_VISIBLE_PAGES / 2) {
                updatedVisible.delete(sorted[0]!)
              } else {
                updatedVisible.delete(sorted[sorted.length - 1]!)
              }
            }
          } else {
            updatedVisible.delete(pageNum)
          }
        })
        visiblePages.value = updatedVisible
      },
      {
        root: containerEl,
        rootMargin: '200px',
      },
    )
  }

  function observePage(el: HTMLElement) {
    observer?.observe(el)
  }

  function unobservePage(el: HTMLElement) {
    observer?.unobserve(el)
  }

  function teardownObserver() {
    observer?.disconnect()
    observer = null
  }

  function isPageVisible(pageNum: number): boolean {
    return visiblePages.value.has(pageNum)
  }

  onUnmounted(() => {
    teardownObserver()
  })

  return {
    zoomLevel,
    scrollPosition,
    visiblePages,
    zoomIn,
    zoomOut,
    setZoom,
    scrollToPage,
    setupObserver,
    observePage,
    unobservePage,
    teardownObserver,
    isPageVisible,
    ZOOM_MIN,
    ZOOM_MAX,
    ZOOM_STEP,
  }
}
