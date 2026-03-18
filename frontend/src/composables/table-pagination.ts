/**
 * table-pagination.ts — Story 9.5
 *
 * Logic for breaking tables across pages:
 * - splitTableRows: divide rows into chunks that fit within maxHeightPx
 * - buildTablePages: build page descriptors with header/continuation metadata
 * - calcMinRowsPerPage: validate / default the minimum rows configuration
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export interface TableRow {
  id: string
  /** height in px */
  height: number
}

export interface TablePaginationConfig {
  /** maximum total height (header + rows) for a single page segment in px */
  maxHeightPx: number
  /** minimum number of rows allowed per page segment */
  minRowsPerPage: number
  /** whether to repeat <thead> on continuation pages */
  repeatHeader: boolean
  /** height of the <thead> in px */
  headerHeightPx: number
}

export interface TablePage {
  pageNumber: number
  rows: TableRow[]
  isContinuation: boolean
  showHeader: boolean
}

// ─── calcMinRowsPerPage ───────────────────────────────────────────────────────

export function calcMinRowsPerPage(min: number | undefined): number {
  if (min === undefined || min === null) return 3
  return Math.max(1, min)
}

// ─── splitTableRows ───────────────────────────────────────────────────────────

/**
 * Split rows into chunks where each chunk fits within maxHeightPx.
 * Ensures no chunk has fewer than minRowsPerPage rows (by merging last chunk if needed).
 */
export function splitTableRows(rows: TableRow[], config: TablePaginationConfig): TableRow[][] {
  if (rows.length === 0) return []

  const { maxHeightPx, headerHeightPx } = config
  const minRows = calcMinRowsPerPage(config.minRowsPerPage)
  const availableForRows = maxHeightPx - headerHeightPx

  const chunks: TableRow[][] = []
  let currentChunk: TableRow[] = []
  let currentHeight = 0

  for (const row of rows) {
    if (
      currentHeight + row.height > availableForRows &&
      currentChunk.length >= minRows
    ) {
      chunks.push(currentChunk)
      currentChunk = [row]
      currentHeight = row.height
    } else {
      currentChunk.push(row)
      currentHeight += row.height
    }
  }

  if (currentChunk.length > 0) {
    // Merge last chunk into previous if it has fewer than minRows
    if (currentChunk.length < minRows && chunks.length > 0) {
      const prevChunk = chunks[chunks.length - 1]!
      chunks[chunks.length - 1] = [...prevChunk, ...currentChunk]
    } else {
      chunks.push(currentChunk)
    }
  }

  return chunks
}

// ─── buildTablePages ─────────────────────────────────────────────────────────

/**
 * Build page descriptors from row chunks.
 * Each descriptor includes: page number, rows, isContinuation, showHeader.
 */
export function buildTablePages(rows: TableRow[], config: TablePaginationConfig): TablePage[] {
  const chunks = splitTableRows(rows, config)
  if (chunks.length === 0) return []

  return chunks.map((chunk, index) => ({
    pageNumber: index + 1,
    rows: chunk,
    isContinuation: index > 0,
    showHeader: index === 0 || config.repeatHeader,
  }))
}
