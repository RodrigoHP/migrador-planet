import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BorderEditor from './BorderEditor.vue'
import { createDefaultBorderConfig } from '../types/template.types'
import type { BorderConfig } from '../types/template.types'

function mountEditor(overrides: Partial<BorderConfig> = {}) {
  const config = { ...createDefaultBorderConfig(), ...overrides }
  return mount(BorderEditor, { props: { modelValue: config } })
}

describe('BorderEditor', () => {
  it('renders in uniform mode by default', () => {
    const w = mountEditor()
    const checkbox = w.find('input[type="checkbox"]')
    expect((checkbox.element as HTMLInputElement).checked).toBe(true)
    // Uniform mode: 1 width + 1 color + 1 style + 4 radius = 7 InspectorInputs total (1 width + 4 radius = 5 number inputs)
    const labels = w.text()
    expect(labels).toContain('Todos os lados')
    expect(labels).toContain('Espessura')
    expect(labels).toContain('Cor')
    expect(labels).toContain('Estilo')
    expect(labels).toContain('Raio')
  })

  it('switches to per-side mode on toggle', async () => {
    const w = mountEditor()
    await w.find('input[type="checkbox"]').setValue(false)
    const emitted = w.emitted('update:modelValue') as BorderConfig[][]
    expect(emitted).toHaveLength(1)
    expect(emitted[0][0].uniform).toBe(false)
  })

  it('switching to uniform copies top to all sides', async () => {
    const config = createDefaultBorderConfig()
    config.uniform = false
    config.top = { width: 3, color: '#ff0000', style: 'dashed' }
    config.right = { width: 0, color: '#000000', style: 'none' }
    const w = mount(BorderEditor, { props: { modelValue: config } })

    await w.find('input[type="checkbox"]').setValue(true)
    const emitted = w.emitted('update:modelValue') as BorderConfig[][]
    const result = emitted[0][0]
    expect(result.uniform).toBe(true)
    expect(result.right).toEqual(result.top)
    expect(result.bottom).toEqual(result.top)
    expect(result.left).toEqual(result.top)
  })

  it('renders preview box with correct border styles', () => {
    const config = createDefaultBorderConfig()
    config.top = { width: 2, color: '#ff0000', style: 'solid' }
    const w = mount(BorderEditor, { props: { modelValue: config } })

    const preview = w.find('.border-editor__preview')
    expect(preview.exists()).toBe(true)
    const style = preview.attributes('style') || ''
    expect(style).toMatch(/border-top: 2px solid (rgb\(255, 0, 0\)|#ff0000)/)
  })

  it('renders 4 width inputs in per-side mode', () => {
    const config = createDefaultBorderConfig()
    config.uniform = false
    const w = mount(BorderEditor, { props: { modelValue: config } })
    const text = w.text()
    expect(text).toContain('Topo')
    expect(text).toContain('Direita')
    expect(text).toContain('Baixo')
    expect(text).toContain('Esquerda')
  })

  it('renders radius inputs always (4 corners)', () => {
    const w = mountEditor()
    const text = w.text()
    expect(text).toContain('Sup-Esq')
    expect(text).toContain('Sup-Dir')
    expect(text).toContain('Inf-Dir')
    expect(text).toContain('Inf-Esq')
  })
})
