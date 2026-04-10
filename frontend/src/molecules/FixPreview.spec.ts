import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FixPreview from './FixPreview.vue'
import type { FixSuggestion } from '@/stores/autoFixStore'

function makeSuggestion(overrides: Partial<FixSuggestion> = {}): FixSuggestion {
  return {
    id: 'fix-001',
    type: 'spacing',
    description: 'Espaçamento inconsistente detectado',
    element_id: 'node-123',
    current_value: '8px',
    suggested_value: '16px',
    confidence: 90,
    ...overrides,
  }
}

describe('FixPreview', () => {
  it('renders the description', () => {
    const wrapper = mount(FixPreview, { props: { suggestion: makeSuggestion() } })
    expect(wrapper.find('[data-testid="fix-description"]').text()).toContain(
      'Espaçamento inconsistente detectado',
    )
  })

  it('renders current value in before slot', () => {
    const wrapper = mount(FixPreview, { props: { suggestion: makeSuggestion() } })
    expect(wrapper.find('[data-testid="fix-before"]').text()).toContain('8px')
  })

  it('renders suggested value in after slot', () => {
    const wrapper = mount(FixPreview, { props: { suggestion: makeSuggestion() } })
    expect(wrapper.find('[data-testid="fix-after"]').text()).toContain('16px')
  })

  it('shows confidence percentage', () => {
    const wrapper = mount(FixPreview, { props: { suggestion: makeSuggestion({ confidence: 90 }) } })
    expect(wrapper.text()).toContain('90% confiança')
  })

  it('shows type label for spacing', () => {
    const wrapper = mount(FixPreview, {
      props: { suggestion: makeSuggestion({ type: 'spacing' }) },
    })
    expect(wrapper.text()).toContain('Espaçamento')
  })

  it('shows type label for alignment', () => {
    const wrapper = mount(FixPreview, {
      props: { suggestion: makeSuggestion({ type: 'alignment' }) },
    })
    expect(wrapper.text()).toContain('Alinhamento')
  })

  it('shows type label for font', () => {
    const wrapper = mount(FixPreview, { props: { suggestion: makeSuggestion({ type: 'font' }) } })
    expect(wrapper.text()).toContain('Fonte')
  })

  it('shows type label for binding', () => {
    const wrapper = mount(FixPreview, {
      props: { suggestion: makeSuggestion({ type: 'binding' }) },
    })
    expect(wrapper.text()).toContain('Binding')
  })

  it('shows type label for position', () => {
    const wrapper = mount(FixPreview, {
      props: { suggestion: makeSuggestion({ type: 'position' }) },
    })
    expect(wrapper.text()).toContain('Posição')
  })

  it('shows element_id', () => {
    const wrapper = mount(FixPreview, {
      props: { suggestion: makeSuggestion({ element_id: 'my-node-42' }) },
    })
    expect(wrapper.text()).toContain('my-node-42')
  })

  it('shows (vazio) when current_value is empty', () => {
    const wrapper = mount(FixPreview, {
      props: { suggestion: makeSuggestion({ current_value: '' }) },
    })
    expect(wrapper.find('[data-testid="fix-before"]').text()).toContain('(vazio)')
  })

  it('has diff section rendered', () => {
    const wrapper = mount(FixPreview, { props: { suggestion: makeSuggestion() } })
    expect(wrapper.find('[data-testid="fix-diff"]').exists()).toBe(true)
  })

  it('renders root element with data-testid fix-preview', () => {
    const wrapper = mount(FixPreview, { props: { suggestion: makeSuggestion() } })
    expect(wrapper.find('[data-testid="fix-preview"]').exists()).toBe(true)
  })
})
