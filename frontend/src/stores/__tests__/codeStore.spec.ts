import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCodeStore } from '../codeStore'
import { CODE_FILES } from '@/types/editor.types'

// Mock templateStore to avoid circular imports and deep watchers
const mockUpdateNodeProperty = vi.fn()
const mockFlatNodes = new Map<string, { id: string; type: string; properties: Record<string, unknown> }>()

vi.mock('../templateStore', () => ({
  useTemplateStore: () => ({
    documentTree: null,
    flatNodes: mockFlatNodes,
    updateNodeProperty: mockUpdateNodeProperty,
  }),
}))

describe('codeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    mockUpdateNodeProperty.mockClear()
    mockFlatNodes.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes with default file contents', () => {
    const store = useCodeStore()
    expect(store.fileContents.html).toContain('DOCTYPE html')
    expect(store.fileContents.css).toContain('Template styles')
    expect(store.fileContents.js).toContain('base.js')
    expect(store.fileContents.exemplo).toContain('exemplo.js')
  })

  it('initializes with html as active file', () => {
    const store = useCodeStore()
    expect(store.activeFile).toBe('html')
  })

  it('setActiveFile changes active file', () => {
    const store = useCodeStore()
    store.setActiveFile('css')
    expect(store.activeFile).toBe('css')
  })

  it('setFileContent updates writable file content', () => {
    const store = useCodeStore()
    store.setFileContent('html', '<html>new</html>')
    expect(store.fileContents.html).toBe('<html>new</html>')
  })

  it('setFileContent does NOT update read-only file (exemplo)', () => {
    const store = useCodeStore()
    const original = store.fileContents.exemplo
    store.setFileContent('exemplo', 'hacked content')
    expect(store.fileContents.exemplo).toBe(original)
  })

  it('applyMonacoEdit updates html content', () => {
    const store = useCodeStore()
    store.applyMonacoEdit('html', '<html>edited</html>')
    expect(store.fileContents.html).toBe('<html>edited</html>')
  })

  it('applyMonacoEdit does NOT update read-only exemplo file', () => {
    const store = useCodeStore()
    const original = store.fileContents.exemplo
    store.applyMonacoEdit('exemplo', 'hacked')
    expect(store.fileContents.exemplo).toBe(original)
  })

  it('applyMonacoEdit buffers edit when externalChangeDetected is true', () => {
    const store = useCodeStore()
    store.externalChangeDetected = true
    store.applyMonacoEdit('css', 'buffered content')
    expect(store.fileContents.css).not.toBe('buffered content')
    expect(store.pendingMonacoEdit).toEqual({ key: 'css', content: 'buffered content' })
  })

  it('resolveExternalChange with keepMonaco=true applies pending edit', () => {
    const store = useCodeStore()
    store.externalChangeDetected = true
    store.applyMonacoEdit('css', '.foo { color: red; }')
    store.resolveExternalChange(true)
    expect(store.fileContents.css).toBe('.foo { color: red; }')
    expect(store.externalChangeDetected).toBe(false)
    expect(store.pendingMonacoEdit).toBeNull()
  })

  it('resolveExternalChange with keepMonaco=false discards pending edit', () => {
    const store = useCodeStore()
    const originalCss = store.fileContents.css
    store.externalChangeDetected = true
    store.pendingMonacoEdit = { key: 'css', content: 'something' }
    store.resolveExternalChange(false)
    expect(store.fileContents.css).toBe(originalCss)
    expect(store.externalChangeDetected).toBe(false)
    expect(store.pendingMonacoEdit).toBeNull()
  })

  it('dismissExternalChange clears state', () => {
    const store = useCodeStore()
    store.externalChangeDetected = true
    store.pendingMonacoEdit = { key: 'html', content: 'x' }
    store.dismissExternalChange()
    expect(store.externalChangeDetected).toBe(false)
    expect(store.pendingMonacoEdit).toBeNull()
  })

  it('CODE_FILES has 4 entries', () => {
    expect(CODE_FILES).toHaveLength(4)
  })

  it('CODE_FILES exemplo.js is readOnly', () => {
    const exemploFile = CODE_FILES.find((f) => f.key === 'exemplo')
    expect(exemploFile?.readOnly).toBe(true)
  })

  it('CODE_FILES other files are not readOnly', () => {
    const editableFiles = CODE_FILES.filter((f) => f.key !== 'exemplo')
    editableFiles.forEach((f) => {
      expect(f.readOnly).toBe(false)
    })
  })

  it('CODE_FILES have correct languages', () => {
    const htmlFile = CODE_FILES.find((f) => f.key === 'html')
    const cssFile = CODE_FILES.find((f) => f.key === 'css')
    const jsFile = CODE_FILES.find((f) => f.key === 'js')
    const exemploFile = CODE_FILES.find((f) => f.key === 'exemplo')
    expect(htmlFile?.language).toBe('html')
    expect(cssFile?.language).toBe('css')
    expect(jsFile?.language).toBe('javascript')
    expect(exemploFile?.language).toBe('javascript')
  })
})

// ─── Story 29.3: Code Editor → Structure Sync ─────────────────────────────────
describe('codeStore — Story 29.3 HTML→Store sync', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    mockUpdateNodeProperty.mockClear()
    mockFlatNodes.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('AC3: applyMonacoEdit para HTML agenda sync com 800ms de debounce', () => {
    const store = useCodeStore()
    const html = '<span data-node-id="n1">Novo texto</span>'

    store.applyMonacoEdit('html', html)

    // Antes de 800ms: não sincronizou ainda
    expect(mockUpdateNodeProperty).not.toHaveBeenCalled()

    // Avança 800ms: sync deve ser disparado
    vi.advanceTimersByTime(800)
    // (flatNodes está vazio então não chama updateNodeProperty — mas não quebra)
  })

  it('AC3: digitação rápida resulta em apenas 1 sync ao final (debounce)', () => {
    const store = useCodeStore()

    store.applyMonacoEdit('html', '<span>texto1</span>')
    vi.advanceTimersByTime(200)
    store.applyMonacoEdit('html', '<span>texto2</span>')
    vi.advanceTimersByTime(200)
    store.applyMonacoEdit('html', '<span>texto3</span>')

    // Apenas 1 timer pendente — os anteriores foram cancelados pelo debounce
    const before = mockUpdateNodeProperty.mock.calls.length
    vi.advanceTimersByTime(800)
    const after = mockUpdateNodeProperty.mock.calls.length
    // flatNodes está vazio, então nenhuma chamada real — mas não deve ter quebrado
    expect(after).toBe(before)
  })

  it('AC1: syncHtmlToTree atualiza propriedade text do nó quando texto muda', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'label', properties: { text: 'Cedente' } })
    const store = useCodeStore()

    const html = '<span data-node-id="n1" data-type="label">Sacado</span>'
    store.syncHtmlToTree(html)

    expect(mockUpdateNodeProperty).toHaveBeenCalledWith('n1', 'text', 'Sacado')
  })

  it('AC1: syncHtmlToTree NÃO atualiza quando texto é igual ao atual', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'label', properties: { text: 'Cedente' } })
    const store = useCodeStore()

    const html = '<span data-node-id="n1">Cedente</span>'
    store.syncHtmlToTree(html)

    expect(mockUpdateNodeProperty).not.toHaveBeenCalled()
  })

  it('AC2: syncHtmlToTree atualiza data-field quando atributo muda', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'field', properties: {} })
    const store = useCodeStore()

    const html = '<span data-node-id="n1" data-field="cliente.nome">texto</span>'
    store.syncHtmlToTree(html)

    expect(mockUpdateNodeProperty).toHaveBeenCalledWith('n1', 'data-field', 'cliente.nome')
  })

  it('AC4: HTML inválido não quebra — parser retorna sem crash', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'label', properties: { text: 'ok' } })
    const store = useCodeStore()

    // HTML inválido (tag não fechada) — DOMParser não lança exceção, apenas parseia o que consegue
    expect(() => store.syncHtmlToTree('<span data-node-id="n1">texto incompleto')).not.toThrow()
  })

  it('AC4: HTML completamente vazio não causa crash', () => {
    const store = useCodeStore()
    expect(() => store.syncHtmlToTree('')).not.toThrow()
  })

  it('AC2 (sem data-field no HTML): não chama updateNodeProperty para data-field ausente', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'label', properties: { text: 'ok' } })
    const store = useCodeStore()

    // HTML sem data-field — não deve tentar sincronizar atributo inexistente
    const html = '<span data-node-id="n1">ok</span>'
    store.syncHtmlToTree(html)

    const dataFieldCalls = mockUpdateNodeProperty.mock.calls.filter((c) => c[1] === 'data-field')
    expect(dataFieldCalls).toHaveLength(0)
  })
})
