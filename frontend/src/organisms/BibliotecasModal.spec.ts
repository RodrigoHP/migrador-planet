import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// ─── Mock useBibliotecas composable ──────────────────────────────────────────

import type { BibliotecaFile, BibliotecaTab } from '@/composables/useBibliotecas'
import { ref } from 'vue'

const mockFiles = ref<BibliotecaFile[]>([
  {
    id: 'system::knockout-3.4.2.js',
    name: 'knockout-3.4.2.js',
    size: 0,
    category: 'js',
    data: new ArrayBuffer(0),
    system: true,
  },
  {
    id: 'system::Chart.min.js',
    name: 'Chart.min.js',
    size: 0,
    category: 'js',
    data: new ArrayBuffer(0),
    system: true,
  },
  {
    id: 'fonts::arial.ttf',
    name: 'arial.ttf',
    size: 10240,
    category: 'fonts',
    data: new ArrayBuffer(0),
  },
  {
    id: 'css::style.css',
    name: 'style.css',
    size: 2048,
    category: 'css',
    data: new ArrayBuffer(0),
  },
])

const mockLoadFiles = vi.fn().mockResolvedValue(undefined)
const mockAddFile = vi.fn().mockResolvedValue({ success: true })
const mockRemoveFile = vi.fn().mockResolvedValue({ success: true })
const mockIsFileReferenced = vi.fn().mockReturnValue(false)

function mockGetByCategory(cat: BibliotecaTab) {
  return mockFiles.value.filter((f) => f.category === cat)
}

const mockLoadComponents = vi.fn().mockResolvedValue(undefined)
const mockSaveComponent = vi.fn().mockResolvedValue({ success: true })
const mockRemoveComponent = vi.fn().mockResolvedValue({ success: true })
const mockGetComponentData = vi.fn().mockReturnValue({
  type: 'container',
  name: 'Mock',
  children: [],
  properties: {},
  visibility: true,
})
const mockComponents = ref<any[]>([])

const mockGeneratePreviewHtml = vi.fn().mockReturnValue('<div>safe-preview</div>')

vi.mock('@/composables/useBibliotecas', () => ({
  ALLOWED_EXTENSIONS: {
    fonts: ['.ttf', '.woff', '.woff2', '.otf'],
    css: ['.css'],
    js: ['.js'],
  },
  SYSTEM_LIBS: [
    'knockout-3.4.2.js',
    'knockout.mapping.js',
    'Chart.min.js',
    'chartjs-plugin-datalabels.min.js',
  ],
  formatFileSize: (n: number) => `${n} B`,
  getExtension: (name: string) => name.slice(name.lastIndexOf('.')).toLowerCase(),
  generatePreviewHtml: (...args: any[]) => mockGeneratePreviewHtml(...args),
  useBibliotecas: () => ({
    files: mockFiles,
    isLoading: ref(false),
    error: ref(null),
    loadFiles: mockLoadFiles,
    addFile: mockAddFile,
    removeFile: mockRemoveFile,
    getByCategory: mockGetByCategory,
    isFileReferenced: mockIsFileReferenced,
    formatFileSize: (n: number) => `${n} B`,
    components: mockComponents,
    loadComponents: mockLoadComponents,
    saveComponent: mockSaveComponent,
    removeComponent: mockRemoveComponent,
    getComponentData: mockGetComponentData,
  }),
}))

// ─── Mock stores ───────────────────────────────────────────────────────────

vi.mock('@/stores/templateStore', () => ({
  useTemplateStore: () => ({
    getRootNode: {
      id: 'root',
      type: 'document',
      name: 'Root',
      children: [],
      properties: {},
      visibility: true,
    },
    addNodeFromSync: vi.fn().mockReturnValue(true),
  }),
  deepCloneNode: vi.fn((node: any) => ({ ...node, id: 'cloned-id', children: [] })),
}))

vi.mock('@/stores/inspectorStore', () => ({
  useInspectorStore: () => ({
    selectedNode: null,
  }),
}))

vi.mock('jszip', () => ({
  default: class MockJSZip {
    files: Record<string, any> = {}
    file(name: string, content: string) {
      this.files[name] = { dir: false, async: () => content }
      return this
    }
    async generateAsync() {
      return new Blob(['mock'])
    }
    static async loadAsync() {
      return new MockJSZip()
    }
  },
}))

// ─── Mock BibliotecaFileList molecule ────────────────────────────────────────

vi.mock('@/molecules/BibliotecaComponentList.vue', () => ({
  default: {
    name: 'BibliotecaComponentList',
    props: ['items'],
    emits: ['insert', 'remove'],
    template: '<div class="mock-component-list">{{ items.length }} components</div>',
  },
}))

vi.mock('@/molecules/BibliotecaFileList.vue', () => ({
  default: {
    name: 'BibliotecaFileList',
    props: ['items'],
    emits: ['remove'],
    template: `
      <ul>
        <li v-for="item in items" :key="item.id" class="mock-file-item" :data-id="item.id">
          {{ item.name }}
          <button
            v-if="!item.system"
            class="mock-remove-btn"
            @click="$emit('remove', item.id, item.name)"
          >🗑️</button>
        </li>
      </ul>
    `,
  },
}))

// ─── Import component (after mocks) ──────────────────────────────────────────

import BibliotecasModal from './BibliotecasModal.vue'

// ─── Mount helper ─────────────────────────────────────────────────────────────

function mountModal(open = true, activeTemplateContent?: string) {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(BibliotecasModal, {
    props: { open, activeTemplateContent },
    global: { plugins: [pinia] },
    attachTo: document.body,
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('BibliotecasModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsFileReferenced.mockReturnValue(false)
    mockRemoveFile.mockResolvedValue({ success: true })
    mockAddFile.mockResolvedValue({ success: true })
  })

  // ── Visibility ─────────────────────────────────────────────────────────────

  it('não renderiza quando open=false', () => {
    const wrapper = mountModal(false)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('renderiza quando open=true', () => {
    const wrapper = mountModal(true)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
  })

  it('chama loadFiles quando abre', async () => {
    mountModal(true)
    await flushPromises()
    expect(mockLoadFiles).toHaveBeenCalledOnce()
  })

  // ── Tabs ───────────────────────────────────────────────────────────────────

  it('renderiza as 4 abas: Fontes, CSS, JS, Componentes', () => {
    const wrapper = mountModal()
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.length).toBe(4)
    const texts = tabs.map((t) => t.text())
    expect(texts.some((t) => t.includes('Fontes'))).toBe(true)
    expect(texts.some((t) => t.includes('CSS'))).toBe(true)
    expect(texts.some((t) => t.includes('JS'))).toBe(true)
    expect(texts.some((t) => t.includes('Componentes'))).toBe(true)
  })

  it('aba Fontes ativa por padrão (aria-selected=true)', () => {
    const wrapper = mountModal()
    const tabs = wrapper.findAll('[role="tab"]')
    const activeTab = tabs.find((t) => t.attributes('aria-selected') === 'true')
    expect(activeTab?.text()).toContain('Fontes')
  })

  it('muda aba ao clicar em CSS', async () => {
    const wrapper = mountModal()
    const tabs = wrapper.findAll('[role="tab"]')
    const cssTab = tabs.find((t) => t.text().includes('CSS'))
    await cssTab!.trigger('click')
    const newActive = wrapper
      .findAll('[role="tab"]')
      .find((t) => t.attributes('aria-selected') === 'true')
    expect(newActive?.text()).toContain('CSS')
  })

  it('muda aba ao clicar em JS', async () => {
    const wrapper = mountModal()
    const tabs = wrapper.findAll('[role="tab"]')
    const jsTab = tabs.find((t) => t.text().includes('JS'))
    await jsTab!.trigger('click')
    const newActive = wrapper
      .findAll('[role="tab"]')
      .find((t) => t.attributes('aria-selected') === 'true')
    expect(newActive?.text()).toContain('JS')
  })

  // ── File list ──────────────────────────────────────────────────────────────

  it('aba JS exibe libs de sistema', async () => {
    const wrapper = mountModal()
    const tabs = wrapper.findAll('[role="tab"]')
    const jsTab = tabs.find((t) => t.text().includes('JS'))
    await jsTab!.trigger('click')

    const html = wrapper.html()
    expect(html).toContain('knockout-3.4.2.js')
    expect(html).toContain('Chart.min.js')
  })

  it('aba Fontes exibe arquivo de fonte de usuário', () => {
    const wrapper = mountModal()
    const html = wrapper.html()
    expect(html).toContain('arial.ttf')
  })

  // ── Remove ─────────────────────────────────────────────────────────────────

  it('remove arquivo sem referência diretamente (sem dialog)', async () => {
    mockIsFileReferenced.mockReturnValue(false)
    const wrapper = mountModal()
    await flushPromises()

    // Click remove on arial.ttf
    const removeBtn = wrapper.find('.mock-remove-btn')
    await removeBtn.trigger('click')
    await flushPromises()

    expect(mockRemoveFile).toHaveBeenCalledOnce()
    // Confirm dialog should NOT be shown
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(false)
  })

  it('exibe dialog de confirmação ao remover arquivo referenciado', async () => {
    mockIsFileReferenced.mockReturnValue(true)
    const wrapper = mountModal(true, 'some content mentioning arial.ttf')
    await flushPromises()

    const removeBtn = wrapper.find('.mock-remove-btn')
    await removeBtn.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(true)
    expect(wrapper.html()).toContain('arial.ttf')
  })

  it('cancela remoção ao clicar em Cancelar no dialog', async () => {
    mockIsFileReferenced.mockReturnValue(true)
    const wrapper = mountModal(true, 'arial.ttf')
    await flushPromises()

    const removeBtn = wrapper.find('.mock-remove-btn')
    await removeBtn.trigger('click')
    await wrapper.vm.$nextTick()

    const cancelBtn = wrapper.find('.bm__btn-confirm-cancel')
    await cancelBtn.trigger('click')
    await wrapper.vm.$nextTick()

    expect(mockRemoveFile).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(false)
  })

  it('confirma remoção ao clicar em Remover no dialog', async () => {
    mockIsFileReferenced.mockReturnValue(true)
    const wrapper = mountModal(true, 'arial.ttf')
    await flushPromises()

    const removeBtn = wrapper.find('.mock-remove-btn')
    await removeBtn.trigger('click')
    await wrapper.vm.$nextTick()

    const confirmBtn = wrapper.find('.bm__btn-confirm-ok')
    await confirmBtn.trigger('click')
    await flushPromises()

    expect(mockRemoveFile).toHaveBeenCalledOnce()
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(false)
  })

  // ── Upload error ───────────────────────────────────────────────────────────

  it('exibe mensagem de erro quando addFile falha', async () => {
    mockAddFile.mockResolvedValue({
      success: false,
      message: 'Arquivo excede o tamanho máximo permitido (5.00 MB)',
    })
    const wrapper = mountModal()
    await flushPromises()

    // Simulate file selection by calling handleFileSelected indirectly
    // We expose it via the component's internal behavior by triggering the input change
    const inputs = wrapper.findAll('input[type="file"]')
    const input = inputs.find((i) => i.attributes('accept') !== '.zip')!
    const file = new File([new ArrayBuffer(10)], 'big.ttf', { type: 'font/ttf' })
    Object.defineProperty(input.element, 'files', { value: [file], writable: false })
    await input.trigger('change')
    await flushPromises()

    expect(wrapper.html()).toContain('Arquivo excede o tamanho máximo')
  })

  // ── Close ──────────────────────────────────────────────────────────────────

  it('emite close ao clicar no botão Fechar no footer', async () => {
    const wrapper = mountModal()
    const closeBtn = wrapper.find('.bm__btn-cancel')
    await closeBtn.trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emite close ao clicar no botão ✕ do header', async () => {
    const wrapper = mountModal()
    const closeBtn = wrapper.find('.bm__btn-close')
    await closeBtn.trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emite close ao clicar no overlay', async () => {
    const wrapper = mountModal()
    const overlay = wrapper.find('.bm__overlay')
    await overlay.trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  // ── accept attribute ───────────────────────────────────────────────────────

  it('input de upload tem accept=.ttf,.woff,.woff2,.otf na aba Fontes', () => {
    const wrapper = mountModal()
    const inputs = wrapper.findAll('input[type="file"]')
    const fileInput = inputs.find((i) => i.attributes('accept') !== '.zip')
    const accept = fileInput?.attributes('accept') ?? ''
    expect(accept).toContain('.ttf')
    expect(accept).toContain('.woff')
    expect(accept).toContain('.otf')
  })

  it('input de upload muda accept para .css ao selecionar aba CSS', async () => {
    const wrapper = mountModal()
    const tabs = wrapper.findAll('[role="tab"]')
    const cssTab = tabs.find((t) => t.text().includes('CSS'))
    await cssTab!.trigger('click')
    await wrapper.vm.$nextTick()

    const inputs = wrapper.findAll('input[type="file"]')
    const fileInput = inputs.find((i) => i.attributes('accept') !== '.zip')
    expect(fileInput?.attributes('accept')).toContain('.css')
  })

  it('input de upload muda accept para .js ao selecionar aba JS', async () => {
    const wrapper = mountModal()
    const tabs = wrapper.findAll('[role="tab"]')
    const jsTab = tabs.find((t) => t.text().includes('JS'))
    await jsTab!.trigger('click')
    await wrapper.vm.$nextTick()

    const inputs = wrapper.findAll('input[type="file"]')
    const fileInput = inputs.find((i) => i.attributes('accept') !== '.zip')
    expect(fileInput?.attributes('accept')).toContain('.js')
  })
})

// ─── TD-38.1: ZIP import sanitizes previewHtml ──────────────────────────────

describe('BibliotecasModal — TD-38.1 ZIP import previewHtml sanitization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGeneratePreviewHtml.mockClear()
    mockGeneratePreviewHtml.mockReturnValue('<div>safe-preview</div>')
  })

  it('regenera previewHtml via generatePreviewHtml ao importar ZIP', async () => {
    const maliciousComponent = {
      name: 'MalComp',
      data: JSON.stringify({
        type: 'container',
        name: 'Root',
        children: [],
        properties: {},
        visibility: true,
      }),
      previewHtml: '<img src=x onerror="alert(1)">',
      nodeCount: 1,
      createdAt: Date.now(),
    }

    // Override loadAsync for this test
    const JSZipMock = (await import('jszip')).default
    vi.spyOn(JSZipMock, 'loadAsync').mockResolvedValueOnce({
      files: {
        'MalComp.json': {
          dir: false,
          async: () => JSON.stringify(maliciousComponent),
        },
      },
    } as any)

    // Mock idb to capture what gets persisted
    const putSpy = vi.fn()
    vi.doMock('idb', () => ({
      openDB: () => Promise.resolve({ put: putSpy }),
    }))

    const wrapper = mountModal()
    await flushPromises()

    // Navigate to components tab
    const tabs = wrapper.findAll('[role="tab"]')
    const compTab = tabs.find((t) => t.text().includes('Componentes'))
    if (compTab) {
      await compTab.trigger('click')
      await wrapper.vm.$nextTick()
    }

    // Trigger ZIP import via hidden file input
    const zipInput = wrapper
      .findAll('input[type="file"]')
      .find((i) => i.attributes('accept') === '.zip')
    if (zipInput) {
      const file = new File([new ArrayBuffer(10)], 'components.zip', { type: 'application/zip' })
      Object.defineProperty(zipInput.element, 'files', { value: [file], writable: false })
      await zipInput.trigger('change')
      await flushPromises()
    }

    // Verify generatePreviewHtml was called (not the malicious HTML used)
    expect(mockGeneratePreviewHtml).toHaveBeenCalled()
  })
})
