import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LayoutAnchor from './LayoutAnchor.vue'
import type { AnchorData } from './LayoutAnchor.vue'

const sampleAnchor: AnchorData = {
  id: 'anchor-title',
  label: 'Título Principal',
  canvasPosition: { x: 100, y: 50 },
  pdfPosition: { x: 120, y: 60 },
}

describe('LayoutAnchor', () => {
  it('renders canvas anchor marker', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    expect(wrapper.find('[data-testid="layout-anchor-canvas"]').exists()).toBe(true)
  })

  it('renders PDF anchor marker', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    expect(wrapper.find('[data-testid="layout-anchor-pdf"]').exists()).toBe(true)
  })

  it('positions canvas anchor correctly', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    const canvasAnchor = wrapper.find('[data-testid="layout-anchor-canvas"]')
    const style = canvasAnchor.attributes('style') ?? ''
    expect(style).toContain('left: 100px')
    expect(style).toContain('top: 50px')
  })

  it('positions PDF anchor correctly', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    const pdfAnchor = wrapper.find('[data-testid="layout-anchor-pdf"]')
    const style = pdfAnchor.attributes('style') ?? ''
    expect(style).toContain('left: 120px')
    expect(style).toContain('top: 60px')
  })

  it('shows label as title attribute on both anchors', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    expect(wrapper.find('[data-testid="layout-anchor-canvas"]').attributes('title')).toBe('Título Principal')
    expect(wrapper.find('[data-testid="layout-anchor-pdf"]').attributes('title')).toBe('Título Principal')
  })

  it('shows label text in tooltip', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    const tooltips = wrapper.findAll('.layout-anchor__tooltip')
    expect(tooltips.length).toBeGreaterThanOrEqual(1)
    expect(tooltips[0]!.text()).toBe('Título Principal')
  })

  it('renders dot marker elements', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    const dots = wrapper.findAll('.layout-anchor__dot')
    expect(dots.length).toBe(2) // one per panel
  })

  it('updates position when anchorData changes', async () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    await wrapper.setProps({
      anchorData: { ...sampleAnchor, canvasPosition: { x: 200, y: 300 } },
    })
    const canvasAnchor = wrapper.find('[data-testid="layout-anchor-canvas"]')
    const style = canvasAnchor.attributes('style') ?? ''
    expect(style).toContain('left: 200px')
    expect(style).toContain('top: 300px')
  })
})
