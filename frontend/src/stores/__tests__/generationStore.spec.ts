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
