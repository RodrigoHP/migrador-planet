import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AmbiguousFieldModal from './AmbiguousFieldModal.vue'
import type { FieldNavItem } from '@/types/field-navigator.types'

const mockField: FieldNavItem = {
  name: 'Vencimento',
  path: 'data.vencimento',
  type: 'string',
  status: 'unconfirmed',
  isOptional: false,
  isAmbiguous: true,
  candidates: [
    { path: 'data.vencimento', confidence: 0.87 },
    { path: 'boleto.data_emissao', confidence: 0.54 },
    { path: 'contrato.data_inicio', confidence: 0.23 },
  ],
}

function mountModal(field = mockField) {
  return mount(AmbiguousFieldModal, {
    props: { field },
    global: {
      stubs: { Teleport: true },
    },
  })
}

describe('AmbiguousFieldModal — Story 28.3', () => {
  it('renderiza candidatos na lista', () => {
    const wrapper = mountModal()
    expect(wrapper.text()).toContain('data.vencimento')
    expect(wrapper.text()).toContain('boleto.data_emissao')
    expect(wrapper.text()).toContain('contrato.data_inicio')
  })

  it('candidatos aparecem ordenados por score descendente', () => {
    const wrapper = mountModal()
    const items = wrapper.findAll('.ambiguous-modal__candidate')
    // First should be highest score (87%)
    expect(items[0].text()).toContain('data.vencimento')
    expect(items[0].text()).toContain('87%')
    // Last should be lowest score (23%)
    expect(items[2].text()).toContain('contrato.data_inicio')
    expect(items[2].text()).toContain('23%')
  })

  it('exibe score como porcentagem', () => {
    const wrapper = mountModal()
    expect(wrapper.text()).toContain('87%')
    expect(wrapper.text()).toContain('54%')
  })

  it('botão Confirmar está disabled quando nada selecionado', () => {
    const wrapper = mountModal()
    const btn = wrapper.find('.ambiguous-modal__btn--primary')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('emite resolve com path ao confirmar seleção', async () => {
    const wrapper = mountModal()
    // Select first candidate
    const radios = wrapper.findAll('.ambiguous-modal__radio')
    await radios[0].setValue('data.vencimento')
    // Click confirm
    const btn = wrapper.find('.ambiguous-modal__btn--primary')
    await btn.trigger('click')
    const emitted = wrapper.emitted('resolve')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBe('data.vencimento')
  })

  it('emite resolve com null ao selecionar Nenhum dos anteriores e confirmar', async () => {
    const wrapper = mountModal()
    // Radio v-model with :value="null" — set checked and fire change so Vue's directive reads _modelValue
    const noneRadio = wrapper.find('.ambiguous-modal__none .ambiguous-modal__radio')
    ;(noneRadio.element as HTMLInputElement).checked = true
    await noneRadio.trigger('change')
    const btn = wrapper.find('.ambiguous-modal__btn--primary')
    await btn.trigger('click')
    const emitted = wrapper.emitted('resolve')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBeNull()
  })

  it('emite cancel ao clicar Cancelar', async () => {
    const wrapper = mountModal()
    await wrapper.find('.ambiguous-modal__btn--secondary').trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('emite cancel ao clicar no botão X', async () => {
    const wrapper = mountModal()
    await wrapper.find('.ambiguous-modal__close').trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })
})
