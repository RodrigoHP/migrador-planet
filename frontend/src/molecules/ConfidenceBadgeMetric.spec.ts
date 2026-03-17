import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfidenceBadgeMetric from './ConfidenceBadgeMetric.vue'

describe('ConfidenceBadgeMetric', () => {
  it('displays rounded percentage', () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: 91.6 } })
    expect(wrapper.text()).toContain('92%')
  })

  it('displays -- when percentage is undefined', () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: undefined } })
    expect(wrapper.text()).toContain('--%')
  })

  it('applies green class when >= 95', () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: 95 } })
    expect(wrapper.classes()).toContain('confidence-badge-metric--green')
  })

  it('applies yellow class when 80-94', () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: 85 } })
    expect(wrapper.classes()).toContain('confidence-badge-metric--yellow')
  })

  it('applies red class when < 80', () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: 60 } })
    expect(wrapper.classes()).toContain('confidence-badge-metric--red')
  })

  it('applies unknown class when undefined', () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: undefined } })
    expect(wrapper.classes()).toContain('confidence-badge-metric--unknown')
  })

  it('emits click when clicked', async () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: 91 } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })

  it('has correct aria-label', () => {
    const wrapper = mount(ConfidenceBadgeMetric, { props: { percentage: 91 } })
    expect(wrapper.attributes('aria-label')).toBe('Confiança: 91%')
  })
})
