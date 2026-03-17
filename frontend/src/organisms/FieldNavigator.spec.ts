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

  // ─── AC1: Grupos por tipo ────────────────────────────────────────────────
  it('renders groups for present field types', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Campos')
    expect(text).toContain('Tabelas')
    expect(text).toContain('Gráficos')
    expect(text).toContain('Recursos')
    // Seções not present (no section fields)
    expect(text).not.toContain('Seções')
  })

  it('shows field count in group headers', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('(4)') // 4 string fields
    expect(text).toContain('(2)') // 2 array fields
  })

  // ─── AC2: Ícones e badges de status ─────────────────────────────────────
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

  it('renders type icons for each group', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('📋') // string
    expect(text).toContain('📊') // array
    expect(text).toContain('📈') // chart
    expect(text).toContain('🖼️') // image
  })

  // ─── AC3: Campos opcionais ───────────────────────────────────────────────
  it('renders ⚠ for optional fields', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    expect(wrapper.text()).toContain('⚠')
  })

  it('does NOT render ⚠ for non-optional fields', async () => {
    const fields: FieldNavItem[] = [
      { name: 'cliente', path: 'data.cliente', type: 'string', status: 'mapped', isOptional: false },
    ]
    const { wrapper } = mountNavigator(fields)
    await flushPromises()
    expect(wrapper.text()).not.toContain('⚠')
  })

  // ─── AC4: Seleção de campo ───────────────────────────────────────────────
  it('clicking a field with nodeId updates inspectorStore and editorStore', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const mappingStore = useMappingStore()
    const inspectorStore = useInspectorStore()
    const editorStore = useEditorStore()
    const templateStore = useTemplateStore()

    mappingStore.setFieldNavItems(makeFields())
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

    // Field with only binding, no nodeId
    const fields: FieldNavItem[] = [
      { name: 'cpf', path: 'data.cpf', type: 'string', status: 'mapped', binding: 'logo', isOptional: false },
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

  it('selected field receives --selected CSS class', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const mappingStore = useMappingStore()
    const templateStore = useTemplateStore()

    mappingStore.setFieldNavItems(makeFields())
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

  // ─── AC5: Resumo de contagem ─────────────────────────────────────────────
  it('displays mapped count summary', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    // 5 mapped out of 9 total
    expect(wrapper.text()).toContain('5 de 9 campos mapeados')
  })

  it('shows 0 de 0 when no fields', async () => {
    const { wrapper } = mountNavigator([])
    await flushPromises()
    expect(wrapper.text()).toContain('0 de 0 campos mapeados')
  })

  // ─── AC7: Ordenação ──────────────────────────────────────────────────────
  it('renders sort buttons for Nome, Status, Tipo', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('Nome')
    expect(text).toContain('Status')
    expect(text).toContain('Tipo')
  })

  it('sort by status puts unmapped fields first', async () => {
    const fields: FieldNavItem[] = [
      { name: 'z_mapped', path: 'z', type: 'string', status: 'mapped', isOptional: false },
      { name: 'a_unmapped', path: 'a', type: 'string', status: 'unmapped', isOptional: false },
      { name: 'm_unconfirmed', path: 'm', type: 'string', status: 'unconfirmed', isOptional: false },
    ]
    const { wrapper } = mountNavigator(fields)
    await flushPromises()

    // Click Status sort button
    const sortBtns = wrapper.findAll('.field-navigator__sort-btn')
    const statusBtn = sortBtns.find((b) => b.text() === 'Status')
    expect(statusBtn).toBeDefined()
    await statusBtn!.trigger('click')
    await flushPromises()

    const items = wrapper.findAll('.field-nav-item')
    expect(items[0]!.text()).toContain('a_unmapped')
    expect(items[1]!.text()).toContain('m_unconfirmed')
    expect(items[2]!.text()).toContain('z_mapped')
  })

  it('sort by name is alphabetical', async () => {
    const fields: FieldNavItem[] = [
      { name: 'z_field', path: 'z', type: 'string', status: 'mapped', isOptional: false },
      { name: 'a_field', path: 'a', type: 'string', status: 'mapped', isOptional: false },
      { name: 'm_field', path: 'm', type: 'string', status: 'mapped', isOptional: false },
    ]
    const { wrapper } = mountNavigator(fields)
    await flushPromises()

    const items = wrapper.findAll('.field-nav-item')
    expect(items[0]!.text()).toContain('a_field')
    expect(items[1]!.text()).toContain('m_field')
    expect(items[2]!.text()).toContain('z_field')
  })

  // ─── Sections collapsible ────────────────────────────────────────────────
  it('group is expanded by default and collapses on header click', async () => {
    const { wrapper } = mountNavigator()
    await flushPromises()

    // Initially fields are visible
    expect(wrapper.text()).toContain('cliente')

    // Click group header to collapse
    const groupHeaders = wrapper.findAll('.field-navigator__group-header')
    expect(groupHeaders.length).toBeGreaterThan(0)
    await groupHeaders[0]!.trigger('click')
    await flushPromises()

    // After collapsing, first group items no longer visible
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
