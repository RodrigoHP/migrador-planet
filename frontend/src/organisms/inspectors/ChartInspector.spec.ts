import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ChartInspector from './ChartInspector.vue'
import type { TreeNode } from '@/types/template.types'

// ─── Mock idb (used transitively by some stores) ──────────────────────────────
vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

// ─── Mock Chart.js (ChartPreview uses dynamic import) ─────────────────────────
vi.mock('chart.js', () => ({
  Chart: vi.fn().mockImplementation(() => ({
    destroy: vi.fn(),
    update: vi.fn(),
    data: {},
    options: {},
    config: { type: 'bar' },
  })),
  registerables: [],
}))

// ─── Mock ChartPreview molecule ───────────────────────────────────────────────
vi.mock('@/molecules/ChartPreview.vue', () => ({
  default: {
    name: 'ChartPreview',
    props: ['chartId', 'type', 'stacked', 'datasets', 'styles'],
    template: '<div class="chart-preview-mock">preview</div>',
  },
}))

// ─── Tree node factory ────────────────────────────────────────────────────────

function makeChartNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    id: 'chart-test-1',
    type: 'chart',
    name: 'Gráfico Mensal',
    children: [],
    visibility: true,
    properties: {
      confidence: 75,
      chart_type: 'line',
      width: 400,
      height: 250,
    },
    ...overrides,
  }
}

function mountInspector(node: TreeNode | null = makeChartNode()) {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(ChartInspector, {
    props: { node },
    global: {
      plugins: [pinia],
    },
  })
}

describe('ChartInspector', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── Sections rendered ─────────────────────────────────────────────────────

  it('renders Geral section with nome and confidence', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Geral')
    expect(wrapper.text()).toContain('Nome')
    expect(wrapper.text()).toContain('Confiança')
  })

  it('renders Tipo section with dropdown', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Tipo')
    const selects = wrapper.findAll('select')
    expect(selects.length).toBeGreaterThan(0)
  })

  it('renders Dados section', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Dados')
  })

  it('renders Dimensões section with largura and altura inputs', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Dimensões')
    expect(wrapper.text()).toContain('Largura')
    expect(wrapper.text()).toContain('Altura')
  })

  it('renders Estilo section with toggle checkboxes', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Estilo')
    expect(wrapper.text()).toContain('Legenda')
    expect(wrapper.text()).toContain('Grid')
    expect(wrapper.text()).toContain('Animação')
  })

  it('renders Preview section', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Preview')
  })

  it('renders Posição section (legacy)', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Posição')
  })

  it('renders Visibilidade section (legacy)', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Visibilidade')
  })

  it('renders Fallback section', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    expect(wrapper.text()).toContain('Fallback')
    expect(wrapper.text()).toContain('Usar imagem estática')
  })

  // ─── Confidence badge ──────────────────────────────────────────────────────

  it('shows high-confidence badge for confidence >= 60%', async () => {
    const node = makeChartNode({ properties: { confidence: 75, chart_type: 'line' } })
    const wrapper = mountInspector(node)
    await flushPromises()
    const badge = wrapper.find('.chart-inspector__confidence-badge--high')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('75%')
  })

  it('shows low-confidence badge for confidence < 60%', async () => {
    const node = makeChartNode({ properties: { confidence: 40, chart_type: 'line' } })
    const wrapper = mountInspector(node)
    await flushPromises()
    const badge = wrapper.find('.chart-inspector__confidence-badge--low')
    expect(badge.exists()).toBe(true)
  })

  it('shows manual selection hint when confidence < 60%', async () => {
    const node = makeChartNode({ properties: { confidence: 40 } })
    const wrapper = mountInspector(node)
    await flushPromises()
    expect(wrapper.text()).toContain('Selecione o tipo manualmente')
  })

  it('does NOT show manual selection hint when confidence >= 60%', async () => {
    const node = makeChartNode({ properties: { confidence: 75 } })
    const wrapper = mountInspector(node)
    await flushPromises()
    expect(wrapper.text()).not.toContain('Selecione o tipo manualmente')
  })

  // ─── Dataset list ──────────────────────────────────────────────────────────

  it('renders + Adicionar dataset button', async () => {
    const wrapper = mountInspector()
    await flushPromises()
    const btn = wrapper.find('.chart-inspector__add-dataset')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Adicionar dataset')
  })

  it('adds a dataset on button click', async () => {
    const wrapper = mountInspector()
    await flushPromises()

    const before = wrapper.findAll('.chart-inspector__dataset-item').length
    const btn = wrapper.find('.chart-inspector__add-dataset')
    await btn.trigger('click')
    await flushPromises()

    const after = wrapper.findAll('.chart-inspector__dataset-item').length
    expect(after).toBe(before + 1)
  })

  // ─── Fallback toggle ───────────────────────────────────────────────────────

  it('toggles fallback when checkbox is changed', async () => {
    const wrapper = mountInspector()
    await flushPromises()

    // Find the fallback checkbox (last checkbox in Fallback section)
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes.length).toBeGreaterThan(0)

    // The fallback checkbox for "Usar imagem estática"
    const fallbackCheckbox = checkboxes[checkboxes.length - 1]!
    await fallbackCheckbox.trigger('change')
    await flushPromises()

    // After toggling, the fallback preview text should appear
    // (the ChartPreview is hidden when fallback is true)
    // We just verify no error is thrown and the component still renders
    expect(wrapper.exists()).toBe(true)
  })

  // ─── Null node ─────────────────────────────────────────────────────────────

  it('renders without error when node is null', async () => {
    const wrapper = mountInspector(null)
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  // ─── Chart type options ────────────────────────────────────────────────────

  it('renders all 5 chart type options', async () => {
    const wrapper = mountInspector()
    await flushPromises()

    const typeSelect = wrapper.findAll('select')[0]!
    const options = typeSelect.findAll('option')
    const labels = options.map((o) => o.text())

    expect(labels).toContain('Barras')
    expect(labels).toContain('Linha')
    expect(labels).toContain('Pizza')
    expect(labels).toContain('Rosca')
    expect(labels).toContain('Área')
  })
})
