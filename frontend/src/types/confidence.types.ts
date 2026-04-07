// ─── Confidence Store Types ───────────────────────────────────────────────

export interface ConfidenceFactors {
  layout_stability: number
  anchor_detection: number
  grid_quality: number
  field_variability: number
  vision_agreement: number
  overall: number
}

export type ConfidenceByLayout = Record<string, ConfidenceFactors>

export type ConfidenceThreshold = 'approved' | 'review' | 'human_review'

// ─── Backend Warning Types (Story 30.5) ───────────────────────────────────

export type BackendWarningCategory =
  | 'table_inconsistent'
  | 'low_confidence'
  | 'missing_binding'

export interface BackendWarning {
  id: string
  category: BackendWarningCategory
  message: string
  severity: 'warning' | 'error'
  /** Optional — when set, clicking the warning selects this node in the canvas */
  nodeId?: string
}
