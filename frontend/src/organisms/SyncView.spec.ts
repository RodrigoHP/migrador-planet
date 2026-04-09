import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SyncView from './SyncView.vue'

// Stub heavy components
const globalStubs = {
  CoverageOverlay: { template: '<div data-testid="coverage-overlay-stub" />' },
  LayoutAnchor: { template: '<div data-testid="layout-anchor-stub" />' },
}

// Mock usePdfRenderer com totalPages configurável via ref compartilhada
import { ref as vueRef } from 'vue'
const mockTotalPages = vueRef(0)
const mockPdfDocument = vueRef<object | null>(null)

vi.mock('@/composables/usePdfRenderer', () => ({
  usePdfRenderer: () => ({
    pdfDocument: mockPdfDocument,
    currentPage: { value: 1 },
    totalPages: mockTotalPages,
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
    // Resetar state do mock entre testes
    mockTotalPages.value = 0
    mockPdfDocument.value = null
    // Stub ResizeObserver if not present
    if (typeof ResizeObserver === 'undefined') {
      vi.stubGlobal(
        'ResizeObserver',
        class {
          observe() {}
          unobserve() {}
          disconnect() {}
        },
      )
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

  it('shows empty state in PDF panel when no PDF is loaded', () => {
    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    const pdfPanel = wrapper.find('[data-testid="sync-panel-pdf"]')
    expect(pdfPanel.find('.sync-view__empty').exists()).toBe(true)
    expect(pdfPanel.find('[data-testid="sync-pdf-canvas"]').exists()).toBe(false)
  })

  it('renders N canvas elements when PDF has N pages (multi-page PDF)', async () => {
    // Simular PDF com 2 páginas carregado
    mockTotalPages.value = 2
    mockPdfDocument.value = {}

    // sessionStore com PDF carregado
    const { useSessionStore } = await import('@/stores/session')
    const session = useSessionStore()
    // @ts-expect-error test stub
    session.uploadedPdfs = [{ bytes: new ArrayBuffer(0) }]

    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    await wrapper.vm.$nextTick()

    const canvases = wrapper.findAll('[data-testid="sync-pdf-canvas"]')
    expect(canvases.length).toBe(2)
  })

  it('canvas overlap fix: layout with 2 page-content children creates 2 SyncPages', async () => {
    const { useGenerationStore } = await import('@/stores/generation')
    const gen = useGenerationStore()

    // HTML com 1 layout-type mas 2 page-content físicos (caso multi-página)
    const html = `
      <div class="page" data-layout-type="boleto">
        <div class="page-content"><span style="position:absolute;top:100px;">Page 1</span></div>
        <div class="page-content"><span style="position:absolute;top:100px;">Page 2</span></div>
      </div>
    `
    gen.loadTemplateDraft({ html, css: '' })

    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    await wrapper.vm.$nextTick()

    // Deve renderizar 2 iframes separados (1 por page-content)
    const iframes = wrapper.findAll('[data-testid="sync-canvas-iframe"]')
    expect(iframes.length).toBe(2)
  })

  it('canvas overlap fix: layout with 1 page-content renders single iframe', async () => {
    const { useGenerationStore } = await import('@/stores/generation')
    const gen = useGenerationStore()

    const html = `
      <div class="page" data-layout-type="boleto">
        <div class="page-content"><span>Single page content</span></div>
      </div>
    `
    gen.loadTemplateDraft({ html, css: '' })

    const wrapper = mount(SyncView, { global: { stubs: globalStubs } })
    await wrapper.vm.$nextTick()

    const iframes = wrapper.findAll('[data-testid="sync-canvas-iframe"]')
    expect(iframes.length).toBe(1)
  })
})
