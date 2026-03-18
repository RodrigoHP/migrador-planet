import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ConfidencePopover from './ConfidencePopover.vue'
import { useConfidenceStore } from '@/stores/confidenceStore'
import { useLayoutStore } from '@/stores/layout'
import type { ConfidenceFactors } from '@/types/confidence.types'

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

const mockFactors: ConfidenceFactors = {
  layout_stability: 88,
  anchor_detection: 95,
  grid_quality: 90,
  field_variability: 93,
  vision_agreement: 89,
  overall: 91,
}

const mockFactorsHigh: ConfidenceFactors = {
  layout_stability: 97,
  anchor_detection: 98,
  grid_quality: 96,
  field_variability: 95,
  vision_agreement: 97,
  overall: 97,
}

const mockFactorsLow: ConfidenceFactors = {
  layout_stability: 60,
  anchor_detection: 70,
  grid_quality: 55,
  field_variability: 65,
  vision_agreement: 60,
  overall: 62,
}

describe('ConfidencePopover', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('does not render when visible=false', () => {
    const wrapper = mount(ConfidencePopover, { props: { visible: false } })
    expect(wrapper.find('[data-testid="confidence-popover"]').exists()).toBe(false)
  })

  it('renders when visible=true', () => {
    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    expect(wrapper.find('[data-testid="confidence-popover"]').exists()).toBe(true)
  })

  it('shows "Nenhum dado de confiança disponível" when no data', () => {
    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('Nenhum dado de confiança disponível')
  })

  it('renders 5 ConfidenceFactor components when data is loaded', () => {
    const confidenceStore = useConfidenceStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    confidenceStore.updateForLayout('layout-1', mockFactors)

    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    const factors = wrapper.findAll('.confidence-factor')
    expect(factors.length).toBe(5)
  })

  it('displays all 5 factor labels', () => {
    const confidenceStore = useConfidenceStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    confidenceStore.updateForLayout('layout-1', mockFactors)

    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    const text = wrapper.text()
    expect(text).toContain('Estabilidade de Layout')
    expect(text).toContain('Detecção de Âncoras')
    expect(text).toContain('Qualidade do Grid')
    expect(text).toContain('Variabilidade de Campos')
    expect(text).toContain('Concordância da Visão')
  })

  it('shows overall percentage', () => {
    const confidenceStore = useConfidenceStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    confidenceStore.updateForLayout('layout-1', mockFactors)

    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('91%')
  })

  it('shows ✅ icon for overall >= 95', () => {
    const confidenceStore = useConfidenceStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    confidenceStore.updateForLayout('layout-1', mockFactorsHigh)

    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('✅')
  })

  it('shows ⚠️ icon for overall 80-94', () => {
    const confidenceStore = useConfidenceStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    confidenceStore.updateForLayout('layout-1', mockFactors) // overall 91

    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('⚠️')
  })

  it('shows 🔴 icon for overall < 80', () => {
    const confidenceStore = useConfidenceStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    confidenceStore.updateForLayout('layout-1', mockFactorsLow)

    const wrapper = mount(ConfidencePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('🔴')
  })

  it('emits close event when useClickOutside triggers', async () => {
    const confidenceStore = useConfidenceStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    confidenceStore.updateForLayout('layout-1', mockFactors)

    const wrapper = mount(ConfidencePopover, {
      props: { visible: true },
      attachTo: document.body,
    })

    // Simulate a click outside the popover
    const outsideEl = document.createElement('div')
    document.body.appendChild(outsideEl)
    outsideEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))

    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('close')).toBeTruthy()
    outsideEl.remove()
    wrapper.unmount()
  })
})
