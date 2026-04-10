import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Button from './Button.vue'

describe('Button', () => {
  it('renders slot content', () => {
    const wrapper = mount(Button, { slots: { default: 'Click me' } })
    expect(wrapper.text()).toContain('Click me')
  })

  it('applies primary variant class by default', () => {
    const wrapper = mount(Button)
    expect(wrapper.classes()).toContain('btn--primary')
  })

  it('applies the given variant class', () => {
    const wrapper = mount(Button, { props: { variant: 'danger' } })
    expect(wrapper.classes()).toContain('btn--danger')
  })

  it('applies the given size class', () => {
    const wrapper = mount(Button, { props: { size: 'lg' } })
    expect(wrapper.classes()).toContain('btn--lg')
  })

  it('defaults to md size', () => {
    const wrapper = mount(Button)
    expect(wrapper.classes()).toContain('btn--md')
  })

  it('is disabled when disabled=true', () => {
    const wrapper = mount(Button, { props: { disabled: true } })
    expect((wrapper.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('is disabled when loading=true', () => {
    const wrapper = mount(Button, { props: { loading: true } })
    expect((wrapper.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('shows spinner when loading', () => {
    const wrapper = mount(Button, { props: { loading: true } })
    expect(wrapper.find('.btn__spinner').exists()).toBe(true)
  })

  it('does not show spinner when not loading', () => {
    const wrapper = mount(Button, { props: { loading: false } })
    expect(wrapper.find('.btn__spinner').exists()).toBe(false)
  })

  it('sets aria-busy=true when loading', () => {
    const wrapper = mount(Button, { props: { loading: true } })
    expect(wrapper.attributes('aria-busy')).toBe('true')
  })

  it('sets aria-busy=false when not loading', () => {
    const wrapper = mount(Button)
    expect(wrapper.attributes('aria-busy')).toBe('false')
  })
})
