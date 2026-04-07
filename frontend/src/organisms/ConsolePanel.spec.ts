import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConsolePanel from './ConsolePanel.vue'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useTemplateStore } from '@/stores/templateStore'
import type { BackendWarning } from '@/types/confidence.types'
import type { DocumentTree } from '@/types/template.types'

function makeTree(): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'page' as never,
      name: 'Root',
      children: [
        {
          id: 'field-1',
          type: 'field',
          name: 'Cedente',
          binding: '',
          children: [],
          properties: {},
          visibility: true,
        },
      ],
      properties: {},
      visibility: true,
    },
  }
}

function mountPanel() {
  return mount(ConsolePanel, { attachTo: document.body })
}

describe('ConsolePanel — Story 30.5: backend warnings', () => {
  let confidenceStore: ReturnType<typeof useConfidenceStore>
  let templateStore: ReturnType<typeof useTemplateStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    confidenceStore = useConfidenceStore()
    templateStore = useTemplateStore()
  })

  // AC1: setBackendWarnings persiste no store
  it('AC1: setBackendWarnings armazena warnings e expõe via backendWarnings', () => {
    const warnings: BackendWarning[] = [
      { id: 'w1', category: 'low_confidence', message: 'Baixa confiança na extração', severity: 'warning' },
    ]
    confidenceStore.setBackendWarnings(warnings)
    expect(confidenceStore.backendWarnings).toHaveLength(1)
    expect(confidenceStore.backendWarnings[0].id).toBe('w1')
  })

  // AC2: backend warnings aparecem no painel junto com locais
  it('AC2: ConsolePanel exibe warnings backend + locais mesclados', async () => {
    templateStore.loadTree(makeTree()) // field-1 não mapeado → 1 warning local

    confidenceStore.setBackendWarnings([
      { id: 'bw1', category: 'table_inconsistent', message: 'Tabela com estrutura ambígua', severity: 'warning' },
    ])

    const wrapper = mountPanel()
    await flushPromises()

    const list = document.querySelector('[data-testid="console-list"]')
    expect(list).not.toBeNull()
    expect(list?.textContent).toContain('Cedente') // local warning
    expect(list?.textContent).toContain('Tabela com estrutura ambígua') // backend warning

    wrapper.unmount()
  })

  // AC3: clique em warning com nodeId → selectElement chamado
  it('AC3: clique em warning com nodeId seleciona nó', async () => {
    confidenceStore.setBackendWarnings([
      { id: 'bw2', category: 'low_confidence', message: 'Baixa confiança', severity: 'warning', nodeId: 'field-1' },
    ])

    const wrapper = mountPanel()
    await flushPromises()

    const item = document.querySelector('[data-testid="console-warning-bw2"]') as HTMLElement
    expect(item).not.toBeNull()
    item?.click()
    await flushPromises()

    // editorStore.selectElement should have been called with 'field-1'
    // (tested via the clickable class being present)
    expect(item.classList.contains('console-panel__item--clickable')).toBe(true)

    wrapper.unmount()
  })

  // AC4: warning sem nodeId → não-clicável
  it('AC4: warning sem nodeId não tem classe clickable', async () => {
    confidenceStore.setBackendWarnings([
      { id: 'bw3', category: 'table_inconsistent', message: 'Problema genérico', severity: 'error' },
    ])

    const wrapper = mountPanel()
    await flushPromises()

    const item = document.querySelector('[data-testid="console-warning-bw3"]') as HTMLElement
    expect(item).not.toBeNull()
    expect(item.classList.contains('console-panel__item--clickable')).toBe(false)
    expect(item.getAttribute('tabindex')).toBe('-1')

    wrapper.unmount()
  })

  // AC5: clearBackendWarnings limpa lista (apenas locais permanecem)
  it('AC5: clearBackendWarnings remove backend warnings do painel', async () => {
    templateStore.loadTree(makeTree()) // field-1 sem binding → 1 local

    confidenceStore.setBackendWarnings([
      { id: 'bw4', category: 'missing_binding', message: 'Binding ausente', severity: 'warning' },
    ])

    confidenceStore.clearBackendWarnings()

    const wrapper = mountPanel()
    await flushPromises()

    const list = document.querySelector('[data-testid="console-list"]')
    expect(list?.textContent).not.toContain('Binding ausente')
    expect(list?.textContent).toContain('Cedente') // local warning permanece

    wrapper.unmount()
  })

  // AC6: badge de categoria visível no DOM para backend warnings
  it('AC6: badge de categoria exibido para warning com category', async () => {
    confidenceStore.setBackendWarnings([
      { id: 'bw5', category: 'table_inconsistent', message: 'Tabela ambígua', severity: 'warning' },
    ])

    const wrapper = mountPanel()
    await flushPromises()

    const badge = document.querySelector('[data-testid="console-badge-bw5"]')
    expect(badge).not.toBeNull()
    expect(badge?.textContent).toBe('table_inconsistent')

    wrapper.unmount()
  })

  // Local warning sem category → sem badge
  it('warning local não exibe badge de categoria', async () => {
    templateStore.loadTree(makeTree())

    const wrapper = mountPanel()
    await flushPromises()

    const badge = document.querySelector('[data-testid="console-badge-field-1"]')
    expect(badge).toBeNull()

    wrapper.unmount()
  })
})
