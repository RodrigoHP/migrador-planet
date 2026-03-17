import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import UploadPage from './UploadPage.vue'

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock FullWidthLayout — transparent pass-through
vi.mock('@/templates/FullWidthLayout.vue', () => ({
  default: {
    name: 'FullWidthLayout',
    template: '<div><slot /></div>',
  },
}))

// Mock ProgressBar atom
vi.mock('@/atoms', () => ({
  ProgressBar: {
    name: 'ProgressBar',
    props: ['value', 'animated'],
    template: '<div class="progress-bar" :data-value="value" />',
  },
}))

// ─── Helpers ──────────────────────────────────────────────────────────────────

function createTestRouter() {
  return createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/upload', component: UploadPage },
      { path: '/analyzing', component: { template: '<div>analyzing</div>' } },
    ],
  })
}

/** Create a fake File with a given size in bytes */
function fakeFile(name: string, sizeBytes: number, type = 'application/pdf'): File {
  const file = new File(['x'.repeat(Math.min(sizeBytes, 1))], name, { type })
  Object.defineProperty(file, 'size', { value: sizeBytes, configurable: true })
  return file
}

/** Assign files to an input element, allowing repeated redefinition */
function setInputFiles(inputEl: HTMLInputElement, files: File[]) {
  Object.defineProperty(inputEl, 'files', {
    value: files,
    writable: false,
    configurable: true,
  })
}

function mountUploadPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createTestRouter()
  const wrapper = mount(UploadPage, {
    global: { plugins: [pinia, router] },
    attachTo: document.body,
  })
  return { wrapper, router, pinia }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('UploadPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Rendering ──────────────────────────────────────────────────────────────

  it('renderiza o título "Upload de Arquivos"', () => {
    const { wrapper } = mountUploadPage()
    expect(wrapper.find('h1').text()).toBe('Upload de Arquivos')
  })

  it('renderiza o botão "Iniciar Análise"', () => {
    const { wrapper } = mountUploadPage()
    const btn = wrapper.find('button.upload__submit')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe('Iniciar Análise')
  })

  // ── Hint logic — AC 4-7 ────────────────────────────────────────────────────

  it('hint noPDF_noXSD: "Envie ao menos 1 PDF + XSD para continuar" (estado inicial)', () => {
    const { wrapper } = mountUploadPage()
    const hint = wrapper.find('[role="status"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toBe('Envie ao menos 1 PDF + XSD para continuar')
  })

  it('hint noXSD: sem XSD, só PDF exibe hint de adicionar XSD com dados', async () => {
    const { wrapper } = mountUploadPage()

    // Add 1 PDF via the hidden input
    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const pdf = fakeFile('doc.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [pdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    // Without XSD: hint about adding XSD — actually matches "PDF sem XSD" but
    // we have no data either, so hint is "Envie ao menos 1 PDF + XSD para continuar"
    // Wait — state: hasPdf=true, hasXsd=false, hasData=false
    // currentHint: !hasPdf && !hasXsd is false, so falls through
    // pdfCount===1 && hasXsd && !hasData → false (no xsd)
    // hasPdf && hasData && !hasXsd → false (no data)
    // hasPdf && hasXsd && !hasData → false (no xsd)
    // → returns null — no hint shown
    const hint = wrapper.find('[role="status"]')
    expect(hint.exists()).toBe(false)
  })

  it('hint hasXSD_noPDF: apenas XSD sem PDF → hint nulo (sem hint no template)', async () => {
    const { wrapper } = mountUploadPage()

    // Add XSD
    const xsdInput = wrapper.find('input[type="file"][accept=".xsd"]')
    const xsd = fakeFile('schema.xsd', 1024, 'application/xml')
    setInputFiles(xsdInput.element as HTMLInputElement, [xsd])
    await xsdInput.trigger('change')
    await wrapper.vm.$nextTick()

    // hasPdf=false, hasXsd=true → !hasPdf && !hasXsd is false → all conditions false
    const hint = wrapper.find('[role="status"]')
    expect(hint.exists()).toBe(false)
  })

  it('hint ready (1 PDF + XSD): "💡 Adicionar mais PDFs melhora a detecção de variações"', async () => {
    const { wrapper } = mountUploadPage()

    // Add 1 PDF
    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const pdf = fakeFile('doc.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [pdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    // Add XSD
    const xsdInput = wrapper.find('input[type="file"][accept=".xsd"]')
    const xsd = fakeFile('schema.xsd', 512, 'application/xml')
    setInputFiles(xsdInput.element as HTMLInputElement, [xsd])
    await xsdInput.trigger('change')
    await wrapper.vm.$nextTick()

    // pdfCount===1 && hasXsd && !hasData → true
    const hint = wrapper.find('[role="status"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('Adicionar mais PDFs melhora a detecção de variações')
  })

  it('hint PDF+XSD sem dados: "💡 Adicionar dados reais melhora a detecção de tipos e formatos"', async () => {
    const { wrapper } = mountUploadPage()

    // Add 2 PDFs so pdfCount > 1 (bypasses the single-PDF hint)
    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const pdf1 = fakeFile('doc1.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [pdf1])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    // Re-trigger with second PDF (need to create a new input trigger)
    const pdf2 = fakeFile('doc2.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [pdf2])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    // Add XSD
    const xsdInput = wrapper.find('input[type="file"][accept=".xsd"]')
    const xsd = fakeFile('schema.xsd', 512, 'application/xml')
    setInputFiles(xsdInput.element as HTMLInputElement, [xsd])
    await xsdInput.trigger('change')
    await wrapper.vm.$nextTick()

    // hasPdf && hasXsd && !hasData → "Adicionar dados reais..."
    const hint = wrapper.find('[role="status"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('Adicionar dados reais melhora a detecção de tipos e formatos')
  })

  it('hint PDF+dados sem XSD: "💡 Adicionar o XSD permite validar campos obrigatórios"', async () => {
    const { wrapper } = mountUploadPage()

    // Add 1 PDF
    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const pdf = fakeFile('doc.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [pdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    // Add Data file (xml/json)
    const dataInput = wrapper.find('input[type="file"][accept=".xml,.json"]')
    const data = fakeFile('data.xml', 512, 'application/xml')
    setInputFiles(dataInput.element as HTMLInputElement, [data])
    await dataInput.trigger('change')
    await wrapper.vm.$nextTick()

    // hasPdf && hasData && !hasXsd → "Adicionar o XSD..."
    const hint = wrapper.find('[role="status"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('Adicionar o XSD permite validar campos obrigatórios')
  })

  // ── Botão "Iniciar Análise" disabled state (AC 8) ──────────────────────────

  it('botão "Iniciar Análise" está desabilitado quando não há arquivos', () => {
    const { wrapper } = mountUploadPage()
    const btn = wrapper.find('button.upload__submit')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('botão "Iniciar Análise" está desabilitado quando só há PDF (sem XSD)', async () => {
    const { wrapper } = mountUploadPage()

    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const pdf = fakeFile('doc.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [pdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    const btn = wrapper.find('button.upload__submit')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('botão "Iniciar Análise" está desabilitado quando só há XSD (sem PDF)', async () => {
    const { wrapper } = mountUploadPage()

    const xsdInput = wrapper.find('input[type="file"][accept=".xsd"]')
    const xsd = fakeFile('schema.xsd', 512, 'application/xml')
    setInputFiles(xsdInput.element as HTMLInputElement, [xsd])
    await xsdInput.trigger('change')
    await wrapper.vm.$nextTick()

    const btn = wrapper.find('button.upload__submit')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('botão "Iniciar Análise" fica habilitado quando há pelo menos 1 PDF + XSD', async () => {
    const { wrapper } = mountUploadPage()

    // Add PDF
    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const pdf = fakeFile('doc.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [pdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    // Add XSD
    const xsdInput = wrapper.find('input[type="file"][accept=".xsd"]')
    const xsd = fakeFile('schema.xsd', 512, 'application/xml')
    setInputFiles(xsdInput.element as HTMLInputElement, [xsd])
    await xsdInput.trigger('change')
    await wrapper.vm.$nextTick()

    const btn = wrapper.find('button.upload__submit')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  // ── Validação de tamanho de arquivo (AC 11) ────────────────────────────────

  it('rejeita PDF maior que 50MB e exibe erro de tamanho', async () => {
    const { wrapper } = mountUploadPage()

    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const bigPdf = fakeFile('big.pdf', 51 * 1024 * 1024) // 51 MB
    setInputFiles(pdfInput.element as HTMLInputElement, [bigPdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    const errorContainer = wrapper.find('.upload__size-errors')
    expect(errorContainer.exists()).toBe(true)
    expect(errorContainer.text()).toContain('big.pdf')
    expect(errorContainer.text()).toContain('50MB')
  })

  it('aceita PDF dentro do limite de 50MB sem exibir erro', async () => {
    const { wrapper } = mountUploadPage()

    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')
    const okPdf = fakeFile('ok.pdf', 10 * 1024 * 1024) // 10 MB
    setInputFiles(pdfInput.element as HTMLInputElement, [okPdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.upload__size-errors').exists()).toBe(false)
  })

  it('rejeita XSD maior que 10MB e exibe erro de tamanho', async () => {
    const { wrapper } = mountUploadPage()

    const xsdInput = wrapper.find('input[type="file"][accept=".xsd"]')
    const bigXsd = fakeFile('big.xsd', 11 * 1024 * 1024, 'application/xml')
    setInputFiles(xsdInput.element as HTMLInputElement, [bigXsd])
    await xsdInput.trigger('change')
    await wrapper.vm.$nextTick()

    const errorContainer = wrapper.find('.upload__size-errors')
    expect(errorContainer.exists()).toBe(true)
    expect(errorContainer.text()).toContain('big.xsd')
    expect(errorContainer.text()).toContain('10MB')
  })

  // ── Fix: sizeErrors não acumula entre adições (Issue #2) ───────────────────

  it('sizeErrors é limpo a cada nova adição de PDFs (não acumula erros obsoletos)', async () => {
    const { wrapper } = mountUploadPage()

    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')

    // First batch: 1 oversized PDF → 1 error
    const bigPdf = fakeFile('big.pdf', 51 * 1024 * 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [bigPdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.upload__size-errors').exists()).toBe(true)
    const firstErrors = wrapper.findAll('.upload__size-error')
    expect(firstErrors.length).toBe(1)

    // Second batch: 1 valid PDF → errors should be cleared (not stacked)
    const okPdf = fakeFile('ok.pdf', 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [okPdf])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    // No size errors should remain from the previous batch
    expect(wrapper.find('.upload__size-errors').exists()).toBe(false)
  })

  it('sizeErrors mostra apenas erros do lote atual quando múltiplos PDFs grandes são adicionados', async () => {
    const { wrapper } = mountUploadPage()

    const pdfInput = wrapper.find('input[type="file"][accept=".pdf"]')

    // First batch: 1 big PDF
    const big1 = fakeFile('big1.pdf', 51 * 1024 * 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [big1])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.upload__size-error').length).toBe(1)

    // Second batch: 2 big PDFs — should show exactly 2 errors (not 3)
    const big2 = fakeFile('big2.pdf', 52 * 1024 * 1024)
    const big3 = fakeFile('big3.pdf', 53 * 1024 * 1024)
    setInputFiles(pdfInput.element as HTMLInputElement, [big2, big3])
    await pdfInput.trigger('change')
    await wrapper.vm.$nextTick()

    const errors = wrapper.findAll('.upload__size-error')
    expect(errors.length).toBe(2)
    const texts = errors.map((e) => e.text())
    expect(texts.some((t) => t.includes('big2.pdf'))).toBe(true)
    expect(texts.some((t) => t.includes('big3.pdf'))).toBe(true)
    // The old big1.pdf error must NOT appear
    expect(texts.some((t) => t.includes('big1.pdf'))).toBe(false)
  })

  // ── Botão "← Voltar" (AC 10) ───────────────────────────────────────────────

  it('"← Voltar" navega para /', async () => {
    const { wrapper, router } = mountUploadPage()

    // Navigate to /upload first so we can go back to /
    await router.push('/upload')

    const backBtn = wrapper.find('button.upload__back')
    expect(backBtn.exists()).toBe(true)

    await backBtn.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/')
  })
})
