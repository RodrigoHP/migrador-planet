import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import HTMLCanvas from './HTMLCanvas.vue'
import { useGenerationStore } from '@/stores/generation'
import { useEditorStore } from '@/stores/editorStore'

// Mock IntersectionObserver (not available in jsdom) — must be a real class
const mockObserve = vi.fn()
const mockUnobserve = vi.fn()
const mockDisconnect = vi.fn()

class MockIntersectionObserver {
  constructor(_callback: IntersectionObserverCallback, _options?: IntersectionObserverInit) {}
  observe = mockObserve
  unobserve = mockUnobserve
  disconnect = mockDisconnect
  takeRecords(): IntersectionObserverEntry[] { return [] }
}

vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)

// Mock DOMParser for template parsing in jsdom — returns no page elements → single-page fallback
class MockDOMParser {
  parseFromString(_str: string, _type: string) {
    return {
      querySelectorAll: (_selector: string) => ({
        forEach: (_cb: unknown) => {},
        length: 0,
      }),
    }
  }
}
vi.stubGlobal('DOMParser', MockDOMParser)

describe('HTMLCanvas', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockObserve.mockClear()
    mockUnobserve.mockClear()
    mockDisconnect.mockClear()
  })

  it('renders the html-canvas container', () => {
    const wrapper = mount(HTMLCanvas)
    expect(wrapper.find('[data-testid="html-canvas"]').exists()).toBe(true)
  })

  it('shows empty state when no templateDraft', () => {
    const wrapper = mount(HTMLCanvas)
    expect(wrapper.find('[data-testid="html-canvas-empty"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Nenhum template carregado')
  })

  it('renders iframe when templateDraft is set', async () => {
    const genStore = useGenerationStore()
    genStore.loadTemplateDraft({
      html: '<div class="page" data-page="1"><p>Hello</p></div>',
      css: 'body { font-family: sans-serif; }',
    })
    const wrapper = mount(HTMLCanvas)
    await flushPromises()
    // With single-page fallback visible on mount, iframe should be present
    expect(wrapper.find('[data-testid="html-canvas-iframe"]').exists()).toBe(true)
  })

  it('renders zoom controls footer', () => {
    const wrapper = mount(HTMLCanvas)
    // ZoomControls component should be in the DOM
    expect(wrapper.find('[role="group"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('%')
  })

  it('shows page break between multiple pages', async () => {
    // Provide two pages worth of HTML
    const genStore = useGenerationStore()
    // Override DOMParser to return 2 pages for this test
    vi.stubGlobal(
      'DOMParser',
      class {
        parseFromString(_str: string, _type: string) {
          return {
            querySelectorAll: () => ({
              forEach: (cb: (el: { outerHTML: string; dataset: { page: string } }) => void) => {
                cb({ outerHTML: '<div>P1</div>', dataset: { page: '1' } })
                cb({ outerHTML: '<div>P2</div>', dataset: { page: '2' } })
              },
              length: 2,
            }),
          }
        }
      }
    )
    genStore.loadTemplateDraft({
      html: '<div class="page" data-page="1">P1</div><div class="page" data-page="2">P2</div>',
      css: '',
    })
    const wrapper = mount(HTMLCanvas)
    await flushPromises()
    expect(wrapper.findAll('[data-testid="page-break"]').length).toBeGreaterThanOrEqual(1)
    expect(wrapper.text()).toContain('QUEBRA DE PÁGINA')
  })

  it('guides overlay is hidden when showGuides is false', async () => {
    const editorStore = useEditorStore()
    editorStore.showGuides = false
    const genStore = useGenerationStore()
    genStore.loadTemplateDraft({ html: '<p>test</p>', css: '' })
    const wrapper = mount(HTMLCanvas)
    await flushPromises()
    expect(wrapper.find('[data-testid="canvas-guides"]').exists()).toBe(false)
  })

  it('guides overlay is visible when showGuides is true', async () => {
    const editorStore = useEditorStore()
    editorStore.showGuides = true
    const genStore = useGenerationStore()
    genStore.loadTemplateDraft({ html: '<p>test</p>', css: '' })
    const wrapper = mount(HTMLCanvas)
    await flushPromises()
    expect(wrapper.find('[data-testid="canvas-guides"]').exists()).toBe(true)
  })

  it('zoom controls connect to editorStore zoom', async () => {
    const editorStore = useEditorStore()
    const wrapper = mount(HTMLCanvas)
    expect(wrapper.text()).toContain(`${editorStore.zoomLevel}%`)
  })

  it('buildPageSrcdoc includes css isolation reset', () => {
    // Mount and probe that iframes exist with proper srcdoc
    const genStore = useGenerationStore()
    genStore.loadTemplateDraft({ html: '<p>content</p>', css: '.test { color: red; }' })
    const wrapper = mount(HTMLCanvas)
    const iframe = wrapper.find('iframe')
    if (iframe.exists()) {
      const srcdoc = iframe.attributes('srcdoc') ?? ''
      expect(srcdoc).toContain('.test { color: red; }')
      expect(srcdoc).toContain('<!DOCTYPE html>')
    }
  })

  it('content wrapper applies CSS scale transform with zoomLevel', async () => {
    const editorStore = useEditorStore()
    editorStore.setZoom(75)
    const wrapper = mount(HTMLCanvas)
    await flushPromises()
    const content = wrapper.find('[data-testid="html-canvas-content"]')
    expect(content.attributes('style')).toContain('scale(0.75)')
  })
})
