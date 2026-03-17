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
    store.layoutTypes = [{ id: 'lt-1', name: 'Transações', pageCount: 2, representativePages: [1] }]
    store.activeLayoutId = 'lt-1'
    const wrapper = mount(LayoutSelector)
    // v-show hides with display:none
    const el = wrapper.find('.layout-selector')
    expect(el.isVisible()).toBe(false)
  })

  it('is visible when > 1 layout types', async () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 2, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 3, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const wrapper = mount(LayoutSelector, { attachTo: document.body })
    const el = wrapper.find('.layout-selector')
    expect(el.isVisible()).toBe(true)
  })

  it('calls setActiveLayout when selection changes', async () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 2, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 3, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const spy = vi.spyOn(store, 'setActiveLayout')
    const wrapper = mount(LayoutSelector)
    const select = wrapper.find('select')
    await select.setValue('lt-2')
    expect(spy).toHaveBeenCalledWith('lt-2')
  })

  it('renders all layout type options', () => {
    const store = useLayoutStore()
    store.layoutTypes = [
      { id: 'lt-1', name: 'Transações', pageCount: 2, representativePages: [1] },
      { id: 'lt-2', name: 'Extrato', pageCount: 3, representativePages: [1] },
    ]
    store.activeLayoutId = 'lt-1'
    const wrapper = mount(LayoutSelector)
    const options = wrapper.findAll('option')
    expect(options).toHaveLength(2)
    expect(options[0]!.text()).toBe('Transações')
    expect(options[1]!.text()).toBe('Extrato')
  })
})
