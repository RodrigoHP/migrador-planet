import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FieldStatusBadge from './FieldStatusBadge.vue'

describe('FieldStatusBadge', () => {
  it('renders the status text', () => {
    const wrapper = mount(FieldStatusBadge, { props: { status: 'ok' } })
    expect(wrapper.text()).toBe('ok')
  })

  it('applies badge--ok class for ok status', () => {
    const wrapper = mount(FieldStatusBadge, { props: { status: 'ok' } })
    expect(wrapper.classes()).toContain('badge--ok')
  })

  it('applies badge--ambiguous class for ambiguous status', () => {
    const wrapper = mount(FieldStatusBadge, { props: { status: 'ambiguous' } })
    expect(wrapper.classes()).toContain('badge--ambiguous')
  })

  it('applies badge--not_found class for not_found status', () => {
    const wrapper = mount(FieldStatusBadge, { props: { status: 'not_found' } })
    expect(wrapper.classes()).toContain('badge--not_found')
  })

  it('applies badge--optional class for optional status', () => {
    const wrapper = mount(FieldStatusBadge, { props: { status: 'optional' } })
    expect(wrapper.classes()).toContain('badge--optional')
  })

  it('renders as a span element', () => {
    const wrapper = mount(FieldStatusBadge, { props: { status: 'ok' } })
    expect(wrapper.element.tagName).toBe('SPAN')
  })

  it('always has the badge base class', () => {
    const wrapper = mount(FieldStatusBadge, { props: { status: 'ambiguous' } })
    expect(wrapper.classes()).toContain('badge')
  })
})
