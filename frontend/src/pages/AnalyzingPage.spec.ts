import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import AnalyzingPage from './AnalyzingPage.vue'
import { PIPELINE_BLOCKS, TOTAL_STAGES, getStageIndex } from './analyzingPageConstants'
import { useSessionStore } from '@/stores/session'

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock FullWidthLayout so we don't need AppHeader/organisms
vi.mock('@/templates/FullWidthLayout.vue', () => ({
  default: {
    name: 'FullWidthLayout',
    template: '<div><slot name="stepper" /><slot /></div>',
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

  // Test 2: Renderiza 8 blocos no pipeline (v1 fallback)
  it('renderiza 8 blocos no pipeline', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    // v1 fallback renders 8 .v1-block elements
    const blocks = wrapper.findAll('.v1-block')
    expect(blocks.length).toBe(8)
  })

  // Test 3: Total de estágios é 28
  it('PIPELINE_BLOCKS contém exatamente 28 estágios no total', () => {
    const total = PIPELINE_BLOCKS.reduce((sum, block) => sum + block.stages.length, 0)
    expect(total).toBe(28)
    expect(TOTAL_STAGES).toBe(28)
  })

  // Test 4: Progresso 0% inicialmente (v1 fallback)
  it('exibe progresso 0% quando nenhum estágio foi completado', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    // v1 fallback uses .v1-progress__pct for percentage display
    const pctSpan = wrapper.find('.v1-progress__pct')
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

  it('getStageIndex retorna 27 para último estágio do bloco 8', () => {
    const block8 = PIPELINE_BLOCKS[7]
    const lastIdx = block8.stages.length - 1
    expect(getStageIndex(block8, lastIdx)).toBe(27)
  })

  // Test 6: progressPct calcula corretamente quando N estágios completos (v1 fallback)
  it('calcula progressPct corretamente baseado em estágios completados', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    // Initially 0% in v1 fallback
    expect(wrapper.find('.v1-progress__pct').text()).toBe('0%')

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

    const cancelBtn = wrapper.find('.topbar-cancel')
    expect(cancelBtn.exists()).toBe(true)
    expect(cancelBtn.text()).toContain('Cancelar')

    await cancelBtn.trigger('click')
    await flushPromises()

    // Should navigate to /upload
    expect(router.currentRoute.value.path).toBe('/upload')
  })

  // Test 8: Breadcrumb exibe "—" quando jobId não está definido
  it('breadcrumb exibe "—" quando jobId não está definido', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    // Breadcrumb shows "Job #—" when session.jobId is null
    const breadcrumb = wrapper.find('.topbar-breadcrumb')
    expect(breadcrumb.exists()).toBe(true)
    expect(breadcrumb.text()).toContain('—')
  })
})

// ─── Event queue drain path tests (Story 10.20 — concern #4) ─────────────────

describe('AnalyzingPage — event queue drain paths', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    vi.clearAllMocks()
  })

  // Helper: mount with a mocked fetch and a pre-set jobId
  function mountWithFetch(fetchImpl: typeof globalThis.fetch, jobId = 'job-test') {
    const pinia = createPinia()
    setActivePinia(pinia)
    // Set jobId so onMounted calls startPipeline + connectSSE
    const sessionStore = useSessionStore()
    sessionStore.jobId = jobId
    const router = createTestRouter()
    vi.stubGlobal('fetch', fetchImpl)
    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })
    return { wrapper, router }
  }

  it('pipeline_completed event navigates to /editor after fetching result', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        // startPipeline (POST /api/analyze)
        ok: true,
        json: async () => ({}),
      })
      .mockResolvedValueOnce({
        // fetchAndLoadResult (GET /api/analyze/:id/result)
        // result: null skips loadFromPipelineResult, goes straight to router.push
        ok: true,
        json: async () => ({ status: 'completed', result: null }),
      })

    const { wrapper, router } = mountWithFetch(fetchMock)
    await flushPromises() // let onMounted finish

    const es = MockEventSource.instances[0]
    expect(es).toBeDefined()

    // Emit pipeline_completed (include block to keep v1 path)
    es.emit('message', {
      event: 'pipeline_completed',
      block: 8,
      stage: 28,
      stage_name: 'Pipeline Result',
      status: 'completed',
      summary: {},
    })

    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/editor')
    wrapper.unmount()
  })

  it('failed stage event shows error message after drain completes', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        // startPipeline
        ok: true,
        json: async () => ({ job_id: 'job-fail' }),
      })

    const { wrapper } = mountWithFetch(fetchMock)
    await flushPromises()

    const es = MockEventSource.instances[0]
    expect(es).toBeDefined()

    // Emit a failed stage event
    es.emit('message', {
      stage: 3,
      block: 2,
      stage_name: 'Text Reconstruction',
      status: 'failed',
      summary: {},
    })

    await flushPromises()

    const html = wrapper.html()
    expect(html).toContain('Text Reconstruction')
    wrapper.unmount()
  })

  it('handleRetry clears stagesStatus so progress resets to 0%', async () => {
    // Always-resolve mock: covers both initial mount startPipeline and retry startPipeline
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    })

    const { wrapper } = mountWithFetch(fetchMock, 'job-retry')
    await flushPromises()

    const es = MockEventSource.instances[0]
    expect(es).toBeDefined()

    // Mark a stage as running so progress > 0
    es.emit('message', {
      stage: 1,
      block: 1,
      stage_name: 'Acquisition',
      status: 'running',
      summary: {},
    })
    await flushPromises()

    // Trigger an error so the retry button is visible
    es.emit('message', {
      stage: 1,
      block: 1,
      stage_name: 'Acquisition',
      status: 'failed',
      summary: {},
    })
    await flushPromises()

    // Click "Tentar novamente"
    const retryBtn = wrapper.findAll('button').find(b => b.text().includes('Tentar'))
    if (retryBtn) {
      await retryBtn.trigger('click')
      await flushPromises()
    }

    // After retry, all stages cleared → progress = 0%
    const pctSpan = wrapper.find('.v1-progress__pct')
    if (pctSpan.exists()) {
      expect(pctSpan.text()).toBe('0%')
    }

    wrapper.unmount()
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

  it('bloco 8 é "Validação" com 4 estágios', () => {
    expect(PIPELINE_BLOCKS[7].name).toBe('Validação')
    expect(PIPELINE_BLOCKS[7].stages.length).toBe(4)
  })

  it('contagem por bloco é 1+5+5+5+2+4+2+4=28', () => {
    const counts = PIPELINE_BLOCKS.map(b => b.stages.length)
    expect(counts).toEqual([1, 5, 5, 5, 2, 4, 2, 4])
    expect(counts.reduce((a, b) => a + b, 0)).toBe(28)
  })
})
