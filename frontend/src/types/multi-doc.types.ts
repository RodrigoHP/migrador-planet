// ─── Multi-Doc Store Types ────────────────────────────────────────────────

export type PdfDocumentRole = 'base' | 'variation'

export interface PdfDocument {
  id: string
  name: string
  role: PdfDocumentRole
  sizeKB: number
  pages: number
  uploadedAt: string
}

export interface VariationMatrix {
  layoutIds: string[]
  variationIds: string[]
  cells: Record<string, Record<string, boolean>>
}

export type DetectionType =
  | 'required'
  | 'optional_field'
  | 'optional_section'
  | 'conditional_section'
  | 'dynamic_table'

export interface Detection {
  id: string
  pdfId: string
  type: DetectionType
  description: string
  confidence: number
  /** binding name to apply to the templateStore node, if applicable */
  nodeBinding?: string
}

// ─── Pipeline Result (consumed by populateFromPipeline) ───────────────────

export interface PipelineResult {
  pdfs: PdfDocument[]
  matrix: VariationMatrix
  detections: Detection[]
}

// ─── Variation Row helpers ─────────────────────────────────────────────────

export interface VariationRowData {
  fieldName: string
  presencePerDoc: boolean[]
}
