import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTemplateStore } from './templateStore'
import type { DocumentTree, CellProperties } from '@/types/template.types'

function makeTree(): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'document',
      name: 'Doc',
      children: [
        {
          id: 'table-1',
          type: 'table',
          name: 'Table 1',
          children: [],
          properties: { columns: [{ field: 'name' }, { field: 'value' }] },
          visibility: true,
        },
      ],
      properties: {},
      visibility: true,
    },
  }
}

describe('templateStore.updateCellProperty', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('creates cells record and sets cell property', () => {
    const store = useTemplateStore()
    store.loadTree(makeTree())

    store.updateCellProperty('table-1', 0, 1, { backgroundColor: '#ff0000' })

    const node = store.getNodeById('table-1')!
    const cells = node.properties.cells as Record<string, CellProperties>
    expect(cells['0-1'].backgroundColor).toBe('#ff0000')
  })

  it('merges with existing cell properties', () => {
    const store = useTemplateStore()
    store.loadTree(makeTree())

    store.updateCellProperty('table-1', 0, 0, { backgroundColor: '#ff0000' })
    store.updateCellProperty('table-1', 0, 0, { padding: { top: 4, right: 4, bottom: 4, left: 4 } })

    const node = store.getNodeById('table-1')!
    const cells = node.properties.cells as Record<string, CellProperties>
    expect(cells['0-0'].backgroundColor).toBe('#ff0000')
    expect(cells['0-0'].padding?.top).toBe(4)
  })

  it('pushes undo snapshot before mutation', () => {
    const store = useTemplateStore()
    store.loadTree(makeTree())

    store.updateCellProperty('table-1', 0, 0, { backgroundColor: '#ff0000' })
    expect(store.undoStack.length).toBe(1)

    store.undoLastAction()
    const node = store.getNodeById('table-1')!
    expect(node.properties.cells).toBeUndefined()
  })
})
