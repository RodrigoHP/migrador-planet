// ─── Pipeline Result Types ────────────────────────────────────────────────

import type { DocumentTree, TreeNode } from './template.types'
import type { CoverageData } from './coverage.types'
import type { ConfidenceFactors } from './confidence.types'
import type { PipelineResult as MultiDocPipelineResult } from './multi-doc.types'

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
  /** Real confidence score from stage4 (0-100 numeric or 'low'/'medium'/'high') */
  confidence?: number | string
  /** Backend-assigned block identifier linking to tree node */
  block_id?: string
  /** Stage5 embedded candidates for ambiguous fields */
  candidates?: Array<{ path: string; score?: number; confidence?: number }>
  /** Flag indicating this field maps to a table cell */
  is_table_cell?: boolean
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

export type OverlayType = 'field' | 'table_container' | 'table_cell'

export interface BackendOverlayItem {
  node_id: string | null
  xsd_path: string | null
  label: string
  value: string
  status: string
  page_number: number
  bbox_canvas: { left: number; top: number; width: number; height: number }
  bbox_pdf: { left: number; top: number; width: number; height: number }
  overlay_type?: OverlayType
}

// ─── Pipeline v2 New Types ─────────────────────────────────────────────────

export interface PageConfig {
  width: number
  height: number
  margin_top?: number
  margin_bottom?: number
  margin_left?: number
  margin_right?: number
}

// Story 28.2 — XSD fields that have no match in the PDF
export interface UnmappedXsdField {
  xsd_path: string
  required: boolean
  reason?: string
}

export interface ValidationResult {
  warnings?: string[]
  errors?: string[]
  type_format_mismatches?: Array<{ field: string; expected: string; actual: string }>
  // Story 28.2: XSD fields with no PDF match (surfaced from backend)
  unmapped_xsd_fields?: UnmappedXsdField[]
}

export interface LayoutIntelligence {
  block_classifications?: Record<string, string>
  classification_quality?: number
}

export interface VisualAnalysisResult {
  regions?: Array<{ id: string; type: string; bbox: { x: number; y: number; w: number; h: number } }>
  consistency_score?: number
}

/** Anchor entry connecting canvas and PDF positions for SyncView (Story 35.1) */
export interface AnchorEntry {
  id: string
  label: string
  bbox_canvas: { left: number; top: number; width: number; height: number }
  bbox_pdf: { left: number; top: number; width: number; height: number }
}

/** Re-exports multi-doc.types.PipelineResult so no cast is needed in session.ts */
export type MultiDocResult = MultiDocPipelineResult

export interface DocumentStructure {
  pages?: number[]
  layout_types?: LayoutType[]
  root?: TreeNode
  trees_by_layout?: Record<string, DocumentTree>
}

// ─── Pipeline Result ───────────────────────────────────────────────────────

export interface PipelineResult {
  document_structure: DocumentTree
  field_mappings: FieldMappingEntry[]
  confidence_scores: Record<string, ConfidenceFactors>
  coverage: Record<string, CoverageData>
  layout_types: LayoutType[]
  template_draft: { html: string; css: string }
  ambiguous_fields: AmbiguousField[]
  format_functions: FormatFunction[]
  overlay_items?: Record<string, BackendOverlayItem[]>
  document_type?: string
  // Pipeline v2 fields (optional for backward compatibility)
  trees_by_layout?: Record<string, DocumentTree>
  validation_result?: ValidationResult
  intelligence?: Record<string, LayoutIntelligence>
  block_classifications_confirmed?: boolean
  multi_doc?: MultiDocResult
  page_config?: PageConfig
  document_type_confidence?: number
  visual_analysis?: Record<string, VisualAnalysisResult>
  anchors?: Record<string, AnchorEntry[]>
}
