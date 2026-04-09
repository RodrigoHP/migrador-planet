import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
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
  setActivePinia(createPinia())
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

describe('StructureTreeNode — Story 28.7: badges de status', () => {
  it('mostra badge com classe --unbound para nó text sem binding', () => {
    const node: TreeNode = {
      id: 'n1',
      type: 'text',
      name: 'T1',
      binding: undefined,
      children: [],
      properties: {},
      visibility: true,
    }
    const wrapper = mountNode(node)
    const badge = wrapper.find('.structure-tree-node__badge')
    expect(badge.exists()).toBe(true)
    expect(badge.classes()).toContain('badge--unbound')
  })

  it('mostra badge com classe --mapped para nó text com binding', () => {
    const node: TreeNode = {
      id: 'n2',
      type: 'text',
      name: 'T2',
      binding: 'data.vencimento',
      children: [],
      properties: {},
      visibility: true,
    }
    const wrapper = mountNode(node)
    const badge = wrapper.find('.structure-tree-node__badge')
    expect(badge.exists()).toBe(true)
    expect(badge.classes()).toContain('badge--mapped')
  })

  it('NÃO mostra badge de status em nó section (container)', () => {
    const node: TreeNode = {
      id: 'n3',
      type: 'section',
      name: 'Section',
      children: [],
      properties: {},
      visibility: true,
    }
    const wrapper = mountNode(node)
    expect(wrapper.find('.structure-tree-node__badge').exists()).toBe(false)
  })

  it('mostra barra de cobertura em container com filhos bindable', () => {
    const child1: TreeNode = {
      id: 'c1',
      type: 'text',
      name: 'C1',
      binding: 'data.a',
      children: [],
      properties: {},
      visibility: true,
    }
    const child2: TreeNode = {
      id: 'c2',
      type: 'text',
      name: 'C2',
      binding: undefined,
      children: [],
      properties: {},
      visibility: true,
    }
    const node: TreeNode = {
      id: 'n4',
      type: 'section',
      name: 'Section',
      children: [child1, child2],
      properties: {},
      visibility: true,
    }
    const wrapper = mountNode(node)
    expect(wrapper.find('.structure-tree-node__coverage-bar').exists()).toBe(true)
    expect(wrapper.text()).toContain('1/2')
  })

  it('NÃO mostra barra de cobertura em container sem filhos bindable', () => {
    const node: TreeNode = {
      id: 'n5',
      type: 'section',
      name: 'Section',
      children: [],
      properties: {},
      visibility: true,
    }
    const wrapper = mountNode(node)
    expect(wrapper.find('.structure-tree-node__coverage-bar').exists()).toBe(false)
  })
})
