// ─── Test Data Store Types ────────────────────────────────────────────────

export interface Dataset {
  id: string
  name: string
  description?: string
  fields: Record<string, unknown>
  createdAt: string
}

export interface ValidationResult {
  datasetId: string
  passed: boolean
  errors: string[]
  warnings: string[]
  testedAt: string
}
