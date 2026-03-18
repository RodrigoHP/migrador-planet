import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useSync } from './useSync'

// Helper to create a mock HTMLElement with scroll properties
function makeMockPanel(scrollTop: number, scrollHeight: number, clientHeight: number): HTMLElement {
  return {
    scrollTop,
    scrollHeight,
    clientHeight,
  } as unknown as HTMLElement
}

describe('useSync', () => {
  beforeEach(() => {
    // Mock requestAnimationFrame
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      cb(0)
      return 0
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('initial state', () => {
    it('scrollLocked is true by default', () => {
      const { scrollLocked } = useSync()
      expect(scrollLocked.value).toBe(true)
    })

    it('selectedElementId is null by default', () => {
      const { selectedElementId } = useSync()
      expect(selectedElementId.value).toBeNull()
    })
  })

  describe('toggleScrollLock', () => {
    it('toggles scrollLocked from true to false', () => {
      const { scrollLocked, toggleScrollLock } = useSync()
      toggleScrollLock()
      expect(scrollLocked.value).toBe(false)
    })

    it('toggles scrollLocked from false to true', () => {
      const { scrollLocked, toggleScrollLock } = useSync()
      toggleScrollLock()
      toggleScrollLock()
      expect(scrollLocked.value).toBe(true)
    })
  })

  describe('syncSelection', () => {
    it('sets selectedElementId', () => {
      const { selectedElementId, syncSelection } = useSync()
      syncSelection('element-42')
      expect(selectedElementId.value).toBe('element-42')
    })

    it('updates selectedElementId on subsequent calls', () => {
      const { selectedElementId, syncSelection } = useSync()
      syncSelection('elem-1')
      syncSelection('elem-2')
      expect(selectedElementId.value).toBe('elem-2')
    })
  })

  describe('clearSelection', () => {
    it('resets selectedElementId to null', () => {
      const { selectedElementId, syncSelection, clearSelection } = useSync()
      syncSelection('some-element')
      clearSelection()
      expect(selectedElementId.value).toBeNull()
    })
  })

  describe('syncScroll', () => {
    it('does not sync when scrollLocked is false', () => {
      const { scrollLocked, syncScroll, toggleScrollLock } = useSync()
      toggleScrollLock()
      expect(scrollLocked.value).toBe(false)

      const source = makeMockPanel(500, 1000, 200)
      const target = makeMockPanel(0, 1000, 200)

      syncScroll(source, target)
      expect(target.scrollTop).toBe(0) // unchanged
    })

    it('syncs scroll proportionally when locked', () => {
      const { syncScroll } = useSync()

      // source: scrollTop=400, max=800 → ratio=0.5
      const source = makeMockPanel(400, 1000, 200)
      // target: max=600
      const target = makeMockPanel(0, 800, 200)

      syncScroll(source, target)
      // ratio = 400 / (1000-200) = 400/800 = 0.5
      // target scrollTop = 0.5 * (800-200) = 0.5 * 600 = 300
      expect(target.scrollTop).toBe(300)
    })

    it('does not sync when sourceMax is 0 (source not scrollable)', () => {
      const { syncScroll } = useSync()

      const source = makeMockPanel(0, 200, 200) // scrollHeight === clientHeight
      const target = makeMockPanel(0, 1000, 200)

      syncScroll(source, target)
      expect(target.scrollTop).toBe(0)
    })

    it('handles proportional mapping at scroll top (ratio=0)', () => {
      const { syncScroll } = useSync()

      const source = makeMockPanel(0, 1000, 200) // ratio=0
      const target = makeMockPanel(500, 1000, 200)

      syncScroll(source, target)
      expect(target.scrollTop).toBe(0)
    })

    it('handles proportional mapping at scroll bottom (ratio=1)', () => {
      const { syncScroll } = useSync()

      // source at bottom: scrollTop = scrollHeight - clientHeight
      const source = makeMockPanel(800, 1000, 200) // ratio=1
      const target = makeMockPanel(0, 800, 200)

      syncScroll(source, target)
      // ratio = 800/800 = 1 → target scrollTop = 1 * 600 = 600
      expect(target.scrollTop).toBe(600)
    })
  })
})
