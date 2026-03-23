import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfidenceBadge from './ConfidenceBadge.vue'

describe('ConfidenceBadge', () => {
  it('renders high confidence (>0.8) in green', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 0.95 } })
    expect(wrapper.text()).toBe('0.95')
    expect(wrapper.classes()).toContain('confidence-badge--high')
    expect(wrapper.attributes('title')).toContain('Alta confiança')
  })

  it('renders medium confidence (0.5-0.8) in yellow', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 0.65 } })
    expect(wrapper.text()).toBe('0.65')
    expect(wrapper.classes()).toContain('confidence-badge--medium')
    expect(wrapper.attributes('title')).toContain('Média confiança')
  })

  it('renders low confidence (<0.5) in red', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 0.3 } })
    expect(wrapper.text()).toBe('0.30')
    expect(wrapper.classes()).toContain('confidence-badge--low')
    expect(wrapper.attributes('title')).toContain('Baixa confiança')
  })

  it('renders boundary 0.8 as medium (not >0.8)', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 0.8 } })
    expect(wrapper.classes()).toContain('confidence-badge--medium')
  })

  it('renders boundary 0.5 as medium', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 0.5 } })
    expect(wrapper.classes()).toContain('confidence-badge--medium')
  })

  it('renders score 0 as low', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 0 } })
    expect(wrapper.text()).toBe('0.00')
    expect(wrapper.classes()).toContain('confidence-badge--low')
  })

  it('renders score 1 as high', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 1 } })
    expect(wrapper.text()).toBe('1.00')
    expect(wrapper.classes()).toContain('confidence-badge--high')
  })

  it('renders default (no score) as unknown', () => {
    const wrapper = mount(ConfidenceBadge)
    expect(wrapper.classes()).toContain('confidence-badge--low')
  })

  it('formats to 2 decimal places', () => {
    const wrapper = mount(ConfidenceBadge, { props: { score: 0.857 } })
    expect(wrapper.text()).toBe('0.86')
  })
})
