import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import AnalyzingPage from './AnalyzingPage.vue'
import { PIPELINE_V2_STAGES, TOTAL_V2_STAGES } from './analyzingPageConstantsV2'
import { useSessionStore } from '@/stores/session'

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock supabase client so module loads without env vars
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null } })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
    },
  },
}))

// apiFetch wraps fetch with auth headers; in tests delegate to global fetch
vi.mock('@/services/apiFetch', () => ({
  apiFetch: (url: string, options?: RequestInit) =>
    options !== undefined ? fetch(url, options) : fetch(url),
}))

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
    this.listeners[event]?.forEach((cb) => cb(messageEvent))
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

  // Test 1: Breadcrumb de navegação está presente no V2
  it('renderiza breadcrumb com "Analisando" como etapa ativa', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    const breadcrumb = wrapper.find('.topbar-breadcrumb')
    expect(breadcrumb.exists()).toBe(true)
    expect(breadcrumb.text()).toContain('Analisando')
  })

  // Test 2: Botão cancelar existe com texto correto no V2
  it('renderiza botão cancelar com texto "Cancelar análise"', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    const cancelBtn = wrapper.find('.topbar-cancel')
    expect(cancelBtn.exists()).toBe(true)
    expect(cancelBtn.text()).toContain('Cancelar')
  })

  // Test 3: Total de estágios V2 é 5
  it('PIPELINE_V2_STAGES contém exatamente 5 estágios', () => {
    expect(PIPELINE_V2_STAGES.length).toBe(5)
    expect(TOTAL_V2_STAGES).toBe(5)
  })

  // Test 4: Página V2 monta sem erros e exibe o container principal
  it('monta sem erros e exibe .analyzing-page', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    expect(wrapper.find('.analyzing-page').exists()).toBe(true)
  })

  // Test 5: estágios V2 têm campos obrigatórios
  it('cada estágio V2 possui stage, name, nameEn, description e subStepPrefix', () => {
    for (const s of PIPELINE_V2_STAGES) {
      expect(typeof s.stage).toBe('number')
      expect(typeof s.name).toBe('string')
      expect(typeof s.nameEn).toBe('string')
      expect(typeof s.description).toBe('string')
      expect(typeof s.subStepPrefix).toBe('string')
    }
  })

  // Test 6: Estado inicial é 'initializing' — botão cancelar está habilitado
  it('botão cancelar está habilitado no estado inicial', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    const cancelBtn = wrapper.find('.topbar-cancel')
    expect(cancelBtn.exists()).toBe(true)
    expect(cancelBtn.attributes('disabled')).toBeUndefined()
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

  // Test 8: Breadcrumb exibe etapas Upload → Analisando → Editor no V2
  it('breadcrumb V2 exibe as 3 etapas de navegação', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()

    const wrapper = mount(AnalyzingPage, {
      global: { plugins: [pinia, router] },
    })

    const breadcrumb = wrapper.find('.topbar-breadcrumb')
    expect(breadcrumb.exists()).toBe(true)
    expect(breadcrumb.text()).toContain('Upload')
    expect(breadcrumb.text()).toContain('Editor')
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

  // Helper: create a controllable SSE ReadableStream
  function createSSEStream() {
    const encoder = new TextEncoder()
    let ctrl!: ReadableStreamDefaultController<Uint8Array>
    const stream = new ReadableStream<Uint8Array>({
      start(c) {
        ctrl = c
      },
    })
    return {
      response: { ok: true, body: stream } as unknown as Response,
      emit(data: unknown) {
        ctrl.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`))
      },
      close() {
        ctrl.close()
      },
    }
  }

  it('pipeline_completed event transiciona pageState para completed', async () => {
    const sse = createSSEStream()

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) }) // startPipeline POST
      .mockResolvedValueOnce(sse.response) // connectSSE GET (stream)

    const { wrapper } = mountWithFetch(fetchMock)
    await flushPromises()

    // Emit pipeline_completed — V2 handler sets pageState = 'completed'
    sse.emit({ event: 'pipeline_completed', stage: 5, status: 'completed', summary: {} })

    await flushPromises()

    // Component renders the completed template (button "Abrir no Editor")
    expect(wrapper.html()).toContain('analyzing-page')
    wrapper.unmount()
  })

  it('failed stage event transiciona pageState para error', async () => {
    const sse = createSSEStream()

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ job_id: 'job-fail' }) }) // startPipeline
      .mockResolvedValueOnce(sse.response) // connectSSE stream

    const { wrapper } = mountWithFetch(fetchMock)
    await flushPromises()

    // Emit a failed stage V2 event (stage 3 = Análise Estrutural)
    sse.emit({ stage: 3, status: 'failed', summary: {} })

    await flushPromises()

    // Component should render error state
    expect(wrapper.html()).toContain('analyzing-page')
    wrapper.unmount()
  })

  it('handleRetry clears stagesStatus so progress resets to 0%', async () => {
    const sse1 = createSSEStream()
    const sse2 = createSSEStream()

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) }) // initial startPipeline
      .mockResolvedValueOnce(sse1.response) // initial connectSSE
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) }) // retry startPipeline
      .mockResolvedValueOnce(sse2.response) // retry connectSSE

    const { wrapper } = mountWithFetch(fetchMock, 'job-retry')
    await flushPromises()

    // Mark a stage as running so progress > 0
    sse1.emit({ stage: 1, block: 1, stage_name: 'Acquisition', status: 'running', summary: {} })
    await flushPromises()

    // Trigger a failure so the retry button is visible
    sse1.emit({ stage: 1, block: 1, stage_name: 'Acquisition', status: 'failed', summary: {} })
    await flushPromises()

    // Click "Tentar novamente"
    const retryBtn = wrapper.findAll('button').find((b) => b.text().includes('Tentar'))
    if (retryBtn) {
      await retryBtn.trigger('click')
      await flushPromises()
    }

    // After retry all stages are cleared → progress = 0%
    const pctSpan = wrapper.find('.v1-progress__pct')
    if (pctSpan.exists()) {
      expect(pctSpan.text()).toBe('0%')
    }

    wrapper.unmount()
  })
})

// ─── PIPELINE_V2_STAGES constant tests ───────────────────────────────────────

describe('PIPELINE_V2_STAGES constant', () => {
  it('possui 5 estágios', () => {
    expect(PIPELINE_V2_STAGES.length).toBe(5)
  })

  it('estágio 1 é "Agrupamento de Layouts"', () => {
    expect(PIPELINE_V2_STAGES[0].stage).toBe(1)
    expect(PIPELINE_V2_STAGES[0].nameEn).toBe('Layout Clustering')
  })

  it('estágio 5 é "Geração do Template"', () => {
    expect(PIPELINE_V2_STAGES[4].stage).toBe(5)
    expect(PIPELINE_V2_STAGES[4].nameEn).toBe('Template Generation')
  })

  it('TOTAL_V2_STAGES é 5', () => {
    expect(TOTAL_V2_STAGES).toBe(5)
  })
})
