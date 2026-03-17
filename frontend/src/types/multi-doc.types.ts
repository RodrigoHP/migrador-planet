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

export interface Detection {
  id: string
  pdfId: string
  type: string
  description: string
  confidence: number
}
