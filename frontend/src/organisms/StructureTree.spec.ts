import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import StructureTree from './StructureTree.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useEditorStore } from '@/stores/editorStore'
import { useLayoutStore } from '@/stores/layout'
import type { DocumentTree, TreeNode } from '@/types/template.types'

// ─── Mock idb (used by layoutStore) ──────────────────────────────────────
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

// ─── Mock tree fixture ────────────────────────────────────────────────────
function makeTree(): DocumentTree {
  const root: TreeNode = {
    id: 'doc-1',
    type: 'document',
    name: 'Document',
    children: [
      {
        id: 'header-1',
        type: 'header',
        name: 'Header',
        children: [
          {
            id: 'logo-1',
            type: 'image',
            name: 'Logo',
            children: [],
            properties: {},
            visibility: true,
          },
          {
            id: 'client-1',
            type: 'text',
            name: 'Cliente',
            binding: 'cliente',
            children: [],
            properties: {},
            visibility: true,
          },
        ],
        properties: {},
        visibility: true,
      },
      {
        id: 'flow-1',
        type: 'flow',
        name: 'Flow',
        children: [
          {
            id: 'title-1',
            type: 'text',
            name: 'Título',
            binding: 'titulo',
            children: [],
            properties: {},
            visibility: true,
          },
          {
            id: 'chart-1',
            type: 'chart',
            name: 'Gráfico Mensal',
            binding: 'grafico_mensal',
            isOptional: true,
            children: [],
            properties: {},
            visibility: true,
          },
        ],
        properties: {},
        visibility: true,
      },
      {
        id: 'footer-1',
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

// ─── Helper: mount with pinia ─────────────────────────────────────────────
function mountTree() {
  const pinia = createPinia()
  return mount(StructureTree, {
    global: {
      plugins: [pinia],
    },
  })
}

describe('StructureTree', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders empty state when no tree is loaded', () => {
    const wrapper = mountTree()
    expect(wrapper.text()).toContain('Nenhum documento carregado')
  })

  it('renders root node after loadTree', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Document')
    expect(wrapper.text()).toContain('📄')
  })

  it('expands root node by default and shows first-level children', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Root is expanded by default so children are visible
    expect(wrapper.text()).toContain('Header')
    expect(wrapper.text()).toContain('Flow')
    expect(wrapper.text()).toContain('Footer')
  })

  it('renders type icons for different node types', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // After expanding Header manually, image/text icons appear
    // Root is expanded → header/flow/footer visible
    expect(wrapper.text()).toContain('📦') // header/flow/footer
  })

  it('renders binding indicator for nodes with binding', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Header is a direct child of root (root is expanded by default)
    // Click header node toggle once to expand it → reveals Logo + Cliente children
    const nodeRows = wrapper.findAll('.structure-tree-node')
    // index 0 = Document (root), index 1 = Header (first child)
    const headerRow = nodeRows[1]
    expect(headerRow).toBeDefined()
    await headerRow!.find('.structure-tree-node__toggle').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('cliente')
  })

  it('renders optional badge for nodes with isOptional=true', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Root is expanded → Header (idx 1), Flow (idx 2), Footer (idx 3) visible
    // Click Flow node toggle once to expand it → reveals Título + Gráfico Mensal (⚠)
    const nodeRows = wrapper.findAll('.structure-tree-node')
    // index 0 = Document, 1 = Header, 2 = Flow, 3 = Footer
    const flowRow = nodeRows[2]
    expect(flowRow).toBeDefined()
    await flowRow!.find('.structure-tree-node__toggle').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('⚠')
  })

  it('clicking a node updates inspectorStore.selectedNode and editorStore.selectedElementId', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    const inspectorStore = useInspectorStore()
    const editorStore = useEditorStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Click root Document node
    const docRow = wrapper.findAll('.structure-tree-node')[0]
    expect(docRow).toBeDefined()
    await docRow!.trigger('click')
    await flushPromises()

    expect(inspectorStore.selectedNode?.id).toBe('doc-1')
    expect(editorStore.selectedElementId).toBe('doc-1')
  })

  it('clicking a different node changes selection (only one selected at a time)', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    const inspectorStore = useInspectorStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Click Document node toggle (not the row itself) to avoid collapsing
    // Use the toggle span to expand/collapse without selecting
    // Instead, click Header node (index 1) to select it
    const headerRow = wrapper.findAll('.structure-tree-node')[1]
    expect(headerRow).toBeDefined()
    await headerRow!.trigger('click')
    await flushPromises()
    expect(inspectorStore.selectedNode?.id).toBe('header-1')

    // Now click Footer node — after Header click, Header expanded (its children added)
    // so we need to find Footer fresh
    const footerRows = wrapper.findAll('.structure-tree-node')
    const footerRow = footerRows.find((r) => r.text().includes('Footer'))
    expect(footerRow).toBeDefined()
    await footerRow!.trigger('click')
    await flushPromises()
    // Footer is now selected
    expect(inspectorStore.selectedNode?.id).toBe('footer-1')
    // Header is no longer selected
    expect(inspectorStore.selectedNode?.id).not.toBe('header-1')
  })

  it('selected node receives --selected CSS class', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    const rows = wrapper.findAll('.structure-tree-node')
    await rows[0]!.trigger('click')
    await flushPromises()

    expect(rows[0]!.classes()).toContain('structure-tree-node--selected')
  })

  it('expand/collapse toggles visibility of children', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Root is expanded → Header visible
    expect(wrapper.text()).toContain('Header')

    // Click root toggle to collapse
    const rootToggle = wrapper.find('.structure-tree-node__toggle')
    await rootToggle.trigger('click')
    await flushPromises()

    // Now Header/Flow/Footer should be hidden
    expect(wrapper.text()).not.toContain('Header')
    expect(wrapper.text()).not.toContain('Flow')
  })

  it('resets selection when activeLayoutId changes', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()
    const inspectorStore = useInspectorStore()
    const layoutStore = useLayoutStore()
    templateStore.loadTree(makeTree())

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Select a node
    const rows = wrapper.findAll('.structure-tree-node')
    await rows[0]!.trigger('click')
    await flushPromises()
    expect(inspectorStore.selectedNode).not.toBeNull()

    // Change layout
    layoutStore.setActiveLayout('layout-2')
    await flushPromises()

    expect(inspectorStore.selectedNode).toBeNull()
  })

  it('renders tree with 5+ levels of depth', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()

    // Build 5-level deep tree
    const level5: TreeNode = {
      id: 'cell-1',
      type: 'text',
      name: 'Cell',
      children: [],
      properties: {},
      visibility: true,
    }
    const level4: TreeNode = {
      id: 'row-1',
      type: 'section',
      name: 'Row',
      children: [level5],
      properties: {},
      visibility: true,
    }
    const level3: TreeNode = {
      id: 'table-1',
      type: 'table',
      name: 'Table',
      children: [level4],
      properties: {},
      visibility: true,
    }
    const level2: TreeNode = {
      id: 'container-1',
      type: 'container',
      name: 'Container',
      children: [level3],
      properties: {},
      visibility: true,
    }
    const level1: TreeNode = {
      id: 'section-1',
      type: 'section',
      name: 'Section',
      children: [level2],
      properties: {},
      visibility: true,
    }
    const deepRoot: TreeNode = {
      id: 'doc-deep',
      type: 'document',
      name: 'Document',
      children: [level1],
      properties: {},
      visibility: true,
    }

    templateStore.loadTree({ root: deepRoot })

    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Expand each level manually
    const expand = async (name: string) => {
      const rows = wrapper.findAll('.structure-tree-node')
      const row = rows.find((r) => r.text().includes(name))
      if (row) {
        await row.find('.structure-tree-node__toggle').trigger('click')
        await flushPromises()
      }
    }

    // Root is expanded, expand Section
    await expand('Section')
    await expand('Container')
    await expand('Table')
    await expand('Row')

    expect(wrapper.text()).toContain('Cell')
  })

  it('performance: tree with 200+ nodes renders without error', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const templateStore = useTemplateStore()

    // Build 200+ node tree
    const children: TreeNode[] = []
    for (let i = 0; i < 50; i++) {
      const subChildren: TreeNode[] = []
      for (let j = 0; j < 4; j++) {
        subChildren.push({
          id: `leaf-${i}-${j}`,
          type: 'text',
          name: `Leaf ${i}-${j}`,
          children: [],
          properties: {},
          visibility: true,
        })
      }
      children.push({
        id: `section-${i}`,
        type: 'section',
        name: `Section ${i}`,
        children: subChildren,
        properties: {},
        visibility: true,
      })
    }

    const bigRoot: TreeNode = {
      id: 'doc-big',
      type: 'document',
      name: 'Document',
      children,
      properties: {},
      visibility: true,
    }

    templateStore.loadTree({ root: bigRoot })

    const start = performance.now()
    const wrapper = mount(StructureTree, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Expand root (already done) then expand a few sections
    const rows = wrapper.findAll('.structure-tree-node')
    const section0 = rows.find((r) => r.text().includes('Section 0'))
    if (section0) {
      const toggleTime = performance.now()
      await section0.find('.structure-tree-node__toggle').trigger('click')
      await flushPromises()
      const elapsed = performance.now() - toggleTime
      // AC#10: expand/collapse <500ms (JSDOM has overhead vs real browser)
      expect(elapsed).toBeLessThan(500)
    }

    const totalTime = performance.now() - start
    // Initial render of 200+ node tree should be reasonable
    expect(totalTime).toBeLessThan(2000)
  })
})
