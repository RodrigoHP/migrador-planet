import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import FileExplorer from './FileExplorer.vue'
import { useCodeStore } from '@/stores/codeStore'
import { useEditorStore } from '@/stores/editorStore'

vi.mock('@/stores/templateStore', () => ({
  useTemplateStore: () => ({
    documentTree: null,
    flatNodes: new Map(),
  }),
}))

describe('FileExplorer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders with role="tree"', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.find('[role="tree"]').exists()).toBe(true)
  })

  it('shows index.html file', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.text()).toContain('index.html')
  })

  it('shows style.css file', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.text()).toContain('style.css')
  })

  it('shows base.js file', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.text()).toContain('base.js')
  })

  it('shows exemplo.js file', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.text()).toContain('exemplo.js')
  })

  it('shows RO badge for exemplo.js', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.text()).toContain('RO')
  })

  it('clicking index.html sets activeFile to html', async () => {
    const codeStore = useCodeStore()
    const wrapper = mount(FileExplorer)
    const buttons = wrapper.findAll('.file-explorer__item')
    const htmlBtn = buttons.find((b) => b.text().includes('index.html'))
    await htmlBtn!.trigger('click')
    expect(codeStore.activeFile).toBe('html')
  })

  it('clicking style.css sets activeFile to css', async () => {
    const codeStore = useCodeStore()
    const wrapper = mount(FileExplorer)
    const buttons = wrapper.findAll('.file-explorer__item')
    const cssBtn = buttons.find((b) => b.text().includes('style.css'))
    await cssBtn!.trigger('click')
    expect(codeStore.activeFile).toBe('css')
  })

  it('clicking base.js sets activeFile to js', async () => {
    const codeStore = useCodeStore()
    const wrapper = mount(FileExplorer)
    const buttons = wrapper.findAll('.file-explorer__item')
    const jsBtn = buttons.find((b) => b.text().includes('base.js'))
    await jsBtn!.trigger('click')
    expect(codeStore.activeFile).toBe('js')
  })

  it('clicking exemplo.js sets activeFile to exemplo', async () => {
    const codeStore = useCodeStore()
    const wrapper = mount(FileExplorer)
    const buttons = wrapper.findAll('.file-explorer__item')
    const exemploBtn = buttons.find((b) => b.text().includes('exemplo.js'))
    await exemploBtn!.trigger('click')
    expect(codeStore.activeFile).toBe('exemplo')
  })

  it('clicking a file switches center panel to code tab', async () => {
    const editorStore = useEditorStore()
    const wrapper = mount(FileExplorer)
    const buttons = wrapper.findAll('.file-explorer__item')
    const htmlBtn = buttons.find((b) => b.text().includes('index.html'))
    await htmlBtn!.trigger('click')
    expect(editorStore.activeCenterTab).toBe('code')
  })

  it('active file is highlighted with active class', async () => {
    const codeStore = useCodeStore()
    codeStore.setActiveFile('css')
    const wrapper = mount(FileExplorer)
    const buttons = wrapper.findAll('.file-explorer__item')
    const cssBtn = buttons.find((b) => b.text().includes('style.css'))
    expect(cssBtn!.classes()).toContain('file-explorer__item--active')
  })

  it('shows MVP hint about blocked operations', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.text()).toContain('bloqueado')
  })

  it('shows template folder group label', () => {
    const wrapper = mount(FileExplorer)
    expect(wrapper.text()).toContain('Template')
  })
})
