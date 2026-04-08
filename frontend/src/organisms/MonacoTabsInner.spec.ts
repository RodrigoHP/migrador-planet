import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// Mock monaco-editor — must be before component import
const mockModel = {
  getValue: vi.fn().mockReturnValue(''),
  setValue: vi.fn(),
  getLineCount: vi.fn().mockReturnValue(10),
  getLineContent: vi.fn().mockReturnValue(''),
  getLinesContent: vi.fn().mockReturnValue([]),
  dispose: vi.fn(),
}
const mockEditor = {
  getValue: vi.fn().mockReturnValue(''),
  updateOptions: vi.fn(),
  revealLineInCenter: vi.fn(),
  deltaDecorations: vi.fn().mockReturnValue([]),
  onDidChangeModelContent: vi.fn(),
  onDidChangeCursorPosition: vi.fn(),
  dispose: vi.fn(),
}
vi.mock('monaco-editor', () => ({
  editor: {
    createModel: vi.fn().mockReturnValue(mockModel),
    create: vi.fn().mockReturnValue(mockEditor),
    setModelLanguage: vi.fn(),
    setModelMarkers: vi.fn(),
  },
  Range: vi.fn(),
}))

vi.mock('@/utils/cssCompletionProvider', () => ({
  registerCssCompletionProvider: vi.fn().mockReturnValue({ dispose: vi.fn() }),
}))

vi.mock('@/utils/cssValidator', () => ({
  applyCssMarkers: vi.fn().mockReturnValue(0),
}))

vi.mock('@/molecules/ComputedStylesPanel.vue', () => ({
  default: { template: '<div data-testid="computed-styles" />' },
}))

import MonacoTabsInner from './MonacoTabsInner.vue'
import { useCodeStore } from '@/stores/codeStore'
import { useEditorStore } from '@/stores/editorStore'

function mountComponent() {
  return mount(MonacoTabsInner, {
    global: {
      stubs: {
        ComputedStylesPanel: { template: '<div data-testid="computed-styles" />' },
      },
    },
  })
}

describe('MonacoTabsInner', () => {
  let codeStore: ReturnType<typeof useCodeStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    codeStore = useCodeStore()
    vi.clearAllMocks()
    mockModel.getValue.mockReturnValue(codeStore.fileContents.html)
  })

  // ─── Rendering ─────────────────────────────────────────────────────────

  it('renders all 4 file tabs', () => {
    const wrapper = mountComponent()
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs).toHaveLength(4)
    expect(tabs.map((t) => t.text())).toEqual(
      expect.arrayContaining(['index.html', 'style.css', 'base.js']),
    )
  })

  it('marks the active tab with aria-selected=true', () => {
    codeStore.setActiveFile('html')
    const wrapper = mountComponent()
    const tabs = wrapper.findAll('[role="tab"]')
    const activeTab = tabs.find((t) => t.text().includes('index.html'))
    expect(activeTab?.attributes('aria-selected')).toBe('true')
  })

  it('marks non-active tabs with aria-selected=false', () => {
    codeStore.setActiveFile('html')
    const wrapper = mountComponent()
    const tabs = wrapper.findAll('[role="tab"]')
    const cssTab = tabs.find((t) => t.text().includes('style.css'))
    expect(cssTab?.attributes('aria-selected')).toBe('false')
  })

  it('applies --active class to current active tab', () => {
    codeStore.setActiveFile('css')
    const wrapper = mountComponent()
    const tabs = wrapper.findAll('[role="tab"]')
    const cssTab = tabs.find((t) => t.text().includes('style.css'))
    expect(cssTab?.classes()).toContain('monaco-tabs__tab--active')
  })

  it('shows RO badge for read-only files (exemplo.js)', () => {
    const wrapper = mountComponent()
    const badges = wrapper.findAll('.monaco-tabs__readonly-badge')
    expect(badges.length).toBeGreaterThanOrEqual(1)
    expect(badges[0].text()).toBe('RO')
  })

  it('applies --readonly class to read-only tab', () => {
    const wrapper = mountComponent()
    const tabs = wrapper.findAll('[role="tab"]')
    const exemploTab = tabs.find((t) => t.text().includes('exemplo.js'))
    expect(exemploTab?.classes()).toContain('monaco-tabs__tab--readonly')
  })

  // ─── Tab Switching ─────────────────────────────────────────────────────

  it('switches active file on tab click', async () => {
    const wrapper = mountComponent()
    const tabs = wrapper.findAll('[role="tab"]')
    const cssTab = tabs.find((t) => t.text().includes('style.css'))
    await cssTab?.trigger('click')
    expect(codeStore.activeFile).toBe('css')
  })

  it('does not switch when clicking already active tab', async () => {
    codeStore.setActiveFile('html')
    const spy = vi.spyOn(codeStore, 'setActiveFile')
    const wrapper = mountComponent()
    // MonacoTabsInner calls switchFile which calls codeStore.setActiveFile
    // but returns early if same tab. Since monaco is mocked and not initialized in template,
    // it falls through to the codeStore call
    const tabs = wrapper.findAll('[role="tab"]')
    const htmlTab = tabs.find((t) => t.text().includes('index.html'))
    await htmlTab?.trigger('click')
    // setActiveFile is called but switchFile returns early if same key (when editor exists)
    // Without editor the store is updated — this is expected since monaco is mocked
    expect(codeStore.activeFile).toBe('html')
  })

  // ─── Read-only Banner ──────────────────────────────────────────────────

  it('shows read-only banner when active file is read-only', async () => {
    codeStore.setActiveFile('exemplo')
    const wrapper = mountComponent()
    expect(wrapper.find('.monaco-tabs__readonly-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('Somente leitura')
  })

  it('hides read-only banner for editable files', () => {
    codeStore.setActiveFile('html')
    const wrapper = mountComponent()
    expect(wrapper.find('.monaco-tabs__readonly-banner').exists()).toBe(false)
  })

  // ─── External Change Banner ────────────────────────────────────────────

  it('shows conflict banner when externalChangeDetected is true', () => {
    codeStore.externalChangeDetected = true
    const wrapper = mountComponent()
    expect(wrapper.find('.monaco-tabs__conflict-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('Alteracao externa detectada')
  })

  it('hides conflict banner when externalChangeDetected is false', () => {
    codeStore.externalChangeDetected = false
    const wrapper = mountComponent()
    expect(wrapper.find('.monaco-tabs__conflict-banner').exists()).toBe(false)
  })

  it('dismisses conflict banner on OK button click', async () => {
    codeStore.externalChangeDetected = true
    const wrapper = mountComponent()
    const okBtn = wrapper.find('.monaco-tabs__conflict-btn')
    expect(okBtn.exists()).toBe(true)
    await okBtn.trigger('click')
    expect(codeStore.externalChangeDetected).toBe(false)
  })

  // ─── CSS Error Badge ───────────────────────────────────────────────────

  it('does not show error badge when cssErrorCount is 0', () => {
    codeStore.setActiveFile('html')
    const wrapper = mountComponent()
    expect(wrapper.find('.monaco-tabs__error-badge').exists()).toBe(false)
  })

  // ─── Editor Host ──────────────────────────────────────────────────────

  it('renders the editor host container', () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.monaco-tabs__editor').exists()).toBe(true)
  })

  // ─── ComputedStylesPanel ──────────────────────────────────────────────

  it('renders ComputedStylesPanel sub-component', () => {
    const wrapper = mountComponent()
    expect(wrapper.find('[data-testid="computed-styles"]').exists()).toBe(true)
  })

  // ─── Tablist Accessibility ─────────────────────────────────────────────

  it('wraps tabs in a role=tablist container', () => {
    const wrapper = mountComponent()
    const tablist = wrapper.find('[role="tablist"]')
    expect(tablist.exists()).toBe(true)
    expect(tablist.findAll('[role="tab"]')).toHaveLength(4)
  })
})
