import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useClipboard } from './useClipboard'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
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
      ],
      properties: {},
      visibility: true,
    },
  }
}

describe('useClipboard', () => {
  let templateStore: ReturnType<typeof useTemplateStore>
  let editorStore: ReturnType<typeof useEditorStore>
  let clipboard: ReturnType<typeof useClipboard>

  beforeEach(() => {
    setActivePinia(createPinia())
    templateStore = useTemplateStore()
    editorStore = useEditorStore()
    templateStore.loadTree(makeTree())
    clipboard = useClipboard()
    // Clear module-level clipboard from previous tests
    clipboard.clipboard.value = []
  })

  it('copySelection copies single selected element', () => {
    editorStore.selectElement('a')
    clipboard.copySelection()
    expect(clipboard.clipboard.value).toHaveLength(1)
    expect(clipboard.clipboard.value[0].node.id).toBe('a')
  })

  it('pasteFromClipboard creates new element with +10px offset', () => {
    editorStore.selectElement('a')
    clipboard.copySelection()
    const pasted = clipboard.pasteFromClipboard()
    expect(pasted).toHaveLength(1)
    expect(pasted[0].properties.x).toBe(20) // 10 + 10
    expect(pasted[0].properties.y).toBe(30) // 20 + 10
    expect(pasted[0].id).not.toBe('a') // new ID
  })

  it('pasteFromClipboard registers in flatNodes', () => {
    editorStore.selectElement('a')
    clipboard.copySelection()
    const before = templateStore.flatNodes.size
    clipboard.pasteFromClipboard()
    expect(templateStore.flatNodes.size).toBe(before + 1)
  })

  it('duplicateSelection creates clone with offset', () => {
    editorStore.selectElement('a')
    const dupes = clipboard.duplicateSelection()
    expect(dupes).toHaveLength(1)
    expect(dupes[0].id).not.toBe('a')
  })

  it('pasteFromClipboard returns empty when clipboard is empty', () => {
    const result = clipboard.pasteFromClipboard()
    expect(result).toEqual([])
  })

  it('copySelection does nothing when no selection', () => {
    editorStore.selectElement(null)
    clipboard.copySelection()
    expect(clipboard.clipboard.value).toHaveLength(0)
  })

  it('pasteFromClipboard calls pushUndoSnapshot', () => {
    editorStore.selectElement('a')
    clipboard.copySelection()
    const spy = vi.spyOn(templateStore, 'pushUndoSnapshot')
    clipboard.pasteFromClipboard()
    expect(spy).toHaveBeenCalled()
  })
})
