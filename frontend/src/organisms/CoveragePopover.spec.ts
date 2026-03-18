import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import CoveragePopover from './CoveragePopover.vue'
import { useCoverageStore } from '@/stores/coverageStore'
import { useLayoutStore } from '@/stores/layout'
import type { CoverageData } from '@/types/coverage.types'

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

const mockCoverage: CoverageData = {
  fields: { mapped: 18, total: 20 },
  tables: { mapped: 3, total: 3 },
  images: { mapped: 2, total: 2 },
  charts: { mapped: 1, total: 2 },
  percentage: 93,
}

const mockCoverageHigh: CoverageData = {
  fields: { mapped: 20, total: 20 },
  tables: { mapped: 3, total: 3 },
  images: { mapped: 2, total: 2 },
  charts: { mapped: 2, total: 2 },
  percentage: 97,
}

const mockCoverageLow: CoverageData = {
  fields: { mapped: 5, total: 20 },
  tables: { mapped: 1, total: 3 },
  images: { mapped: 0, total: 2 },
  charts: { mapped: 0, total: 1 },
  percentage: 23,
}

describe('CoveragePopover', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('does not render when visible=false', () => {
    const wrapper = mount(CoveragePopover, { props: { visible: false } })
    expect(wrapper.find('[data-testid="coverage-popover"]').exists()).toBe(false)
  })

  it('renders when visible=true', () => {
    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    expect(wrapper.find('[data-testid="coverage-popover"]').exists()).toBe(true)
  })

  it('shows "Nenhum dado de cobertura disponível" when no data', () => {
    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('Nenhum dado de cobertura disponível')
  })

  it('renders 4 CoverageBreakdown rows when data is loaded', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverage)

    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    const rows = wrapper.findAll('.coverage-breakdown')
    expect(rows.length).toBe(4)
  })

  it('displays all 4 breakdown labels', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverage)

    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    const text = wrapper.text()
    expect(text).toContain('Campos')
    expect(text).toContain('Tabelas')
    expect(text).toContain('Imagens')
    expect(text).toContain('Gráficos')
  })

  it('shows overall percentage', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverage)

    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('93%')
  })

  it('shows ✅ icon for overall >= 95', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverageHigh)

    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('✅')
  })

  it('shows ⚠️ icon for overall 80-94', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverage) // 93%

    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('⚠️')
  })

  it('shows 🔴 icon for overall < 80', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverageLow)

    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    expect(wrapper.text()).toContain('🔴')
  })

  it('shows breakdown counts correctly', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverage)

    const wrapper = mount(CoveragePopover, { props: { visible: true } })
    const text = wrapper.text()
    expect(text).toContain('18/20')
    expect(text).toContain('3/3')
    expect(text).toContain('2/2')
    expect(text).toContain('1/2')
  })

  it('emits close event when useClickOutside triggers', async () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.updateForLayout('layout-1', mockCoverage)

    const wrapper = mount(CoveragePopover, {
      props: { visible: true },
      attachTo: document.body,
    })

    const outsideEl = document.createElement('div')
    document.body.appendChild(outsideEl)
    outsideEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))

    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('close')).toBeTruthy()
    outsideEl.remove()
    wrapper.unmount()
  })
})
