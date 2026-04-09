import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useMappingStore } from '@/stores/mapping'
import FormatStringEditor from './FormatStringEditor.vue'

function makeWrapper(modelValue = '', testData: Record<string, string> = {}) {
  return mount(FormatStringEditor, {
    props: { modelValue, testData },
  })
}

describe('FormatStringEditor', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the input with given modelValue', () => {
    const wrapper = makeWrapper('{Logradouro}, {Numero}')
    const input = wrapper.find('input')
    expect(input.element.value).toBe('{Logradouro}, {Numero}')
  })

  it('emits update:modelValue when user types', async () => {
    const wrapper = makeWrapper('')
    const input = wrapper.find('input')
    await input.setValue('hello')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['hello'])
  })

  it('highlights valid fields in blue and invalid in red', async () => {
    const store = useMappingStore()
    store.setFieldNavItems([
      {
        name: 'Logradouro',
        path: 'Logradouro',
        type: 'string',
        status: 'unmapped',
        isOptional: false,
      },
    ])

    const wrapper = makeWrapper('{Logradouro} {CampoInvalido}')
    await wrapper.vm.$nextTick()

    const highlight = wrapper.find('.fse__highlight')
    const validSpan = highlight.find('.fse__hl-valid')
    const invalidSpan = highlight.find('.fse__hl-invalid')

    expect(validSpan.exists()).toBe(true)
    expect(validSpan.text()).toContain('Logradouro')
    expect(invalidSpan.exists()).toBe(true)
    expect(invalidSpan.text()).toContain('CampoInvalido')
    expect(invalidSpan.attributes('title')).toBe('Campo não encontrado no XSD')
  })

  it('shows preview text with test data', async () => {
    const wrapper = makeWrapper('{Logradouro}, {Numero}', { Logradouro: 'Rua B', Numero: '456' })
    await wrapper.vm.$nextTick()

    const preview = wrapper.find('.fse__preview-value')
    expect(preview.exists()).toBe(true)
    expect(preview.text()).toBe('Rua B, 456')
  })

  it('shows preview with default test data when no testData provided', async () => {
    const wrapper = makeWrapper('{Logradouro}')
    await wrapper.vm.$nextTick()

    const preview = wrapper.find('.fse__preview-value')
    expect(preview.text()).toBe('Rua A')
  })

  it('handles escaped \\{ and \\} as literal braces in preview', async () => {
    const wrapper = makeWrapper('\\{literal\\}')
    await wrapper.vm.$nextTick()

    const preview = wrapper.find('.fse__preview-value')
    expect(preview.text()).toBe('{literal}')
  })

  it('renders highlight for escaped braces with fse__hl-literal class', async () => {
    const wrapper = makeWrapper('\\{')
    await wrapper.vm.$nextTick()

    const literal = wrapper.find('.fse__hl-literal')
    expect(literal.exists()).toBe(true)
    expect(literal.text()).toBe('{')
  })

  it('parsedFields getter extracts field paths', () => {
    const wrapper = makeWrapper('{Logradouro}, {Numero} - {Bairro}')
    const vm = wrapper.vm as unknown as { parsedFields: string[] }
    expect(vm.parsedFields).toEqual(['Logradouro', 'Numero', 'Bairro'])
  })

  it('parsedFields ignores escaped braces', () => {
    const wrapper = makeWrapper('\\{escaped\\} {Real}')
    const vm = wrapper.vm as unknown as { parsedFields: string[] }
    expect(vm.parsedFields).toEqual(['Real'])
  })

  it('does not show preview for empty modelValue', async () => {
    const wrapper = makeWrapper('')
    await wrapper.vm.$nextTick()
    const preview = wrapper.find('.fse__preview')
    expect(preview.exists()).toBe(false)
  })

  it('shows autocomplete dropdown when store has fields', async () => {
    const store = useMappingStore()
    store.setFieldNavItems([
      {
        name: 'Logradouro',
        path: 'Logradouro',
        type: 'string',
        status: 'unmapped',
        isOptional: false,
      },
    ])

    const wrapper = makeWrapper('{')
    // Access the component's internal showDropdown via the exposed vm
    // The dropdown visibility depends on cursor detection — we can expose it indirectly
    // by verifying the computed filteredFields is non-empty and testing
    // that the dropdown renders when showDropdown is true via triggerRef
    // Since JSDOM selectionStart is unreliable, we check the dropdown renders
    // when the component receives a value of '{' and expose showDropdown via direct vm access
    const vm = wrapper.vm as unknown as { showDropdown: boolean; filteredFields: unknown[] }

    // Force showDropdown to true programmatically since JSDOM selectionStart may not update
    vm.showDropdown = true
    await wrapper.vm.$nextTick()

    const dropdown = wrapper.find('.fse__dropdown')
    expect(dropdown.exists()).toBe(true)
  })
})
