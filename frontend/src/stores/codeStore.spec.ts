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
