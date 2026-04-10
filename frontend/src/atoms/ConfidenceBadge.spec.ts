import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfidenceBadge from './ConfidenceBadge.vue'

describe('ConfidenceBadge', () => {
  it('renders the confidence text', () => {
    const wrapper = mount(ConfidenceBadge, { props: { confidence: 'high' } })
    expect(wrapper.text()).toBe('high')
  })

  it('applies badge--high class for high confidence', () => {
    const wrapper = mount(ConfidenceBadge, { props: { confidence: 'high' } })
    expect(wrapper.classes()).toContain('badge--high')
  })

  it('applies badge--medium class for medium confidence', () => {
    const wrapper = mount(ConfidenceBadge, { props: { confidence: 'medium' } })
    expect(wrapper.classes()).toContain('badge--medium')
  })

  it('applies badge--low class for low confidence', () => {
    const wrapper = mount(ConfidenceBadge, { props: { confidence: 'low' } })
    expect(wrapper.classes()).toContain('badge--low')
  })

  it('renders as a span element', () => {
    const wrapper = mount(ConfidenceBadge, { props: { confidence: 'high' } })
    expect(wrapper.element.tagName).toBe('SPAN')
  })

  it('always has the badge base class', () => {
    const wrapper = mount(ConfidenceBadge, { props: { confidence: 'medium' } })
    expect(wrapper.classes()).toContain('badge')
  })
})
