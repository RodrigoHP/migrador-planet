import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import CanvasContextMenu from './CanvasContextMenu.vue'

function mountMenu(props: { visible: boolean; x: number; y: number }) {
  return mount(CanvasContextMenu, {
    props,
    attachTo: document.body,
  })
}

describe('CanvasContextMenu — Story 30.7: keyboard hints', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // AC4: ctx-remove item must display "Del" shortcut hint
  it('shows Del hint next to Remover Elemento', async () => {
    const wrapper = mountMenu({ visible: true, x: 0, y: 0 })
    await flushPromises()

    const removeBtn = document.querySelector('[data-testid="ctx-remove"]')
    expect(removeBtn).not.toBeNull()
    expect(removeBtn?.textContent).toContain('Del')

    wrapper.unmount()
  })

  // AC5: kbd element is present and uses the __kbd class
  it('renders kbd element inside ctx-remove button', async () => {
    const wrapper = mountMenu({ visible: true, x: 0, y: 0 })
    await flushPromises()

    const kbdEl = document.querySelector('[data-testid="ctx-remove"] kbd')
    expect(kbdEl).not.toBeNull()
    expect(kbdEl?.classList.contains('canvas-context-menu__kbd')).toBe(true)
    expect(kbdEl?.textContent).toBe('Del')

    wrapper.unmount()
  })

  // Other items should NOT have kbd hints (only Remover has one in this story)
  it('does not add kbd hints to non-remove items', async () => {
    const wrapper = mountMenu({ visible: true, x: 0, y: 0 })
    await flushPromises()

    const mapBtn = document.querySelector('[data-testid="ctx-map-field"]')
    expect(mapBtn?.querySelector('kbd')).toBeNull()

    const convertBtn = document.querySelector('[data-testid="ctx-convert-table"]')
    expect(convertBtn?.querySelector('kbd')).toBeNull()

    wrapper.unmount()
  })
})
