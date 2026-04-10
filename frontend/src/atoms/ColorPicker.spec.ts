import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ColorPicker from './ColorPicker.vue'

describe('ColorPicker', () => {
  it('renders the label text', () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: '#ff0000', label: 'Background' },
    })
    expect(wrapper.text()).toContain('Background')
  })

  it('displays the current hex value', () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: '#00ff00', label: 'Cor' },
    })
    expect(wrapper.find('code').text()).toBe('#00ff00')
  })

  it('shows a color swatch with the current color', () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: '#0000ff', label: 'Cor' },
    })
    const swatch = wrapper.find('.color-picker__swatch')
    expect(swatch.attributes('style')).toContain('background-color: rgb(0, 0, 255)')
  })

  it('sets input type=color with current value', () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: '#abcdef', label: 'Cor' },
    })
    const input = wrapper.find('input[type="color"]')
    expect(input.exists()).toBe(true)
    expect((input.element as HTMLInputElement).value).toBe('#abcdef')
  })

  it('emits update:modelValue on input change', async () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: '#000000', label: 'Cor' },
    })
    const input = wrapper.find('input[type="color"]')
    await input.setValue('#ff5500')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['#ff5500'])
  })

  it('renders inside a label element', () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: '#000', label: 'Cor' },
    })
    expect(wrapper.element.tagName).toBe('LABEL')
  })
})
