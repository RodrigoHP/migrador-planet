import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import CenterPanel from './CenterPanel.vue'
import { useEditorStore } from '@/stores/editorStore'

describe('CenterPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders 4 tab buttons', () => {
    const wrapper = mount(CenterPanel)
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs).toHaveLength(4)
  })

  it('tab labels include Canvas, PDF, Código, Sincronizar', () => {
    const wrapper = mount(CenterPanel)
    const text = wrapper.text()
    expect(text).toContain('Canvas')
    expect(text).toContain('PDF')
    expect(text).toContain('Código')
    expect(text).toContain('Sincronizar')
  })

  it('default active tab is canvas', () => {
    const wrapper = mount(CenterPanel)
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs[0]!.classes()).toContain('center-panel__tab--active')
  })

  it('switches to PDF tab on click', async () => {
    const store = useEditorStore()
    const wrapper = mount(CenterPanel)
    const tabs = wrapper.findAll('[role="tab"]')
    await tabs[1]!.trigger('click')
    expect(store.activeCenterTab).toBe('pdf')
    expect(tabs[1]!.classes()).toContain('center-panel__tab--active')
  })

  it('shows "Em breve" for code tab', async () => {
    const store = useEditorStore()
    store.setActiveCenterTab('code')
    const wrapper = mount(CenterPanel)
    expect(wrapper.text()).toContain('Em breve')
  })

  it('shows "Em breve" for sync tab', async () => {
    const store = useEditorStore()
    store.setActiveCenterTab('sync')
    const wrapper = mount(CenterPanel)
    expect(wrapper.text()).toContain('Em breve')
  })

  it('has correct tablist aria-label', () => {
    const wrapper = mount(CenterPanel)
    const nav = wrapper.find('[role="tablist"]')
    expect(nav.attributes('aria-label')).toBe('Painel central')
  })
})
