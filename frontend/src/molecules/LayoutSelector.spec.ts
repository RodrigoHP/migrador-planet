import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import LayoutSelector from './LayoutSelector.vue'
import { useLayoutStore } from '@/stores/layout'

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

describe('LayoutSelector', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('is hidden when only 1 layout type', () => {
    const store = useLayoutStore()
    store.layoutTypes = [{ id: 'lt-1', name: 'Transações', pageCount: 285, docCount: 3, representativePages: [1] }]
    store.activeLayoutId = 'lt-1'
    const wrapper = mount(LayoutSelector)
    // v-show hides with display:none
    const el = wrapper.find('.layout-selector')
    expect(el.isVisible()).toBe(false)
  })

  it('is visible when > 1 layout types', async () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 285, docCount: 3, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 10, docCount: 1, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const wrapper = mount(LayoutSelector, { attachTo: document.body })
    const el = wrapper.find('.layout-selector')
    expect(el.isVisible()).toBe(true)
  })

  it('calls setActiveLayout when selection changes', async () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 285, docCount: 3, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 10, docCount: 1, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const spy = vi.spyOn(store, 'setActiveLayout')
    const wrapper = mount(LayoutSelector)
    const select = wrapper.find('select')
    await select.setValue('lt-2')
    expect(spy).toHaveBeenCalledWith('lt-2')
  })

  it('shows rename input on pencil button click', async () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 285, docCount: 3, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 10, docCount: 1, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const wrapper = mount(LayoutSelector, { attachTo: document.body })
    expect(wrapper.find('.layout-selector__rename-overlay').exists()).toBe(false)
    await wrapper.find('.layout-selector__rename-btn').trigger('click')
    expect(wrapper.find('.layout-selector__rename-overlay').exists()).toBe(true)
    const input = wrapper.find('.layout-selector__rename-input')
    expect((input.element as HTMLInputElement).value).toBe('Transações')
  })

  it('renames layout on Enter key', async () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 285, docCount: 3, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 10, docCount: 1, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const spy = vi.spyOn(store, 'renameLayout')
    const wrapper = mount(LayoutSelector, { attachTo: document.body })
    await wrapper.find('.layout-selector__rename-btn').trigger('click')
    const input = wrapper.find('.layout-selector__rename-input')
    await input.setValue('Novo Nome')
    await input.trigger('keydown.enter')
    expect(spy).toHaveBeenCalledWith('lt-1', 'Novo Nome')
    expect(wrapper.find('.layout-selector__rename-overlay').exists()).toBe(false)
  })

  it('cancels rename on Escape key', async () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 285, docCount: 3, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 10, docCount: 1, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const spy = vi.spyOn(store, 'renameLayout')
    const wrapper = mount(LayoutSelector, { attachTo: document.body })
    await wrapper.find('.layout-selector__rename-btn').trigger('click')
    await wrapper.find('.layout-selector__rename-input').trigger('keydown.escape')
    expect(spy).not.toHaveBeenCalled()
    expect(wrapper.find('.layout-selector__rename-overlay').exists()).toBe(false)
  })

  it('renders all layout type options with pageCount and docCount', () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 285, docCount: 3, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 10, docCount: 1, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const wrapper = mount(LayoutSelector)
    const options = wrapper.findAll('option')
    expect(options).toHaveLength(2)
    expect(options[0]!.text()).toBe('Transações (285 pgs em 3 docs)')
    expect(options[1]!.text()).toBe('Extrato (10 pgs em 1 docs)')
  })
})
