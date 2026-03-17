import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PDFReference from './PDFReference.vue'
import { useSessionStore } from '@/stores/session'
import { useEditorStore } from '@/stores/editorStore'
import { useLayoutStore } from '@/stores/layout'

// Mock pdfjs-dist so tests don't need a real PDF rendering context
vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: vi.fn(() => ({
    promise: Promise.resolve({
      numPages: 5,
      getPage: vi.fn(() =>
        Promise.resolve({
          getViewport: vi.fn(() => ({ width: 600, height: 800 })),
          render: vi.fn(() => ({ promise: Promise.resolve() })),
        })
      ),
      destroy: vi.fn(() => Promise.resolve()),
    }),
  })),
}))

vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({ default: 'worker-stub.js' }))

describe('PDFReference', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the toolbar with document selector', () => {
    const wrapper = mount(PDFReference)
    expect(wrapper.find('[aria-label="PDF Reference toolbar"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Selecionar documento"]').exists()).toBe(true)
  })

  it('shows empty state when no PDFs uploaded', () => {
    const wrapper = mount(PDFReference)
    expect(wrapper.text()).toContain('Nenhum PDF disponível')
  })

  it('renders page navigation controls', () => {
    const wrapper = mount(PDFReference)
    expect(wrapper.find('[aria-label="Página anterior"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Próxima página"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Navegação de página"]').exists()).toBe(true)
  })

  it('renders zoom controls', () => {
    const wrapper = mount(PDFReference)
    expect(wrapper.find('[aria-label="Controles de zoom do PDF"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Aumentar zoom"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Diminuir zoom"]').exists()).toBe(true)
  })

  it('displays zoom level from editorStore.pdfZoom', () => {
    const editorStore = useEditorStore()
    editorStore.setPdfZoom(150)
    const wrapper = mount(PDFReference)
    expect(wrapper.text()).toContain('150%')
  })

  it('disables prev button when on first page', () => {
    const wrapper = mount(PDFReference)
    const prevBtn = wrapper.find('[aria-label="Página anterior"]')
    expect(prevBtn.attributes('disabled')).toBeDefined()
  })

  it('lists uploaded PDFs in selector', () => {
    const sessionStore = useSessionStore()
    sessionStore.uploadedPdfs = [
      { name: 'extrato_jan.pdf', pages: 3, sizeKB: 100, bytes: new ArrayBuffer(0) },
      { name: 'extrato_fev.pdf', pages: 2, sizeKB: 80, bytes: new ArrayBuffer(0) },
    ]
    const wrapper = mount(PDFReference)
    const options = wrapper.findAll('option')
    expect(options.length).toBe(2)
    expect(options[0]!.text()).toBe('extrato_jan.pdf')
    expect(options[1]!.text()).toBe('extrato_fev.pdf')
  })

  it('renders canvas element for PDF display', () => {
    const wrapper = mount(PDFReference)
    expect(wrapper.find('canvas').exists()).toBe(true)
  })

  it('shows cluster indicator when clusterPageCount > 1', async () => {
    const layoutStore = useLayoutStore()
    layoutStore.loadLayoutTypes([
      { id: 'l1', name: 'Layout 1', pageCount: 5, representativePages: [2] },
    ])
    layoutStore.setActiveLayout('l1')
    const wrapper = mount(PDFReference)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[aria-label="Indicador de cluster"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('5 páginas')
  })

  it('hides cluster indicator when clusterPageCount <= 1', async () => {
    const layoutStore = useLayoutStore()
    layoutStore.loadLayoutTypes([
      { id: 'l1', name: 'Layout 1', pageCount: 1, representativePages: [1] },
    ])
    layoutStore.setActiveLayout('l1')
    const wrapper = mount(PDFReference)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[aria-label="Indicador de cluster"]').exists()).toBe(false)
  })

  it('zoom-in button increases pdfZoom', async () => {
    const editorStore = useEditorStore()
    editorStore.setPdfZoom(100)
    const wrapper = mount(PDFReference)
    await wrapper.find('[aria-label="Aumentar zoom"]').trigger('click')
    expect(editorStore.pdfZoom).toBe(110)
  })

  it('zoom-out button decreases pdfZoom', async () => {
    const editorStore = useEditorStore()
    editorStore.setPdfZoom(100)
    const wrapper = mount(PDFReference)
    await wrapper.find('[aria-label="Diminuir zoom"]').trigger('click')
    expect(editorStore.pdfZoom).toBe(90)
  })

  it('zoom-in disabled at 200%', () => {
    const editorStore = useEditorStore()
    editorStore.setPdfZoom(200)
    const wrapper = mount(PDFReference)
    expect(wrapper.find('[aria-label="Aumentar zoom"]').attributes('disabled')).toBeDefined()
  })

  it('zoom-out disabled at 50%', () => {
    const editorStore = useEditorStore()
    editorStore.setPdfZoom(50)
    const wrapper = mount(PDFReference)
    expect(wrapper.find('[aria-label="Diminuir zoom"]').attributes('disabled')).toBeDefined()
  })
})
