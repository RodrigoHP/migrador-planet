import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgressBar from './ProgressBar.vue'

describe('ProgressBar', () => {
  it('renders with role=progressbar', () => {
    const wrapper = mount(ProgressBar, { props: { value: 50 } })
    expect(wrapper.attributes('role')).toBe('progressbar')
  })

  it('sets aria-valuenow to given value', () => {
    const wrapper = mount(ProgressBar, { props: { value: 75 } })
    expect(wrapper.attributes('aria-valuenow')).toBe('75')
  })

  it('sets aria-valuemin=0 and aria-valuemax=100', () => {
    const wrapper = mount(ProgressBar, { props: { value: 50 } })
    expect(wrapper.attributes('aria-valuemin')).toBe('0')
    expect(wrapper.attributes('aria-valuemax')).toBe('100')
  })

  it('clamps value below 0 to 0', () => {
    const wrapper = mount(ProgressBar, { props: { value: -10 } })
    expect(wrapper.attributes('aria-valuenow')).toBe('0')
    expect(wrapper.find('.progress__inner').attributes('style')).toContain('width: 0%')
  })

  it('clamps value above 100 to 100', () => {
    const wrapper = mount(ProgressBar, { props: { value: 150 } })
    expect(wrapper.attributes('aria-valuenow')).toBe('100')
    expect(wrapper.find('.progress__inner').attributes('style')).toContain('width: 100%')
  })

  it('sets inner bar width to value percent', () => {
    const wrapper = mount(ProgressBar, { props: { value: 42 } })
    expect(wrapper.find('.progress__inner').attributes('style')).toContain('width: 42%')
  })

  it('applies animated class by default', () => {
    const wrapper = mount(ProgressBar, { props: { value: 50 } })
    expect(wrapper.find('.progress__inner').classes()).toContain('progress__inner--animated')
  })

  it('does not apply animated class when animated=false', () => {
    const wrapper = mount(ProgressBar, { props: { value: 50, animated: false } })
    expect(wrapper.find('.progress__inner').classes()).not.toContain('progress__inner--animated')
  })

  it('rounds fractional values', () => {
    const wrapper = mount(ProgressBar, { props: { value: 33.7 } })
    expect(wrapper.attributes('aria-valuenow')).toBe('34')
  })
})
