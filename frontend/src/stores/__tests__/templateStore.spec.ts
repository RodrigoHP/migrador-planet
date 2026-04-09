import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTemplateStore } from '../templateStore'
import type { DocumentTree, TreeNode } from '@/types/template.types'

const mockRoot: TreeNode = {
  id: 'root-1',
  type: 'document',
  name: 'Document',
  children: [
    {
      id: 'header-1',
      type: 'header',
      name: 'Header',
      children: [
        {
          id: 'field-1',
          type: 'field',
          name: 'CompanyName',
          binding: '{{company_name}}',
          children: [],
          properties: { fontSize: 16 },
          visibility: true,
        },
      ],
      properties: {},
      visibility: true,
    },
    {
      id: 'section-1',
      type: 'section',
      name: 'Main Section',
      children: [],
      properties: {},
      visibility: true,
    },
  ],
  properties: {},
  visibility: true,
}

const mockTree: DocumentTree = { root: mockRoot }

describe('templateStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with null documentTree', () => {
    const store = useTemplateStore()
    expect(store.documentTree).toBeNull()
    expect(store.flatNodes.size).toBe(0)
  })

  it('loadTree populates documentTree and flatNodes', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    expect(store.documentTree).toEqual(mockTree)
    // root + header + field + section = 4 nodes
    expect(store.flatNodes.size).toBe(4)
  })

  it('getRootNode returns the root after loadTree', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    expect(store.getRootNode?.id).toBe('root-1')
  })

  it('getNodeById returns the correct node', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    const node = store.getNodeById('field-1')
    expect(node).toBeDefined()
    expect(node?.name).toBe('CompanyName')
    expect(node?.binding).toBe('{{company_name}}')
  })

  it('getNodeById returns undefined for unknown id', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    expect(store.getNodeById('nonexistent')).toBeUndefined()
  })

  it('getNodesByType returns nodes of given type', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    const fields = store.getNodesByType('field')
    expect(fields).toHaveLength(1)
    expect(fields[0]?.id).toBe('field-1')
  })

  it('getChildren returns direct children of a node', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    const children = store.getChildren('root-1')
    expect(children).toHaveLength(2)
    expect(children.map((c) => c.id)).toContain('header-1')
    expect(children.map((c) => c.id)).toContain('section-1')
  })

  it('updateNodeProperties merges properties', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    store.updateNodeProperties('field-1', { fontSize: 20, color: 'red' })
    const node = store.getNodeById('field-1')
    expect(node?.properties.fontSize).toBe(20)
    expect(node?.properties.color).toBe('red')
  })

  // Story 10.3 — Bug 2: loadTree com document_structure vazio não deve lançar exceção
  it('loadTree({}) does not throw when tree has no root', () => {
    const store = useTemplateStore()
    expect(() => store.loadTree({} as any)).not.toThrow()
    expect(store.documentTree).toBeNull()
    expect(store.flatNodes.size).toBe(0)
  })

  it('loadTree with null does not throw', () => {
    const store = useTemplateStore()
    expect(() => store.loadTree(null as any)).not.toThrow()
    expect(store.documentTree).toBeNull()
  })

  // Story 12.8 — documentType badge
  it('documentType starts as null', () => {
    const store = useTemplateStore()
    expect(store.documentType).toBeNull()
  })

  it('setDocumentType updates documentType', () => {
    const store = useTemplateStore()
    store.setDocumentType('boleto-bancario')
    expect(store.documentType).toBe('boleto-bancario')
  })

  // Story 33.3 — updateNodeProperties bulk increments mutationVersion
  it('updateNodeProperties increments mutationVersion', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    const vBefore = store.mutationVersion
    store.updateNodeProperties('field-1', { fontSize: 24 })
    expect(store.mutationVersion).toBe(vBefore + 1)
  })

  it('updateNodeProperties pushes undo snapshot', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    expect(store.undoStack.length).toBe(0)
    store.updateNodeProperties('field-1', { fontSize: 24 })
    expect(store.undoStack.length).toBe(1)
  })

  // Story 39.1 — Redo
  it('undoLastAction moves current state to redoStack', () => {
    const store = useTemplateStore()
    const tree: DocumentTree = { root: {
      id: 'r', type: 'document', name: 'D', children: [{
        id: 'f1', type: 'field', name: 'F', children: [],
        properties: { fontSize: 10 }, visibility: true,
      }], properties: {}, visibility: true,
    }}
    store.loadTree(tree)
    store.updateNodeProperties('f1', { fontSize: 24 })
    expect(store.undoStack.length).toBe(1)
    expect(store.redoStack.length).toBe(0)
    store.undoLastAction()
    expect(store.undoStack.length).toBe(0)
    expect(store.redoStack.length).toBe(1)
  })

  it('redoAction restores undone state', () => {
    const store = useTemplateStore()
    const tree: DocumentTree = { root: {
      id: 'r', type: 'document', name: 'D', children: [{
        id: 'f1', type: 'field', name: 'F', children: [],
        properties: { fontSize: 10 }, visibility: true,
      }], properties: {}, visibility: true,
    }}
    store.loadTree(tree)
    store.updateNodeProperties('f1', { fontSize: 50 })
    expect(store.getNodeById('f1')!.properties.fontSize).toBe(50)
    store.undoLastAction()
    expect(store.getNodeById('f1')!.properties.fontSize).toBe(10)
    store.redoAction()
    expect(store.getNodeById('f1')!.properties.fontSize).toBe(50)
  })

  it('new mutation clears redoStack', () => {
    const store = useTemplateStore()
    const tree: DocumentTree = { root: {
      id: 'r', type: 'document', name: 'D', children: [{
        id: 'f1', type: 'field', name: 'F', children: [],
        properties: { fontSize: 10 }, visibility: true,
      }], properties: {}, visibility: true,
    }}
    store.loadTree(tree)
    store.updateNodeProperties('f1', { fontSize: 24 })
    store.undoLastAction()
    expect(store.redoStack.length).toBe(1)
    store.updateNodeProperties('f1', { fontSize: 30 })
    expect(store.redoStack.length).toBe(0)
  })

  // Story 33.5 — updateNodeProperty handles VisibilityConfig objects
  it('updateNodeProperty handles VisibilityConfig object with mode', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    store.updateNodeProperty('field-1', 'visibility', { mode: 'hidden' })
    const node = store.getNodeById('field-1')
    expect(node?.properties.visibility).toEqual({ mode: 'hidden' })
  })

  it('updateNodeProperty handles VisibilityConfig with mode=always', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    store.updateNodeProperty('field-1', 'visibility', { mode: 'always' })
    const node = store.getNodeById('field-1')
    expect(node?.properties.visibility).toEqual({ mode: 'always' })
  })

  it('updateNodeProperty still handles boolean visibility', () => {
    const store = useTemplateStore()
    store.loadTree(mockTree)
    store.updateNodeProperty('field-1', 'visibility', false)
    const node = store.getNodeById('field-1')
    expect(node?.properties.visibility).toBe(false)
  })
})
