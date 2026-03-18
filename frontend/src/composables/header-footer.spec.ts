/**
 * header-footer.spec.ts — Story 9.6
 *
 * Tests for Header/Footer repetition in the Layout Engine (usePagination):
 * - buildHeaderFooterLayout: which sections appear on which pages
 * - calculateRemainingSpace: body space after header/footer
 * - Integration with calculatePageBreaks when header/footer heights are set
 */
import { describe, it, expect } from 'vitest'
import {
  buildHeaderFooterLayout,
  calculateRemainingSpace,
  calcBodyHeight,
  calculatePageBreaks,
  usePagination,
  MM_TO_PX,
  PAGE_SIZES_MM,
} from './usePagination'
import type { PageConfig, HeaderFooterSection } from './usePagination'

// ─── Fixtures ────────────────────────────────────────────────────────────────

const baseConfig: PageConfig = {
  size: 'A4',
  orientation: 'portrait',
  marginTop: 0,
  marginBottom: 0,
  marginLeft: 0,
  marginRight: 0,
  headerHeight: 0,
  footerHeight: 0,
}

const A4_HEIGHT_PX = Math.round(PAGE_SIZES_MM.A4.height * MM_TO_PX)

// ─── buildHeaderFooterLayout ─────────────────────────────────────────────────

describe('buildHeaderFooterLayout', () => {
  it('returns one layout entry per page', () => {
    const sections: HeaderFooterSection[] = []
    const layout = buildHeaderFooterLayout(sections, 3)
    expect(layout).toHaveLength(3)
    expect(layout[0]!.page).toBe(1)
    expect(layout[1]!.page).toBe(2)
    expect(layout[2]!.page).toBe(3)
  })

  it('section with repeat=true appears on all pages', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'hdr-1', role: 'header', height: 80, repeat: true },
    ]
    const layout = buildHeaderFooterLayout(sections, 3)
    expect(layout[0]!.headerIds).toContain('hdr-1')
    expect(layout[1]!.headerIds).toContain('hdr-1')
    expect(layout[2]!.headerIds).toContain('hdr-1')
  })

  it('section with repeat=false appears only on page 1', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'hdr-2', role: 'header', height: 80, repeat: false },
    ]
    const layout = buildHeaderFooterLayout(sections, 3)
    expect(layout[0]!.headerIds).toContain('hdr-2')
    expect(layout[1]!.headerIds).not.toContain('hdr-2')
    expect(layout[2]!.headerIds).not.toContain('hdr-2')
  })

  it('footer with repeat=true appears on all pages', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'ftr-1', role: 'footer', height: 60, repeat: true },
    ]
    const layout = buildHeaderFooterLayout(sections, 4)
    layout.forEach((p) => {
      expect(p.footerIds).toContain('ftr-1')
    })
  })

  it('footer with repeat=false appears only on page 1', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'ftr-2', role: 'footer', height: 60, repeat: false },
    ]
    const layout = buildHeaderFooterLayout(sections, 3)
    expect(layout[0]!.footerIds).toContain('ftr-2')
    expect(layout[1]!.footerIds).not.toContain('ftr-2')
  })

  it('mixes repeating and non-repeating sections correctly', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'hdr-repeat', role: 'header', height: 80, repeat: true },
      { id: 'hdr-once', role: 'header', height: 40, repeat: false },
      { id: 'ftr-repeat', role: 'footer', height: 60, repeat: true },
    ]
    const layout = buildHeaderFooterLayout(sections, 2)

    // Page 1: all sections
    expect(layout[0]!.headerIds).toContain('hdr-repeat')
    expect(layout[0]!.headerIds).toContain('hdr-once')
    expect(layout[0]!.footerIds).toContain('ftr-repeat')

    // Page 2: only repeating sections
    expect(layout[1]!.headerIds).toContain('hdr-repeat')
    expect(layout[1]!.headerIds).not.toContain('hdr-once')
    expect(layout[1]!.footerIds).toContain('ftr-repeat')
  })

  it('headerIds and footerIds are separate arrays', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'h1', role: 'header', height: 80, repeat: true },
      { id: 'f1', role: 'footer', height: 60, repeat: true },
    ]
    const layout = buildHeaderFooterLayout(sections, 1)
    expect(layout[0]!.headerIds).toContain('h1')
    expect(layout[0]!.headerIds).not.toContain('f1')
    expect(layout[0]!.footerIds).toContain('f1')
    expect(layout[0]!.footerIds).not.toContain('h1')
  })

  it('returns empty arrays when no sections configured', () => {
    const layout = buildHeaderFooterLayout([], 2)
    expect(layout[0]!.headerIds).toHaveLength(0)
    expect(layout[0]!.footerIds).toHaveLength(0)
    expect(layout[1]!.headerIds).toHaveLength(0)
    expect(layout[1]!.footerIds).toHaveLength(0)
  })

  it('handles single page document', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'h1', role: 'header', height: 100, repeat: true },
    ]
    const layout = buildHeaderFooterLayout(sections, 1)
    expect(layout).toHaveLength(1)
    expect(layout[0]!.headerIds).toContain('h1')
  })
})

// ─── calculateRemainingSpace ──────────────────────────────────────────────────

describe('calculateRemainingSpace', () => {
  it('returns full bodyHeight when header and footer are 0', () => {
    const body = calcBodyHeight(baseConfig)
    expect(calculateRemainingSpace(body, 0, 0)).toBe(body)
  })

  it('subtracts header height from bodyHeight', () => {
    const body = A4_HEIGHT_PX
    expect(calculateRemainingSpace(body, 100, 0)).toBe(A4_HEIGHT_PX - 100)
  })

  it('subtracts footer height from bodyHeight', () => {
    const body = A4_HEIGHT_PX
    expect(calculateRemainingSpace(body, 0, 60)).toBe(A4_HEIGHT_PX - 60)
  })

  it('subtracts both header and footer heights', () => {
    const body = A4_HEIGHT_PX
    expect(calculateRemainingSpace(body, 100, 60)).toBe(A4_HEIGHT_PX - 160)
  })

  it('returns 0 when header+footer exceed bodyHeight', () => {
    expect(calculateRemainingSpace(100, 80, 80)).toBe(0)
  })

  it('never returns negative value', () => {
    expect(calculateRemainingSpace(50, 100, 100)).toBe(0)
  })
})

// ─── Integration: header/footer heights affect page breaks ────────────────────

describe('header/footer integration with calculatePageBreaks', () => {
  it('with header and footer configured, bodyHeight is reduced correctly', () => {
    const cfg: PageConfig = {
      ...baseConfig,
      headerHeight: 100,
      footerHeight: 100,
    }
    // bodyHeight = A4_HEIGHT_PX - 200
    const bodyH = calcBodyHeight(cfg)
    expect(bodyH).toBe(A4_HEIGHT_PX - 200)
  })

  it('header/footer reduces available space, causing more page breaks', () => {
    // Without header/footer: A4 body ≈ 1122px → two 500px elements fit in 1 page
    const resultNone = calculatePageBreaks(
      [{ id: 'a', height: 500 }, { id: 'b', height: 500 }],
      baseConfig,
    )
    expect(resultNone.pageCount).toBe(1)

    // With large header/footer: body < 500px → each element needs its own page
    const cfgWithHeaders: PageConfig = {
      ...baseConfig,
      headerHeight: 400,
      footerHeight: 400,
    }
    const resultWithHeaders = calculatePageBreaks(
      [{ id: 'a', height: 500 }, { id: 'b', height: 500 }],
      cfgWithHeaders,
    )
    expect(resultWithHeaders.pageCount).toBeGreaterThan(1)
  })

  it('header/footer on 3-page document — layout has 3 entries', () => {
    const sections: HeaderFooterSection[] = [
      { id: 'hdr', role: 'header', height: 80, repeat: true },
      { id: 'ftr', role: 'footer', height: 60, repeat: true },
    ]
    const cfg: PageConfig = {
      ...baseConfig,
      headerHeight: 80,
      footerHeight: 60,
    }
    // Generate a 3-page scenario
    const bodyH = calcBodyHeight(cfg)
    const elHeight = Math.ceil(bodyH / 2) + 10 // each element bigger than half → causes breaks
    const elements = [
      { id: 'a', height: elHeight },
      { id: 'b', height: elHeight },
      { id: 'c', height: elHeight },
    ]
    const { pageCount } = calculatePageBreaks(elements, cfg)
    expect(pageCount).toBeGreaterThanOrEqual(2)

    const layout = buildHeaderFooterLayout(sections, pageCount)
    expect(layout).toHaveLength(pageCount)
    // Header and footer repeat on every page
    layout.forEach((p) => {
      expect(p.headerIds).toContain('hdr')
      expect(p.footerIds).toContain('ftr')
    })
  })
})

// ─── usePagination composable — header/footer extensions ─────────────────────

describe('usePagination — header/footer API', () => {
  it('exposes buildHeaderFooterLayout', () => {
    const { buildHeaderFooterLayout: fn } = usePagination()
    expect(typeof fn).toBe('function')
  })

  it('exposes calculateRemainingSpace', () => {
    const { calculateRemainingSpace: fn } = usePagination()
    expect(typeof fn).toBe('function')
  })

  it('exposes repositionFixedElement', () => {
    const { repositionFixedElement: fn } = usePagination()
    expect(typeof fn).toBe('function')
  })

  it('buildHeaderFooterLayout via composable works correctly', () => {
    const { buildHeaderFooterLayout: fn } = usePagination()
    const sections: HeaderFooterSection[] = [
      { id: 'h1', role: 'header', height: 80, repeat: true },
    ]
    const layout = fn(sections, 2)
    expect(layout[0]!.headerIds).toContain('h1')
    expect(layout[1]!.headerIds).toContain('h1')
  })
})
