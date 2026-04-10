import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCanvasIframe } from './useCanvasIframe'
import { useGenerationStore } from '@/stores/generation'

// Mock borderStyleGenerator to avoid dependency on full templateStore
vi.mock('@/utils/borderStyleGenerator', () => ({
  generateAllBorderOverrides: () => '',
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
