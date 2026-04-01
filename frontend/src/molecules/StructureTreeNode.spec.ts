import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StructureTreeNode from './StructureTreeNode.vue'
import type { TreeNode } from '@/types/template.types'

const leafNode: TreeNode = {
  id: 'node-leaf',
  type: 'text',
  name: 'LeafNode',
  children: [],
  properties: {},
  visibility: true,
}

const containerNode: TreeNode = {
  id: 'node-container',
  type: 'section',
  name: 'ContainerNode',
  children: [leafNode],
  properties: {},
  visibility: true,
}

function mountNode(node: TreeNode, extra = {}) {
  return mount(StructureTreeNode, {
    props: {
      node,
      depth: 0,
      expandedNodes: new Set<string>(),
      selectedNodeId: null,
      ...extra,
    },
    global: {
      stubs: {
        // Stub recursive component to prevent infinite render
        StructureTreeNode: true,
      },
    },
  })
}

describe('StructureTreeNode — Story 28.6', () => {
  it('clicar no nó seleciona (emite select) mas NÃO emite toggle', async () => {
    const wrapper = mountNode(containerNode)
    await wrapper.find('.structure-tree-node').trigger('click')
    expect(wrapper.emitted('select')).toHaveLength(1)
    expect(wrapper.emitted('select')![0][0]).toMatchObject({ id: 'node-container' })
    expect(wrapper.emitted('toggle')).toBeUndefined()
  })

  it('clicar no ícone toggle emite toggle mas não emite select por si só', async () => {
    const wrapper = mountNode(containerNode, { expandedNodes: new Set(['node-container']) })
    const toggleEl = wrapper.find('.structure-tree-node__toggle')
    // The toggle icon exists for nodes with children
    expect(toggleEl.exists()).toBe(true)
    // Click with .stop — should emit toggle NOT select
    await toggleEl.trigger('click')
    expect(wrapper.emitted('toggle')).toHaveLength(1)
    expect(wrapper.emitted('toggle')![0][0]).toBe('node-container')
    // select should NOT have been emitted from the toggle icon click
    expect(wrapper.emitted('select')).toBeUndefined()
  })

  it('nó sem filhos não mostra seta expand/collapse', () => {
    const wrapper = mountNode(leafNode)
    expect(wrapper.find('.structure-tree-node__arrow').exists()).toBe(false)
    expect(wrapper.find('.structure-tree-node__leaf').exists()).toBe(true)
  })

  it('nó selecionado recebe classe --selected', () => {
    const wrapper = mountNode(leafNode, { selectedNodeId: 'node-leaf' })
    expect(wrapper.find('.structure-tree-node--selected').exists()).toBe(true)
  })

  it('nó não selecionado não recebe classe --selected', () => {
    const wrapper = mountNode(leafNode, { selectedNodeId: null })
    expect(wrapper.find('.structure-tree-node--selected').exists()).toBe(false)
  })
})
