import { describe, it, expect } from 'vitest'
import {
  usePagination,
  calculatePageBreaks,
  calcBodyHeight,
  calcRemainingSpace,
  getPageDimensionsPx,
  PAGE_SIZES_MM,
  MM_TO_PX,
} from './usePagination'
import type { PageConfig, LayoutElement } from './usePagination'

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

// A4 portrait: 297mm * 3.7795 ≈ 1122px total
const A4_HEIGHT_PX = Math.round(PAGE_SIZES_MM.A4.height * MM_TO_PX)

// ─── getPageDimensionsPx ─────────────────────────────────────────────────────

describe('getPageDimensionsPx', () => {
  it('returns correct A4 portrait dimensions', () => {
    const dims = getPageDimensionsPx(baseConfig)
    expect(dims.width).toBe(Math.round(210 * MM_TO_PX))
    expect(dims.height).toBe(Math.round(297 * MM_TO_PX))
  })

  it('swaps width and height for landscape', () => {
    const cfg: PageConfig = { ...baseConfig, orientation: 'landscape' }
    const dims = getPageDimensionsPx(cfg)
    expect(dims.width).toBe(Math.round(297 * MM_TO_PX))
    expect(dims.height).toBe(Math.round(210 * MM_TO_PX))
  })

  it('uses custom dimensions', () => {
    const cfg: PageConfig = {
      ...baseConfig,
      size: 'custom',
      customWidth: 100,
      customHeight: 200,
    }
    const dims = getPageDimensionsPx(cfg)
    expect(dims.width).toBe(Math.round(100 * MM_TO_PX))
    expect(dims.height).toBe(Math.round(200 * MM_TO_PX))
  })

  it('uses letter dimensions', () => {
    const cfg: PageConfig = { ...baseConfig, size: 'letter' }
    const dims = getPageDimensionsPx(cfg)
    expect(dims.width).toBe(Math.round(216 * MM_TO_PX))
    expect(dims.height).toBe(Math.round(279 * MM_TO_PX))
  })
})

// ─── calcBodyHeight ──────────────────────────────────────────────────────────

describe('calcBodyHeight', () => {
  it('returns full page height when no margins/header/footer', () => {
    const h = calcBodyHeight(baseConfig)
    expect(h).toBe(A4_HEIGHT_PX)
  })

  it('subtracts header and footer heights', () => {
    const cfg: PageConfig = { ...baseConfig, headerHeight: 100, footerHeight: 50 }
    const h = calcBodyHeight(cfg)
    expect(h).toBe(A4_HEIGHT_PX - 150)
  })

  it('subtracts margin top and bottom (converted from mm)', () => {
    const cfg: PageConfig = { ...baseConfig, marginTop: 10, marginBottom: 10 }
    const h = calcBodyHeight(cfg)
    // Approximate due to rounding
    expect(h).toBeCloseTo(A4_HEIGHT_PX - 20 * MM_TO_PX, 0)
  })

  it('returns 0 when margins exceed page height', () => {
    const cfg: PageConfig = { ...baseConfig, headerHeight: A4_HEIGHT_PX + 100, footerHeight: 0 }
    const h = calcBodyHeight(cfg)
    expect(h).toBe(0)
  })
})

// ─── calcRemainingSpace ──────────────────────────────────────────────────────

describe('calcRemainingSpace', () => {
  it('equals bodyHeight when no elements rendered', () => {
    const rs = calcRemainingSpace(baseConfig)
    expect(rs).toBe(calcBodyHeight(baseConfig))
  })

  it('matches calcBodyHeight result', () => {
    const cfg: PageConfig = { ...baseConfig, headerHeight: 80, footerHeight: 40 }
    expect(calcRemainingSpace(cfg)).toBe(calcBodyHeight(cfg))
  })
})

// ─── calculatePageBreaks ─────────────────────────────────────────────────────

describe('calculatePageBreaks', () => {
  it('returns no breaks when all elements fit in one page', () => {
    const elements: LayoutElement[] = [
      { id: 'a', height: 100 },
      { id: 'b', height: 200 },
    ]
    const result = calculatePageBreaks(elements, baseConfig)
    expect(result.pageBreaks).toHaveLength(0)
    expect(result.pageCount).toBe(1)
  })

  it('inserts one break when content exceeds body height', () => {
    // body height = A4_HEIGHT_PX ≈ 1122
    // two elements each 600px → second overflows
    const elements: LayoutElement[] = [
      { id: 'a', height: 600 },
      { id: 'b', height: 600 },
    ]
    const result = calculatePageBreaks(elements, baseConfig)
    expect(result.pageBreaks).toHaveLength(1)
    expect(result.pageBreaks[0]!.afterIndex).toBe(0)
    expect(result.pageBreaks[0]!.newPage).toBe(2)
    expect(result.pageCount).toBe(2)
  })

  it('inserts multiple breaks for many elements', () => {
    // Use a small page config so multiple breaks are guaranteed
    const smallPageConfig: PageConfig = {
      ...baseConfig,
      size: 'custom',
      customWidth: 100,
      customHeight: 50, // 50mm * 3.7795 ≈ 188px body
    }
    const elements: LayoutElement[] = [
      { id: 'a', height: 100 },
      { id: 'b', height: 100 },
      { id: 'c', height: 100 },
    ]
    const result = calculatePageBreaks(elements, smallPageConfig)
    expect(result.pageBreaks.length).toBeGreaterThanOrEqual(2)
    expect(result.pageCount).toBeGreaterThanOrEqual(3)
  })

  it('break label includes page number', () => {
    const elements: LayoutElement[] = [
      { id: 'a', height: 700 },
      { id: 'b', height: 700 },
    ]
    const result = calculatePageBreaks(elements, baseConfig)
    expect(result.pageBreaks[0]!.label).toContain('QUEBRA DE PÁGINA')
    expect(result.pageBreaks[0]!.label).toContain('2')
  })

  it('calculates remainingSpace after last element', () => {
    const elements: LayoutElement[] = [{ id: 'a', height: 200 }]
    const result = calculatePageBreaks(elements, baseConfig)
    expect(result.remainingSpace).toBe(A4_HEIGHT_PX - 200)
  })

  it('handles empty elements array', () => {
    const result = calculatePageBreaks([], baseConfig)
    expect(result.pageBreaks).toHaveLength(0)
    expect(result.pageCount).toBe(1)
    expect(result.remainingSpace).toBe(A4_HEIGHT_PX)
  })

  it('respects header and footer when calculating breaks', () => {
    const cfg: PageConfig = {
      ...baseConfig,
      headerHeight: 400,
      footerHeight: 400,
    }
    // bodyHeight ≈ 1122 - 800 = 322px
    // element 300px fits, element 200px causes break
    const elements: LayoutElement[] = [
      { id: 'a', height: 300 },
      { id: 'b', height: 200 },
    ]
    const result = calculatePageBreaks(elements, cfg)
    expect(result.pageBreaks).toHaveLength(1)
    expect(result.pageCount).toBe(2)
  })
})

// ─── usePagination composable ────────────────────────────────────────────────

describe('usePagination', () => {
  it('initializes with default page config', () => {
    const { pageConfig } = usePagination()
    expect(pageConfig.value.size).toBe('A4')
    expect(pageConfig.value.orientation).toBe('portrait')
  })

  it('accepts initial config override', () => {
    const { pageConfig } = usePagination({ size: 'letter', orientation: 'landscape' })
    expect(pageConfig.value.size).toBe('letter')
    expect(pageConfig.value.orientation).toBe('landscape')
  })

  it('setPageConfig merges partial config', () => {
    const { pageConfig, setPageConfig } = usePagination()
    setPageConfig({ headerHeight: 120 })
    expect(pageConfig.value.headerHeight).toBe(120)
    expect(pageConfig.value.size).toBe('A4') // other props preserved
  })

  it('setElements updates elements and recomputes pageBreaks', () => {
    const { setElements, pageBreaks, currentPageCount } = usePagination()
    setElements([
      { id: 'a', height: 700 },
      { id: 'b', height: 700 },
    ])
    expect(pageBreaks.value).toHaveLength(1)
    expect(currentPageCount.value).toBe(2)
  })

  it('addElement appends element', () => {
    const { addElement, elements } = usePagination()
    addElement({ id: 'x', height: 100 })
    expect(elements.value).toHaveLength(1)
    expect(elements.value[0]!.id).toBe('x')
  })

  it('clearElements empties the list', () => {
    const { addElement, clearElements, elements } = usePagination()
    addElement({ id: 'x', height: 100 })
    clearElements()
    expect(elements.value).toHaveLength(0)
  })

  it('remainingSpace is reactive to config changes', () => {
    const { remainingSpace, setPageConfig } = usePagination()
    const initial = remainingSpace.value
    setPageConfig({ headerHeight: 200 })
    expect(remainingSpace.value).toBeCloseTo(initial - 200, 5)
  })

  it('bodyHeight is reactive to page size change', () => {
    // Use default config with no margins/header/footer so bodyHeight = page height
    const { bodyHeight, setPageConfig } = usePagination({
      marginTop: 0,
      marginBottom: 0,
      marginLeft: 0,
      marginRight: 0,
      headerHeight: 0,
      footerHeight: 0,
    })
    const a4Height = bodyHeight.value
    setPageConfig({ size: 'letter' })
    // letter is shorter than A4, so bodyHeight should change
    expect(bodyHeight.value).not.toBe(a4Height)
    // letter height: 279mm
    const letterHeightApprox = 279 * MM_TO_PX
    expect(bodyHeight.value).toBeCloseTo(letterHeightApprox, 0)
  })

  it('pageCount updates after reconfiguring page size', () => {
    const { setElements, setPageConfig, currentPageCount } = usePagination()
    // A4: body ≈ 1122px, 2 elements of 600px → 2 pages
    setElements([
      { id: 'a', height: 600 },
      { id: 'b', height: 600 },
    ])
    expect(currentPageCount.value).toBe(2)
    // Increase header to reduce body, forcing more pages
    setPageConfig({ headerHeight: 600, footerHeight: 200 })
    // bodyHeight ≈ 1122 - 800 = 322px → each 600px element on its own page
    expect(currentPageCount.value).toBeGreaterThanOrEqual(2)
  })
})
