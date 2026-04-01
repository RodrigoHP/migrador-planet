import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FieldNavGroup from './FieldNavGroup.vue'

describe('FieldNavGroup — Story 28.2', () => {
  it('renderiza título e badge do grupo', () => {
    const wrapper = mount(FieldNavGroup, {
      props: { label: 'Sem binding', badge: '🟥', count: 5, startOpen: true },
    })
    expect(wrapper.text()).toContain('Sem binding')
    expect(wrapper.text()).toContain('🟥')
    expect(wrapper.text()).toContain('(5)')
  })

  it('começa colapsado quando startOpen=false', () => {
    const wrapper = mount(FieldNavGroup, {
      props: { label: 'Mapeados', badge: '🟩', count: 10, startOpen: false },
    })
    expect(wrapper.find('.field-nav-group__items').exists()).toBe(false)
    expect(wrapper.text()).toContain('▶')
  })

  it('começa expandido quando startOpen=true', () => {
    const wrapper = mount(FieldNavGroup, {
      props: { label: 'Ambíguos', badge: '🟨', count: 3, startOpen: true },
      slots: { default: '<div class="test-item">Item</div>' },
    })
    expect(wrapper.find('.field-nav-group__items').exists()).toBe(true)
    expect(wrapper.text()).toContain('▼')
  })

  it('toggle expande/colapsa ao clicar no header', async () => {
    const wrapper = mount(FieldNavGroup, {
      props: { label: 'Teste', badge: '🟩', count: 2, startOpen: true },
      slots: { default: '<div>item</div>' },
    })
    // Initially expanded
    expect(wrapper.find('.field-nav-group__items').exists()).toBe(true)
    // Click header to collapse
    await wrapper.find('.field-nav-group__header').trigger('click')
    expect(wrapper.find('.field-nav-group__items').exists()).toBe(false)
    // Click again to expand
    await wrapper.find('.field-nav-group__header').trigger('click')
    expect(wrapper.find('.field-nav-group__items').exists()).toBe(true)
  })

  it('mostra contagem de items no badge', () => {
    const wrapper = mount(FieldNavGroup, {
      props: { label: 'XSD', badge: '🔴', count: 8, startOpen: true },
    })
    expect(wrapper.text()).toContain('(8)')
  })
})
