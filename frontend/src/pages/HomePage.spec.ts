import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import HomePage from './HomePage.vue'

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock FullWidthLayout — emits 'open-bibliotecas' when show-bibliotecas prop is present
vi.mock('@/templates/FullWidthLayout.vue', () => ({
  default: {
    name: 'FullWidthLayout',
    props: ['showBibliotecas'],
    emits: ['open-bibliotecas'],
    template: `
      <div>
        <button
          v-if="showBibliotecas"
          class="bibliotecas-trigger"
          @click="$emit('open-bibliotecas')"
        >Bibliotecas</button>
        <slot />
      </div>
    `,
  },
}))

// Mock BibliotecasModal — renders sentinel element when open
vi.mock('@/organisms', () => ({
  BibliotecasModal: {
    name: 'BibliotecasModal',
    props: ['open'],
    emits: ['close'],
    template: `
      <div v-if="open" class="bibliotecas-modal-open">
        <button class="modal-close" @click="$emit('close')">Fechar</button>
      </div>
    `,
  },
}))

// Mock Button atom — renders a native button with the slot content
vi.mock('@/atoms', () => ({
  Button: {
    name: 'Button',
    props: ['variant', 'loading'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot /></button>',
  },
}))

// ─── Helpers ──────────────────────────────────────────────────────────────────

function createTestRouter() {
  return createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: '/', component: HomePage },
      { path: '/upload', component: { template: '<div>upload</div>' } },
      { path: '/editor', component: { template: '<div>editor</div>' } },
    ],
  })
}

function mountHomePage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createTestRouter()
  const wrapper = mount(HomePage, {
    global: { plugins: [pinia, router] },
  })
  return { wrapper, router, pinia }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Rendering ──────────────────────────────────────────────────────────────

  it('renderiza os dois cards (Novo Template e Abrir Projeto)', () => {
    const { wrapper } = mountHomePage()

    const html = wrapper.html()
    expect(html).toContain('Novo Template')
    expect(html).toContain('Abrir Projeto')
  })

  it('renderiza botão "Começar →" e botão "Carregar arquivo"', () => {
    const { wrapper } = mountHomePage()

    const buttons = wrapper.findAll('button')
    const texts = buttons.map((b) => b.text())
    expect(texts).toContain('Começar →')
    expect(texts.some((t) => t.includes('Carregar arquivo'))).toBe(true)
  })

  it('renderiza input file hidden com accept=".json"', () => {
    const { wrapper } = mountHomePage()

    const input = wrapper.find('input[type="file"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('accept')).toBe('.json')
  })

  // ── startNew() ─────────────────────────────────────────────────────────────

  it('startNew(): reseta stores e navega para /upload ao clicar "Começar →"', async () => {
    const { wrapper, router, pinia } = mountHomePage()

    // Grab store instances created inside the component
    const { useSessionStore } = await import('@/stores/session')
    const { useMappingStore } = await import('@/stores/mapping')
    const { useLayoutStore } = await import('@/stores/layout')
    const { useGenerationStore } = await import('@/stores/generation')

    const session = useSessionStore(pinia)
    const mapping = useMappingStore(pinia)
    const layout = useLayoutStore(pinia)
    const generation = useGenerationStore(pinia)

    const sessionReset = vi.spyOn(session, '$reset').mockImplementation(() => {})
    const mappingReset = vi.spyOn(mapping, '$reset').mockImplementation(() => {})
    const layoutReset = vi.spyOn(layout, '$reset').mockImplementation(() => {})
    const generationReset = vi.spyOn(generation, '$reset').mockImplementation(() => {})

    const buttons = wrapper.findAll('button')
    const startBtn = buttons.find((b) => b.text() === 'Começar →')
    expect(startBtn).toBeDefined()

    await startBtn!.trigger('click')
    await flushPromises()

    expect(sessionReset).toHaveBeenCalledOnce()
    expect(mappingReset).toHaveBeenCalledOnce()
    expect(layoutReset).toHaveBeenCalledOnce()
    expect(generationReset).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.path).toBe('/upload')
  })

  // ── onFileSelected() ───────────────────────────────────────────────────────

  it('onFileSelected(): carrega JSON válido e navega para /editor', async () => {
    const { wrapper, router, pinia } = mountHomePage()

    const { useSessionStore } = await import('@/stores/session')
    const { useMappingStore } = await import('@/stores/mapping')
    const { useLayoutStore } = await import('@/stores/layout')
    const { useGenerationStore } = await import('@/stores/generation')

    const session = useSessionStore(pinia)
    vi.spyOn(session, '$reset').mockImplementation(() => {})
    vi.spyOn(useMappingStore(pinia), '$reset').mockImplementation(() => {})
    vi.spyOn(useLayoutStore(pinia), '$reset').mockImplementation(() => {})
    vi.spyOn(useGenerationStore(pinia), '$reset').mockImplementation(() => {})

    // Build a minimal valid project JSON
    const projectData = { foo: 'bar' }
    const file = new File([JSON.stringify(projectData)], 'project.json', {
      type: 'application/json',
    })

    const input = wrapper.find('input[type="file"]')
    // Simulate file selection by setting files property via Object.defineProperty
    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })

    await input.trigger('change')
    await flushPromises()

    expect(session.analysisCompleted).toBe(true)
    expect(router.currentRoute.value.path).toBe('/editor')
  })

  it('onFileSelected(): JSON inválido (string pura) define erro no session store', async () => {
    const { wrapper, pinia } = mountHomePage()

    const { useSessionStore } = await import('@/stores/session')
    const session = useSessionStore(pinia)

    // JSON.parse of a bare string returns a string — typeof !== 'object'
    // Actually JSON.parse('"text"') returns a string, which fails the object check
    const file = new File(['"not-an-object"'], 'bad.json', {
      type: 'application/json',
    })

    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })

    await input.trigger('change')
    await flushPromises()

    expect(session.error).toBe('Arquivo de projeto inválido ou corrompido.')
  })

  it('onFileSelected(): JSON corrompido (parse error) define erro no session store', async () => {
    const { wrapper, pinia } = mountHomePage()

    const { useSessionStore } = await import('@/stores/session')
    const session = useSessionStore(pinia)

    const file = new File(['{ broken json :::'], 'corrupt.json', {
      type: 'application/json',
    })

    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })

    await input.trigger('change')
    await flushPromises()

    expect(session.error).toBe('Arquivo de projeto inválido ou corrompido.')
  })

  it('onFileSelected(): quando nenhum arquivo selecionado, não faz nada', async () => {
    const { wrapper, pinia } = mountHomePage()

    const { useSessionStore } = await import('@/stores/session')
    const session = useSessionStore(pinia)

    const input = wrapper.find('input[type="file"]')
    // files is undefined / empty
    Object.defineProperty(input.element, 'files', {
      value: [],
      writable: false,
    })

    await input.trigger('change')
    await flushPromises()

    expect(session.error).toBeNull()
    expect(session.analysisCompleted).toBe(false)
  })

  // ── BibliotecasModal wiring ─────────────────────────────────────────────────

  it('BibliotecasModal: está fechado por padrão', () => {
    const { wrapper } = mountHomePage()

    expect(wrapper.find('.bibliotecas-modal-open').exists()).toBe(false)
  })

  it('BibliotecasModal: abre quando FullWidthLayout emite open-bibliotecas', async () => {
    const { wrapper } = mountHomePage()

    // Trigger the emit from the mocked FullWidthLayout
    const trigger = wrapper.find('.bibliotecas-trigger')
    expect(trigger.exists()).toBe(true)

    await trigger.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.bibliotecas-modal-open').exists()).toBe(true)
  })

  it('BibliotecasModal: fecha quando modal emite close', async () => {
    const { wrapper } = mountHomePage()

    // Open the modal first
    const trigger = wrapper.find('.bibliotecas-trigger')
    await trigger.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.bibliotecas-modal-open').exists()).toBe(true)

    // Close via modal's close button
    const closeBtn = wrapper.find('.modal-close')
    await closeBtn.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.bibliotecas-modal-open').exists()).toBe(false)
  })
})
