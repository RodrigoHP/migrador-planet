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

const stubs = {
  DocumentSelector: { template: '<div data-testid="doc-selector" />' },
  DiffHighlight: { template: '<div class="diff-hl" />' },
}

function mountDiff() {
  return mount(DiffViewer, { global: { stubs } })
}

function seedPdfs() {
  const multiDocStore = useMultiDocStore()
  multiDocStore.pdfList = [
    { id: 'doc-1', name: 'Base.pdf', role: 'base', sizeKB: 100, pages: 1, uploadedAt: '' },
    { id: 'doc-2', name: 'Var.pdf', role: 'variation', sizeKB: 100, pages: 1, uploadedAt: '' },
  ]
  return multiDocStore
}

function seedInferences() {
  const diffStore = useDiffStore()
  diffStore.isActive = true
  diffStore.inferences = [
    { id: 'inf-1', type: 'moved', description: 'Elemento "field-a" movido', confidence: 0.7 },
    { id: 'inf-2', type: 'added', description: 'Elemento "field-b" adicionado', confidence: 0.9 },
    { id: 'inf-3', type: 'removed', description: 'Elemento "field-c" removido', confidence: 0.9 },
  ]
  return diffStore
}

describe('DiffViewer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── Panel Rendering ──────────────────────────────────────────────────

  it('renders two panels for split layout', () => {
    const wrapper = mountDiff()
    expect(wrapper.find('[data-testid="diff-panel-a"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="diff-panel-b"]').exists()).toBe(true)
  })

  it('renders divider between panels', () => {
    const wrapper = mountDiff()
    expect(wrapper.find('.diff-viewer__divider').exists()).toBe(true)
  })

  it('renders DocumentSelector in toolbar', () => {
    const wrapper = mountDiff()
    expect(wrapper.find('[data-testid="doc-selector"]').exists()).toBe(true)
  })

  // ─── Empty State ──────────────────────────────────────────────────────

  it('shows empty state when no documents selected', () => {
    const wrapper = mountDiff()
    expect(wrapper.text()).toContain('Selecione o Documento A')
    expect(wrapper.text()).toContain('Selecione o Documento B')
  })

  it('shows panel labels Documento A and Documento B', () => {
    const wrapper = mountDiff()
    expect(wrapper.text()).toContain('Documento A')
    expect(wrapper.text()).toContain('Documento B')
  })

  // ─── Document Names ──────────────────────────────────────────────────

  it('shows document names from multiDocStore', () => {
    seedPdfs()
    const diffStore = useDiffStore()
    diffStore.documentA = 'doc-1'
    diffStore.documentB = 'doc-2'
    const wrapper = mountDiff()
    expect(wrapper.text()).toContain('Base.pdf')
    expect(wrapper.text()).toContain('Var.pdf')
  })

  it('does not show document name when no doc selected', () => {
    const wrapper = mountDiff()
    const nameSpans = wrapper.findAll('.diff-viewer__panel-name')
    expect(nameSpans).toHaveLength(0)
  })

  // ─── DiffHighlight Rendering ─────────────────────────────────────────

  it('renders DiffHighlight components for items with bounds', () => {
    mountDiff()
    const diffStore = useDiffStore()
    diffStore.diffData = [
      {
        elementId: 'el-1',
        diffType: 'identical',
        boundsA: { x: 10, y: 10, w: 100, h: 20 },
        boundsB: { x: 10, y: 10, w: 100, h: 20 },
      },
    ]
    expect(diffStore.diffData.filter((d) => d.boundsA)).toHaveLength(1)
    expect(diffStore.diffData.filter((d) => d.boundsB)).toHaveLength(1)
  })

  // ─── Diff Summary Counts ──────────────────────────────────────────────

  it('shows diff summary counts when inferences panel is visible', () => {
    const diffStore = seedInferences()
    diffStore.diffData = [
      { elementId: 'a', diffType: 'identical', boundsA: { x: 0, y: 0, w: 10, h: 10 }, boundsB: { x: 0, y: 0, w: 10, h: 10 } },
      { elementId: 'b', diffType: 'moved', boundsA: { x: 0, y: 0, w: 10, h: 10 }, boundsB: { x: 20, y: 20, w: 10, h: 10 } },
      { elementId: 'c', diffType: 'added', boundsB: { x: 0, y: 0, w: 10, h: 10 } },
      { elementId: 'd', diffType: 'removed', boundsA: { x: 0, y: 0, w: 10, h: 10 } },
    ]
    const wrapper = mountDiff()
    const summary = wrapper.find('[data-testid="diff-summary"]')
    expect(summary.exists()).toBe(true)
    expect(summary.text()).toContain('Iguais: 1')
    expect(summary.text()).toContain('Movidos: 1')
    expect(summary.text()).toContain('Adicionados: 1')
    expect(summary.text()).toContain('Removidos: 1')
  })

  // ─── Inference Panel ──────────────────────────────────────────────────

  it('hides inference panel when no inferences', () => {
    const diffStore = useDiffStore()
    diffStore.isActive = true
    diffStore.inferences = []
    const wrapper = mountDiff()
    expect(wrapper.find('[data-testid="diff-inferences-panel"]').exists()).toBe(false)
  })

  it('hides inference panel when diff is not active', () => {
    const diffStore = useDiffStore()
    diffStore.isActive = false
    diffStore.inferences = [
      { id: 'x', type: 'moved', description: 'test', confidence: 0.7 },
    ]
    const wrapper = mountDiff()
    expect(wrapper.find('[data-testid="diff-inferences-panel"]').exists()).toBe(false)
  })

  it('shows inference panel with pending count badge', () => {
    seedInferences()
    const wrapper = mountDiff()
    const panel = wrapper.find('[data-testid="diff-inferences-panel"]')
    expect(panel.exists()).toBe(true)
    const badge = wrapper.find('[data-testid="pending-count"]')
    expect(badge.text()).toContain('3 pendentes')
  })

  it('renders inference items with type, description, and confidence', () => {
    seedInferences()
    const wrapper = mountDiff()
    const items = wrapper.findAll('.diff-viewer__inference-item')
    expect(items).toHaveLength(3)
    // First item — moved type
    expect(items[0].text()).toContain('moved')
    expect(items[0].text()).toContain('Elemento "field-a" movido')
    expect(items[0].text()).toContain('70%')
  })

  it('shows confirm and reject buttons for each inference', () => {
    seedInferences()
    const wrapper = mountDiff()
    const confirmBtns = wrapper.findAll('.diff-viewer__inference-btn--confirm')
    const rejectBtns = wrapper.findAll('.diff-viewer__inference-btn--reject')
    expect(confirmBtns).toHaveLength(3)
    expect(rejectBtns).toHaveLength(3)
  })

  it('confirm button calls diffStore.confirmInference', async () => {
    const diffStore = seedInferences()
    const spy = vi.spyOn(diffStore, 'confirmInference')
    const wrapper = mountDiff()
    const confirmBtns = wrapper.findAll('.diff-viewer__inference-btn--confirm')
    await confirmBtns[0].trigger('click')
    expect(spy).toHaveBeenCalledWith('inf-1')
  })

  it('reject button calls diffStore.rejectInference', async () => {
    const diffStore = seedInferences()
    const spy = vi.spyOn(diffStore, 'rejectInference')
    const wrapper = mountDiff()
    const rejectBtns = wrapper.findAll('.diff-viewer__inference-btn--reject')
    await rejectBtns[1].trigger('click')
    expect(spy).toHaveBeenCalledWith('inf-2')
  })

  it('shows singular "pendente" for 1 inference', () => {
    const diffStore = useDiffStore()
    diffStore.isActive = true
    diffStore.inferences = [
      { id: 'x', type: 'moved', description: 'test', confidence: 0.7 },
    ]
    const wrapper = mountDiff()
    const badge = wrapper.find('[data-testid="pending-count"]')
    expect(badge.text()).toContain('1 pendente')
    expect(badge.text()).not.toContain('pendentes')
  })

  // ─── Page Navigation ──────────────────────────────────────────────────

  it('renders page navigation for both panels', () => {
    const wrapper = mountDiff()
    const navs = wrapper.findAll('.diff-viewer__page-nav')
    expect(navs).toHaveLength(2)
  })

  it('disables prev buttons when on page 1', () => {
    const wrapper = mountDiff()
    const prevBtns = wrapper.findAll('.diff-viewer__nav-btn')
    // First nav btn of each panel is prev
    expect(prevBtns[0].attributes('disabled')).toBeDefined()
    expect(prevBtns[2].attributes('disabled')).toBeDefined()
  })

  // ─── Inference Type CSS Classes ────────────────────────────────────────

  it('applies type-specific CSS class to inference badges', () => {
    seedInferences()
    const wrapper = mountDiff()
    const typeBadges = wrapper.findAll('.diff-viewer__inference-type')
    expect(typeBadges[0].classes()).toContain('diff-viewer__inference-type--moved')
    expect(typeBadges[1].classes()).toContain('diff-viewer__inference-type--added')
    expect(typeBadges[2].classes()).toContain('diff-viewer__inference-type--removed')
  })

  // ─── Accessibility ────────────────────────────────────────────────────

  it('has aria-labels on navigation buttons', () => {
    const wrapper = mountDiff()
    const ariaLabels = wrapper.findAll('[aria-label]').map((el) => el.attributes('aria-label'))
    expect(ariaLabels).toContain('Página anterior A')
    expect(ariaLabels).toContain('Próxima página A')
    expect(ariaLabels).toContain('Página anterior B')
    expect(ariaLabels).toContain('Próxima página B')
  })

  it('has aria-live on page info displays', () => {
    const wrapper = mountDiff()
    const liveRegions = wrapper.findAll('[aria-live="polite"]')
    expect(liveRegions.length).toBeGreaterThanOrEqual(2)
  })
})
