/**
 * Story 29.5 — ConsolePanel.vue tests
 * Covers: AC2 (unmapped fields), AC3 (reactive), AC4 (badge count), AC5 (click to select), AC6 (empty state)
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConsolePanel from '../ConsolePanel.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useEditorStore } from '@/stores/editorStore'
import type { DocumentTree, TreeNode } from '@/types/template.types'

// ─── Fixture factory ──────────────────────────────────────────────────────────
function makeNode(id: string, type: string, name: string, binding = ''): TreeNode {
  return {
    id,
    type: type as TreeNode['type'],
    name,
    binding,
    isOptional: false,
    children: [],
    properties: {},
    visibility: true,
  }
}

function makeTree(nodes: TreeNode[]): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'document',
      name: 'Document',
      binding: '',
      isOptional: false,
      children: [
        {
          id: 'flow',
          type: 'flow',
          name: 'Flow',
          binding: '',
          isOptional: false,
          children: nodes,
          properties: {},
          visibility: true,
        },
      ],
      properties: {},
      visibility: true,
    },
  }
}

describe('ConsolePanel.vue — Story 29.5', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('AC6: exibe mensagem de estado vazio quando não há warnings', () => {
    const store = useTemplateStore()
    // Load tree with only non-bindable nodes
    store.loadTree(makeTree([makeNode('section-1', 'section', 'Seção', '')]))

    const wrapper = mount(ConsolePanel)

    expect(wrapper.find('[data-testid="console-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="console-list"]').exists()).toBe(false)
  })

  it('AC2: exibe warning para cada nó bindável sem binding', () => {
    const store = useTemplateStore()
    store.loadTree(
      makeTree([
        makeNode('field-1', 'field', 'Cedente', ''),
        makeNode('field-2', 'value', 'Valor Total', ''),
        makeNode('section-1', 'section', 'Seção', ''), // não bindável
      ]),
    )

    const wrapper = mount(ConsolePanel)

    expect(wrapper.find('[data-testid="console-list"]').exists()).toBe(true)
    const items = wrapper.findAll('[data-testid^="console-warning-"]')
    expect(items).toHaveLength(2)
    expect(wrapper.text()).toContain('Cedente')
    expect(wrapper.text()).toContain('Valor Total')
    // section não deve aparecer
    expect(wrapper.text()).not.toContain('Seção')
  })

  it('AC2: campo com binding não aparece como warning', () => {
    const store = useTemplateStore()
    store.loadTree(
      makeTree([
        makeNode('field-1', 'field', 'Cedente', ''), // sem binding → warning
        makeNode('field-2', 'field', 'CNPJ', '/CNPJ'), // com binding → sem warning
      ]),
    )

    const wrapper = mount(ConsolePanel)

    const items = wrapper.findAll('[data-testid^="console-warning-"]')
    expect(items).toHaveLength(1)
    expect(wrapper.text()).toContain('Cedente')
    expect(wrapper.text()).not.toContain('CNPJ')
  })

  it('AC3: warnings somem reativamente quando campo é mapeado', async () => {
    const store = useTemplateStore()
    store.loadTree(makeTree([makeNode('field-1', 'field', 'Cedente', '')]))

    const wrapper = mount(ConsolePanel)
    expect(wrapper.findAll('[data-testid^="console-warning-"]')).toHaveLength(1)

    // Simular mapeamento do campo diretamente no flatNodes
    const node = store.flatNodes.get('field-1')
    if (node) node.binding = '/Cedente'
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="console-empty"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid^="console-warning-"]')).toHaveLength(0)
  })

  it('AC4: warnings computed expõe contagem correta via defineExpose', () => {
    const store = useTemplateStore()
    store.loadTree(
      makeTree([
        makeNode('field-1', 'field', 'A', ''),
        makeNode('field-2', 'value', 'B', ''),
        makeNode('field-3', 'likely_dynamic', 'C', ''),
      ]),
    )

    const wrapper = mount(ConsolePanel)
    // defineExpose makes warnings accessible as a plain value in test context
    const exposed = wrapper.vm as unknown as { warnings: unknown[] }
    expect(Array.isArray(exposed.warnings)).toBe(true)
    expect((exposed.warnings as unknown[]).length).toBe(3)
  })

  it('AC5: clicar no warning chama editorStore.selectElement com nodeId correto', async () => {
    const store = useTemplateStore()
    const editorStore = useEditorStore()
    store.loadTree(makeTree([makeNode('field-1', 'field', 'Cedente', '')]))

    const wrapper = mount(ConsolePanel)
    await wrapper.find('[data-testid="console-warning-field-1"]').trigger('click')

    expect(editorStore.selectedElementId).toBe('field-1')
  })

  it('AC2: likely_dynamic sem binding aparece como warning', () => {
    const store = useTemplateStore()
    store.loadTree(makeTree([makeNode('dyn-1', 'likely_dynamic', 'R$ 1.500,00', '')]))

    const wrapper = mount(ConsolePanel)

    expect(wrapper.findAll('[data-testid^="console-warning-"]')).toHaveLength(1)
    expect(wrapper.text()).toContain('R$ 1.500,00')
  })

  // ── Story 34.8: Coverage warning integration ─────────────────────────────

  it('34.8: shows coverage warning when percentage is below 80', async () => {
    const store = useTemplateStore()
    store.loadTree(makeTree([makeNode('section-1', 'section', 'Seção', '')]))

    // Load low coverage into coverageStore
    const { useCoverageStore } = await import('@/stores/coverageStore')
    const coverageStore = useCoverageStore()
    const { useLayoutStore } = await import('@/stores/layout')
    const layoutStore = useLayoutStore()
    // Set active layout
    ;(layoutStore as unknown as Record<string, unknown>).activeLayoutId = 'layout-a'
    coverageStore.loadCoverage({
      'layout-a': {
        fields: { mapped: 3, total: 10 },
        tables: { mapped: 0, total: 1 },
        images: { mapped: 0, total: 1 },
        charts: { mapped: 0, total: 0 },
        percentage: 30,
      },
    })

    const wrapper = mount(ConsolePanel)
    await wrapper.vm.$nextTick()

    const warnings = wrapper.findAll('[data-testid^="console-warning-"]')
    const hasCoverageWarning = warnings.some((w) => w.text().includes('Cobertura abaixo de 80%'))
    expect(hasCoverageWarning).toBe(true)
  })

  it('34.8: no coverage warning when percentage is 80+', async () => {
    const store = useTemplateStore()
    store.loadTree(makeTree([makeNode('section-1', 'section', 'Seção', '')]))

    const { useCoverageStore } = await import('@/stores/coverageStore')
    const coverageStore = useCoverageStore()
    const { useLayoutStore } = await import('@/stores/layout')
    const layoutStore = useLayoutStore()
    ;(layoutStore as unknown as Record<string, unknown>).activeLayoutId = 'layout-a'
    coverageStore.loadCoverage({
      'layout-a': {
        fields: { mapped: 9, total: 10 },
        tables: { mapped: 1, total: 1 },
        images: { mapped: 1, total: 1 },
        charts: { mapped: 0, total: 0 },
        percentage: 95,
      },
    })

    const wrapper = mount(ConsolePanel)
    await wrapper.vm.$nextTick()

    const warnings = wrapper.findAll('[data-testid^="console-warning-"]')
    const hasCoverageWarning = warnings.some((w) => w.text().includes('Cobertura abaixo de 80%'))
    expect(hasCoverageWarning).toBe(false)
  })
})
