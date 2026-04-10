import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChecklistItem from './ChecklistItem.vue'

describe('ChecklistItem', () => {
  it('renders the label text', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Check fonts', status: 'ok' },
    })
    expect(wrapper.text()).toContain('Check fonts')
  })

  it('shows check icon for ok status', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Test', status: 'ok' },
    })
    expect(wrapper.find('.check-item__icon').text()).toContain('\u2713')
  })

  it('shows exclamation icon for warning status', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Test', status: 'warning' },
    })
    expect(wrapper.find('.check-item__icon').text()).toBe('!')
  })

  it('shows X icon for error status', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Test', status: 'error' },
    })
    expect(wrapper.find('.check-item__icon').text()).toContain('\u2715')
  })

  it('applies status class', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Test', status: 'warning' },
    })
    expect(wrapper.classes()).toContain('check-item--warning')
  })

  it('renders note when provided', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Test', status: 'ok', note: 'All good' },
    })
    expect(wrapper.find('.check-item__note').text()).toBe('All good')
  })

  it('does not render note when not provided', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Test', status: 'ok' },
    })
    expect(wrapper.find('.check-item__note').exists()).toBe(false)
  })

  it('renders as li element', () => {
    const wrapper = mount(ChecklistItem, {
      props: { label: 'Test', status: 'ok' },
    })
    expect(wrapper.element.tagName).toBe('LI')
  })
})
