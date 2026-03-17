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
