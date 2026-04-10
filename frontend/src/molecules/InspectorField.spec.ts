import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import InspectorField from './InspectorField.vue'

describe('InspectorField', () => {
  it('renders the label text', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Width', value: '100px' },
    })
    expect(wrapper.find('.inspector-field__label').text()).toBe('Width')
  })

  it('renders the value as plain text by default', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Font Size', value: '16px' },
    })
    expect(wrapper.find('.inspector-field__value').text()).toBe('16px')
  })

  it('renders numeric values', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Width', value: 200 },
    })
    expect(wrapper.find('.inspector-field__value').text()).toBe('200')
  })

  it('renders color swatch when type=color', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Background', value: '#ff0000', type: 'color' },
    })
    expect(wrapper.find('.inspector-field__color-swatch').exists()).toBe(true)
    expect(wrapper.find('.inspector-field__color-swatch').attributes('style')).toContain(
      'background',
    )
  })

  it('renders badge when type=badge', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Status', value: 'active', type: 'badge' },
    })
    expect(wrapper.find('.inspector-field__badge').exists()).toBe(true)
    expect(wrapper.find('.inspector-field__badge').text()).toBe('active')
  })

  it('does not render color swatch for text type', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Name', value: 'Test' },
    })
    expect(wrapper.find('.inspector-field__color-swatch').exists()).toBe(false)
  })

  it('does not render badge for text type', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Name', value: 'Test' },
    })
    expect(wrapper.find('.inspector-field__badge').exists()).toBe(false)
  })

  it('has inspector-field class on root', () => {
    const wrapper = mount(InspectorField, {
      props: { label: 'Test', value: 'val' },
    })
    expect(wrapper.classes()).toContain('inspector-field')
  })
})
