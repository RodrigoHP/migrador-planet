import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCanvasKeyboard } from './useCanvasKeyboard'
import { useEditorStore } from '@/stores/editorStore'
import { useTemplateStore } from '@/stores/templateStore'
import type { DocumentTree } from '@/types/template.types'

function makeTree(): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'page',
      name: 'Root',
      children: [
        {
          id: 'el-1',
          type: 'field',
          name: 'Field 1',
          children: [],
          properties: { x: 100, y: 200, width: 50, height: 30 },
          visibility: true,
        },
      ],
      properties: {},
      visibility: true,
    },
  }
}

function fireKey(handler: (e: KeyboardEvent) => void, key: string, opts?: Partial<KeyboardEvent>) {
  const event = new KeyboardEvent('keydown', {
    key,
    bubbles: true,
    cancelable: true,
    ...opts,
  })
  // Simulate target as a div (not input)
  Object.defineProperty(event, 'target', { value: document.createElement('div') })
  handler(event)
}

describe('useCanvasKeyboard', () => {
  let editorStore: ReturnType<typeof useEditorStore>
  let templateStore: ReturnType<typeof useTemplateStore>
  let handleKeyDown: ReturnType<typeof useCanvasKeyboard>['handleKeyDown']

  beforeEach(() => {
    setActivePinia(createPinia())
    editorStore = useEditorStore()
    templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())
    editorStore.selectElement('el-1')
    ;({ handleKeyDown } = useCanvasKeyboard())
  })

  it('moves element 1px on ArrowRight', () => {
    fireKey(handleKeyDown, 'ArrowRight')
    const node = templateStore.getNodeById('el-1')!
    expect(node.properties.x).toBe(101)
  })

  it('moves element 1px on ArrowUp', () => {
    fireKey(handleKeyDown, 'ArrowUp')
    const node = templateStore.getNodeById('el-1')!
    expect(node.properties.y).toBe(199)
  })

  it('moves element gridSize px on Shift+Arrow', () => {
    editorStore.setGridSize(10)
    fireKey(handleKeyDown, 'ArrowDown', { shiftKey: true })
    const node = templateStore.getNodeById('el-1')!
    expect(node.properties.y).toBe(210)
  })

  it('resizes element on Alt+ArrowRight', () => {
    fireKey(handleKeyDown, 'ArrowRight', { altKey: true })
    const node = templateStore.getNodeById('el-1')!
    expect(node.properties.width).toBe(51)
  })

  it('resizes element on Alt+ArrowUp (min 1)', () => {
    // Set height to 1 first
    templateStore.updateNodeProperty('el-1', 'height', 1)
    fireKey(handleKeyDown, 'ArrowUp', { altKey: true })
    const node = templateStore.getNodeById('el-1')!
    expect(node.properties.height).toBe(1) // min clamped
  })

  it('duplicates on Ctrl+D', () => {
    const before = templateStore.flatNodes.size
    fireKey(handleKeyDown, 'd', { ctrlKey: true })
    expect(templateStore.flatNodes.size).toBe(before + 1)
  })

  it('removes element on Delete', () => {
    fireKey(handleKeyDown, 'Delete')
    expect(templateStore.getNodeById('el-1')).toBeUndefined()
    expect(editorStore.selectedElementId).toBeNull()
  })

  it('does nothing when no element selected', () => {
    editorStore.selectElement(null)
    fireKey(handleKeyDown, 'ArrowRight')
    const node = templateStore.getNodeById('el-1')!
    expect(node.properties.x).toBe(100) // unchanged
  })

  it('does not intercept when target is input', () => {
    const event = new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })
    Object.defineProperty(event, 'target', { value: document.createElement('input') })
    handleKeyDown(event)
    const node = templateStore.getNodeById('el-1')!
    expect(node.properties.x).toBe(100) // unchanged
  })

  // Story 30.7 — Backspace sem metaKey deve remover (AC2)
  it('removes element on Backspace (no metaKey required)', () => {
    fireKey(handleKeyDown, 'Backspace')
    expect(templateStore.getNodeById('el-1')).toBeUndefined()
    expect(editorStore.selectedElementId).toBeNull()
  })

  // Story 30.7 — Backspace em input não deve ser interceptado (AC3)
  it('does not remove when Backspace fired inside input', () => {
    const event = new KeyboardEvent('keydown', { key: 'Backspace', bubbles: true, cancelable: true })
    Object.defineProperty(event, 'target', { value: document.createElement('input') })
    handleKeyDown(event)
    expect(templateStore.getNodeById('el-1')).toBeDefined() // not removed
  })

  // Story 30.7 — Backspace em textarea não deve ser interceptado (AC3)
  it('does not remove when Backspace fired inside textarea', () => {
    const event = new KeyboardEvent('keydown', { key: 'Backspace', bubbles: true, cancelable: true })
    Object.defineProperty(event, 'target', { value: document.createElement('textarea') })
    handleKeyDown(event)
    expect(templateStore.getNodeById('el-1')).toBeDefined() // not removed
  })
})
