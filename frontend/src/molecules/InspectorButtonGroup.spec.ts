import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import InspectorButtonGroup from './InspectorButtonGroup.vue'

const alignOptions = [
  { value: 'left', icon: '⫷', label: 'Esquerda' },
  { value: 'center', icon: '⫶', label: 'Centro' },
  { value: 'right', icon: '⫸', label: 'Direita' },
]

const decoOptions = [
  { value: 'underline', icon: 'U̲', label: 'Sublinhado' },
  { value: 'line-through', icon: 'S̶', label: 'Tachado' },
]

describe('InspectorButtonGroup', () => {
  it('renders all option buttons', () => {
    const w = mount(InspectorButtonGroup, {
      props: { options: alignOptions, modelValue: 'left' },
    })
    const btns = w.findAll('.inspector-btn-group__btn')
    expect(btns).toHaveLength(3)
  })

  it('marks active button with aria-pressed', () => {
    const w = mount(InspectorButtonGroup, {
      props: { options: alignOptions, modelValue: 'center' },
    })
    const btns = w.findAll('.inspector-btn-group__btn')
    expect(btns[0].attributes('aria-pressed')).toBe('false')
    expect(btns[1].attributes('aria-pressed')).toBe('true')
    expect(btns[2].attributes('aria-pressed')).toBe('false')
  })

  it('emits update:modelValue on click (single mode)', async () => {
    const w = mount(InspectorButtonGroup, {
      props: { options: alignOptions, modelValue: 'left' },
    })
    await w.findAll('.inspector-btn-group__btn')[2].trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual(['right'])
  })

  it('renders label when provided', () => {
    const w = mount(InspectorButtonGroup, {
      props: { options: alignOptions, modelValue: 'left', label: 'Alinhamento' },
    })
    expect(w.text()).toContain('Alinhamento')
  })

  it('multiple mode: toggles values in space-separated string', async () => {
    const w = mount(InspectorButtonGroup, {
      props: { options: decoOptions, modelValue: 'underline', multiple: true },
    })
    // Add line-through
    await w.findAll('.inspector-btn-group__btn')[1].trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual(['underline line-through'])
  })

  it('multiple mode: removing last value emits "none"', async () => {
    const w = mount(InspectorButtonGroup, {
      props: { options: decoOptions, modelValue: 'underline', multiple: true },
    })
    // Remove underline (only active value)
    await w.findAll('.inspector-btn-group__btn')[0].trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual(['none'])
  })

  it('multiple mode: marks multiple active buttons', () => {
    const w = mount(InspectorButtonGroup, {
      props: { options: decoOptions, modelValue: 'underline line-through', multiple: true },
    })
    const btns = w.findAll('.inspector-btn-group__btn')
    expect(btns[0].attributes('aria-pressed')).toBe('true')
    expect(btns[1].attributes('aria-pressed')).toBe('true')
  })
})
