import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CrossValidationBadge from './CrossValidationBadge.vue'

describe('CrossValidationBadge', () => {
  it('shows compatible title when status is ok', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: 'ok', divergences: [] },
    })
    expect(wrapper.text()).toContain('Arquivos compat\u00edveis')
  })

  it('shows divergence title when status is divergence', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: 'divergence', divergences: ['field mismatch'] },
    })
    expect(wrapper.text()).toContain('Diverg\u00eancias encontradas')
  })

  it('shows waiting title when status is null', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: null, divergences: [] },
    })
    expect(wrapper.text()).toContain('Aguardando valida\u00e7\u00e3o')
  })

  it('applies ok class for ok status', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: 'ok', divergences: [] },
    })
    expect(wrapper.find('.cross-badge--ok').exists()).toBe(true)
  })

  it('applies divergence class for divergence status', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: 'divergence', divergences: [] },
    })
    expect(wrapper.find('.cross-badge--divergence').exists()).toBe(true)
  })

  it('applies neutral class for null status', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: null, divergences: [] },
    })
    expect(wrapper.find('.cross-badge--neutral').exists()).toBe(true)
  })

  it('renders divergence items as list when status is divergence', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: 'divergence', divergences: ['item A', 'item B'] },
    })
    const items = wrapper.findAll('.cross-badge__list li')
    expect(items.length).toBe(2)
    expect(items[0].text()).toBe('item A')
    expect(items[1].text()).toBe('item B')
  })

  it('does not render list when status is ok', () => {
    const wrapper = mount(CrossValidationBadge, {
      props: { status: 'ok', divergences: [] },
    })
    expect(wrapper.find('.cross-badge__list').exists()).toBe(false)
  })
})
