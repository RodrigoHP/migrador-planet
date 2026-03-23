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
