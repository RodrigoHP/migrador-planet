import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ToggleButton from './ToggleButton.vue'

describe('ToggleButton', () => {
  it('renders icon and label', () => {
    const wrapper = mount(ToggleButton, {
      props: { icon: '🗺️', label: 'Cobertura', active: false },
    })
    expect(wrapper.text()).toContain('🗺️')
    expect(wrapper.text()).toContain('Cobertura')
  })

  it('has aria-pressed=false when not active', () => {
    const wrapper = mount(ToggleButton, {
      props: { icon: '🗺️', label: 'Cobertura', active: false },
    })
    expect(wrapper.attributes('aria-pressed')).toBe('false')
  })

  it('has aria-pressed=true when active', () => {
    const wrapper = mount(ToggleButton, {
      props: { icon: '🗺️', label: 'Cobertura', active: true },
    })
    expect(wrapper.attributes('aria-pressed')).toBe('true')
  })

  it('applies active class when active=true', () => {
    const wrapper = mount(ToggleButton, {
      props: { icon: '🗺️', label: 'Cobertura', active: true },
    })
    expect(wrapper.classes()).toContain('toggle-button--active')
  })

  it('does not apply active class when active=false', () => {
    const wrapper = mount(ToggleButton, {
      props: { icon: '🗺️', label: 'Cobertura', active: false },
    })
    expect(wrapper.classes()).not.toContain('toggle-button--active')
  })

  it('emits click on button click', async () => {
    const wrapper = mount(ToggleButton, {
      props: { icon: '🗺️', label: 'Cobertura', active: false },
    })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
