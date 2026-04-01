import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import XsdOnlyField from './XsdOnlyField.vue'
import type { UnmappedXsdField } from '@/types/pipeline.types'

const field: UnmappedXsdField = {
  xsd_path: 'cliente.nome',
  required: true,
  reason: 'No PDF text matched this XSD field',
}

describe('XsdOnlyField — Story 28.2', () => {
  it('renderiza campo XSD com badge 🔴', () => {
    const wrapper = mount(XsdOnlyField, { props: { field } })
    expect(wrapper.text()).toContain('🔴')
    expect(wrapper.find('.xsd-only-field').exists()).toBe(true)
  })

  it('exibe xsd_path como identificador', () => {
    const wrapper = mount(XsdOnlyField, { props: { field } })
    expect(wrapper.text()).toContain('cliente.nome')
  })

  it('exibe nome semântico derivado do último segmento do XSD path', () => {
    const wrapper = mount(XsdOnlyField, { props: { field } })
    // 'cliente.nome' → 'Nome'
    expect(wrapper.text()).toContain('Nome')
  })

  it('exibe label "XSD obrigatório"', () => {
    const wrapper = mount(XsdOnlyField, { props: { field } })
    expect(wrapper.text()).toContain('XSD obrigatório')
  })

  it('funciona com campo sem reason', () => {
    const wrapper = mount(XsdOnlyField, {
      props: { field: { xsd_path: 'data.vencimento', required: false } },
    })
    expect(wrapper.text()).toContain('Vencimento')
  })
})
