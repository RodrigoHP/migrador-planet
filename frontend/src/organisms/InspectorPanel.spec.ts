import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import InspectorPanel from './InspectorPanel.vue'
import { useInspectorStore } from '@/stores/inspectorStore'
import type { TreeNode } from '@/types/template.types'

// ─── Mock idb (used by layoutStore transitively) ──────────────────────────
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

// ─── Mock inspector-level sub-components to isolate routing logic ─────────
vi.mock('./inspectors/PageInspector.vue', () => ({
  default: { template: '<div class="page-inspector-mock" />', props: ['node'] },
}))
vi.mock('./inspectors/SectionInspector.vue', () => ({
  default: { template: '<div class="section-inspector-mock" />', props: ['node'] },
}))
vi.mock('./inspectors/ComponentInspector.vue', () => ({
  default: { template: '<div class="component-inspector-mock" />', props: ['node'] },
}))
vi.mock('./inspectors/ElementInspector.vue', () => ({
  default: { template: '<div class="element-inspector-mock" />', props: ['node'] },
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────
function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    id: 'node-1',
    type: 'document',
    name: 'Documento Principal',
    children: [],
    properties: {},
    visibility: true,
    ...overrides,
  }
}

// ─── Mount helper ─────────────────────────────────────────────────────────
function mountPanel() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(InspectorPanel, {
    global: { plugins: [pinia] },
  })
  const inspector = useInspectorStore()
  return { wrapper, inspector }
}

// ─── Tests ────────────────────────────────────────────────────────────────
describe('InspectorPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // AC 1: renders in its container
  it('renders the inspector-panel root element', () => {
    const { wrapper } = mountPanel()
    expect(wrapper.find('.inspector-panel').exists()).toBe(true)
  })

  // AC 4: no selection → PageInspector (level default = 'page')
  it('renders PageInspector by default when no node is selected', () => {
    const { wrapper } = mountPanel()
    expect(wrapper.find('.page-inspector-mock').exists()).toBe(true)
  })

  // AC 2: level = 'section' → SectionInspector
  it('renders SectionInspector when level is section', async () => {
    const { wrapper, inspector } = mountPanel()
    const sectionNode = makeNode({ type: 'section', name: 'Header Seção' })
    inspector.selectNode(sectionNode)
    await flushPromises()
    expect(wrapper.find('.section-inspector-mock').exists()).toBe(true)
  })

  // AC 2: level = 'component' → ComponentInspector
  it('renders ComponentInspector when level is component', async () => {
    const { wrapper, inspector } = mountPanel()
    const tableNode = makeNode({ type: 'table', name: 'Tabela Principal' })
    inspector.selectNode(tableNode)
    await flushPromises()
    expect(wrapper.find('.component-inspector-mock').exists()).toBe(true)
  })

  // AC 2: chart node → level = 'component' → ComponentInspector
  it('renders ComponentInspector for chart node', async () => {
    const { wrapper, inspector } = mountPanel()
    const chartNode = makeNode({ type: 'chart', name: 'Gráfico de Vendas' })
    inspector.selectNode(chartNode)
    await flushPromises()
    expect(wrapper.find('.component-inspector-mock').exists()).toBe(true)
  })

  // AC 2: level = 'element' → ElementInspector
  it('renders ElementInspector when level is element', async () => {
    const { wrapper, inspector } = mountPanel()
    const textNode = makeNode({ type: 'text', name: 'Campo Texto' })
    inspector.selectNode(textNode)
    await flushPromises()
    expect(wrapper.find('.element-inspector-mock').exists()).toBe(true)
  })

  // AC 2: field node → level = 'element' → ElementInspector
  it('renders ElementInspector for field node', async () => {
    const { wrapper, inspector } = mountPanel()
    const fieldNode = makeNode({ type: 'field', name: 'Campo CPF' })
    inspector.selectNode(fieldNode)
    await flushPromises()
    expect(wrapper.find('.element-inspector-mock').exists()).toBe(true)
  })

  // AC 4: clearSelection → back to PageInspector
  it('returns to PageInspector after clearSelection', async () => {
    const { wrapper, inspector } = mountPanel()
    inspector.selectNode(makeNode({ type: 'section', name: 'Seção' }))
    await flushPromises()
    expect(wrapper.find('.section-inspector-mock').exists()).toBe(true)

    inspector.clearSelection()
    await flushPromises()
    expect(wrapper.find('.page-inspector-mock').exists()).toBe(true)
  })

  // AC 5: title format "Inspetor de {levelLabel}: {node.name}"
  it('shows default title when no node is selected', () => {
    const { wrapper } = mountPanel()
    const title = wrapper.find('.inspector-panel__title').text()
    expect(title).toContain('Inspetor de')
    expect(title).toContain('Documento')
  })

  it('shows node name in title when node is selected', async () => {
    const { wrapper, inspector } = mountPanel()
    inspector.selectNode(makeNode({ type: 'section', name: 'Cabeçalho' }))
    await flushPromises()
    const title = wrapper.find('.inspector-panel__title').text()
    expect(title).toContain('Cabeçalho')
    expect(title).toContain('Inspetor de')
  })

  it('shows "Inspetor de Página" for page-level node', async () => {
    const { wrapper, inspector } = mountPanel()
    inspector.selectNode(makeNode({ type: 'document', name: 'Doc' }))
    await flushPromises()
    const title = wrapper.find('.inspector-panel__title').text()
    expect(title).toContain('Página')
  })

  it('shows "Inspetor de Seção" for section node', async () => {
    const { wrapper, inspector } = mountPanel()
    inspector.selectNode(makeNode({ type: 'section', name: 'Minha Seção' }))
    await flushPromises()
    const title = wrapper.find('.inspector-panel__title').text()
    expect(title).toContain('Seção')
    expect(title).toContain('Minha Seção')
  })

  it('shows "Inspetor de Componente" for table node', async () => {
    const { wrapper, inspector } = mountPanel()
    inspector.selectNode(makeNode({ type: 'table', name: 'Tabela' }))
    await flushPromises()
    const title = wrapper.find('.inspector-panel__title').text()
    expect(title).toContain('Componente')
  })

  it('shows "Inspetor de Elemento" for text node', async () => {
    const { wrapper, inspector } = mountPanel()
    inspector.selectNode(makeNode({ type: 'text', name: 'Título' }))
    await flushPromises()
    const title = wrapper.find('.inspector-panel__title').text()
    expect(title).toContain('Elemento')
    expect(title).toContain('Título')
  })

  // Routing switches correctly when different nodes are selected sequentially
  it('switches inspector component when node type changes', async () => {
    const { wrapper, inspector } = mountPanel()

    // Select element node
    inspector.selectNode(makeNode({ type: 'field', name: 'Campo' }))
    await flushPromises()
    expect(wrapper.find('.element-inspector-mock').exists()).toBe(true)

    // Switch to section node
    inspector.selectNode(makeNode({ type: 'section', name: 'Seção' }))
    await flushPromises()
    expect(wrapper.find('.section-inspector-mock').exists()).toBe(true)
    expect(wrapper.find('.element-inspector-mock').exists()).toBe(false)
  })

  // Panel has a scrollable content area (AC: scroll vertical)
  it('has a scrollable content region', () => {
    const { wrapper } = mountPanel()
    expect(wrapper.find('.inspector-panel__content').exists()).toBe(true)
  })
})
