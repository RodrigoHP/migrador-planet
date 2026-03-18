import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SyncView from './SyncView.vue'

// Stub heavy components
const globalStubs = {
  CoverageOverlay: { template: '<div data-testid="coverage-overlay-stub" />' },
  LayoutAnchor: { template: '<div data-testid="layout-anchor-stub" />' },
}

// Mock usePdfRenderer
vi.mock('@/composables/usePdfRenderer', () => ({
  usePdfRenderer: () => ({
    pdfDocument: { value: null },
    currentPage: { value: 1 },
    totalPages: { value: 0 },
    isLoading: { value: false },
    error: { value: null },
    loadPdf: vi.fn().mockResolvedValue(undefined),
    renderPage: vi.fn().mockResolvedValue(undefined),
    goToPage: vi.fn(),
    prevPage: vi.fn(),
    nextPage: vi.fn(),
    zoomIn: vi.fn(),
    zoomOut: vi.fn(),
  }),
}))

describe('SyncView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Stub ResizeObserver if not present
    if (typeof ResizeObserver === 'undefined') {
      vi.stubGlobal('ResizeObserver', class {
        observe() {}
        unobserve() {}
        disconnect() {}
      })
    }
  })

  it('renders the sync-view container', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="sync-view"]').exists()).toBe(true)
  })

  it('renders split panels container', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="sync-panels"]').exists()).toBe(true)
  })

  it('renders canvas panel', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="sync-panel-canvas"]').exists()).toBe(true)
  })

  it('renders PDF panel', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="sync-panel-pdf"]').exists()).toBe(true)
  })

  it('renders resizable divider', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="sync-divider"]').exists()).toBe(true)
  })

  it('shows scroll lock button', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const btn = wrapper.find('.sync-view__lock-btn')
    expect(btn.exists()).toBe(true)
  })

  it('scroll lock button is active by default (scrollLocked=true)', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const btn = wrapper.find('.sync-view__lock-btn')
    expect(btn.classes()).toContain('sync-view__lock-btn--active')
  })

  it('toggles scroll lock on button click', async () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const btn = wrapper.find('.sync-view__lock-btn')
    await btn.trigger('click')
    expect(btn.classes()).not.toContain('sync-view__lock-btn--active')
  })

  it('renders zoom controls for canvas panel', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const canvasPanel = wrapper.find('[data-testid="sync-panel-canvas"]')
    const zoomBtns = canvasPanel.findAll('.sync-view__zoom-btn')
    expect(zoomBtns.length).toBeGreaterThanOrEqual(2)
  })

  it('renders zoom controls for PDF panel', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const pdfPanel = wrapper.find('[data-testid="sync-panel-pdf"]')
    const zoomBtns = pdfPanel.findAll('.sync-view__zoom-btn')
    expect(zoomBtns.length).toBeGreaterThanOrEqual(2)
  })

  it('canvas and PDF zoom levels are independent', async () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })

    // Zoom in canvas
    const canvasPanel = wrapper.find('[data-testid="sync-panel-canvas"]')
    const canvasZoomIn = canvasPanel.findAll('.sync-view__zoom-btn')[1]!
    await canvasZoomIn.trigger('click')

    // Canvas zoom changed
    const canvasZoomValue = canvasPanel.find('.sync-view__zoom-value').text()
    expect(canvasZoomValue).toBe('110%')

    // PDF zoom should remain 100%
    const pdfPanel = wrapper.find('[data-testid="sync-panel-pdf"]')
    const pdfZoomValue = pdfPanel.find('.sync-view__zoom-value').text()
    expect(pdfZoomValue).toBe('100%')
  })

  it('shows empty state when no template is loaded', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const emptyMsg = wrapper.find('[data-testid="sync-panel-canvas"] .sync-view__empty')
    expect(emptyMsg.exists()).toBe(true)
    expect(emptyMsg.text()).toContain('Nenhum template carregado')
  })

  it('renders coverage overlay stubs inside canvas panel', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const stubs = wrapper.findAll('[data-testid="coverage-overlay-stub"]')
    expect(stubs.length).toBeGreaterThanOrEqual(1)
  })
})
