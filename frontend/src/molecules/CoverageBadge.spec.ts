import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CoverageBadge from './CoverageBadge.vue'

describe('CoverageBadge', () => {
  it('displays rounded percentage', () => {
    const wrapper = mount(CoverageBadge, { props: { percentage: 93.3 } })
    expect(wrapper.text()).toContain('93%')
  })

  it('displays -- when percentage is undefined', () => {
    const wrapper = mount(CoverageBadge, { props: { percentage: undefined } })
    expect(wrapper.text()).toContain('--%')
  })

  it('applies green class when >= 95', () => {
    const wrapper = mount(CoverageBadge, { props: { percentage: 97 } })
    expect(wrapper.classes()).toContain('coverage-badge--green')
  })

  it('applies yellow class when 80-94', () => {
    const wrapper = mount(CoverageBadge, { props: { percentage: 82 } })
    expect(wrapper.classes()).toContain('coverage-badge--yellow')
  })

  it('applies red class when < 80', () => {
    const wrapper = mount(CoverageBadge, { props: { percentage: 50 } })
    expect(wrapper.classes()).toContain('coverage-badge--red')
  })

  it('emits click when clicked', async () => {
    const wrapper = mount(CoverageBadge, { props: { percentage: 93 } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })

  it('has correct aria-label', () => {
    const wrapper = mount(CoverageBadge, { props: { percentage: 93 } })
    expect(wrapper.attributes('aria-label')).toBe('Cobertura: 93%')
  })
})
