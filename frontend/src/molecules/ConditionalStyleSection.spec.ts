import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConditionalStyleSection from './ConditionalStyleSection.vue'
import type { StyleRule } from '@/utils/formatStringGenerator'

const emptyRule: StyleRule = {
  fieldPath: '',
  operator: '===',
  value: '',
  property: 'color',
  propertyValue: '#000000',
}

function makeWrapper(modelValue: StyleRule[] = []) {
  return mount(ConditionalStyleSection, {
    props: { modelValue },
  })
}

describe('ConditionalStyleSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders title "Estilo Condicional"', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('Estilo Condicional')
  })

  it('renders "+ Regra" button', () => {
    const wrapper = makeWrapper()
    const btn = wrapper.find('.css-section__add')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('+ Regra')
  })

  it('renders no rules when modelValue is empty', () => {
    const wrapper = makeWrapper([])
    const rules = wrapper.findAll('.csr')
    expect(rules).toHaveLength(0)
  })

  it('renders rules matching modelValue length', () => {
    const rules: StyleRule[] = [emptyRule, { ...emptyRule, fieldPath: 'Status' }]
    const wrapper = makeWrapper(rules)
    const rendered = wrapper.findAll('.csr')
    expect(rendered).toHaveLength(2)
  })

  it('emits update:modelValue with new rule when "+ Regra" clicked', async () => {
    const wrapper = makeWrapper([])
    const btn = wrapper.find('.css-section__add')
    await btn.trigger('click')

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const newRules = emitted?.[0]?.[0] as StyleRule[]
    expect(newRules).toHaveLength(1)
    expect(newRules[0]).toMatchObject({
      fieldPath: '',
      operator: '===',
      value: '',
      property: 'color',
    })
  })

  it('emits update:modelValue with correct count after adding two rules', async () => {
    const wrapper = makeWrapper([emptyRule])
    const btn = wrapper.find('.css-section__add')
    await btn.trigger('click')

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const newRules = emitted?.[0]?.[0] as StyleRule[]
    expect(newRules).toHaveLength(2)
  })

  it('emits update:modelValue with removed rule when remove event fires', async () => {
    const rules: StyleRule[] = [
      { ...emptyRule, fieldPath: 'A' },
      { ...emptyRule, fieldPath: 'B' },
    ]
    const wrapper = makeWrapper(rules)

    // Trigger remove on first rule
    const ruleComponents = wrapper.findAllComponents({ name: 'ConditionalStyleRule' })
    await ruleComponents[0]!.vm.$emit('remove')

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const remaining = emitted?.[0]?.[0] as StyleRule[]
    expect(remaining).toHaveLength(1)
    expect(remaining[0]!.fieldPath).toBe('B')
  })
})
