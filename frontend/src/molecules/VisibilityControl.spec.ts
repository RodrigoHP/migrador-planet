import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VisibilityControl from './VisibilityControl.vue'
import type { VisibilityConfig } from './VisibilityControl.vue'
import { useMappingStore } from '@/stores/mapping'

function makeConfig(override?: Partial<VisibilityConfig>): VisibilityConfig {
  return { mode: 'always', ...override }
}

describe('VisibilityControl', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Seed some field nav items so dropdown is populated
    const mappingStore = useMappingStore()
    mappingStore.setFieldNavItems([
      { name: 'Nome', path: 'dados.nome', type: 'string', status: 'unmapped', isOptional: false },
      { name: 'Telefone', path: 'dados.telefone', type: 'string', status: 'unmapped', isOptional: true },
    ])
  })

  it('renders the visibility dropdown', () => {
    const wrapper = mount(VisibilityControl, {
      props: { modelValue: makeConfig() },
    })
    const select = wrapper.find('.visibility-control__select')
    expect(select.exists()).toBe(true)
  })

  it('shows "Sempre visível" as default', () => {
    const wrapper = mount(VisibilityControl, {
      props: { modelValue: makeConfig() },
    })
    const select = wrapper.find<HTMLSelectElement>('.visibility-control__select')
    expect(select.element.value).toBe('always')
  })

  it('does not show builder when mode is "always"', () => {
    const wrapper = mount(VisibilityControl, {
      props: { modelValue: makeConfig({ mode: 'always' }) },
    })
    expect(wrapper.find('.visibility-control__builder').exists()).toBe(false)
  })

  it('expands builder when mode is "conditional"', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: 'dados.nome', operator: 'exists', value: '' }],
        }),
      },
    })
    expect(wrapper.find('.visibility-control__builder').exists()).toBe(true)
  })

  it('shows hidden info when mode is "hidden"', () => {
    const wrapper = mount(VisibilityControl, {
      props: { modelValue: makeConfig({ mode: 'hidden' }) },
    })
    expect(wrapper.find('.visibility-control__hidden-info').exists()).toBe(true)
  })

  it('emits update:modelValue when mode changes', async () => {
    const wrapper = mount(VisibilityControl, {
      props: { modelValue: makeConfig({ mode: 'always' }) },
    })
    const select = wrapper.find('.visibility-control__select')
    await select.setValue('hidden')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect((emitted![0]![0] as VisibilityConfig).mode).toBe('hidden')
  })

  it('emits update:modelValue with initial condition when switching to conditional', async () => {
    const wrapper = mount(VisibilityControl, {
      props: { modelValue: makeConfig({ mode: 'always' }) },
    })
    const select = wrapper.find('.visibility-control__select')
    await select.setValue('conditional')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const config = emitted![0]![0] as VisibilityConfig
    expect(config.mode).toBe('conditional')
    expect(config.conditions).toHaveLength(1)
  })

  it('renders a condition row for each condition', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [
            { fieldPath: 'dados.nome', operator: 'exists', value: '' },
            { fieldPath: 'dados.telefone', operator: 'equals', value: 'test', logic: 'AND' },
          ],
        }),
      },
    })
    const rows = wrapper.findAll('.visibility-control__condition-row')
    expect(rows).toHaveLength(2)
  })

  it('shows E/OU badge on second+ conditions', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [
            { fieldPath: 'dados.nome', operator: 'exists', value: '' },
            { fieldPath: 'dados.telefone', operator: 'exists', value: '', logic: 'OR' },
          ],
        }),
      },
    })
    const badges = wrapper.findAll('.visibility-control__logic-badge')
    expect(badges).toHaveLength(1)
    expect(badges[0]!.text()).toBe('OU')
  })

  it('shows E badge for AND logic', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [
            { fieldPath: 'dados.nome', operator: 'exists', value: '' },
            { fieldPath: 'dados.telefone', operator: 'exists', value: '', logic: 'AND' },
          ],
        }),
      },
    })
    const badges = wrapper.findAll('.visibility-control__logic-badge--and')
    expect(badges).toHaveLength(1)
    expect(badges[0]!.text()).toBe('E')
  })

  it('emits new condition on "+ E" button click', async () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: 'dados.nome', operator: 'exists', value: '' }],
        }),
      },
    })
    const addBtns = wrapper.findAll('.visibility-control__add-btn')
    await addBtns[0]!.trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const config = emitted![0]![0] as VisibilityConfig
    expect(config.conditions).toHaveLength(2)
    expect(config.conditions![1]!.logic).toBe('AND')
  })

  it('emits new condition on "+ OU" button click', async () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: 'dados.nome', operator: 'exists', value: '' }],
        }),
      },
    })
    const addBtns = wrapper.findAll('.visibility-control__add-btn')
    await addBtns[1]!.trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const config = emitted![0]![0] as VisibilityConfig
    expect(config.conditions).toHaveLength(2)
    expect(config.conditions![1]!.logic).toBe('OR')
  })

  it('emits remove condition when remove button clicked', async () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [
            { fieldPath: 'dados.nome', operator: 'exists', value: '' },
            { fieldPath: 'dados.telefone', operator: 'exists', value: '', logic: 'AND' },
          ],
        }),
      },
    })
    const removeBtns = wrapper.findAll('.visibility-control__remove-btn')
    await removeBtns[0]!.trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const config = emitted![0]![0] as VisibilityConfig
    expect(config.conditions).toHaveLength(1)
  })

  it('shows Knockout preview for single "exists" condition', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: 'dados.telefone', operator: 'exists', value: '' }],
        }),
      },
    })
    const preview = wrapper.find('.visibility-control__preview-code')
    expect(preview.exists()).toBe(true)
    expect(preview.text()).toBe('<!-- ko if: dados.telefone -->')
  })

  it('shows Knockout preview for "equals" condition', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: 'dados.nome', operator: 'equals', value: 'João' }],
        }),
      },
    })
    const preview = wrapper.find('.visibility-control__preview-code')
    expect(preview.text()).toBe("<!-- ko if: dados.nome() === 'João' -->")
  })

  it('shows Knockout preview for compound condition with OR', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [
            { fieldPath: 'dados.telefone', operator: 'exists', value: '' },
            { fieldPath: 'dados.nome', operator: 'exists', value: '', logic: 'OR' },
          ],
        }),
      },
    })
    const preview = wrapper.find('.visibility-control__preview-code')
    expect(preview.text()).toBe('<!-- ko if: dados.telefone || dados.nome -->')
  })

  it('shows Knockout preview for compound condition with AND', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [
            { fieldPath: 'dados.telefone', operator: 'exists', value: '' },
            { fieldPath: 'dados.nome', operator: 'not_exists', value: '', logic: 'AND' },
          ],
        }),
      },
    })
    const preview = wrapper.find('.visibility-control__preview-code')
    expect(preview.text()).toBe('<!-- ko if: dados.telefone && !dados.nome -->')
  })

  it('hides value input when operator is "exists"', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: 'dados.nome', operator: 'exists', value: '' }],
        }),
      },
    })
    expect(wrapper.find('.visibility-control__value-input').exists()).toBe(false)
  })

  it('shows value input when operator is "equals"', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: 'dados.nome', operator: 'equals', value: 'X' }],
        }),
      },
    })
    expect(wrapper.find('.visibility-control__value-input').exists()).toBe(true)
  })

  it('populates field dropdown from mappingStore', () => {
    const wrapper = mount(VisibilityControl, {
      props: {
        modelValue: makeConfig({
          mode: 'conditional',
          conditions: [{ fieldPath: '', operator: 'exists', value: '' }],
        }),
      },
    })
    const fieldSelect = wrapper.find('.visibility-control__field-select')
    expect(fieldSelect.text()).toContain('Nome')
    expect(fieldSelect.text()).toContain('Telefone')
  })
})
