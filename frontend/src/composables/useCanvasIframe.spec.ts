import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCanvasIframe, replaceChartsWithPlaceholders } from './useCanvasIframe'
import { useGenerationStore } from '@/stores/generation'
import { useTemplateStore } from '@/stores/templateStore'

// Mock borderStyleGenerator to avoid dependency on full templateStore
vi.mock('@/utils/borderStyleGenerator', () => ({
  generateAllBorderOverrides: () => '',
}))

// Mock useExport to isolate SVG inline logic from filesystem/fetch deps
vi.mock('@/composables/useExport', () => ({
  replaceImgWithSvgInline: vi.fn((html: string) =>
    html.replace(
      /<img[^>]*id="img-svg-1"[^>]*>/g,
      '<svg id="img-svg-1" style="width:100px"><!-- inlined --></svg>',
    ),
  ),
}))

describe('useCanvasIframe', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('returns empty pages when no template draft', () => {
    const { pages } = useCanvasIframe()
    expect(pages.value).toEqual([])
  })

  it('returns default A4 page dimensions', () => {
    const { pageWidth, pageHeight } = useCanvasIframe()
    expect(pageWidth.value).toBe(794)
    expect(pageHeight.value).toBe(1123)
  })

  it('builds srcdoc with CSS and interaction script', () => {
    const { buildPageSrcdoc } = useCanvasIframe()
    const result = buildPageSrcdoc('<div>Hello</div>', '.test { color: red; }')
    expect(result).toContain('<div>Hello</div>')
    expect(result).toContain('.test { color: red; }')
    expect(result).toContain('canvas-element-clicked')
  })

  it('parses single page when no data-layout-type found', () => {
    const gen = useGenerationStore()
    gen.loadTemplateDraft({ html: '<div>Simple content</div>', css: '' })
    const { pages } = useCanvasIframe()
    expect(pages.value.length).toBe(1)
    expect(pages.value[0].pageNum).toBe(1)
  })

  it('findPageForElement returns null when element not found', () => {
    const { findPageForElement } = useCanvasIframe()
    expect(findPageForElement('nonexistent')).toBeNull()
  })
})

// ─── Story 42.3 — SVG inline canvas sync ────────────────────────────────────

describe('buildPageSrcdoc — SVG inline sync (Story 42.3)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('passes HTML unchanged when no image nodes have svgInline', () => {
    const { buildPageSrcdoc } = useCanvasIframe()
    const html = '<div><img id="img-1" src="test.png" style="width:100px"></div>'
    const result = buildPageSrcdoc(html, '')
    expect(result).toContain('<img id="img-1"')
    expect(result).not.toContain('<!-- inlined -->')
  })

  it('replaces <img> with <svg> in srcdoc when node has svgInline: true', () => {
    const templateStore = useTemplateStore()
    // Set up a document tree with an image node that has svgInline: true
    templateStore.loadTree({
      root: {
        id: 'root',
        type: 'document',
        properties: {},
        visibility: true,
        children: [
          {
            id: 'img-svg-1',
            type: 'image',
            properties: {
              svgInline: true,
              svgInlineContent: '<svg>test</svg>',
              src: 'test.svg',
            },
            visibility: true,
            children: [],
          },
        ],
      },
    })
    const { buildPageSrcdoc } = useCanvasIframe()
    const html = '<div><img id="img-svg-1" src="test.svg" style="width:100px"></div>'
    const result = buildPageSrcdoc(html, '')
    // replaceImgWithSvgInline mock replaces the <img> with <svg>
    expect(result).toContain('<svg id="img-svg-1"')
    expect(result).toContain('<!-- inlined -->')
    expect(result).not.toContain('<img id="img-svg-1"')
  })

  it('does not apply svgInline for invisible nodes', () => {
    const templateStore = useTemplateStore()
    templateStore.loadTree({
      root: {
        id: 'root',
        type: 'document',
        properties: {},
        visibility: true,
        children: [
          {
            id: 'img-hidden',
            type: 'image',
            properties: { svgInline: true, svgInlineContent: '<svg/>', src: 'test.svg' },
            visibility: false,
            children: [],
          },
        ],
      },
    })
    const { buildPageSrcdoc } = useCanvasIframe()
    const html = '<div><img id="img-hidden" src="test.svg"></div>'
    const result = buildPageSrcdoc(html, '')
    // invisible node — img should remain unchanged
    expect(result).toContain('<img id="img-hidden"')
  })
})

// ─── Story 41.11 — replaceChartsWithPlaceholders (pure function) ────────────

describe('replaceChartsWithPlaceholders', () => {
  it('returns HTML unchanged when chartNodeIds is empty', () => {
    const html = '<div><canvas id="chart-1" style="width:200px"></canvas></div>'
    const result = replaceChartsWithPlaceholders(html, new Map())
    expect(result).toBe(html)
  })

  it('replaces matching <canvas> with <div class="chart-placeholder">', () => {
    const html = '<canvas id="chart-1" style="width:200px;height:100px"></canvas>'
    const nodes = new Map([['chart-1', 'bar']])
    const result = replaceChartsWithPlaceholders(html, nodes)
    expect(result).toContain('<div class="chart-placeholder" data-chart-type="bar"')
    expect(result).toContain('id="chart-1"')
    expect(result).not.toContain('<canvas')
  })

  it('does not replace canvas whose id is not in chartNodeIds', () => {
    const html = '<canvas id="other-canvas" style="width:50px"></canvas>'
    const nodes = new Map([['chart-1', 'pie']])
    const result = replaceChartsWithPlaceholders(html, nodes)
    expect(result).toContain('<canvas id="other-canvas"')
    expect(result).not.toContain('chart-placeholder')
  })

  it('replaces multiple chart canvases in one pass', () => {
    const html = [
      '<canvas id="chart-1" style="width:200px"></canvas>',
      '<canvas id="chart-2" style="width:300px"></canvas>',
    ].join('\n')
    const nodes = new Map([
      ['chart-1', 'bar'],
      ['chart-2', 'line'],
    ])
    const result = replaceChartsWithPlaceholders(html, nodes)
    expect(result).toContain('data-chart-type="bar"')
    expect(result).toContain('data-chart-type="line"')
    expect(result).not.toContain('<canvas')
  })

  it('preserves data-node-id attribute in the output div', () => {
    const html =
      '<canvas id="chart-1" data-node-id="chart-1" style="position:absolute;left:10px"></canvas>'
    const nodes = new Map([['chart-1', 'doughnut']])
    const result = replaceChartsWithPlaceholders(html, nodes)
    expect(result).toContain('data-node-id="chart-1"')
    expect(result).toContain('data-chart-type="doughnut"')
    expect(result).toContain('style="position:absolute;left:10px"')
  })

  it('HTML without any canvas is returned unmodified', () => {
    const html = '<div class="page"><p>No charts here</p></div>'
    const nodes = new Map([['chart-1', 'bar']])
    const result = replaceChartsWithPlaceholders(html, nodes)
    expect(result).toBe(html)
  })
})
