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
  it('renders canvas anchor marker by default', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    expect(wrapper.find('[data-testid="layout-anchor-canvas"]').exists()).toBe(true)
  })

  it('renders PDF anchor marker when side=pdf', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor, side: 'pdf' } })
    expect(wrapper.find('[data-testid="layout-anchor-pdf"]').exists()).toBe(true)
  })

  it('positions canvas anchor correctly', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor, side: 'canvas' } })
    const anchor = wrapper.find('[data-testid="layout-anchor-canvas"]')
    const style = anchor.attributes('style') ?? ''
    expect(style).toContain('left: 100px')
    expect(style).toContain('top: 50px')
  })

  it('positions PDF anchor correctly', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor, side: 'pdf' } })
    const anchor = wrapper.find('[data-testid="layout-anchor-pdf"]')
    const style = anchor.attributes('style') ?? ''
    expect(style).toContain('left: 120px')
    expect(style).toContain('top: 60px')
  })

  it('shows label as title attribute', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    expect(wrapper.find('[data-testid="layout-anchor-canvas"]').attributes('title')).toBe(
      'Título Principal',
    )
  })

  it('shows label text in tooltip', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    const tooltip = wrapper.find('.layout-anchor__tooltip')
    expect(tooltip.exists()).toBe(true)
    expect(tooltip.text()).toBe('Título Principal')
  })

  it('renders single dot marker element', () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    const dots = wrapper.findAll('.layout-anchor__dot')
    expect(dots.length).toBe(1)
  })

  it('updates position when anchorData changes', async () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor, side: 'canvas' } })
    await wrapper.setProps({
      anchorData: { ...sampleAnchor, canvasPosition: { x: 200, y: 300 } },
    })
    const anchor = wrapper.find('[data-testid="layout-anchor-canvas"]')
    const style = anchor.attributes('style') ?? ''
    expect(style).toContain('left: 200px')
    expect(style).toContain('top: 300px')
  })

  it('emits select event on click', async () => {
    const wrapper = mount(LayoutAnchor, { props: { anchorData: sampleAnchor } })
    await wrapper.find('[data-testid="layout-anchor-canvas"]').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual(['anchor-title'])
  })
})
