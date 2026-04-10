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

  it('fileContents.html é atualizado quando templateDraft.html muda (primeira carga NÃO sinaliza conflito)', async () => {
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()

    genStore.loadTemplateDraft({ html: '<main>conteudo real do backend</main>', css: '' })

    // Aguarda Vue flush watchers
    await Promise.resolve()

    expect(codeStore.fileContents.html).toBe('<main>conteudo real do backend</main>')
    // RCA-2026-04-06: primeira carga do backend NÃO sinaliza externalChangeDetected —
    // não há edição do usuário em conflito, apenas a chegada do HTML do pipeline.
    // Banner de conflito seria falso positivo e causaria confusão no usuário.
    expect(codeStore.externalChangeDetected).toBe(false)
  })

  it('externalChangeDetected é setado quando templateDraft.html muda APÓS carga inicial', async () => {
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()

    // Primeira carga — não deve sinalizar conflito
    genStore.loadTemplateDraft({ html: '<main>html inicial do backend</main>', css: '' })
    await Promise.resolve()
    expect(codeStore.externalChangeDetected).toBe(false)

    // Segunda mudança (ex: layout switch) — DEVE sinalizar conflito
    genStore.loadTemplateDraft({ html: '<main>html atualizado do backend</main>', css: '' })
    await Promise.resolve()
    expect(codeStore.fileContents.html).toBe('<main>html atualizado do backend</main>')
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

describe('codeStore — inicialização com templateDraft já carregado (RCA-2026-04-06 4ª recorrência)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('fileContents.html inicializa com HTML do backend quando codeStore é instanciado APÓS pipeline completar', () => {
    // Cenário crítico: pipeline completa (templateDraft setado) ANTES do usuário abrir a Aba Código.
    // codeStore.ts é um Pinia store — watchers SÓ são registrados quando o store é instanciado.
    // Se o store for instanciado pela primeira vez DEPOIS que templateDraft.html já está definido,
    // os watchers nunca disparam para o valor existente (Vue watch não tem immediate:true).
    // A solução é inicializar fileContents diretamente de generationStore.templateDraft na criação.

    // 1. Carrega templateDraft ANTES de usar codeStore (simula pipeline completando antes do Monaco montar)
    const genStore = useGenerationStore()
    const backendHtml = '<html><body><main>HTML REAL DO BACKEND</main></body></html>'
    const backendCss = 'body { color: red; }'
    genStore.loadTemplateDraft({ html: backendHtml, css: backendCss })

    // 2. Agora instancia codeStore pela primeira vez (simula usuário navegando para a Aba Código)
    const codeStore = useCodeStore()

    // 3. fileContents deve imediatamente refletir o HTML do backend — SEM precisar aguardar watch
    expect(codeStore.fileContents.html).toBe(backendHtml)
    expect(codeStore.fileContents.css).toBe(backendCss)
  })

  it('fileContents.html inicializa com DEFAULT_HTML quando templateDraft não está carregado', () => {
    const codeStore = useCodeStore()
    expect(codeStore.fileContents.html).toContain('DOCTYPE html')
    expect(codeStore.fileContents.html).toContain('template-header')
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

describe('codeStore — Monaco watch integration: store atualiza DEPOIS que Monaco monta', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('fileContents.html é detectável pelo watch Vue quando muda de DEFAULT para html real', async () => {
    // Este teste valida que o watch Vue () => codeStore.fileContents[activeFile] é reativo:
    // quando fileContents.html muda, o watchEffect pode detectar a mudança.
    // Isso simula o cenário onde Monaco já montou com DEFAULT_HTML e depois
    // o backend entrega o HTML real via templateDraft.

    const codeStore = useCodeStore()
    const genStore = useGenerationStore()

    // Estado inicial: store sem templateDraft (Monaco teria montado com DEFAULT_HTML)
    expect(codeStore.fileContents.html).toContain('DOCTYPE html')
    expect(codeStore.fileContents.html).toContain('template-header')

    // Captura mudanças via watchEffect (simula o watch do Monaco)
    let watchedValue: string | null = null
    const { watchEffect } = await import('vue')
    const stop = watchEffect(() => {
      watchedValue = codeStore.fileContents.html
    })

    // Simula pipeline completando: loadTemplateDraft → watch templateDraft.html dispara
    const backendHtml = '<html><body><main>HTML REAL DO BACKEND</main></body></html>'
    genStore.loadTemplateDraft({ html: backendHtml, css: '' })
    await Promise.resolve()

    // O watchEffect deve ter capturado o novo valor
    expect(codeStore.fileContents.html).toBe(backendHtml)
    expect(watchedValue).toBe(backendHtml)

    // Sem banner de conflito na primeira carga
    expect(codeStore.externalChangeDetected).toBe(false)

    stop()
  })

  it('Monaco recebe valor correto mesmo quando store é instanciado ANTES da pipeline com múltiplas mutações', async () => {
    // Cenário: codeStore instanciado → documentTree muta → templateDraft carrega
    // Verifica que a sequência correta (templateDraft tem prioridade) é mantida.

    const { useTemplateStore } = await import('./templateStore')
    const codeStore = useCodeStore()
    const genStore = useGenerationStore()
    const templateStore = useTemplateStore()

    const backendHtml = '<html><body><p>HTML do backend</p></body></html>'

    // 1. documentTree muta (sem templateDraft ainda)
    templateStore.loadTree({
      root: { id: 'root-1', type: 'document', name: 'Doc', children: [], properties: {} },
    })
    await Promise.resolve()

    // Scaffold foi gerado (sem backend html)
    const scaffoldHtml = codeStore.fileContents.html
    expect(scaffoldHtml).toContain('DOCTYPE html')
    expect(scaffoldHtml).not.toBe(backendHtml)

    // 2. templateDraft chega do backend
    genStore.loadTemplateDraft({ html: backendHtml, css: '' })
    await Promise.resolve()

    // Backend HTML deve sobrescrever o scaffold
    expect(codeStore.fileContents.html).toBe(backendHtml)

    // 3. documentTree muta novamente (simula reconcileFieldBindings) — não deve sobrescrever backend HTML
    codeStore.dismissExternalChange() // reseta flag para focar no passo 3
    templateStore.loadTree({
      root: {
        id: 'root-1',
        type: 'document',
        name: 'DocUpdated',
        children: [{ id: 'child-1', type: 'header', name: 'Header', children: [], properties: {} }],
        properties: {},
      },
    })
    await Promise.resolve()

    // HTML do backend deve prevalecer sobre o scaffold (documentTree watch com guard)
    expect(codeStore.fileContents.html).toBe(backendHtml)
    // documentTree watch retornou early (guard templateDraft?.html) — não setou externalChangeDetected
    expect(codeStore.externalChangeDetected).toBe(false)
  })
})
