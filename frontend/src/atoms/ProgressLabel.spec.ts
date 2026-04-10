import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgressLabel from './ProgressLabel.vue'

describe('ProgressLabel', () => {
  it('renders the text prop', () => {
    const wrapper = mount(ProgressLabel, { props: { text: 'Processando...' } })
    expect(wrapper.text()).toContain('Processando...')
  })

  it('renders a spinner element', () => {
    const wrapper = mount(ProgressLabel, { props: { text: 'Loading' } })
    expect(wrapper.find('.progress-label__spinner').exists()).toBe(true)
  })

  it('marks spinner as aria-hidden', () => {
    const wrapper = mount(ProgressLabel, { props: { text: 'Loading' } })
    expect(wrapper.find('.progress-label__spinner').attributes('aria-hidden')).toBe('true')
  })

  it('has the progress-label class', () => {
    const wrapper = mount(ProgressLabel, { props: { text: 'Test' } })
    expect(wrapper.classes()).toContain('progress-label')
  })
})
