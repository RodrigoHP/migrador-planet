import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import TopToolbar from './TopToolbar.vue'
import { useSessionStore } from '@/stores/session'
import { useEditorStore } from '@/stores/editorStore'
import { useLayoutStore } from '@/stores/layout'

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

vi.mock('jszip', () => {
  return {
    default: class MockJSZip {
      folder = vi.fn().mockReturnThis()
      file = vi.fn().mockReturnThis()
      generateAsync = vi.fn().mockResolvedValue(new Blob(['zip'], { type: 'application/zip' }))
    },
  }
})

vi.mock('@/composables/useExport', async () => {
  const { ref } = await import('vue')
  return {
    useExport: () => ({
      exportZip: vi.fn().mockResolvedValue({ success: true }),
      isExporting: ref(false),
      exportError: ref(null),
    }),
    downloadBlob: vi.fn(),
    downloadJson: vi.fn(),
  }
})

describe('TopToolbar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('displays template name from sessionStore', () => {
    const session = useSessionStore()
    session.template_name = 'Extrato_Bancario'
    const wrapper = mount(TopToolbar)
    expect(wrapper.text()).toContain('Extrato_Bancario')
  })

  it('displays fallback when template_name is null', () => {
    const session = useSessionStore()
    session.template_name = null
    const wrapper = mount(TopToolbar)
    expect(wrapper.text()).toContain('Sem template')
  })

  it('renders 4 toggle buttons (Cobertura, Diff, Snap, Guias)', () => {
    const wrapper = mount(TopToolbar)
    // Cobertura, Diff, Snap, Guias (Auto Fix is a dedicated action button, not a toggle)
    const toggleButtons = wrapper.findAll('.toggle-button')
    expect(toggleButtons.length).toBeGreaterThanOrEqual(4)
  })

  it('renders Salvar and Exportar action buttons', () => {
    const wrapper = mount(TopToolbar)
    const text = wrapper.text()
    expect(text).toContain('Salvar')
    expect(text).toContain('Exportar')
  })

  it('toggles coverageMode on Cobertura button click', async () => {
    const store = useEditorStore()
    const wrapper = mount(TopToolbar)
    const coverageBtn = wrapper.find('[title="Cobertura"]')
    await coverageBtn.trigger('click')
    expect(store.coverageMode).toBe(true)
  })

  it('toggles diffMode on Diff button click', async () => {
    const store = useEditorStore()
    const wrapper = mount(TopToolbar)
    const diffBtn = wrapper.find('[title="Diff"]')
    await diffBtn.trigger('click')
    expect(store.diffMode).toBe(true)
  })

  it('toggles snapEnabled on Snap button click', async () => {
    const store = useEditorStore()
    expect(store.snapEnabled).toBe(true)
    const wrapper = mount(TopToolbar)
    const snapBtn = wrapper.find('[title="Snap"]')
    await snapBtn.trigger('click')
    expect(store.snapEnabled).toBe(false)
  })

  it('toggles showGuides on Guias button click', async () => {
    const store = useEditorStore()
    expect(store.showGuides).toBe(false)
    const wrapper = mount(TopToolbar)
    const guidesBtn = wrapper.find('[title="Guias"]')
    await guidesBtn.trigger('click')
    expect(store.showGuides).toBe(true)
  })

  it('Auto Fix button is rendered with data-testid btn-auto-fix', () => {
    const wrapper = mount(TopToolbar)
    const autoFixBtn = wrapper.find('[data-testid="btn-auto-fix"]')
    expect(autoFixBtn.exists()).toBe(true)
  })

  it('Salvar button calls downloadBlob with .zip', async () => {
    const { downloadBlob } = await import('@/composables/useExport')
    const wrapper = mount(TopToolbar)
    const saveBtn = wrapper.find('[aria-label="Salvar"]')
    await saveBtn.trigger('click')
    // Story 36.4: onSave now generates a .zip via JSZip and calls downloadBlob
    expect(downloadBlob).toHaveBeenCalled()
    const [, filename] = (downloadBlob as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(filename).toMatch(/\.projeto\.zip$/)
  })

  it('Exportar button opens modal when datasets exist', async () => {
    const { useTestDataStore } = await import('@/stores/testDataStore')
    const testDataStore = useTestDataStore()
    testDataStore.datasets = [{ id: 'ds-1', name: 'Dataset 1', fields: {}, rawContent: '{}', createdAt: '2026-01-01', size: 10, status: 'valid' }]
    const wrapper = mount(TopToolbar)
    const exportBtn = wrapper.find('[aria-label="Exportar"]')
    await exportBtn.trigger('click')
    expect(wrapper.text()).toContain('Incluir datasets de teste')
  })

  it('layout selector hidden when 1 layout type', () => {
    const layout = useLayoutStore()
    layout.layoutTypes = [{ id: 'lt-1', name: 'Transações', pageCount: 2, docCount: 1, representativePages: [1] }]
    const wrapper = mount(TopToolbar, { attachTo: document.body })
    const sel = wrapper.find('.layout-selector')
    expect(sel.exists()).toBe(true)
    expect(sel.isVisible()).toBe(false)
  })
})
