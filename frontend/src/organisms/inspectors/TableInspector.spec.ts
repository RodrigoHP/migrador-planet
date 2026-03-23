import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import TableInspector from './TableInspector.vue'
import type { TreeNode } from '@/types/template.types'

vi.mock('@/stores/templateStore', () => {
  const updateNodeProperty = vi.fn()
  return {
    useTemplateStore: () => ({
      updateNodeProperty,
      flatNodes: new Map(),
    }),
  }
})

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    id: 'table-1',
    name: 'TestTable',
    type: 'table',
    properties: {
      columns: [
        { field: 'nome', width: '100', align: 'left' },
        { field: 'valor', width: '80', align: 'right' },
      ],
    },
    children: [],
    ...overrides,
  } as TreeNode
}

describe('TableInspector', () => {
  let updateNodeProperty: ReturnType<typeof vi.fn>

  beforeEach(async () => {
    setActivePinia(createPinia())
    const mod = await import('@/stores/templateStore')
    updateNodeProperty = (mod.useTemplateStore() as any).updateNodeProperty
    updateNodeProperty.mockClear()
  })

  it('renders column rows for each column', () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const rows = wrapper.findAll('.table-inspector__col-row')
    expect(rows).toHaveLength(2)
  })

  it('renders editable width input', () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const inputs = wrapper.findAll('.table-inspector__col-input')
    expect(inputs.length).toBeGreaterThanOrEqual(2)
    expect((inputs[0]!.element as HTMLInputElement).value).toBe('100')
  })

  it('renders align select', () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const selects = wrapper.findAll('.table-inspector__col-select')
    expect(selects.length).toBeGreaterThanOrEqual(2)
    expect((selects[1]!.element as HTMLSelectElement).value).toBe('right')
  })

  it('updateColWidth dispatches updateNodeProperty', async () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const input = wrapper.find('.table-inspector__col-input')
    await input.setValue('200')
    await input.trigger('input')
    expect(updateNodeProperty).toHaveBeenCalledWith(
      'table-1',
      'columns',
      expect.arrayContaining([
        expect.objectContaining({ field: 'nome', width: '200' }),
      ]),
    )
  })

  it('updateColAlign dispatches updateNodeProperty', async () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const select = wrapper.find('.table-inspector__col-select')
    await select.setValue('center')
    expect(updateNodeProperty).toHaveBeenCalledWith(
      'table-1',
      'columns',
      expect.arrayContaining([
        expect.objectContaining({ field: 'nome', align: 'center' }),
      ]),
    )
  })

  it('addColumn adds a new column', async () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const addBtn = wrapper.find('.table-inspector__col-add')
    await addBtn.trigger('click')
    expect(updateNodeProperty).toHaveBeenCalledWith(
      'table-1',
      'columns',
      expect.arrayContaining([
        expect.objectContaining({ field: 'col_3' }),
      ]),
    )
  })

  it('removeColumn removes the column at index', async () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const removeBtns = wrapper.findAll('.table-inspector__col-remove')
    await removeBtns[0]!.trigger('click')
    expect(updateNodeProperty).toHaveBeenCalledWith(
      'table-1',
      'columns',
      [expect.objectContaining({ field: 'valor' })],
    )
  })

  it('has ARIA role="grid" on column container', () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const grid = wrapper.find('[role="grid"]')
    expect(grid.exists()).toBe(true)
    expect(grid.attributes('aria-label')).toBe('Colunas da tabela')
  })

  it('has aria-live for announcements', () => {
    const wrapper = mount(TableInspector, { props: { node: makeNode() } })
    const live = wrapper.find('[aria-live="polite"]')
    expect(live.exists()).toBe(true)
  })

  it('renders empty state when no columns', () => {
    const node = makeNode({ properties: { columns: [] } })
    const wrapper = mount(TableInspector, { props: { node } })
    expect(wrapper.findAll('.table-inspector__col-row')).toHaveLength(0)
  })
})
