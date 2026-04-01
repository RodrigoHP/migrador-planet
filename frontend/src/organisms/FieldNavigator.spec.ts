import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import FieldNavigator from './FieldNavigator.vue'
import { useMappingStore } from '@/stores/mapping'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useEditorStore } from '@/stores/editorStore'
import { useTemplateStore } from '@/stores/templateStore'
import type { FieldNavItem } from '@/types/field-navigator.types'
import type { DocumentTree, TreeNode } from '@/types/template.types'

// ─── Mocks ────────────────────────────────────────────────────────────────
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────
function makeFields(): FieldNavItem[] {
  return [
    { name: 'cliente', path: 'data.cliente', type: 'string', status: 'mapped', binding: 'cliente', nodeId: 'node-1', isOptional: false },
    { name: 'cpf', path: 'data.cpf', type: 'string', status: 'mapped', binding: 'cpf', isOptional: false },
    { name: 'endereco', path: 'data.endereco', type: 'string', status: 'unconfirmed', isOptional: true },
    { name: 'telefone', path: 'data.telefone', type: 'string', status: 'unmapped', isOptional: false },
    { name: 'transacoes', path: 'data.transacoes', type: 'array', status: 'mapped', binding: 'transacoes', isOptional: false },
    { name: 'lancamentos', path: 'data.lancamentos', type: 'array', status: 'unconfirmed', isOptional: false },
    { name: 'grafico_mensal', path: 'data.grafico_mensal', type: 'chart', status: 'mapped', binding: 'grafico_mensal', nodeId: 'chart-1', isOptional: true },
    { name: 'grafico_anual', path: 'data.grafico_anual', type: 'chart', status: 'unmapped', isOptional: false },
    { name: 'logo', path: 'data.logo', type: 'image', status: 'mapped', binding: 'logo', nodeId: 'img-1', isOptional: false },
  ]
}

function makeTree(): DocumentTree {
  const root: TreeNode = {
    id: 'doc-1',
    type: 'document',
    name: 'Document',
    children: [
      {
        id: 'node-1',
        type: 'text',
        name: 'Cliente',
        binding: 'cliente',
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
      {
        id: 'img-1',
        type: 'image',
        name: 'Logo',
        binding: 'logo',
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

// ─── Mount helper ─────────────────────────────────────────────────────────
function mountNavigator(fields?: FieldNavItem[]) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const mappingStore = useMappingStore()
  mappingStore.setFieldNavItems(fields ?? makeFields())
  return { wrapper: mount(FieldNavigator, { global: { plugins: [pinia] } }), pinia }
}

describe('FieldNavigator', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── AC3: Status groups (Story 28.2) ────────────────────────────────────
  it('renders STATUS groups (Sem binding, Ambíguos, Mapeados)', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()

    const text = wrapper.text()
    // Status groups replace old type groups
    expect(text).toContain('Sem binding')   // unmapped group label
    expect(text).toContain('Ambíguos')      // unconfirmed group label
    expect(text).toContain('Mapeados')      // mapped group label (even when collapsed)
  })

  it('shows field count in STATUS group headers', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()

    const text = wrapper.text()
    // 2 unmapped + 2 unconfirmed visible; mapped group shows count too
    expect(text).toContain('(2)') // unmapped group: telefone + grafico_anual
  })

  // ─── AC2: Status badges ───────────────────────────────────────────────────
  it('renders mapped status icon 🟩 for mapped fields', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    expect(wrapper.text()).toContain('🟩')
  })

  it('renders unmapped status icon 🟥 for unmapped fields', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    expect(wrapper.text()).toContain('🟥')
  })

  it('renders unconfirmed status icon 🟨 for unconfirmed fields', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    expect(wrapper.text()).toContain('🟨')
  })

  it('renders status badges for each group header', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('🟥') // unmapped group badge
    expect(text).toContain('🟨') // unconfirmed group badge
    expect(text).toContain('🟩') // mapped group badge
  })

  // ─── AC3: Campos opcionais ───────────────────────────────────────────────
  it('renders ⚠ for optional fields', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    expect(wrapper.text()).toContain('⚠')
  })

  it('does NOT render ⚠ for non-optional fields', async () => {
    const fields: FieldNavItem[] = [
      { name: 'cliente', path: 'data.cliente', type: 'string', status: 'unmapped', isOptional: false },
    ]
    const { wrapper } = mountNavigator(fields)
    await flushPromises()
    expect(wrapper.text()).not.toContain('⚠')
  })

  // ─── AC4: Seleção de campo ───────────────────────────────────────────────
  // Note: mapped group starts collapsed (Story 28.2 AC6); use unmapped fields for click tests

  it('clicking a field with nodeId updates inspectorStore and editorStore', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const mappingStore = useMappingStore()
    const inspectorStore = useInspectorStore()
    const editorStore = useEditorStore()
    const templateStore = useTemplateStore()

    // Use unmapped field with nodeId so it's visible (not in collapsed mapped group)
    const fields: FieldNavItem[] = [
      { name: 'cliente', path: 'data.cliente', type: 'string', status: 'unmapped', nodeId: 'node-1', isOptional: false },
    ]
    mappingStore.setFieldNavItems(fields)
    templateStore.loadTree(makeTree())

    const wrapper = mount(FieldNavigator, { global: { plugins: [pinia] } })
    await flushPromises()

    // Find the field-nav-item for 'cliente' and click it
    const items = wrapper.findAll('.field-nav-item')
    const clienteItem = items.find((el) => el.text().includes('cliente'))
    expect(clienteItem).toBeDefined()
    await clienteItem!.trigger('click')
    await flushPromises()

    expect(inspectorStore.selectedNode?.id).toBe('node-1')
    expect(editorStore.selectedElementId).toBe('node-1')
  })

  it('clicking a field with binding (no nodeId) resolves via binding search', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const mappingStore = useMappingStore()
    const inspectorStore = useInspectorStore()
    const editorStore = useEditorStore()
    const templateStore = useTemplateStore()

    // Use unmapped field with binding (no nodeId) so it's visible
    const fields: FieldNavItem[] = [
      { name: 'cpf', path: 'data.cpf', type: 'string', status: 'unmapped', binding: 'logo', isOptional: false },
    ]
    mappingStore.setFieldNavItems(fields)
    templateStore.loadTree(makeTree())

    const wrapper = mount(FieldNavigator, { global: { plugins: [pinia] } })
    await flushPromises()

    const items = wrapper.findAll('.field-nav-item')
    expect(items.length).toBeGreaterThan(0)
    await items[0]!.trigger('click')
    await flushPromises()

    // Should find 'logo' node via binding
    expect(inspectorStore.selectedNode?.id).toBe('img-1')
    expect(editorStore.selectedElementId).toBe('img-1')
  })

  it('clicking a field with path only (no nodeId, no binding) resolves via path search', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const mappingStore = useMappingStore()
    const inspectorStore = useInspectorStore()
    const editorStore = useEditorStore()
    const templateStore = useTemplateStore()

    // Use unmapped field with only path so it's visible
    const tree = makeTree()
    const node = tree.root.children[0]! // node-1
    node.binding = 'xsd.cliente'
    templateStore.loadTree(tree)

    const fields: FieldNavItem[] = [
      { name: 'cliente', path: 'xsd.cliente', type: 'string', status: 'unmapped', isOptional: false },
    ]
    mappingStore.setFieldNavItems(fields)

    const wrapper = mount(FieldNavigator, { global: { plugins: [pinia] } })
    await flushPromises()

    const items = wrapper.findAll('.field-nav-item')
    expect(items.length).toBeGreaterThan(0)
    await items[0]!.trigger('click')
    await flushPromises()

    expect(inspectorStore.selectedNode?.id).toBe('node-1')
    expect(editorStore.selectedElementId).toBe('node-1')
  })

  it('selected field receives --selected CSS class', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const mappingStore = useMappingStore()
    const templateStore = useTemplateStore()

    // Use unmapped field so it's visible by default
    const fields: FieldNavItem[] = [
      { name: 'cliente', path: 'data.cliente', type: 'string', status: 'unmapped', nodeId: 'node-1', isOptional: false },
    ]
    mappingStore.setFieldNavItems(fields)
    templateStore.loadTree(makeTree())

    const wrapper = mount(FieldNavigator, { global: { plugins: [pinia] } })
    await flushPromises()

    const items = wrapper.findAll('.field-nav-item')
    const clienteItem = items.find((el) => el.text().includes('cliente'))
    expect(clienteItem).toBeDefined()
    await clienteItem!.trigger('click')
    await flushPromises()

    expect(clienteItem!.classes()).toContain('field-nav-item--selected')
  })

  // ─── AC5: Resumo de contagem (Story 28.2: dual count format) ─────────────
  it('displays mapped count summary in PDF format', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    // Story 28.2: format is "X de Y PDF" (without XSD when none)
    expect(wrapper.text()).toContain('5 de 9 PDF')
  })

  it('shows 0 de 0 PDF when no fields', async () => {
    const { wrapper } = mountNavigator([])
    await flushPromises()
    expect(wrapper.text()).toContain('0 de 0 PDF')
  })

  // ─── AC3: STATUS ordering — unmapped first ──────────────────────────────
  it('unmapped group appears before mapeados group in DOM order', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()

    const groupHeaders = wrapper.findAll('.field-navigator__group-header')
    expect(groupHeaders.length).toBeGreaterThan(0)

    // First group header should be unmapped (🟥 "Sem binding")
    expect(groupHeaders[0]!.text()).toContain('Sem binding')
  })

  it('unmapped fields are visible and mapped group starts collapsed', async () => {
    // Use paths matching names so secondary text (path) is checkable
    const fields: FieldNavItem[] = [
      { name: 'z_mapped', path: 'z_mapped', type: 'string', status: 'mapped', isOptional: false },
      { name: 'a_unmapped', path: 'a_unmapped', type: 'string', status: 'unmapped', isOptional: false },
      { name: 'm_unconfirmed', path: 'm_unconfirmed', type: 'string', status: 'unconfirmed', isOptional: false },
    ]
    const { wrapper } = mountNavigator(fields)
    await flushPromises()

    const items = wrapper.findAll('.field-nav-item')
    // Only unmapped and unconfirmed fields visible (mapped starts collapsed)
    expect(items.length).toBe(2)
    const texts = items.map((i) => i.text())
    // FieldNavItem shows path as secondary text
    expect(texts.some((t) => t.includes('a_unmapped'))).toBe(true)
    expect(texts.some((t) => t.includes('m_unconfirmed'))).toBe(true)
    expect(texts.some((t) => t.includes('z_mapped'))).toBe(false)
  })

  it('items in unmapped group appear in order they are provided', async () => {
    // Use paths matching names so secondary text (path) is checkable
    const fields: FieldNavItem[] = [
      { name: 'z_field', path: 'z_field', type: 'string', status: 'unmapped', isOptional: false },
      { name: 'a_field', path: 'a_field', type: 'string', status: 'unmapped', isOptional: false },
      { name: 'm_field', path: 'm_field', type: 'string', status: 'unmapped', isOptional: false },
    ]
    const { wrapper } = mountNavigator(fields)
    await flushPromises()

    // FieldNavItem renders path as secondary text, so path is visible in item text
    const items = wrapper.findAll('.field-nav-item')
    expect(items[0]!.text()).toContain('z_field')
    expect(items[1]!.text()).toContain('a_field')
    expect(items[2]!.text()).toContain('m_field')
  })

  // ─── Sections collapsible ────────────────────────────────────────────────
  it('unmapped group is expanded by default and collapses on header click', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()

    // Initially unmapped fields visible (telefone is unmapped)
    expect(wrapper.text()).toContain('telefone')

    // Click unmapped group header to collapse it
    const groupHeaders = wrapper.findAll('.field-navigator__group-header')
    const unmappedHeader = groupHeaders.find((h) => h.text().includes('Sem binding'))
    expect(unmappedHeader).toBeDefined()
    await unmappedHeader!.trigger('click')
    await flushPromises()

    // After collapsing unmapped group, its items no longer visible
    const allGroups = wrapper.findAll('.field-navigator__group')
    const firstGroup = allGroups[0]
    const itemsInFirstGroup = firstGroup?.findAll('.field-nav-item') ?? []
    expect(itemsInFirstGroup.length).toBe(0)
  })

  // ─── Empty state ──────────────────────────────────────────────────────────
  it('shows empty state when no fields available', async () => {
    const { wrapper } = mountNavigator([])
    await flushPromises()
    expect(wrapper.text()).toContain('Nenhum campo disponível')
  })

  // ─── ProgressBar ─────────────────────────────────────────────────────────
  it('renders a ProgressBar element', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(true)
  })
})
