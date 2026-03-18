import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import LeftPanel from './LeftPanel.vue'
import { useEditorStore } from '@/stores/editorStore'

// Mock StructureTree to keep tests isolated
vi.mock('@/organisms/StructureTree.vue', () => ({
  default: { template: '<div class="structure-tree-mock" />' },
}))

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

describe('LeftPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders 2 tab buttons', () => {
    const wrapper = mount(LeftPanel)
    const buttons = wrapper.findAll('[role="tab"]')
    expect(buttons).toHaveLength(2)
    expect(buttons[0]!.text()).toBe('Estrutura')
    expect(buttons[1]!.text()).toBe('Campos')
  })

  it('default active tab is structure', () => {
    const wrapper = mount(LeftPanel)
    const buttons = wrapper.findAll('[role="tab"]')
    expect(buttons[0]!.classes()).toContain('left-panel__tab--active')
    expect(buttons[1]!.classes()).not.toContain('left-panel__tab--active')
  })

  it('switches to Campos tab on click', async () => {
    const store = useEditorStore()
    const wrapper = mount(LeftPanel)
    const buttons = wrapper.findAll('[role="tab"]')
    await buttons[1]!.trigger('click')
    expect(store.activeLeftTab).toBe('fields')
    expect(buttons[1]!.classes()).toContain('left-panel__tab--active')
  })

  it('shows StructureTree when structure tab is active', () => {
    const wrapper = mount(LeftPanel)
    expect(wrapper.find('.structure-tree-mock').exists()).toBe(true)
  })

  it('shows campos placeholder when fields tab is active', async () => {
    const store = useEditorStore()
    store.setActiveLeftTab('fields')
    const wrapper = mount(LeftPanel)
    expect(wrapper.text()).toContain('Campos')
  })

  it('has correct aria attributes on tablist', () => {
    const wrapper = mount(LeftPanel)
    const nav = wrapper.find('[role="tablist"]')
    expect(nav.attributes('aria-label')).toBe('Painel esquerdo')
  })
})
