// ─── Coverage Store Types ─────────────────────────────────────────────────

export interface CoverageBreakdown {
  mapped: number
  total: number
}

export interface CoverageData {
  fields: CoverageBreakdown
  tables: CoverageBreakdown
  images: CoverageBreakdown
  charts: CoverageBreakdown
  percentage: number
}

export type CoverageByLayout = Record<string, CoverageData>

export type CoverageThreshold = 'complete' | 'review' | 'incomplete'
