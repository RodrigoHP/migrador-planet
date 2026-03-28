import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import EditorLayout from './EditorLayout.vue'

// Mock supabase client so module loads without env vars
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null } })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
    },
  },
}))

// Mock child organisms to isolate layout tests
vi.mock('@/organisms/TopToolbar.vue', () => ({
  default: { template: '<div class="top-toolbar-mock" />' },
}))
vi.mock('@/organisms/LeftPanel.vue', () => ({
  default: { template: '<div class="left-panel-mock" />' },
}))
vi.mock('@/organisms/CenterPanel.vue', () => ({
  default: { template: '<div class="center-panel-mock" />' },
}))
vi.mock('@/atoms/ResizableHandle.vue', () => ({
  default: { template: '<div class="resizable-handle-mock" />', props: ['direction'] },
}))

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

describe('EditorLayout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders grid layout container', () => {
    const wrapper = mount(EditorLayout)
    expect(wrapper.find('.editor-layout').exists()).toBe(true)
  })

  it('renders TopToolbar in toolbar area', () => {
    const wrapper = mount(EditorLayout)
    expect(wrapper.find('.top-toolbar-mock').exists()).toBe(true)
  })

  it('renders LeftPanel', () => {
    const wrapper = mount(EditorLayout)
    expect(wrapper.find('.left-panel-mock').exists()).toBe(true)
  })

  it('renders CenterPanel', () => {
    const wrapper = mount(EditorLayout)
    expect(wrapper.find('.center-panel-mock').exists()).toBe(true)
  })

  it('renders inspector placeholder', () => {
    const wrapper = mount(EditorLayout)
    expect(wrapper.find('.editor-layout__inspector').exists()).toBe(true)
    expect(wrapper.text()).toContain('Inspetor')
  })

  it('renders bottom panel', () => {
    const wrapper = mount(EditorLayout)
    expect(wrapper.find('.editor-layout__bottom').exists()).toBe(true)
  })

  it('bottom panel is not collapsed by default', () => {
    const wrapper = mount(EditorLayout)
    const bottom = wrapper.find('.editor-layout__bottom')
    expect(bottom.classes()).not.toContain('editor-layout__bottom--collapsed')
  })

  it('toggles bottom panel on chevron button click', async () => {
    const wrapper = mount(EditorLayout)
    const btn = wrapper.find('.editor-layout__bottom-toggle')
    await btn.trigger('click')
    const bottom = wrapper.find('.editor-layout__bottom')
    expect(bottom.classes()).toContain('editor-layout__bottom--collapsed')
  })

  it('re-expands bottom panel on second toggle click', async () => {
    const wrapper = mount(EditorLayout)
    const btn = wrapper.find('.editor-layout__bottom-toggle')
    await btn.trigger('click')
    await btn.trigger('click')
    const bottom = wrapper.find('.editor-layout__bottom')
    expect(bottom.classes()).not.toContain('editor-layout__bottom--collapsed')
  })

  it('applies --left-panel-width CSS variable in style', () => {
    const wrapper = mount(EditorLayout)
    const style = wrapper.find('.editor-layout').attributes('style')
    expect(style).toContain('--left-panel-width')
  })

  it('applies --inspector-width CSS variable in style', () => {
    const wrapper = mount(EditorLayout)
    const style = wrapper.find('.editor-layout').attributes('style')
    expect(style).toContain('--inspector-width')
  })

  it('renders ResizableHandle components', () => {
    const wrapper = mount(EditorLayout)
    expect(wrapper.findAll('.resizable-handle-mock').length).toBeGreaterThanOrEqual(2)
  })
})
