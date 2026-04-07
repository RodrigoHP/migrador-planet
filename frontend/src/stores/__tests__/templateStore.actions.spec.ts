/**
 * Story 7.2 — templateStore actions tests
 * Covers: moveNode, addNode, duplicateNode, removeNode, groupNodes, undo
 * Story 29.7 — mutationVersion increments + generation patch hooks
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTemplateStore } from '../templateStore'
import { useGenerationStore } from '../generation'
import type { DocumentTree, TreeNode } from '@/types/template.types'

// ─── Fixture factory ──────────────────────────────────────────────────────────
function makeTree(): DocumentTree {
  const root: TreeNode = {
    id: 'root',
    type: 'document',
    name: 'Document',
    children: [
      {
        id: 'header',
        type: 'header',
        name: 'Header',
        children: [
          { id: 'logo', type: 'image', name: 'Logo', children: [], properties: {}, visibility: true },
        ],
        properties: {},
        visibility: true,
      },
      {
        id: 'flow',
        type: 'flow',
        name: 'Flow',
        children: [
          { id: 'title', type: 'text', name: 'Título', children: [], properties: {}, visibility: true },
          { id: 'chart', type: 'chart', name: 'Gráfico', children: [], properties: {}, visibility: true },
        ],
        properties: {},
        visibility: true,
      },
      {
        id: 'footer',
        type: 'footer',
        name: 'Footer',
        children: [],
        properties: {},
        visibility: true,
      },
    ],
    properties: {},
    visibility: true,
  }
  return { root }
}

// ─── Suite ────────────────────────────────────────────────────────────────────
describe('templateStore — Story 7.2 actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── moveNode ──────────────────────────────────────────────────────────────
  describe('moveNode', () => {
    it('reorders nodes within the same parent', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      // Move 'chart' before 'title' (index 0)
      store.moveNode('chart', 'flow', 0)

      const flowChildren = store.getChildren('flow')
      expect(flowChildren[0]?.id).toBe('chart')
      expect(flowChildren[1]?.id).toBe('title')
    })

    it('moves node to different parent (cross-section)', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      // Move 'logo' from header to flow
      store.moveNode('logo', 'flow')

      expect(store.getChildren('header').map((c) => c.id)).not.toContain('logo')
      expect(store.getChildren('flow').map((c) => c.id)).toContain('logo')
    })

    it('does nothing when moving node to itself', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const before = store.getChildren('flow').map((c) => c.id)
      store.moveNode('title', 'title')
      const after = store.getChildren('flow').map((c) => c.id)

      expect(after).toEqual(before)
    })

    it('does nothing when moving node into its own descendant', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const before = store.getChildren('root').map((c) => c.id)
      store.moveNode('flow', 'chart') // 'chart' is inside 'flow'
      const after = store.getChildren('root').map((c) => c.id)

      expect(after).toEqual(before)
    })

    it('updates flatNodes after move', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      store.moveNode('title', 'header')

      // title should still be in flatNodes
      expect(store.getNodeById('title')).toBeDefined()
    })

    it('pushes undo snapshot before mutation', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      expect(store.undoStack.length).toBe(0)
      store.moveNode('title', 'header')
      expect(store.undoStack.length).toBe(1)
    })
  })

  // ─── addNode ──────────────────────────────────────────────────────────────
  describe('addNode', () => {
    it('adds a child node to the given parent', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const newNode = store.addNode('flow', 'text')
      expect(newNode).not.toBeNull()
      expect(store.getChildren('flow').map((c) => c.id)).toContain(newNode!.id)
    })

    it('adds at specific index', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const newNode = store.addNode('flow', 'image', 0)
      expect(newNode).not.toBeNull()
      expect(store.getChildren('flow')[0]?.id).toBe(newNode!.id)
    })

    it('new node has correct type and default properties', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const newNode = store.addNode('footer', 'table')
      expect(newNode?.type).toBe('table')
      expect(newNode?.children).toEqual([])
      expect(newNode?.visibility).toBe(true)
    })

    it('registers new node in flatNodes', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const newNode = store.addNode('flow', 'text')
      expect(store.getNodeById(newNode!.id)).toBeDefined()
    })

    it('pushes undo snapshot', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      store.addNode('flow', 'text')
      expect(store.undoStack.length).toBe(1)
    })

    it('returns null when parent not found', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const result = store.addNode('nonexistent-id', 'text')
      expect(result).toBeNull()
    })
  })

  // ─── duplicateNode ────────────────────────────────────────────────────────
  describe('duplicateNode', () => {
    it('creates a copy below the original', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const clone = store.duplicateNode('title')
      expect(clone).not.toBeNull()

      const flowChildren = store.getChildren('flow')
      const titleIdx = flowChildren.findIndex((c) => c.id === 'title')
      const cloneIdx = flowChildren.findIndex((c) => c.id === clone!.id)
      expect(cloneIdx).toBe(titleIdx + 1)
    })

    it('clone has a new unique id', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const clone = store.duplicateNode('title')
      expect(clone?.id).not.toBe('title')
    })

    it('deep clones children recursively', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      // header has logo as child
      const clone = store.duplicateNode('header')
      expect(clone).not.toBeNull()
      expect(clone!.children.length).toBe(1)
      expect(clone!.children[0]?.id).not.toBe('logo') // new id
      expect(clone!.children[0]?.type).toBe('image')
    })

    it('registers clone in flatNodes', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const clone = store.duplicateNode('title')
      expect(store.getNodeById(clone!.id)).toBeDefined()
    })

    it('pushes undo snapshot', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      store.duplicateNode('title')
      expect(store.undoStack.length).toBe(1)
    })

    it('returns null for unknown id', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      expect(store.duplicateNode('unknown')).toBeNull()
    })
  })

  // ─── removeNode ───────────────────────────────────────────────────────────
  describe('removeNode', () => {
    it('removes a leaf node', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const result = store.removeNode('title')
      expect(result).toBe(true)
      expect(store.getChildren('flow').map((c) => c.id)).not.toContain('title')
      expect(store.getNodeById('title')).toBeUndefined()
    })

    it('removes a node with children recursively', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const result = store.removeNode('header')
      expect(result).toBe(true)
      expect(store.getChildren('root').map((c) => c.id)).not.toContain('header')
      // Children should also be removed from flatNodes
      expect(store.getNodeById('logo')).toBeUndefined()
    })

    it('returns false for unknown id', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      expect(store.removeNode('nonexistent')).toBe(false)
    })

    it('pushes undo snapshot before removal', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      store.removeNode('title')
      expect(store.undoStack.length).toBe(1)
    })
  })

  // ─── groupNodes ───────────────────────────────────────────────────────────
  describe('groupNodes', () => {
    it('wraps selected nodes in a new section', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const section = store.groupNodes(['title', 'chart'], 'flow')
      expect(section).not.toBeNull()
      expect(section!.type).toBe('section')
      expect(section!.children.map((c) => c.id)).toEqual(['title', 'chart'])
    })

    it('section is inserted at the position of the first grouped node', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const section = store.groupNodes(['title', 'chart'], 'flow')
      const flowChildren = store.getChildren('flow')
      // flow previously had [title, chart] → now has [section]
      expect(flowChildren[0]?.id).toBe(section!.id)
      expect(flowChildren.length).toBe(1)
    })

    it('registers section and children in flatNodes', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      const section = store.groupNodes(['title'], 'flow')
      expect(store.getNodeById(section!.id)).toBeDefined()
    })

    it('pushes undo snapshot', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      store.groupNodes(['title'], 'flow')
      expect(store.undoStack.length).toBe(1)
    })

    it('returns null when nodeIds are empty', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      expect(store.groupNodes([], 'flow')).toBeNull()
    })
  })

  // ─── undo stack ───────────────────────────────────────────────────────────
  describe('undoLastAction', () => {
    it('reverts the last operation', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      // Move title → header
      store.moveNode('title', 'header')
      expect(store.getChildren('header').map((c) => c.id)).toContain('title')

      // Undo
      store.undoLastAction()
      expect(store.getChildren('header').map((c) => c.id)).not.toContain('title')
      expect(store.getChildren('flow').map((c) => c.id)).toContain('title')
    })

    it('can undo multiple operations in sequence', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      store.addNode('flow', 'text')        // op 1
      store.addNode('footer', 'image')     // op 2

      expect(store.getChildren('footer').length).toBe(1)

      store.undoLastAction() // reverts op 2
      expect(store.getChildren('footer').length).toBe(0)

      store.undoLastAction() // reverts op 1
      expect(store.getChildren('flow').length).toBe(2) // back to original
    })

    it('does nothing when stack is empty', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      expect(() => store.undoLastAction()).not.toThrow()
    })

    it('loadTree clears the undo stack', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      store.moveNode('title', 'header')
      expect(store.undoStack.length).toBe(1)

      store.loadTree(makeTree())
      expect(store.undoStack.length).toBe(0)
    })

    it('stack is capped at 20 snapshots', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())

      // Do 25 addNode operations → only last 20 should remain
      for (let i = 0; i < 25; i++) {
        store.addNode('footer', 'text')
      }

      expect(store.undoStack.length).toBeLessThanOrEqual(20)
    })
  })

  // ─── Story 29.7: mutationVersion + generation patch hooks ─────────────────
  describe('Story 29.7 — mutationVersion + generation patch hooks', () => {
    it('moveNode incrementa mutationVersion', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())
      const versionAntes = store.mutationVersion

      store.moveNode('title', 'header')

      expect(store.mutationVersion).toBe(versionAntes + 1)
    })

    it('addNode incrementa mutationVersion', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())
      const versionAntes = store.mutationVersion

      store.addNode('flow', 'label')

      expect(store.mutationVersion).toBe(versionAntes + 1)
    })

    it('removeNode incrementa mutationVersion', () => {
      const store = useTemplateStore()
      store.loadTree(makeTree())
      const versionAntes = store.mutationVersion

      store.removeNode('title')

      expect(store.mutationVersion).toBe(versionAntes + 1)
    })

    it('removeNode chama patchRemoveNode na generationStore', () => {
      const store = useTemplateStore()
      const genStore = useGenerationStore()
      store.loadTree(makeTree())
      const spy = vi.spyOn(genStore, 'patchRemoveNode')

      store.removeNode('title')

      expect(spy).toHaveBeenCalledWith('title')
    })

    it('addNode chama patchAddNode na generationStore', () => {
      const store = useTemplateStore()
      const genStore = useGenerationStore()
      store.loadTree(makeTree())
      const spy = vi.spyOn(genStore, 'patchAddNode')

      store.addNode('flow', 'label')

      expect(spy).toHaveBeenCalledOnce()
      const [calledNode, calledParentId] = spy.mock.calls[0]!
      expect(calledNode.type).toBe('label')
      expect(calledParentId).toBe('flow')
    })

    it('moveNode chama patchMoveNode na generationStore', () => {
      const store = useTemplateStore()
      const genStore = useGenerationStore()
      store.loadTree(makeTree())
      const spy = vi.spyOn(genStore, 'patchMoveNode')

      store.moveNode('title', 'header')

      expect(spy).toHaveBeenCalledWith('title', 'header')
    })
  })
})
