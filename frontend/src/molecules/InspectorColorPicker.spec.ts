import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import InspectorColorPicker from './InspectorColorPicker.vue'

const baseProps = {
  label: 'Cor de Fundo',
  modelValue: '#336699',
}

describe('InspectorColorPicker', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders label and color swatch', () => {
    const w = mount(InspectorColorPicker, { props: baseProps })
    expect(w.find('.inspector-color-picker__label').text()).toBe('Cor de Fundo')
    expect(w.find('input[type="color"]').exists()).toBe(true)
  })

  it('displays hex value', () => {
    const w = mount(InspectorColorPicker, { props: baseProps })
    expect(w.find('.inspector-color-picker__hex').text()).toBe('#336699')
  })

  it('emits update:modelValue on color input', async () => {
    const w = mount(InspectorColorPicker, { props: baseProps })
    const input = w.find('input[type="color"]')
    await input.setValue('#ff0000')
    await input.trigger('input')
    expect(w.emitted('update:modelValue')).toBeTruthy()
  })

  it('shows opacity slider when enableAlpha=true (default)', () => {
    const w = mount(InspectorColorPicker, { props: baseProps })
    expect(w.find('.inspector-color-picker__opacity-slider').exists()).toBe(true)
    expect(w.find('input[type="range"]').attributes('aria-label')).toBe('Opacidade')
  })

  it('hides opacity slider when enableAlpha=false', () => {
    const w = mount(InspectorColorPicker, { props: { ...baseProps, enableAlpha: false } })
    expect(w.find('.inspector-color-picker__opacity-slider').exists()).toBe(false)
  })

  it('shows preset buttons when showPresets=true', () => {
    const w = mount(InspectorColorPicker, { props: { ...baseProps, showPresets: true } })
    const presets = w.findAll('.inspector-color-picker__preset')
    expect(presets).toHaveLength(2)
    expect(presets[0].attributes('aria-label')).toBe('Definir como transparente')
    expect(presets[1].attributes('aria-label')).toBe('Herdar cor do elemento pai')
  })

  it('emits transparent on preset click', async () => {
    const w = mount(InspectorColorPicker, { props: { ...baseProps, showPresets: true } })
    await w.findAll('.inspector-color-picker__preset')[0].trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual(['transparent'])
  })

  it('emits inherit on preset click', async () => {
    const w = mount(InspectorColorPicker, { props: { ...baseProps, showPresets: true } })
    await w.findAll('.inspector-color-picker__preset')[1].trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual(['inherit'])
  })

  it('renders document colors palette', () => {
    const w = mount(InspectorColorPicker, {
      props: { ...baseProps, documentColors: ['#ff0000', '#00ff00', '#0000ff'] },
    })
    const swatches = w.findAll('[role="option"]')
    expect(swatches.length).toBeGreaterThanOrEqual(3)
    expect(w.find('[role="listbox"][aria-label="Cores do documento"]').exists()).toBe(true)
  })

  it('emits color on swatch click', async () => {
    const w = mount(InspectorColorPicker, {
      props: { ...baseProps, documentColors: ['#ff0000'] },
    })
    const swatch = w.find('[role="option"]')
    await swatch.trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual(['#ff0000'])
  })

  it('has aria-live region', () => {
    const w = mount(InspectorColorPicker, { props: baseProps })
    expect(w.find('[aria-live="polite"]').exists()).toBe(true)
  })

  it('hides opacity slider for transparent value', () => {
    const w = mount(InspectorColorPicker, { props: { ...baseProps, modelValue: 'transparent' } })
    expect(w.find('.inspector-color-picker__opacity-slider').exists()).toBe(false)
  })

  // Retrocompatibility: basic usage without new props works
  it('works with only label and modelValue (retrocompat)', () => {
    const w = mount(InspectorColorPicker, {
      props: { label: 'Cor', modelValue: '#000000' },
    })
    expect(w.find('.inspector-color-picker__label').text()).toBe('Cor')
    // No presets by default
    expect(w.findAll('.inspector-color-picker__preset')).toHaveLength(0)
  })
})
