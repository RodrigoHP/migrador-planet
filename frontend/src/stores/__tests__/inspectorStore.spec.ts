import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useInspectorStore } from '../inspectorStore'
import type { TreeNode } from '@/types/template.types'

const makeNode = (overrides: Partial<TreeNode> = {}): TreeNode => ({
  id: 'node-1',
  type: 'document',
  name: 'Document Root',
  children: [],
  properties: { x: 10, y: 20, width: 794, height: 1123 },
  visibility: true,
  ...overrides,
})

describe('inspectorStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with default level = page and no selection', () => {
    const store = useInspectorStore()
    expect(store.level).toBe('page')
    expect(store.selectedNode).toBeNull()
    expect(store.hasSelection).toBe(false)
  })

  it('selectNode sets selectedNode, level and properties', () => {
    const store = useInspectorStore()
    const node = makeNode({ type: 'text', id: 'el-1', name: 'Label' })
    store.selectNode(node)
    expect(store.selectedNode).toEqual(node)
    expect(store.level).toBe('element')
    expect(store.properties['x']).toBe(10)
  })

  it('selectNode maps document type to page level', () => {
    const store = useInspectorStore()
    const node = makeNode({ type: 'document' })
    store.selectNode(node)
    expect(store.level).toBe('page')
  })

  it('selectNode maps section type to section level', () => {
    const store = useInspectorStore()
    const node = makeNode({ type: 'section', id: 's-1', name: 'Section' })
    store.selectNode(node)
    expect(store.level).toBe('section')
  })

  it('selectNode maps table type to component level', () => {
    const store = useInspectorStore()
    const node = makeNode({ type: 'table', id: 't-1', name: 'Table' })
    store.selectNode(node)
    expect(store.level).toBe('component')
  })

  it('clearSelection resets state', () => {
    const store = useInspectorStore()
    store.selectNode(makeNode({ type: 'text' }))
    store.clearSelection()
    expect(store.selectedNode).toBeNull()
    expect(store.level).toBe('page')
    expect(store.properties).toEqual({})
    expect(store.hasSelection).toBe(false)
  })

  it('setLevel changes level directly', () => {
    const store = useInspectorStore()
    store.setLevel('section')
    expect(store.level).toBe('section')
  })

  it('initFromTree sets root node as selected with page level', () => {
    const store = useInspectorStore()
    const root = makeNode({ type: 'document', id: 'root-1', name: 'Root Document' })
    store.initFromTree(root)
    expect(store.selectedNode).toEqual(root)
    expect(store.level).toBe('page')
    expect(store.hasSelection).toBe(true)
    expect(store.properties['x']).toBe(10)
  })

  it('initFromTree with header node sets section level (Story 33.1)', () => {
    const store = useInspectorStore()
    const header = makeNode({ type: 'header', id: 'h-1', name: 'Header' })
    store.initFromTree(header)
    expect(store.level).toBe('section')
  })

  it('selectNode maps footer to section level (Story 33.1)', () => {
    const store = useInspectorStore()
    const footer = makeNode({ type: 'footer', id: 'f-1', name: 'Footer' })
    store.selectNode(footer)
    expect(store.level).toBe('section')
  })

  it('selectNode maps flow to section level (Story 33.1)', () => {
    const store = useInspectorStore()
    const flow = makeNode({ type: 'flow', id: 'fl-1', name: 'Flow' })
    store.selectNode(flow)
    expect(store.level).toBe('section')
  })

  it('currentLevelLabel returns correct label for level', () => {
    const store = useInspectorStore()
    expect(store.currentLevelLabel).toBe('Page')
    store.setLevel('section')
    expect(store.currentLevelLabel).toBe('Section')
    store.setLevel('component')
    expect(store.currentLevelLabel).toBe('Component')
    store.setLevel('element')
    expect(store.currentLevelLabel).toBe('Element')
  })
})
