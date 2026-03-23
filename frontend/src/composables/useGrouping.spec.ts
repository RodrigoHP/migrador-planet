import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGrouping } from './useGrouping'
import { useTemplateStore } from '@/stores/templateStore'
import type { DocumentTree } from '@/types/template.types'

function makeTree(): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'page',
      name: 'Root',
      children: [
        { id: 'a', type: 'field', name: 'A', children: [], properties: { x: 10, y: 20, width: 50, height: 30 }, visibility: true },
        { id: 'b', type: 'field', name: 'B', children: [], properties: { x: 100, y: 200, width: 60, height: 40 }, visibility: true },
        { id: 'c', type: 'field', name: 'C', children: [], properties: { x: 50, y: 50, width: 80, height: 20 }, visibility: true },
      ],
      properties: {},
      visibility: true,
    },
  }
}

describe('useGrouping', () => {
  let templateStore: ReturnType<typeof useTemplateStore>
  let grouping: ReturnType<typeof useGrouping>

  beforeEach(() => {
    setActivePinia(createPinia())
    templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())
    grouping = useGrouping()
  })

  it('createGroup groups 2+ nodes', () => {
    const group = grouping.createGroup(['a', 'b'])
    expect(group).not.toBeNull()
    expect(group!.properties['isGroup']).toBe(true)
    expect(group!.children).toHaveLength(2)
  })

  it('createGroup returns null for < 2 nodes', () => {
    expect(grouping.createGroup(['a'])).toBeNull()
    expect(grouping.createGroup([])).toBeNull()
  })

  it('ungroupNode restores children to parent', () => {
    const group = grouping.createGroup(['a', 'b'])!
    const root = templateStore.getRootNode!
    const childCountBefore = root.children.length
    // root now has: [group, c] = 2 children
    expect(childCountBefore).toBe(2)

    grouping.ungroupNode(group.id)
    // After ungroup: [a, b, c] = 3 children
    expect(root.children.length).toBe(3)
  })

  it('moveGroup moves all children', () => {
    const group = grouping.createGroup(['a', 'b'])!
    grouping.moveGroup(group.id, 5, 10)
    const a = templateStore.getNodeById('a')!
    const b = templateStore.getNodeById('b')!
    expect(a.properties.x).toBe(15) // 10 + 5
    expect(b.properties.y).toBe(210) // 200 + 10
  })

  it('applyBatchProperty applies to all children', () => {
    const group = grouping.createGroup(['a', 'b'])!
    grouping.applyBatchProperty(group.id, 'color', '#ff0000')
    const a = templateStore.getNodeById('a')!
    const b = templateStore.getNodeById('b')!
    expect(a.properties['color']).toBe('#ff0000')
    expect(b.properties['color']).toBe('#ff0000')
  })

  it('resizeGroup scales children proportionally', () => {
    const group = grouping.createGroup(['a', 'b'])!
    grouping.resizeGroup(group.id, 2, 2)
    const a = templateStore.getNodeById('a')!
    expect(a.properties.width).toBe(100) // 50 * 2
    expect(a.properties.height).toBe(60) // 30 * 2
  })
})
