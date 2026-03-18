import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DetectionCard from './DetectionCard.vue'
import type { Detection } from '@/types/multi-doc.types'

function makeDetection(overrides: Partial<Detection> = {}): Detection {
  return {
    id: 'det-1',
    pdfId: 'pdf-1',
    type: 'required',
    description: 'Campo obrigatório em todos os docs',
    confidence: 0.95,
    ...overrides,
  }
}

describe('DetectionCard', () => {
  it('renders detection description', () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection() },
    })
    expect(wrapper.text()).toContain('Campo obrigatório em todos os docs')
  })

  it('renders type badge with label', () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection({ type: 'optional_field' }) },
    })
    expect(wrapper.text()).toContain('Campo Opcional')
  })

  it('renders confidence percentage', () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection({ confidence: 0.75 }) },
    })
    expect(wrapper.text()).toContain('75%')
  })

  it('emits confirm event with detection id on confirm button click', async () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection({ id: 'det-abc' }) },
    })
    await wrapper.find('[aria-label="Confirmar inferência"]').trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('confirm')?.[0]).toEqual(['det-abc'])
  })

  it('emits reject event with detection id on reject button click', async () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection({ id: 'det-xyz' }) },
    })
    await wrapper.find('[aria-label="Rejeitar inferência"]').trigger('click')
    expect(wrapper.emitted('reject')).toBeTruthy()
    expect(wrapper.emitted('reject')?.[0]).toEqual(['det-xyz'])
  })

  it('applies high confidence class when confidence >= 80%', () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection({ confidence: 0.9 }) },
    })
    const badge = wrapper.find('.detection-card__confidence')
    expect(badge.classes()).toContain('detection-card__confidence--high')
  })

  it('applies medium confidence class when confidence 50-79%', () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection({ confidence: 0.6 }) },
    })
    const badge = wrapper.find('.detection-card__confidence')
    expect(badge.classes()).toContain('detection-card__confidence--medium')
  })

  it('applies low confidence class when confidence < 50%', () => {
    const wrapper = mount(DetectionCard, {
      props: { detection: makeDetection({ confidence: 0.3 }) },
    })
    const badge = wrapper.find('.detection-card__confidence')
    expect(badge.classes()).toContain('detection-card__confidence--low')
  })

  it('renders all detection types correctly', () => {
    const types: Detection['type'][] = [
      'required',
      'optional_field',
      'optional_section',
      'conditional_section',
      'dynamic_table',
    ]
    const labels = ['Obrigatório', 'Campo Opcional', 'Seção Opcional', 'Seção Condicional', 'Tabela Dinâmica']

    types.forEach((type, idx) => {
      const wrapper = mount(DetectionCard, {
        props: { detection: makeDetection({ type }) },
      })
      expect(wrapper.text()).toContain(labels[idx])
    })
  })
})
