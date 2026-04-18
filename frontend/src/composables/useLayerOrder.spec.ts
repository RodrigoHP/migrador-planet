import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLayerOrder } from './useLayerOrder'
import { useTemplateStore } from '@/stores/templateStore'
import type { DocumentTree } from '@/types/template.types'

function makeTree(): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'document',
      name: 'Root',
      children: [
        {
          id: 'a',
          type: 'field',
          name: 'A',
          children: [],
          properties: { zIndex: 10 },
          visibility: true,
        },
        {
          id: 'b',
          type: 'field',
          name: 'B',
          children: [],
          properties: { zIndex: 30 },
          visibility: true,
        },
        {
          id: 'c',
          type: 'field',
          name: 'C',
          children: [],
          properties: { zIndex: 20 },
          visibility: true,
        },
      ],
      properties: {},
      visibility: true,
    },
  }
}

describe('useLayerOrder', () => {
  let templateStore: ReturnType<typeof useTemplateStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())
  })

  it('returns layers ordered by z-index descending', () => {
    const { orderedLayers } = useLayerOrder()
    const ids = orderedLayers.value.map((l) => l.id)
    expect(ids).toEqual(['b', 'c', 'a']) // 30, 20, 10
  })

  it('bringToFront sets z-index above highest', () => {
    const { bringToFront } = useLayerOrder()
    bringToFront('a')
    const node = templateStore.getNodeById('a')!
    expect(node.properties['zIndex']).toBe(40) // 30 + 10
  })

  it('sendToBack sets z-index below lowest', () => {
    const { sendToBack } = useLayerOrder()
    sendToBack('b')
    const node = templateStore.getNodeById('b')!
    expect(node.properties['zIndex']).toBe(0) // 10 - 10
  })

  it('moveLayerUp swaps z-index with layer above', () => {
    const { moveLayerUp } = useLayerOrder()
    // Order: b(30), c(20), a(10). Move c up → swap with b
    moveLayerUp('c')
    expect(templateStore.getNodeById('c')!.properties['zIndex']).toBe(30)
    expect(templateStore.getNodeById('b')!.properties['zIndex']).toBe(20)
  })

  it('moveLayerDown swaps z-index with layer below', () => {
    const { moveLayerDown } = useLayerOrder()
    // Order: b(30), c(20), a(10). Move c down → swap with a
    moveLayerDown('c')
    expect(templateStore.getNodeById('c')!.properties['zIndex']).toBe(10)
    expect(templateStore.getNodeById('a')!.properties['zIndex']).toBe(20)
  })

  it('reorderByDrag reassigns z-indices', () => {
    const { reorderByDrag, orderedLayers } = useLayerOrder()
    // Move first (b, idx 0) to last (idx 2)
    reorderByDrag(0, 2)
    const reordered = orderedLayers.value.map((l) => l.id)
    // After: c, a, b
    expect(reordered).toEqual(['c', 'a', 'b'])
  })
})
