import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// Mock templateStore for confirmDetection/rejectDetection
vi.mock('@/stores/templateStore', () => ({
  useTemplateStore: () => ({
    flatNodes: new Map(),
    getNodesByType: () => [],
    updateNodeProperties: vi.fn(),
  }),
}))

import DiffSummary from './DiffSummary.vue'
import { useDiffStore } from '@/stores/diffStore'
import { useMultiDocStore } from '@/stores/multiDocStore'

describe('DiffSummary', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows empty message when no inferences', () => {
    const wrapper = mount(DiffSummary)
    expect(wrapper.text()).toContain('Nenhuma inferência encontrada')
  })

  it('renders a list of inferences', () => {
    const store = useDiffStore()
    store.inferences = [
      { id: 'inf-1', type: 'removed', description: 'Campo X removido', confidence: 0.9 },
      { id: 'inf-2', type: 'added', description: 'Campo Y adicionado', confidence: 0.8 },
    ]
    const wrapper = mount(DiffSummary)
    expect(wrapper.text()).toContain('Campo X removido')
    expect(wrapper.text()).toContain('Campo Y adicionado')
  })

  it('shows confidence percentage', () => {
    const store = useDiffStore()
    store.inferences = [
      { id: 'inf-1', type: 'removed', description: 'desc', confidence: 0.75 },
    ]
    const wrapper = mount(DiffSummary)
    expect(wrapper.text()).toContain('75%')
  })

  it('calls confirmInference when Confirmar is clicked', async () => {
    const store = useDiffStore()
    const multiDocStore = useMultiDocStore()
    multiDocStore.detections = [
      { id: 'inf-1', pdfId: '', type: 'required', description: 'test', confidence: 1.0 },
    ]
    store.inferences = [
      { id: 'inf-1', type: 'removed', description: 'desc', confidence: 0.9 },
    ]

    const wrapper = mount(DiffSummary)
    const confirmBtn = wrapper.find('[data-testid="confirm-inf-1"]')
    expect(confirmBtn.exists()).toBe(true)
    await confirmBtn.trigger('click')

    expect(store.inferences.find((i) => i.id === 'inf-1')).toBeUndefined()
  })

  it('calls rejectInference when Rejeitar is clicked', async () => {
    const store = useDiffStore()
    const multiDocStore = useMultiDocStore()
    multiDocStore.detections = [
      { id: 'inf-1', pdfId: '', type: 'required', description: 'test', confidence: 1.0 },
    ]
    store.inferences = [
      { id: 'inf-1', type: 'added', description: 'desc', confidence: 0.8 },
    ]
    store.diffData = [{ elementId: 'inf-1', diffType: 'added' }]

    const wrapper = mount(DiffSummary)
    const rejectBtn = wrapper.find('[data-testid="reject-inf-1"]')
    expect(rejectBtn.exists()).toBe(true)
    await rejectBtn.trigger('click')

    expect(store.inferences).toHaveLength(0)
    expect(store.diffData).toHaveLength(0)
  })

  it('renders badge labels correctly', () => {
    const store = useDiffStore()
    store.inferences = [
      { id: 'a', type: 'identical', description: 'desc a', confidence: 1.0 },
      { id: 'b', type: 'moved', description: 'desc b', confidence: 0.7 },
      { id: 'c', type: 'added', description: 'desc c', confidence: 0.9 },
      { id: 'd', type: 'removed', description: 'desc d', confidence: 0.9 },
    ]
    const wrapper = mount(DiffSummary)
    expect(wrapper.text()).toContain('= Idêntico')
    expect(wrapper.text()).toContain('↕ Movido')
    expect(wrapper.text()).toContain('+ Adicionado')
    expect(wrapper.text()).toContain('− Removido')
  })
})
