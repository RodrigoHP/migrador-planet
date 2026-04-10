import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import CoverageOverlay from './CoverageOverlay.vue'
import { useCoverageStore } from '@/stores/coverageStore'
import { useLayoutStore } from '@/stores/layout'
import type { OverlayItemData } from '@/types/coverage.types'

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      get: vi.fn(() => Promise.resolve(undefined)),
      put: vi.fn(() => Promise.resolve()),
    }),
  ),
}))

const canvasItems: OverlayItemData[] = [
  {
    elementId: 'el-1',
    boundingBox: { x: 10, y: 20, w: 100, h: 50 },
    status: 'bound',
    type: 'field',
  },
  {
    elementId: 'el-2',
    boundingBox: { x: 10, y: 80, w: 100, h: 50 },
    status: 'unbound',
    type: 'field',
  },
  {
    elementId: 'el-3',
    boundingBox: { x: 10, y: 140, w: 200, h: 80 },
    status: 'table',
    type: 'table',
  },
]

const pdfItems: OverlayItemData[] = [
  {
    elementId: 'pdf-1',
    boundingBox: { x: 5, y: 5, w: 150, h: 30 },
    status: 'text_block',
    type: 'text',
  },
  {
    elementId: 'pdf-2',
    boundingBox: { x: 5, y: 45, w: 150, h: 30 },
    status: 'mapped',
    type: 'field',
  },
  {
    elementId: 'pdf-3',
    boundingBox: { x: 5, y: 85, w: 150, h: 30 },
    status: 'unmapped',
    type: 'field',
  },
]

describe('CoverageOverlay', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('does not render when visible=false', () => {
    const wrapper = mount(CoverageOverlay, {
      props: { target: 'canvas', visible: false },
    })
    expect(wrapper.find('[data-testid="coverage-overlay"]').exists()).toBe(false)
  })

  it('does not render when visible=true but no overlay data', () => {
    const wrapper = mount(CoverageOverlay, {
      props: { target: 'canvas', visible: true },
    })
    expect(wrapper.find('[data-testid="coverage-overlay"]').exists()).toBe(false)
  })

  it('renders canvas overlay items when visible=true and data loaded', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.setOverlayData('layout-1', 'canvas', canvasItems)

    const wrapper = mount(CoverageOverlay, {
      props: { target: 'canvas', visible: true },
    })
    expect(wrapper.find('[data-testid="coverage-overlay"]').exists()).toBe(true)
    const items = wrapper.findAll('.coverage-overlay__item')
    expect(items.length).toBe(3)
  })

  it('renders pdf overlay items with target=pdf', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.setOverlayData('layout-1', 'pdf', pdfItems)

    const wrapper = mount(CoverageOverlay, {
      props: { target: 'pdf', visible: true },
    })
    expect(wrapper.find('[data-testid="coverage-overlay"]').exists()).toBe(true)
    const items = wrapper.findAll('.coverage-overlay__item')
    expect(items.length).toBe(3)
  })

  it('hides overlay when visible toggles to false', async () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.setOverlayData('layout-1', 'canvas', canvasItems)

    const wrapper = mount(CoverageOverlay, {
      props: { target: 'canvas', visible: true },
    })
    expect(wrapper.find('[data-testid="coverage-overlay"]').exists()).toBe(true)

    await wrapper.setProps({ visible: false })
    expect(wrapper.find('[data-testid="coverage-overlay"]').exists()).toBe(false)
  })

  it('applies correct status class to overlay items', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.setOverlayData('layout-1', 'canvas', canvasItems)

    const wrapper = mount(CoverageOverlay, {
      props: { target: 'canvas', visible: true },
    })
    const items = wrapper.findAll('.coverage-overlay__item')
    expect(items[0]?.classes()).toContain('coverage-overlay__item--bound')
    expect(items[1]?.classes()).toContain('coverage-overlay__item--unbound')
    expect(items[2]?.classes()).toContain('coverage-overlay__item--table')
  })

  it('sets position styles based on bounding box', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.setOverlayData('layout-1', 'canvas', [
      {
        elementId: 'el-1',
        boundingBox: { x: 15, y: 25, w: 120, h: 60 },
        status: 'bound',
        type: 'field',
      },
    ])

    const wrapper = mount(CoverageOverlay, {
      props: { target: 'canvas', visible: true },
    })
    const item = wrapper.find('.coverage-overlay__item')
    const style = item.attributes('style') ?? ''
    expect(style).toContain('left: 15px')
    expect(style).toContain('top: 25px')
    expect(style).toContain('width: 120px')
    expect(style).toContain('height: 60px')
  })

  it('applies dashed border class for optional_section on canvas', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-1'
    coverageStore.setOverlayData('layout-1', 'canvas', [
      {
        elementId: 'el-opt',
        boundingBox: { x: 0, y: 0, w: 100, h: 50 },
        status: 'optional_section',
        type: 'section',
      },
    ])

    const wrapper = mount(CoverageOverlay, {
      props: { target: 'canvas', visible: true },
    })
    const item = wrapper.find('.coverage-overlay__item')
    expect(item.classes()).toContain('coverage-overlay__item--dashed')
  })

  it('loads overlay data via loadOverlayData', () => {
    const coverageStore = useCoverageStore()
    const layoutStore = useLayoutStore()
    layoutStore.activeLayoutId = 'layout-2'
    coverageStore.loadOverlayData({
      'layout-2': { canvas: canvasItems, pdf: pdfItems },
    })

    const canvasResult = coverageStore.getOverlayData('layout-2', 'canvas')
    expect(canvasResult.length).toBe(3)

    const pdfResult = coverageStore.getOverlayData('layout-2', 'pdf')
    expect(pdfResult.length).toBe(3)
  })
})
