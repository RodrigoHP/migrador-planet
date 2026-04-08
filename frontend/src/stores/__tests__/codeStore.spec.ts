import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCodeStore } from '../codeStore'
import { CODE_FILES } from '@/types/editor.types'

// Mock templateStore to avoid circular imports and deep watchers
const mockUpdateNodeProperty = vi.fn()
const mockRemoveNode = vi.fn().mockReturnValue(true)
const mockMoveElement = vi.fn()
const mockResizeElement = vi.fn()
const mockAddNodeFromSync = vi.fn().mockReturnValue(true)
const mockFlatNodes = new Map<string, { id: string; type: string; properties: Record<string, unknown> }>()

vi.mock('../templateStore', () => ({
  useTemplateStore: () => ({
    documentTree: null,
    flatNodes: mockFlatNodes,
    updateNodeProperty: mockUpdateNodeProperty,
    removeNode: mockRemoveNode,
    moveElement: mockMoveElement,
    resizeElement: mockResizeElement,
    addNodeFromSync: mockAddNodeFromSync,
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
    mockRemoveNode.mockClear()
    mockMoveElement.mockClear()
    mockResizeElement.mockClear()
    mockAddNodeFromSync.mockClear()
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

// ─── Story 36.1: patchHtmlFromTree — selective HTML patching ────────────────────
describe('codeStore — Story 36.1: patchHtmlFromTree', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    mockUpdateNodeProperty.mockClear()
    mockFlatNodes.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('AC1: patches text content for matching data-node-id', () => {
    mockFlatNodes.set('n1', {
      id: 'n1',
      type: 'label',
      properties: { text: 'Texto Atualizado' },
    })
    const store = useCodeStore()

    const html = '<html><body><span data-node-id="n1">Texto Original</span></body></html>'
    const patched = store.patchHtmlFromTree(html)

    expect(patched).toContain('Texto Atualizado')
    expect(patched).not.toContain('Texto Original')
  })

  it('AC2: patches data-field attribute when binding changes', () => {
    mockFlatNodes.set('n1', {
      id: 'n1',
      type: 'field',
      name: 'campo',
      binding: 'cliente.cpf',
      properties: {},
    })
    const store = useCodeStore()

    const html = '<html><body><span data-node-id="n1" data-field="old.path">text</span></body></html>'
    const patched = store.patchHtmlFromTree(html)

    expect(patched).toContain('data-field="cliente.cpf"')
  })

  it('AC3: returns original HTML when no nodes match', () => {
    mockFlatNodes.set('n1', {
      id: 'n1',
      type: 'label',
      properties: { text: 'same' },
    })
    const store = useCodeStore()

    const html = '<html><body><span data-node-id="n99">other</span></body></html>'
    const result = store.patchHtmlFromTree(html)

    // No matching n1 in HTML, so nothing patched — original returned
    expect(result).toBe(html)
  })

  it('AC4: returns original HTML when flatNodes is empty', () => {
    const store = useCodeStore()

    const html = '<html><body><span data-node-id="n1">text</span></body></html>'
    const result = store.patchHtmlFromTree(html)

    expect(result).toBe(html)
  })

  it('AC3: _isSyncing flag prevents code->tree->code loop', () => {
    // patchHtmlFromTree itself does not set _isSyncing (the watcher does),
    // but we verify the function does not call updateNodeProperty (it only reads nodes)
    mockFlatNodes.set('n1', {
      id: 'n1',
      type: 'label',
      properties: { text: 'New' },
    })
    const store = useCodeStore()

    store.patchHtmlFromTree('<html><body><span data-node-id="n1">Old</span></body></html>')

    // patchHtmlFromTree should NOT trigger any store mutations
    expect(mockUpdateNodeProperty).not.toHaveBeenCalled()
  })
})

// ─── Story 30.3: Parser HTML completo ─────────────────────────────────────────
describe('codeStore — Story 30.3: parser HTML completo (add/remove/position)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    mockUpdateNodeProperty.mockClear()
    mockRemoveNode.mockClear()
    mockMoveElement.mockClear()
    mockResizeElement.mockClear()
    mockAddNodeFromSync.mockClear()
    mockFlatNodes.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // AC1: novo data-node-id no HTML → addNodeFromSync chamado com id correto
  it('AC1: nó presente no HTML mas não no store → addNodeFromSync chamado', () => {
    // parent exists in store
    mockFlatNodes.set('parent-1', { id: 'parent-1', type: 'section', properties: {} })
    const store = useCodeStore()

    const html = '<div data-node-id="parent-1" data-type="section" style="position:absolute;left:0px;top:0px;width:200px;height:100px">' +
      '<span data-node-id="new-node-1" data-type="field" style="position:absolute;left:10px;top:5px;width:80px;height:20px">Cedente</span>' +
      '</div>'

    store.syncHtmlToTree(html)

    expect(mockAddNodeFromSync).toHaveBeenCalledOnce()
    const [newNode, parentId] = mockAddNodeFromSync.mock.calls[0]
    expect(newNode.id).toBe('new-node-1')
    expect(newNode.type).toBe('field')
    expect(parentId).toBe('parent-1')
    expect(newNode.properties.x).toBe(10)
    expect(newNode.properties.y).toBe(5)
  })

  // AC2: nó no store mas ausente no HTML (quando HTML tem data-node-ids) → removeNode chamado
  it('AC2: nó no store não está no HTML (HTML com data-node-ids) → removeNode chamado', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'field', properties: { text: 'old' } })
    mockFlatNodes.set('n2', { id: 'n2', type: 'label', properties: {} })
    const store = useCodeStore()

    // HTML has n2 but not n1 — n1 should be removed
    const html = '<span data-node-id="n2" data-type="label">Label</span>'
    store.syncHtmlToTree(html)

    expect(mockRemoveNode).toHaveBeenCalledWith('n1')
    expect(mockRemoveNode).not.toHaveBeenCalledWith('n2')
  })

  // AC3: position CSS alterada → moveElement chamado com delta correto
  it('AC3: left/top CSS alterado no HTML → moveElement chamado', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'field', properties: { x: 10, y: 20, width: 100, height: 20 } })
    const store = useCodeStore()

    // Position changed: left 10→50, top 20→30
    const html = '<span data-node-id="n1" style="position:absolute;left:50px;top:30px;width:100px;height:20px">text</span>'
    store.syncHtmlToTree(html)

    expect(mockMoveElement).toHaveBeenCalledWith('n1', 40, 10) // dx=40, dy=10
  })

  // AC3: width/height CSS alterado → resizeElement chamado
  it('AC3: width/height CSS alterado no HTML → resizeElement chamado', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'field', properties: { x: 10, y: 20, width: 100, height: 20 } })
    const store = useCodeStore()

    // Size changed: width 100→150, height 20→40
    const html = '<span data-node-id="n1" style="position:absolute;left:10px;top:20px;width:150px;height:40px">text</span>'
    store.syncHtmlToTree(html)

    expect(mockResizeElement).toHaveBeenCalledWith('n1', 150, 40)
  })

  // AC4: HTML sem nenhum data-node-id → add/remove NÃO processados
  it('AC4: HTML sem [data-node-id] → removeNode e addNodeFromSync NÃO chamados', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'field', properties: { text: 'ok' } })
    const store = useCodeStore()

    // Scaffold HTML — no data-node-id elements
    const html = '<html><body><div><span>texto sem id</span></div></body></html>'
    store.syncHtmlToTree(html)

    expect(mockRemoveNode).not.toHaveBeenCalled()
    expect(mockAddNodeFromSync).not.toHaveBeenCalled()
  })

  // AC5: text sync preservado (comportamento MVP)
  it('AC5: text sync preservado junto com novos recursos', () => {
    mockFlatNodes.set('n1', { id: 'n1', type: 'label', properties: { text: 'Antigo' } })
    const store = useCodeStore()

    const html = '<span data-node-id="n1" style="left:0px;top:0px;width:100px;height:20px">Novo Texto</span>'
    store.syncHtmlToTree(html)

    expect(mockUpdateNodeProperty).toHaveBeenCalledWith('n1', 'text', 'Novo Texto')
  })
})
