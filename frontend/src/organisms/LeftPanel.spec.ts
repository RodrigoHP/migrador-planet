import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import LeftPanel from './LeftPanel.vue'
import { useEditorStore } from '@/stores/editorStore'

// Mock StructureTree to keep tests isolated
vi.mock('@/organisms/StructureTree.vue', () => ({
  default: { template: '<div class="structure-tree-mock" />' },
}))

vi.mock('@/organisms/FileExplorer.vue', () => ({
  default: { template: '<div class="file-explorer-mock" />' },
}))


vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

vi.mock('@/stores/codeStore', () => ({
  useCodeStore: () => ({
    activeFile: 'html',
    fileContents: { html: '', css: '', js: '', exemplo: '' },
    externalChangeDetected: false,
    setActiveFile: vi.fn(),
    applyMonacoEdit: vi.fn(),
    dismissExternalChange: vi.fn(),
  }),
}))

vi.mock('@/stores/templateStore', () => ({
  useTemplateStore: () => ({
    documentTree: null,
    flatNodes: new Map(),
  }),
}))


describe('LeftPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders 2 tab buttons when center tab is canvas', () => {
    const wrapper = mount(LeftPanel)
    const buttons = wrapper.findAll('[role="tab"]')
    expect(buttons).toHaveLength(2)
    expect(buttons[0]!.text()).toBe('Estrutura')
    expect(buttons[1]!.text()).toBe('Campos')
  })

  it('renders 3 tab buttons when center tab is code', () => {
    const store = useEditorStore()
    store.setActiveCenterTab('code')
    const wrapper = mount(LeftPanel)
    const buttons = wrapper.findAll('[role="tab"]')
    expect(buttons).toHaveLength(3)
    expect(buttons[2]!.text()).toBe('Arquivos')
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

  it('switches to files tab when code center tab is activated', async () => {
    const store = useEditorStore()
    const wrapper = mount(LeftPanel)
    store.setActiveCenterTab('code')
    await wrapper.vm.$nextTick()
    expect(store.activeLeftTab).toBe('files')
  })

  it('reverts to structure tab when leaving code center tab', async () => {
    const store = useEditorStore()
    store.setActiveCenterTab('code')
    const wrapper = mount(LeftPanel)
    await wrapper.vm.$nextTick()
    store.setActiveCenterTab('canvas')
    await wrapper.vm.$nextTick()
    expect(store.activeLeftTab).toBe('structure')
  })

  it('shows FileExplorer when files tab is active', async () => {
    const store = useEditorStore()
    store.setActiveCenterTab('code')
    store.setActiveLeftTab('files')
    const wrapper = mount(LeftPanel)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.file-explorer-mock').exists()).toBe(true)
  })
})
