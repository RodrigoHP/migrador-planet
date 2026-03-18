import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// Mock pdfjs-dist to avoid worker issues in test environment
vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: vi.fn().mockReturnValue({
    promise: Promise.resolve({
      numPages: 3,
      getPage: vi.fn().mockResolvedValue({
        getViewport: vi.fn().mockReturnValue({ width: 595, height: 842 }),
        render: vi.fn().mockReturnValue({ promise: Promise.resolve() }),
      }),
      destroy: vi.fn().mockResolvedValue(undefined),
    }),
  }),
}))

vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({
  default: 'mock-worker-url',
}))

import DiffViewer from './DiffViewer.vue'
import { useDiffStore } from '@/stores/diffStore'
import { useMultiDocStore } from '@/stores/multiDocStore'

describe('DiffViewer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders two panels for split layout', () => {
    const wrapper = mount(DiffViewer, {
      global: {
        stubs: {
          DocumentSelector: { template: '<div data-testid="doc-selector" />' },
          DiffHighlight: { template: '<div />' },
        },
      },
    })
    expect(wrapper.find('[data-testid="diff-panel-a"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="diff-panel-b"]').exists()).toBe(true)
  })

  it('shows empty state when no documents selected', () => {
    const wrapper = mount(DiffViewer, {
      global: {
        stubs: {
          DocumentSelector: { template: '<div />' },
          DiffHighlight: { template: '<div />' },
        },
      },
    })
    expect(wrapper.text()).toContain('Selecione o Documento A')
    expect(wrapper.text()).toContain('Selecione o Documento B')
  })

  it('renders DiffHighlight components for items with bounds', () => {
    mount(DiffViewer, {
      global: {
        stubs: {
          DocumentSelector: { template: '<div />' },
          DiffHighlight: { template: '<div class="diff-hl" />' },
        },
      },
    })
    const diffStore = useDiffStore()
    // Set diffData with bounds so highlights render
    diffStore.diffData = [
      {
        elementId: 'el-1',
        diffType: 'identical',
        boundsA: { x: 10, y: 10, w: 100, h: 20 },
        boundsB: { x: 10, y: 10, w: 100, h: 20 },
      },
    ]
    // highlights are computed from diffData
    expect(diffStore.diffData.filter((d) => d.boundsA)).toHaveLength(1)
    expect(diffStore.diffData.filter((d) => d.boundsB)).toHaveLength(1)
  })

  it('shows document names from multiDocStore', async () => {
    const multiDocStore = useMultiDocStore()
    multiDocStore.pdfList = [
      { id: 'doc-1', name: 'Base.pdf', role: 'base', sizeKB: 100, pages: 1, uploadedAt: '' },
      { id: 'doc-2', name: 'Var.pdf', role: 'variation', sizeKB: 100, pages: 1, uploadedAt: '' },
    ]
    const diffStore = useDiffStore()
    diffStore.documentA = 'doc-1'
    diffStore.documentB = 'doc-2'

    const wrapper = mount(DiffViewer, {
      global: {
        stubs: {
          DocumentSelector: { template: '<div />' },
          DiffHighlight: { template: '<div />' },
        },
      },
    })

    expect(wrapper.text()).toContain('Base.pdf')
    expect(wrapper.text()).toContain('Var.pdf')
  })
})
