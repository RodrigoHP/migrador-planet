import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCodeStore } from './codeStore'
import { useGenerationStore } from './generation'

describe('codeStore — CSS Live Editor (Story 14.1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('injectTemplateCSS updates generationStore.templateDraft.css', () => {
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()
    genStore.loadTemplateDraft({ html: '<p>test</p>', css: 'body {}' })

    codeStore.injectTemplateCSS('.new { color: blue; }')
    expect(genStore.templateDraft!.css).toBe('.new { color: blue; }')
  })

  it('applyMonacoEdit for CSS triggers injectTemplateCSS', () => {
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()
    genStore.loadTemplateDraft({ html: '<p>test</p>', css: 'body {}' })

    codeStore.applyMonacoEdit('css', '.updated { margin: 0; }')

    expect(codeStore.fileContents.css).toBe('.updated { margin: 0; }')
    expect(genStore.templateDraft!.css).toBe('.updated { margin: 0; }')
  })

  it('applyMonacoEdit for HTML does not touch CSS', () => {
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()
    genStore.loadTemplateDraft({ html: '<p>test</p>', css: 'body {}' })

    codeStore.applyMonacoEdit('html', '<div>updated</div>')

    expect(genStore.templateDraft!.css).toBe('body {}')
  })

  it('does not apply edits to read-only files', () => {
    const codeStore = useCodeStore()
    const original = codeStore.fileContents.exemplo

    codeStore.applyMonacoEdit('exemplo', 'hacked!')
    expect(codeStore.fileContents.exemplo).toBe(original)
  })
})

describe('codeStore — templateDraft.html sync', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('fileContents.html é atualizado quando templateDraft.html muda', async () => {
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()

    genStore.loadTemplateDraft({ html: '<main>conteudo real do backend</main>', css: '' })

    // Aguarda Vue flush watchers
    await Promise.resolve()

    expect(codeStore.fileContents.html).toBe('<main>conteudo real do backend</main>')
    expect(codeStore.externalChangeDetected).toBe(true)
  })

  it('fileContents.html não é sobrescrito se templateDraft.html for null/undefined', async () => {
    const codeStore = useCodeStore()
    const original = codeStore.fileContents.html

    // templateDraft não carregado → html fica como DEFAULT_HTML
    await Promise.resolve()

    expect(codeStore.fileContents.html).toBe(original)
  })

  it('fileContents.html não dispara externalChangeDetected se conteúdo igual', async () => {
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()

    genStore.loadTemplateDraft({ html: codeStore.fileContents.html, css: '' })
    await Promise.resolve()

    expect(codeStore.externalChangeDetected).toBe(false)
  })
})

describe('codeStore — templateDraft.html tem prioridade sobre documentTree watch (RCA-2026-04-06)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('documentTree watch não sobrescreve fileContents.html quando templateDraft.html está definido', async () => {
    const { useTemplateStore } = await import('./templateStore')
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()
    const templateStore = useTemplateStore()

    const backendHtml = '<html><body><p>HTML real do backend</p></body></html>'

    // 1. Carrega o HTML do backend via templateDraft (simula loadTemplateDraft em loadFromPipelineResult)
    genStore.loadTemplateDraft({ html: backendHtml, css: 'body {}' })
    await Promise.resolve()
    expect(codeStore.fileContents.html).toBe(backendHtml)

    // 2. Simula reconcileFieldBindings: muta a árvore após loadTemplateDraft
    //    Isso dispara o watch deep de documentTree — não deve sobrescrever o HTML do backend
    templateStore.loadTree({
      root: {
        id: 'root-1',
        type: 'document',
        name: 'Doc',
        children: [],
        properties: {},
      },
    })
    await Promise.resolve()

    // O HTML do backend deve prevalecer — o scaffold do cliente não deve sobrescrever
    expect(codeStore.fileContents.html).toBe(backendHtml)
  })

  it('documentTree watch PODE atualizar fileContents.html quando não há templateDraft definido', async () => {
    const { useTemplateStore } = await import('./templateStore')
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()
    const templateStore = useTemplateStore()

    // Sem templateDraft carregado, o watch de documentTree deve funcionar normalmente
    expect(genStore.templateDraft).toBeNull()

    templateStore.loadTree({
      root: {
        id: 'root-1',
        type: 'document',
        name: 'Doc',
        children: [],
        properties: {},
      },
    })
    await Promise.resolve()

    // O scaffold gerado deve ter sido aplicado (não é o DEFAULT_HTML com DOCTYPE simples)
    expect(codeStore.fileContents.html).toContain('DOCTYPE html')
  })
})
