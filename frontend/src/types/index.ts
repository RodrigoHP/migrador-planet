// ─── Session Store Types ───────────────────────────────────────────────────

export interface ExtractionResult {
  fields: FieldMapping[]
  pdfPageCount: number
  xsdFieldCount: number
  processingTime: number
}

export interface CrossValidation {
  status: 'ok' | 'divergence' | null
  divergences: string[]
}

export interface PdfFile {
  name: string
  pages: number
  sizeKB: number
  bytes: ArrayBuffer
}

export interface XsdFile {
  name: string
  fieldCount: number
  optionalCount: number
  bytes: ArrayBuffer
}

export interface DataFile {
  name: string
  fieldCount: number
  bytes: ArrayBuffer
}

// ─── Mapping Store Types ───────────────────────────────────────────────────

export interface FieldMapping {
  id: string
  pdfText: string
  jsonPath: string
  type: 'text' | 'date' | 'currency' | 'list' | 'composite'
  confidence: 'high' | 'medium' | 'low'
  status: 'ok' | 'ambiguous' | 'not_found' | 'optional'
  candidates?: string[]
  isManual: boolean
  pageRef?: number
  boundingBox?: { x: number; y: number; width: number; height: number }
}

// ─── Generation Store Types ────────────────────────────────────────────────

export interface IASuggestion {
  id: string
  type: 'info' | 'warning' | 'improvement'
  message: string
  action?: string
}

export interface ChartjsConfig {
  id: string
  chartType: 'bar' | 'line' | 'pie' | 'doughnut'
  dataField: string
  labelField: string
  colors: string[]
  title: string
}

// ─── Project File Types ────────────────────────────────────────────────────

export interface ProjectFile {
  version: '1.0'
  savedAt: string
  currentStep: 0 | 1 | 2 | 3 | 4 | 5
  session: {
    currentStep: number
    jobId: string | null
    processingStep: string
    processingPct: number
    error: string | null
    crossValidation: CrossValidation
    extraction: ExtractionResult | null
  }
  mapping: {
    fields: FieldMapping[]
    confirmed: boolean
  }
  layout: {
    pageSize: 'A4' | 'Letter' | 'A3'
    marginTop: number
    marginBottom: number
    marginLeft: number
    marginRight: number
    baseFontFamily: string
    baseFontSize: number
    primaryColor: string
    lineHeight: number
    bibliotecasVersions: Record<string, string>
    confirmed: boolean
  }
  generation: {
    monacoEdits: { html?: string; css?: string; js?: string }
    chartConfigs: Record<string, ChartjsConfig>
  }
}
