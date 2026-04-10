import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, ref, h, nextTick } from 'vue'
import { useFocusTrap } from './useFocusTrap'

function createTestComponent(active: boolean) {
  return defineComponent({
    setup() {
      const containerRef = ref<HTMLElement | null>(null)
      const isActive = ref(active)
      useFocusTrap(containerRef, isActive)
      return { containerRef, isActive }
    },
    render() {
      return h('div', { ref: 'containerRef', tabindex: '-1' }, [
        h('button', { id: 'btn1' }, 'First'),
        h('input', { id: 'input1', type: 'text' }),
        h('button', { id: 'btn2' }, 'Last'),
      ])
    },
  })
}

describe('useFocusTrap', () => {
  it('focuses first focusable element on activation', async () => {
    const wrapper = mount(createTestComponent(true), {
      attachTo: document.body,
    })
    await nextTick()
    await nextTick() // Wait for focus trap nextTick

    expect(document.activeElement?.id).toBe('btn1')
    wrapper.unmount()
  })

  it('wraps focus from last to first on Tab', async () => {
    const wrapper = mount(createTestComponent(true), {
      attachTo: document.body,
    })
    await nextTick()
    await nextTick()

    // Focus last button
    const btn2 = document.getElementById('btn2')!
    btn2.focus()
    expect(document.activeElement?.id).toBe('btn2')

    // Press Tab on last element — should wrap to first
    const tabEvent = new KeyboardEvent('keydown', {
      key: 'Tab',
      bubbles: true,
      cancelable: true,
    })
    document.dispatchEvent(tabEvent)

    expect(document.activeElement?.id).toBe('btn1')
    wrapper.unmount()
  })

  it('wraps focus from first to last on Shift+Tab', async () => {
    const wrapper = mount(createTestComponent(true), {
      attachTo: document.body,
    })
    await nextTick()
    await nextTick()

    // Focus should be on first button
    expect(document.activeElement?.id).toBe('btn1')

    // Press Shift+Tab on first element — should wrap to last
    const shiftTabEvent = new KeyboardEvent('keydown', {
      key: 'Tab',
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    })
    document.dispatchEvent(shiftTabEvent)

    expect(document.activeElement?.id).toBe('btn2')
    wrapper.unmount()
  })

  it('deactivates trap and restores focus on unmount', async () => {
    // Create an external button to be the "previously focused" element
    const externalBtn = document.createElement('button')
    externalBtn.id = 'external'
    document.body.appendChild(externalBtn)
    externalBtn.focus()

    const wrapper = mount(createTestComponent(true), {
      attachTo: document.body,
    })
    await nextTick()
    await nextTick()

    // Focus is inside trap
    expect(document.activeElement?.id).toBe('btn1')

    // Unmount should restore focus to external button
    wrapper.unmount()
    expect(document.activeElement?.id).toBe('external')

    document.body.removeChild(externalBtn)
  })
})
