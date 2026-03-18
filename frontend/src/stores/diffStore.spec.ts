import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDiffStore } from '@/stores/diffStore'
import { useMultiDocStore } from '@/stores/multiDocStore'

// Mock templateStore to avoid deep dependencies
vi.mock('@/stores/templateStore', () => ({
  useTemplateStore: () => ({
    flatNodes: new Map(),
    getNodesByType: () => [],
  }),
}))

describe('diffStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── toggleDiffMode ─────────────────────────────────────────────────────
  it('starts inactive', () => {
    const store = useDiffStore()
    expect(store.isActive).toBe(false)
  })

  it('toggleDiffMode activates diff mode', () => {
    const store = useDiffStore()
    store.toggleDiffMode()
    expect(store.isActive).toBe(true)
  })

  it('toggleDiffMode deactivates diff mode when called twice', () => {
    const store = useDiffStore()
    store.toggleDiffMode()
    store.toggleDiffMode()
    expect(store.isActive).toBe(false)
  })

  // ─── setDocuments ────────────────────────────────────────────────────────
  it('setDocuments assigns documentA and documentB', () => {
    const store = useDiffStore()
    store.setDocuments('pdf-1', 'pdf-2')
    expect(store.documentA).toBe('pdf-1')
    expect(store.documentB).toBe('pdf-2')
  })

  it('setDocuments triggers computeDiff (diffData populated or empty)', () => {
    const store = useDiffStore()
    // No matrix available, so diffData may come from fallback
    store.setDocuments('pdf-1', 'pdf-2')
    // Just verify it ran without throwing
    expect(Array.isArray(store.diffData)).toBe(true)
  })

  // ─── computeDiff ─────────────────────────────────────────────────────────
  it('computeDiff clears data when no documents selected', () => {
    const store = useDiffStore()
    store.diffData = [{ elementId: 'x', diffType: 'identical' }]
    store.computeDiff()
    expect(store.diffData).toHaveLength(0)
  })

  it('computeDiff populates diffData with matrix', () => {
    const store = useDiffStore()
    const multiDocStore = useMultiDocStore()

    multiDocStore.pdfList = [
      { id: 'pdf-a', name: 'A.pdf', role: 'base', sizeKB: 100, pages: 1, uploadedAt: '' },
      { id: 'pdf-b', name: 'B.pdf', role: 'variation', sizeKB: 100, pages: 1, uploadedAt: '' },
    ]
    multiDocStore.variationMatrix = {
      layoutIds: ['field-1', 'field-2'],
      variationIds: ['pdf-b'],
      cells: {
        'field-1': { 'pdf-a': true, 'pdf-b': true },
        'field-2': { 'pdf-a': true, 'pdf-b': false },
      },
    }

    store.documentA = 'pdf-a'
    store.documentB = 'pdf-b'
    store.computeDiff()

    expect(store.diffData.length).toBeGreaterThan(0)
    const field1 = store.diffData.find((d) => d.elementId === 'field-1')
    expect(field1?.diffType).toBe('identical')
    const field2 = store.diffData.find((d) => d.elementId === 'field-2')
    expect(field2?.diffType).toBe('removed')
  })

  it('computeDiff marks added element (only in B)', () => {
    const store = useDiffStore()
    const multiDocStore = useMultiDocStore()

    multiDocStore.pdfList = [
      { id: 'pdf-a', name: 'A.pdf', role: 'base', sizeKB: 100, pages: 1, uploadedAt: '' },
      { id: 'pdf-b', name: 'B.pdf', role: 'variation', sizeKB: 100, pages: 1, uploadedAt: '' },
    ]
    multiDocStore.variationMatrix = {
      layoutIds: ['field-x'],
      variationIds: ['pdf-b'],
      cells: {
        'field-x': { 'pdf-a': false, 'pdf-b': true },
      },
    }

    store.setDocuments('pdf-a', 'pdf-b')
    const item = store.diffData.find((d) => d.elementId === 'field-x')
    expect(item?.diffType).toBe('added')
  })

  // ─── highlightsByType ────────────────────────────────────────────────────
  it('highlightsByType groups items correctly', () => {
    const store = useDiffStore()
    store.diffData = [
      { elementId: 'a', diffType: 'identical' },
      { elementId: 'b', diffType: 'removed' },
      { elementId: 'c', diffType: 'identical' },
    ]
    expect(store.highlightsByType.identical).toHaveLength(2)
    expect(store.highlightsByType.removed).toHaveLength(1)
    expect(store.highlightsByType.added).toHaveLength(0)
  })

  // ─── confirmInference ────────────────────────────────────────────────────
  it('confirmInference removes inference from list', () => {
    const store = useDiffStore()
    const multiDocStore = useMultiDocStore()

    // Populate detections in multiDocStore so confirmDetection works
    multiDocStore.detections = [
      { id: 'inf-1', pdfId: '', type: 'required', description: 'test', confidence: 1.0 },
    ]

    store.inferences = [
      { id: 'inf-1', type: 'removed', description: 'desc', confidence: 0.9 },
      { id: 'inf-2', type: 'added', description: 'desc2', confidence: 0.8 },
    ]

    store.confirmInference('inf-1')
    expect(store.inferences.find((i) => i.id === 'inf-1')).toBeUndefined()
    expect(store.inferences).toHaveLength(1)
  })

  // ─── rejectInference ─────────────────────────────────────────────────────
  it('rejectInference removes inference and diffData item', () => {
    const store = useDiffStore()
    const multiDocStore = useMultiDocStore()

    multiDocStore.detections = [
      { id: 'inf-1', pdfId: '', type: 'required', description: 'test', confidence: 1.0 },
    ]

    store.inferences = [{ id: 'inf-1', type: 'removed', description: 'desc', confidence: 0.9 }]
    store.diffData = [{ elementId: 'inf-1', diffType: 'removed' }]

    store.rejectInference('inf-1')
    expect(store.inferences).toHaveLength(0)
    expect(store.diffData).toHaveLength(0)
  })
})
