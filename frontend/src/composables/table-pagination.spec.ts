/**
 * table-pagination.spec.ts — Story 9.5
 *
 * Tests for table pagination logic: breaking tables across pages,
 * thead repetition, and minimum rows per page.
 */
import { describe, it, expect } from 'vitest'
import { splitTableRows, buildTablePages, calcMinRowsPerPage } from './table-pagination'
import type { TableRow, TablePaginationConfig } from './table-pagination'

// ─── Fixtures ────────────────────────────────────────────────────────────────

const makeRows = (count: number, height = 30): TableRow[] =>
  Array.from({ length: count }, (_, i) => ({ id: `row-${i}`, height }))

const baseConfig: TablePaginationConfig = {
  maxHeightPx: 300,
  minRowsPerPage: 3,
  repeatHeader: true,
  headerHeightPx: 40,
}

// ─── splitTableRows ──────────────────────────────────────────────────────────

describe('splitTableRows', () => {
  it('returns single chunk when all rows fit', () => {
    // 8 rows * 30px = 240px header 40 → total 280 < 300
    const rows = makeRows(8, 30)
    const chunks = splitTableRows(rows, baseConfig)
    expect(chunks).toHaveLength(1)
    expect(chunks[0]).toHaveLength(8)
  })

  it('splits rows when they exceed maxHeight', () => {
    // header 40 + n*30 <= 300 → n <= 8.67 → 8 rows/page
    const rows = makeRows(20, 30)
    const chunks = splitTableRows(rows, baseConfig)
    expect(chunks.length).toBeGreaterThan(1)
    // each chunk (except possibly last) should not exceed max
    for (const chunk of chunks) {
      const totalH = baseConfig.headerHeightPx + chunk.reduce((s, r) => s + r.height, 0)
      expect(totalH).toBeLessThanOrEqual(baseConfig.maxHeightPx)
    }
  })

  it('respects minRowsPerPage — no chunk has fewer rows than minimum', () => {
    // 9 rows with minRowsPerPage=3: any remainder chunk must have >= 3 rows
    const rows = makeRows(9, 30)
    const chunks = splitTableRows(rows, baseConfig)
    for (const chunk of chunks) {
      expect(chunk.length).toBeGreaterThanOrEqual(baseConfig.minRowsPerPage)
    }
  })

  it('handles exactly minRowsPerPage rows', () => {
    const rows = makeRows(3, 30)
    const chunks = splitTableRows(rows, { ...baseConfig, maxHeightPx: 200 })
    // 40 + 3*30 = 130 <= 200 → 1 chunk
    expect(chunks).toHaveLength(1)
  })

  it('handles empty rows array', () => {
    const chunks = splitTableRows([], baseConfig)
    expect(chunks).toHaveLength(0)
  })
})

// ─── buildTablePages ─────────────────────────────────────────────────────────

describe('buildTablePages', () => {
  it('returns pages with correct page numbers', () => {
    const rows = makeRows(20, 30)
    const pages = buildTablePages(rows, baseConfig)
    expect(pages[0]!.pageNumber).toBe(1)
    pages.forEach((p, i) => expect(p.pageNumber).toBe(i + 1))
  })

  it('marks first page as not continuation', () => {
    const rows = makeRows(20, 30)
    const pages = buildTablePages(rows, baseConfig)
    expect(pages[0]!.isContinuation).toBe(false)
  })

  it('marks subsequent pages as continuation', () => {
    const rows = makeRows(20, 30)
    const pages = buildTablePages(rows, baseConfig)
    if (pages.length > 1) {
      for (let i = 1; i < pages.length; i++) {
        expect(pages[i]!.isContinuation).toBe(true)
      }
    }
  })

  it('sets repeatHeader flag from config', () => {
    const rows = makeRows(20, 30)
    const pages = buildTablePages(rows, { ...baseConfig, repeatHeader: true })
    if (pages.length > 1) {
      expect(pages[1]!.showHeader).toBe(true)
    }
  })

  it('does not repeat header when repeatHeader=false', () => {
    const rows = makeRows(20, 30)
    const pages = buildTablePages(rows, { ...baseConfig, repeatHeader: false })
    if (pages.length > 1) {
      expect(pages[1]!.showHeader).toBe(false)
    }
  })

  it('first page always shows header', () => {
    const rows = makeRows(5, 30)
    const pages = buildTablePages(rows, { ...baseConfig, repeatHeader: false })
    expect(pages[0]!.showHeader).toBe(true)
  })
})

// ─── calcMinRowsPerPage ──────────────────────────────────────────────────────

describe('calcMinRowsPerPage', () => {
  it('returns configured minRowsPerPage', () => {
    expect(calcMinRowsPerPage(3)).toBe(3)
    expect(calcMinRowsPerPage(5)).toBe(5)
  })

  it('falls back to default 3 when not specified', () => {
    expect(calcMinRowsPerPage(undefined)).toBe(3)
  })

  it('clamps to at least 1', () => {
    expect(calcMinRowsPerPage(0)).toBe(1)
    expect(calcMinRowsPerPage(-5)).toBe(1)
  })
})
