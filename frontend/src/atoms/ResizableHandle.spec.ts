import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ResizableHandle from './ResizableHandle.vue'

describe('ResizableHandle', () => {
  it('renders with correct direction class — horizontal', () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'horizontal' } })
    expect(wrapper.classes()).toContain('resizable-handle--horizontal')
  })

  it('renders with correct direction class — vertical', () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'vertical' } })
    expect(wrapper.classes()).toContain('resizable-handle--vertical')
  })

  it('has role=separator', () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'horizontal' } })
    expect(wrapper.attributes('role')).toBe('separator')
  })

  it('emits resize on ArrowRight keydown (horizontal)', async () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'horizontal' } })
    await wrapper.trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.emitted('resize')).toBeTruthy()
    expect((wrapper.emitted('resize')![0] as number[])[0]).toBe(10)
  })

  it('emits resize on ArrowLeft keydown (horizontal)', async () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'horizontal' } })
    await wrapper.trigger('keydown', { key: 'ArrowLeft' })
    expect((wrapper.emitted('resize')![0] as number[])[0]).toBe(-10)
  })

  it('emits resize on ArrowDown keydown (vertical)', async () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'vertical' } })
    await wrapper.trigger('keydown', { key: 'ArrowDown' })
    expect((wrapper.emitted('resize')![0] as number[])[0]).toBe(10)
  })

  it('emits resize on ArrowUp keydown (vertical)', async () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'vertical' } })
    await wrapper.trigger('keydown', { key: 'ArrowUp' })
    expect((wrapper.emitted('resize')![0] as number[])[0]).toBe(-10)
  })

  it('does not emit resize on unrelated key', async () => {
    const wrapper = mount(ResizableHandle, { props: { direction: 'horizontal' } })
    await wrapper.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('resize')).toBeFalsy()
  })

  it('registers mousemove/mouseup listeners on mousedown', async () => {
    const addSpy = vi.spyOn(document, 'addEventListener')
    const wrapper = mount(ResizableHandle, { props: { direction: 'horizontal' } })
    await wrapper.trigger('mousedown', { clientX: 100 })
    expect(addSpy).toHaveBeenCalledWith('mousemove', expect.any(Function))
    expect(addSpy).toHaveBeenCalledWith('mouseup', expect.any(Function))
    addSpy.mockRestore()
  })
})
