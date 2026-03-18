// ─── Test Data Store Types ────────────────────────────────────────────────

export type DatasetStatus = 'valid' | 'warning' | 'invalid' | 'unvalidated'

export interface Dataset {
  id: string
  name: string
  description?: string
  fields: Record<string, unknown>
  /** Raw JSON content as string (for Monaco editor) */
  rawContent: string
  createdAt: string
  size: number
  status: DatasetStatus
}

export interface ValidationResult {
  datasetId: string
  status: DatasetStatus
  /** Counts */
  fieldCount: number
  loopCount: number
  /** Errors: required fields missing or type incompatible */
  errors: string[]
  /** Warnings: optional fields missing */
  warnings: string[]
  testedAt: string
}

/** Minimal XSD field descriptor used for validation */
export interface XsdFieldDef {
  path: string
  type: 'string' | 'decimal' | 'date' | 'integer' | 'boolean' | 'array' | string
  required: boolean
}
