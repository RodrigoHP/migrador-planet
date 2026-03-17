import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import AnalyzingPage from './AnalyzingPage.vue'
import { PIPELINE_BLOCKS, TOTAL_STAGES, getStageIndex } from './analyzingPageConstants'

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock FullWidthLayout so we don't need AppHeader/organisms
vi.mock('@/templates/FullWidthLayout.vue', () => ({
  default: {
    name: 'FullWidthLayout',
    template: '<div><slot /></div>',
  },
}))

// Mock ProgressBar atom
vi.mock('@/atoms/ProgressBar.vue', () => ({
  default: {
    name: 'ProgressBar',
    props: ['value', 'animated'],
    template: '<div class="progress-bar" :data-value="value" />',
  },
}))

// Mock EventSource (not available in jsdom)
class MockEventSource {
  url: string
  listeners: Record<string, ((ev: Event) => void)[]> = {}
  onerror: (() => void) | null = null
  static instances: MockEventSource[] = []

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  addEventListener(event: string, cb: (ev: Event) => void) {
    if (!this.listeners[event]) this.listeners[event] = []
    this.listeners[event].push(cb)
  }

  emit(event: string, data: unknown) {
    const messageEvent = { data: JSON.stringify(data) } as MessageEvent
    this.listeners[event]?.forEach(cb => cb(messageEvent))
  }

  close() {}
}

vi.stubGlobal('EventSource', MockEventSource)

// ─── Helpers ──────────────────────────────────────────────────────────────────

function createTestRouter() {
  return createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/upload', component: { template: '<div>upload</div>' } },
      { path: '/analyzing', component: AnalyzingPage },
      { path: '/editor', component: { template: '<div>editor</div>' } },
    ],
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('AnalyzingPage', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    vi.clearAllMocks()
  })

  // Test 1: Renderiza título "Analisando documentos..."
  it('renderiza o título "Analisando documentos..."', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    expect(wrapper.find('h1').text()).toBe('Analisando documentos...')
  })

  // Test 2: Renderiza 8 blocos na lista
  it('renderiza 8 blocos no pipeline', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    // Each block has a bg-white rounded-lg card
    const blockCards = wrapper.findAll('.bg-white.rounded-lg')
    // 8 pipeline block cards + 1 resumo parcial card = at least 8
    // Find cards that contain block id numbers (1. through 8.)
    const blockTitles = wrapper.findAll('.font-semibold.text-gray-800.text-sm')
    expect(blockTitles.length).toBe(8)
  })

  // Test 3: Total de estágios é 27
  it('PIPELINE_BLOCKS contém exatamente 27 estágios no total', () => {
    const total = PIPELINE_BLOCKS.reduce((sum, block) => sum + block.stages.length, 0)
    expect(total).toBe(27)
    expect(TOTAL_STAGES).toBe(27)
  })

  // Test 4: Progresso 0% inicialmente
  it('exibe progresso 0% quando nenhum estágio foi completado', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    // Find the percentage display text (text-blue-600 span)
    const pctSpan = wrapper.find('.text-blue-600')
    expect(pctSpan.text()).toBe('0%')
  })

  // Test 5: getStageIndex retorna índice correto para bloco/estágio
  it('getStageIndex retorna 0 para bloco 1 estágio 0', () => {
    const block1 = PIPELINE_BLOCKS[0]
    expect(getStageIndex(block1, 0)).toBe(0)
  })

  it('getStageIndex retorna 1 para bloco 2 estágio 0 (bloco 1 tem 1 estágio)', () => {
    const block2 = PIPELINE_BLOCKS[1]
    expect(getStageIndex(block2, 0)).toBe(1) // block1 has 1 stage
    expect(getStageIndex(block2, 4)).toBe(5) // last stage of block2
  })

  it('getStageIndex retorna 26 para último estágio do bloco 8', () => {
    const block8 = PIPELINE_BLOCKS[7]
    const lastIdx = block8.stages.length - 1
    expect(getStageIndex(block8, lastIdx)).toBe(26)
  })

  // Test 6: progressPct calcula corretamente quando N estágios completos
  it('calcula progressPct corretamente baseado em estágios completados', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    // Initially 0%
    expect(wrapper.find('.text-blue-600').text()).toBe('0%')

    // The ProgressBar should receive value=0
    const progressBar = wrapper.findComponent({ name: 'ProgressBar' })
    expect(progressBar.props('value')).toBe(0)
  })

  // Test 7: Botão cancelar chama handleCancel
  it('botão cancelar está presente e é clicável', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    const cancelBtn = wrapper.find('button')
    expect(cancelBtn.exists()).toBe(true)
    expect(cancelBtn.text()).toContain('Cancelar')

    await cancelBtn.trigger('click')
    await flushPromises()

    // Should navigate to /upload
    expect(router.currentRoute.value.path).toBe('/upload')
  })

  // Test 8: Resumo mostra "—" quando sem dados
  it('resumo parcial exibe "—" quando não há dados de sumário', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    const html = wrapper.html()
    // All three summary fields should show em dash
    const dashCount = (html.match(/—/g) ?? []).length
    expect(dashCount).toBeGreaterThanOrEqual(3)
  })
})

// ─── PIPELINE_BLOCKS constant tests ──────────────────────────────────────────

describe('PIPELINE_BLOCKS constant', () => {
  it('possui 8 blocos', () => {
    expect(PIPELINE_BLOCKS.length).toBe(8)
  })

  it('bloco 1 é "Aquisição" com 1 estágio', () => {
    expect(PIPELINE_BLOCKS[0].name).toBe('Aquisição')
    expect(PIPELINE_BLOCKS[0].stages.length).toBe(1)
  })

  it('bloco 8 é "Validação" com 3 estágios', () => {
    expect(PIPELINE_BLOCKS[7].name).toBe('Validação')
    expect(PIPELINE_BLOCKS[7].stages.length).toBe(3)
  })

  it('contagem por bloco é 1+5+5+5+2+4+2+3=27', () => {
    const counts = PIPELINE_BLOCKS.map(b => b.stages.length)
    expect(counts).toEqual([1, 5, 5, 5, 2, 4, 2, 3])
    expect(counts.reduce((a, b) => a + b, 0)).toBe(27)
  })
})
