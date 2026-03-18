import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// Mock templateStore dependency from diffStore → multiDocStore → confirmDetection
vi.mock('@/stores/templateStore', () => ({
  useTemplateStore: () => ({
    flatNodes: new Map(),
    getNodesByType: () => [],
    updateNodeProperties: vi.fn(),
  }),
}))

import DocumentSelector from './DocumentSelector.vue'
import { useDiffStore } from '@/stores/diffStore'
import { useMultiDocStore } from '@/stores/multiDocStore'

describe('DocumentSelector', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders two dropdowns', () => {
    const wrapper = mount(DocumentSelector)
    const selects = wrapper.findAll('select')
    expect(selects).toHaveLength(2)
  })

  it('populates options from multiDocStore.pdfList', () => {
    const multiDocStore = useMultiDocStore()
    multiDocStore.pdfList = [
      { id: 'p1', name: 'Doc1.pdf', role: 'base', sizeKB: 100, pages: 1, uploadedAt: '' },
      { id: 'p2', name: 'Doc2.pdf', role: 'variation', sizeKB: 100, pages: 1, uploadedAt: '' },
    ]
    const wrapper = mount(DocumentSelector)
    const options = wrapper.findAll('option')
    const texts = options.map((o) => o.text())
    expect(texts).toContain('Doc1.pdf')
    expect(texts).toContain('Doc2.pdf')
  })

  it('shows label "Documento A" and "Documento B"', () => {
    const wrapper = mount(DocumentSelector)
    expect(wrapper.text()).toContain('Documento A')
    expect(wrapper.text()).toContain('Documento B')
  })

  it('calls diffStore.setDocuments when both are selected', async () => {
    const multiDocStore = useMultiDocStore()
    multiDocStore.pdfList = [
      { id: 'p1', name: 'Doc1.pdf', role: 'base', sizeKB: 100, pages: 1, uploadedAt: '' },
      { id: 'p2', name: 'Doc2.pdf', role: 'variation', sizeKB: 100, pages: 1, uploadedAt: '' },
    ]
    const diffStore = useDiffStore()
    diffStore.documentA = 'p1' // pre-set A

    const wrapper = mount(DocumentSelector)
    const selectB = wrapper.find('#doc-selector-b')

    // Simulate selecting doc B
    await selectB.setValue('p2')
    await selectB.trigger('change')

    expect(diffStore.documentB).toBe('p2')
  })

  it('sets documentA without triggering computeDiff when B not yet selected', async () => {
    const multiDocStore = useMultiDocStore()
    multiDocStore.pdfList = [
      { id: 'p1', name: 'Doc1.pdf', role: 'base', sizeKB: 100, pages: 1, uploadedAt: '' },
    ]
    const diffStore = useDiffStore()

    const wrapper = mount(DocumentSelector)
    const selectA = wrapper.find('#doc-selector-a')
    await selectA.setValue('p1')
    await selectA.trigger('change')

    // documentA should be set, documentB still null
    expect(diffStore.documentA).toBe('p1')
    expect(diffStore.documentB).toBeNull()
  })
})
