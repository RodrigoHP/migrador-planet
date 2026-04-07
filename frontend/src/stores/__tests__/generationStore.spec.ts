import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGenerationStore } from '../generation'

describe('generationStore.loadTemplateDraft()', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('Formato 1: monolítico { html, css }', () => {
    it('carrega templateDraft com html e css corretos', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: '<div>Olá</div>', css: 'body { color: red; }' })

      expect(store.templateDraft).toEqual({ html: '<div>Olá</div>', css: 'body { color: red; }' })
    })

    it('popula campos html e css para compatibilidade retroativa', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: '<p>Teste</p>', css: '.cls { font-size: 12px; }' })

      expect(store.html).toBe('<p>Teste</p>')
      expect(store.css).toBe('.cls { font-size: 12px; }')
    })

    it('aceita html vazio sem quebrar', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: '', css: '' })

      expect(store.templateDraft).toEqual({ html: '', css: '' })
      expect(store.html).toBe('')
      expect(store.css).toBe('')
    })

    it('preserva HTML com múltiplas páginas marcadas com data-page', () => {
      const multiPageHtml = `<div data-page="1">Página 1</div><div data-page="2">Página 2</div>`
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: multiPageHtml, css: '.page {}' })

      expect(store.templateDraft?.html).toContain('data-page="1"')
      expect(store.templateDraft?.html).toContain('data-page="2"')
    })
  })

  describe('Formato 2: objeto paginado { pages: TemplateDraftPage[] }', () => {
    it('concatena html de todas as páginas e usa css da primeira', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({
        pages: [
          { pageNum: 1, html: '<div>Página 1</div>', css: 'body { margin: 0; }' },
          { pageNum: 2, html: '<div>Página 2</div>', css: 'body { margin: 0; }' },
        ],
      })

      expect(store.templateDraft?.html).toContain('<div>Página 1</div>')
      expect(store.templateDraft?.html).toContain('<div>Página 2</div>')
      expect(store.templateDraft?.css).toBe('body { margin: 0; }')
    })

    it('aceita array de páginas vazio sem quebrar', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ pages: [] })

      expect(store.templateDraft).toEqual({ html: '', css: '' })
    })

    it('popula html e css para compatibilidade retroativa', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({
        pages: [{ pageNum: 1, html: '<section>X</section>', css: 'p {}' }],
      })

      expect(store.html).toContain('<section>X</section>')
      expect(store.css).toBe('p {}')
    })
  })

  describe('Formato 3: array paginado TemplateDraftPage[]', () => {
    it('concatena html de todas as páginas e usa css da primeira', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft([
        { pageNum: 1, html: '<p>P1</p>', css: '.root { font: 12px; }' },
        { pageNum: 2, html: '<p>P2</p>', css: '.root { font: 12px; }' },
        { pageNum: 3, html: '<p>P3</p>', css: '.root { font: 12px; }' },
      ])

      expect(store.templateDraft?.html).toContain('<p>P1</p>')
      expect(store.templateDraft?.html).toContain('<p>P2</p>')
      expect(store.templateDraft?.html).toContain('<p>P3</p>')
      expect(store.templateDraft?.css).toBe('.root { font: 12px; }')
    })

    it('aceita array vazio sem quebrar', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft([])

      expect(store.templateDraft).toEqual({ html: '', css: '' })
    })
  })

  describe('Estado inicial e reset', () => {
    it('templateDraft é null no estado inicial', () => {
      const store = useGenerationStore()
      expect(store.templateDraft).toBeNull()
    })

    it('isFidelityLow é false quando fidelityScore é null', () => {
      const store = useGenerationStore()
      expect(store.isFidelityLow).toBe(false)
    })

    it('isFidelityLow é true quando fidelityScore < 70', () => {
      const store = useGenerationStore()
      store.fidelityScore = 65
      expect(store.isFidelityLow).toBe(true)
    })

    it('isFidelityLow é false quando fidelityScore >= 70', () => {
      const store = useGenerationStore()
      store.fidelityScore = 70
      expect(store.isFidelityLow).toBe(false)
    })
  })
})

describe('generationStore — Opção C patch functions (ADR-029)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const SAMPLE_HTML = `<span data-node-id="node-1" data-type="label" style="position:absolute;left:10px;top:20px;width:100px;height:30px">Texto original</span>`

  describe('patchNodeGeometry()', () => {
    it('atualiza style com novas coordenadas quando nó existe', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })

      store.patchNodeGeometry('node-1', 50, 80, 200, 40)

      expect(store.templateDraft?.html).toContain('left:50px')
      expect(store.templateDraft?.html).toContain('top:80px')
      expect(store.templateDraft?.html).toContain('width:200px')
      expect(store.templateDraft?.html).toContain('height:40px')
    })

    it('cria novo objeto templateDraft (nova referência) para disparar watcher', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchNodeGeometry('node-1', 50, 80, 200, 40)

      expect(store.templateDraft).not.toBe(refAntes)
    })

    it('não modifica templateDraft quando nodeId não existe no HTML', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchNodeGeometry('node-inexistente', 0, 0, 50, 50)

      expect(store.templateDraft).toBe(refAntes)
    })

    it('não modifica templateDraft quando templateDraft é null', () => {
      const store = useGenerationStore()
      // templateDraft é null por padrão
      expect(() => store.patchNodeGeometry('node-1', 0, 0, 100, 100)).not.toThrow()
      expect(store.templateDraft).toBeNull()
    })

    it('preserva css ao fazer patch de html', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: 'body { margin: 0; }' })

      store.patchNodeGeometry('node-1', 5, 5, 80, 25)

      expect(store.templateDraft?.css).toBe('body { margin: 0; }')
    })
  })

  describe('patchNodeText()', () => {
    it('atualiza conteúdo de texto quando nó existe', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })

      store.patchNodeText('node-1', 'Novo texto')

      expect(store.templateDraft?.html).toContain('Novo texto')
      expect(store.templateDraft?.html).not.toContain('Texto original')
    })

    it('cria novo objeto templateDraft para disparar watcher', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchNodeText('node-1', 'Novo texto')

      expect(store.templateDraft).not.toBe(refAntes)
    })

    it('escapa HTML entities em texto com caracteres especiais', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })

      store.patchNodeText('node-1', 'R$ 1.500,00 <especial>')

      // DOMParser/serialização deve escapar < e >
      expect(store.templateDraft?.html).toContain('R$ 1.500,00')
      expect(store.templateDraft?.html).not.toContain('<especial>')
    })

    it('não modifica templateDraft quando nodeId não existe', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchNodeText('node-inexistente', 'Qualquer texto')

      expect(store.templateDraft).toBe(refAntes)
    })
  })

  describe('patchRemoveNode() — Story 29.7', () => {
    it('remove o elemento do HTML quando nó existe', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })

      store.patchRemoveNode('node-1')

      expect(store.templateDraft?.html).not.toContain('data-node-id="node-1"')
    })

    it('cria novo objeto templateDraft para disparar watcher', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchRemoveNode('node-1')

      expect(store.templateDraft).not.toBe(refAntes)
    })

    it('não modifica templateDraft quando nodeId não existe no HTML', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchRemoveNode('node-inexistente')

      expect(store.templateDraft).toBe(refAntes)
    })

    it('não lança erro quando templateDraft é null', () => {
      const store = useGenerationStore()
      expect(() => store.patchRemoveNode('node-1')).not.toThrow()
    })
  })

  describe('patchAddNode() — Story 29.7', () => {
    const PARENT_HTML = `<div data-node-id="section-1" data-type="section" style="position:absolute;left:0px;top:0px;width:200px;height:100px"></div>`

    it('insere elemento placeholder no pai correto', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: PARENT_HTML, css: '' })

      const newNode = {
        id: 'new-label-1',
        type: 'label' as const,
        name: 'Novo Label',
        binding: '',
        isOptional: false,
        children: [],
        visibility: true,
        properties: { x: 10, y: 20, width: 80, height: 18, text: 'Novo Label' },
      }
      store.patchAddNode(newNode, 'section-1')

      expect(store.templateDraft?.html).toContain('data-node-id="new-label-1"')
      expect(store.templateDraft?.html).toContain('data-type="label"')
    })

    it('gera placeholder sem erro quando pai não tem data-node-id (no-op)', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: SAMPLE_HTML, css: '' })
      const refAntes = store.templateDraft

      const newNode = {
        id: 'new-1',
        type: 'label' as const,
        name: 'X',
        binding: '',
        isOptional: false,
        children: [],
        visibility: true,
        properties: {},
      }
      store.patchAddNode(newNode, 'pai-sem-data-node-id')

      expect(store.templateDraft).toBe(refAntes)
    })

    it('não lança erro quando templateDraft é null', () => {
      const store = useGenerationStore()
      const node = {
        id: 'x',
        type: 'label' as const,
        name: 'X',
        binding: '',
        isOptional: false,
        children: [],
        visibility: true,
        properties: {},
      }
      expect(() => store.patchAddNode(node, 'section-1')).not.toThrow()
    })
  })

  describe('patchMoveNode() — Story 29.7', () => {
    const MOVE_HTML = `<div data-node-id="parent-a" data-type="section" style="position:absolute;left:0px;top:0px;width:200px;height:100px"><span data-node-id="child-1" data-type="label" style="position:absolute">Texto</span></div><div data-node-id="parent-b" data-type="section" style="position:absolute;left:200px;top:0px;width:200px;height:100px"></div>`

    it('move o elemento para o novo pai no DOM', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: MOVE_HTML, css: '' })

      store.patchMoveNode('child-1', 'parent-b')

      const html = store.templateDraft?.html ?? ''
      // child-1 deve agora ser filho de parent-b
      expect(html).toContain('data-node-id="child-1"')
      // parent-b deve conter child-1
      const parentBIdx = html.indexOf('data-node-id="parent-b"')
      const childIdx = html.indexOf('data-node-id="child-1"')
      expect(childIdx).toBeGreaterThan(parentBIdx)
    })

    it('cria novo objeto templateDraft após mover', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: MOVE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchMoveNode('child-1', 'parent-b')

      expect(store.templateDraft).not.toBe(refAntes)
    })

    it('não modifica templateDraft quando nodeId ou newParentId não existe', () => {
      const store = useGenerationStore()
      store.loadTemplateDraft({ html: MOVE_HTML, css: '' })
      const refAntes = store.templateDraft

      store.patchMoveNode('inexistente', 'parent-b')

      expect(store.templateDraft).toBe(refAntes)
    })

    it('não lança erro quando templateDraft é null', () => {
      const store = useGenerationStore()
      expect(() => store.patchMoveNode('child-1', 'parent-b')).not.toThrow()
    })
  })
})
