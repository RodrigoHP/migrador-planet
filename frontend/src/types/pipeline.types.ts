// ─── Pipeline Result Types ────────────────────────────────────────────────

import type { DocumentTree } from './template.types'
import type { CoverageData } from './coverage.types'
import type { ConfidenceFactors } from './confidence.types'

export interface LayoutType {
  id: string
  name: string
  pageCount: number
  docCount: number
  representativePages: number[]
  // Rich state — populated after pipeline analysis, preserved on layout switch
  documentTree?: DocumentTree
  confidence?: ConfidenceFactors
  coverage?: CoverageData
}

export interface FieldMappingEntry {
  name: string
  path: string
  type: string
  status: 'mapped' | 'unmapped' | 'ambiguous' | 'optional'
  binding?: string
  isOptional: boolean
}

export interface AmbiguousField {
  name: string
  candidates: string[]
  confidence: number
}

export interface FormatFunction {
  id: string
  name: string
  type: string
  parameters: Record<string, unknown>
}

export interface PipelineResult {
  document_structure: DocumentTree
  field_mappings: FieldMappingEntry[]
  confidence_scores: Record<string, ConfidenceFactors>
  coverage: Record<string, CoverageData>
  layout_types: LayoutType[]
  template_draft: { html: string; css: string }
  ambiguous_fields: AmbiguousField[]
  format_functions: FormatFunction[]
}
