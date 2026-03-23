/**
 * Constants for AnalyzingPage — Pipeline v2 (5 stages).
 *
 * Story 13.3: Pipeline v2 has 5 substantial stages instead of 28 granular ones.
 * Story 13.13: Expanded with PT-BR names, descriptions, sub-step descriptions,
 * and stage detail metadata for the redesigned AnalyzingPage.
 */

export interface PipelineV2StageInfo {
  stage: number
  name: string              // PT-BR display name
  nameEn: string            // English name (for SSE matching)
  description: string       // Human-readable sub-step description
  subStepPrefix: string     // e.g. "1." for sub-steps like "1.2 Fingerprint"
  pendingDesc: string       // Description while pending
}

export const PIPELINE_V2_STAGES: readonly PipelineV2StageInfo[] = [
  {
    stage: 1,
    name: 'Agrupamento de Layouts',
    nameEn: 'Layout Clustering',
    description: 'Analisando similaridades visuais entre páginas para agrupar layouts distintos',
    subStepPrefix: '1.',
    pendingDesc: 'Agrupar páginas por layout',
  },
  {
    stage: 2,
    name: 'Extração Profunda',
    nameEn: 'Deep Extraction',
    description: 'Extraindo texto, imagens, tabelas, fontes e grid de cada página',
    subStepPrefix: '2.',
    pendingDesc: 'Extrair conteúdo das páginas',
  },
  {
    stage: 3,
    name: 'Análise Estrutural',
    nameEn: 'Structural Analysis',
    description: 'Identificando o que é cada elemento na página — labels, campos dinâmicos, tabelas...',
    subStepPrefix: '3.',
    pendingDesc: 'Classificar elementos da página',
  },
  {
    stage: 4,
    name: 'Mapeamento de Campos',
    nameEn: 'Field Mapping',
    description: 'Conectando campos detectados no PDF aos nós do XSD',
    subStepPrefix: '4.',
    pendingDesc: 'Conectar campos PDF ao XSD',
  },
  {
    stage: 5,
    name: 'Geração do Template',
    nameEn: 'Template Generation',
    description: 'Montando o HTML/CSS final com posicionamento e estilos',
    subStepPrefix: '5.',
    pendingDesc: 'Montar HTML/CSS final',
  },
] as const

export type PipelineV2Stage = typeof PIPELINE_V2_STAGES[number]

export const TOTAL_V2_STAGES = 5

/**
 * Page-level state for the analyzing page.
 * Drives which top-level view is rendered.
 */
export type AnalyzingPageState =
  | 'initializing'
  | 'processing'
  | 'checkpoint'
  | 'error'
  | 'completed'

/**
 * Step circle visual state.
 */
export type StepCircleState =
  | 'done'
  | 'active'
  | 'pending'
  | 'error'
  | 'warning'

/**
 * Completed stage summary data (received from SSE or computed).
 */
export interface CompletedStageSummary {
  stage: number
  name: string
  shortSummary: string
  elapsedSeconds: number
  details: string[]
}

/**
 * Checkpoint data for human review.
 */
export interface CheckpointData {
  stage: number
  stageName: string
  message: string
  confidence?: number
  layouts?: Array<{
    id: string
    label: string
    pageCount: number
    similar?: boolean
  }>
  suggestion?: {
    text: string
    resultLayouts?: number
    resultConfidence?: number
  }
  timeoutSeconds: number
  timeoutAction: 'confirm' | 'fallback' | 'skip'
}

/**
 * Error data for service failure display.
 */
export interface ErrorData {
  stage: number
  stageName: string
  service: string
  errorMessage: string
  retriesAttempted: number
}

/**
 * Final summary metrics after pipeline completion.
 */
export interface CompletedSummaryData {
  totalTimeSeconds: number
  apiCostEstimate?: number
  layoutCount: number
  pageCount: number
  fieldsMapped?: number
  coverageTotal?: number
  coverageBreakdown?: Array<{
    label: string
    pct: number
  }>
  warnings?: string[]
}
