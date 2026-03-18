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

  it('renders 4 toggle buttons', () => {
    const wrapper = mount(TopToolbar)
    // Cobertura, Diff, Snap, Auto Fix
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
    const wrapper = mount(TopToolbar)
    const snapBtn = wrapper.find('[title="Snap"]')
    await snapBtn.trigger('click')
    expect(store.snapEnabled).toBe(true)
  })

  it('toggles autoFixEnabled on Auto Fix button click', async () => {
    const store = useEditorStore()
    const wrapper = mount(TopToolbar)
    const autoFixBtn = wrapper.find('[title="Auto Fix"]')
    await autoFixBtn.trigger('click')
    expect(store.autoFixEnabled).toBe(true)
  })

  it('Salvar button calls console.log placeholder', async () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    const wrapper = mount(TopToolbar)
    const saveBtn = wrapper.find('[aria-label="Salvar"]')
    await saveBtn.trigger('click')
    expect(consoleSpy).toHaveBeenCalledWith('[TopToolbar] save placeholder')
    consoleSpy.mockRestore()
  })

  it('Exportar button calls console.log placeholder', async () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    const wrapper = mount(TopToolbar)
    const exportBtn = wrapper.find('[aria-label="Exportar"]')
    await exportBtn.trigger('click')
    expect(consoleSpy).toHaveBeenCalledWith('[TopToolbar] export placeholder')
    consoleSpy.mockRestore()
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
