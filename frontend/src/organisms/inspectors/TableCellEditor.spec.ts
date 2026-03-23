import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import TableCellEditor from './TableCellEditor.vue'
import { createDefaultCellProperties } from '@/types/template.types'

describe('TableCellEditor', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders with cell coordinates in header', () => {
    const w = mount(TableCellEditor, {
      props: {
        tableNodeId: 'table-1',
        row: 2,
        col: 3,
        cellProps: createDefaultCellProperties(),
      },
    })
    expect(w.text()).toContain('Célula [2, 3]')
  })

  it('renders border, background and padding sections', () => {
    const w = mount(TableCellEditor, {
      props: {
        tableNodeId: 'table-1',
        row: 0,
        col: 0,
        cellProps: createDefaultCellProperties(),
      },
    })
    expect(w.text()).toContain('Bordas da Célula')
    expect(w.text()).toContain('Fundo')
    expect(w.text()).toContain('Padding')
  })

  it('emits deselect when close button clicked', async () => {
    const w = mount(TableCellEditor, {
      props: {
        tableNodeId: 'table-1',
        row: 0,
        col: 0,
        cellProps: createDefaultCellProperties(),
      },
    })
    await w.find('.table-cell-editor__close').trigger('click')
    expect(w.emitted('deselect')).toHaveLength(1)
  })
})
