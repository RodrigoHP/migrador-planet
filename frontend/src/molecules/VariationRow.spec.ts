import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import VariationRow from './VariationRow.vue'

describe('VariationRow', () => {
  it('renders field name', () => {
    const wrapper = mount(VariationRow, {
      props: { fieldName: 'nomeCliente', presencePerDoc: [true, false] },
    })
    expect(wrapper.text()).toContain('nomeCliente')
  })

  it('renders ✔ for present documents', () => {
    const wrapper = mount(VariationRow, {
      props: { fieldName: 'campo', presencePerDoc: [true, true] },
    })
    const cells = wrapper.findAll('[role="cell"]')
    expect(cells[0]?.text()).toContain('✔')
    expect(cells[1]?.text()).toContain('✔')
  })

  it('renders ✖ for absent documents', () => {
    const wrapper = mount(VariationRow, {
      props: { fieldName: 'campo', presencePerDoc: [false, true] },
    })
    const cells = wrapper.findAll('[role="cell"]')
    expect(cells[0]?.text()).toContain('✖')
    expect(cells[1]?.text()).toContain('✔')
  })

  it('renders correct number of cells equal to presencePerDoc length', () => {
    const wrapper = mount(VariationRow, {
      props: { fieldName: 'campo', presencePerDoc: [true, false, true] },
    })
    const cells = wrapper.findAll('[role="cell"]')
    expect(cells).toHaveLength(3)
  })

  it('has aria-label indicating presence/absence on each cell', () => {
    const wrapper = mount(VariationRow, {
      props: { fieldName: 'campo', presencePerDoc: [true, false] },
    })
    const cells = wrapper.findAll('[role="cell"]')
    expect(cells[0]?.attributes('aria-label')).toContain('presente')
    expect(cells[1]?.attributes('aria-label')).toContain('ausente')
  })
})
