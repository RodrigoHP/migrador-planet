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

// ─── Overlay Types ────────────────────────────────────────────────────────

export interface OverlayItemData {
  elementId: string
  boundingBox: { x: number; y: number; w: number; h: number }
  status: string
  type: string
}

export type OverlayTarget = 'canvas' | 'pdf'

/** Keyed by layoutId → target → list of overlay items */
export type OverlayDataByLayout = Record<string, Record<OverlayTarget, OverlayItemData[]>>
