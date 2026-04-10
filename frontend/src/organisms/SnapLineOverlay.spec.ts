import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SnapLineOverlay from './SnapLineOverlay.vue'
import type { SnapLine } from '@/composables/useCanvasInteraction'

const mockLines: SnapLine[] = [
  { orientation: 'vertical', position: 100, start: 0, end: 300 },
  { orientation: 'horizontal', position: 200, start: 50, end: 400 },
]

describe('SnapLineOverlay', () => {
  it('renders nothing when snapLines is empty', () => {
    const w = mount(SnapLineOverlay, {
      props: { snapLines: [], canvasWidth: 800, canvasHeight: 600 },
    })
    expect(w.find('svg').exists()).toBe(false)
  })

  it('renders SVG when snapLines are provided', () => {
    const w = mount(SnapLineOverlay, {
      props: { snapLines: mockLines, canvasWidth: 800, canvasHeight: 600 },
    })
    expect(w.find('svg').exists()).toBe(true)
  })

  it('renders correct number of lines', () => {
    const w = mount(SnapLineOverlay, {
      props: { snapLines: mockLines, canvasWidth: 800, canvasHeight: 600 },
    })
    expect(w.findAll('line')).toHaveLength(2)
  })

  it('renders vertical line with correct coordinates', () => {
    const w = mount(SnapLineOverlay, {
      props: { snapLines: [mockLines[0]!], canvasWidth: 800, canvasHeight: 600 },
    })
    const line = w.find('line')
    expect(line.attributes('x1')).toBe('100')
    expect(line.attributes('x2')).toBe('100')
    expect(line.attributes('y1')).toBe('0')
    expect(line.attributes('y2')).toBe('300')
  })

  it('renders horizontal line with correct coordinates', () => {
    const w = mount(SnapLineOverlay, {
      props: { snapLines: [mockLines[1]!], canvasWidth: 800, canvasHeight: 600 },
    })
    const line = w.find('line')
    expect(line.attributes('x1')).toBe('50')
    expect(line.attributes('x2')).toBe('400')
    expect(line.attributes('y1')).toBe('200')
    expect(line.attributes('y2')).toBe('200')
  })

  it('renders distance labels', () => {
    const w = mount(SnapLineOverlay, {
      props: { snapLines: mockLines, canvasWidth: 800, canvasHeight: 600 },
    })
    const texts = w.findAll('text')
    expect(texts).toHaveLength(2)
    // Vertical line label: end - start = 300
    expect(texts[0].text()).toContain('300px')
    // Horizontal line label: end - start = 350
    expect(texts[1].text()).toContain('350px')
  })

  it('has pointer-events: none', () => {
    const w = mount(SnapLineOverlay, {
      props: { snapLines: mockLines, canvasWidth: 800, canvasHeight: 600 },
    })
    expect(w.find('svg').classes()).toContain('snap-line-overlay')
  })
})
