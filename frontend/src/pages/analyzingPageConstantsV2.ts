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
/**
 * PT-BR labels for sub-step prefixes emitted by the backend.
 * Key = numeric prefix extracted from sub_step via /^(\d+\.\d+)/ regex.
 * Backend strings are stable IDs — translation is frontend responsibility (@architect decision).
 */
export const SUB_STEP_LABELS: Record<string, string> = {
  // Stage 1 — Layout Clustering
  '1.0': 'Iniciando',
  '1.1': 'Classificação de páginas',
  '1.2': 'Extração de blocos',
  '1.3': 'Normalização',
  '1.4': 'Abstração de conteúdo',
  '1.5': 'Filtragem de regiões',
  '1.6': 'Matriz de similaridade',
  '1.7': 'Clusterização por grafo',
  '1.8': 'Verificação de consenso',
  '1.9': 'Seleção de representantes',
  '1.10': 'Qualidade dos clusters',
  '1.11': 'Verificação cruzada pHash',
  '1.12': 'Validação de representantes',
  '1.13': 'Validação LLM',
  '1.14': 'Auto-correção',
  '1.15': 'Score de confiança',
  '1.16': 'Verificação de homogeneidade',
  // Stage 2 — Deep Extraction
  '2.1': 'Extração de texto',
  '2.2': 'Reconstrução de texto',
  '2.3': 'Análise de fontes',
  '2.4': 'Extração de imagens',
  '2.5': 'Screenshot da página',
  '2.6': 'Detecção de grade',
  '2.7': 'Detecção de tabelas',
  '2.8': 'Estruturação de tabelas',
  '2.9': 'Verificação de qualidade',
  // Stage 3 — Structural Analysis
  '3.1': 'Análise multi-exemplo + visual (paralelo)',
  '3.2': 'Análise multi-exemplo + visual (concluído)',
  '3.3': 'Classificação semântica',
  '3.4': 'Construção de hierarquia',
  // Stage 4 — Field Mapping
  '4.1': 'Parsing do schema XSD',
  '4.2': 'Validação de pares',
  '4.3': 'Pré-detecção de formato + matching seção-XSD',
  '4.4': 'Matching em lote de campos',
  '4.5': 'Matching em lote de campos',
  '4.6': 'Scoring de confiança + validação de consistência',
  '4.7': 'Mapeamento de campos concluído',
  // Stage 5 — Template Generation
  '5.1': 'Gerando estrutura HTML',
  '5.2': 'Gerando CSS a partir da extração',
  '5.3': 'Calculando cobertura',
  '5.4': 'Aplicando itens de sobreposição',
  '5.5': 'Construindo matriz de variações',
  '5.6': 'Montando resultado do pipeline',
  '5.7': 'Persistindo resultado',
}

/**
 * PT-BR labels for SSE summary keys.
 * Key = snake_case metric name from backend summary payload.
 */
export const METRIC_LABELS: Record<string, string> = {
  total_stages: 'Total de estágios',
  pdf_count: 'PDFs processados',
  page_count: 'Páginas',
  total_blocks_classified: 'Blocos classificados',
  total_labels: 'Labels encontrados',
  total_dynamic: 'Campos dinâmicos',
  total_pairs: 'Pares detectados',
  trees_built: 'Árvores construídas',
  vision_api_calls: 'Chamadas Vision API',
  total_mappings: 'Mapeamentos totais',
  ambiguous_count: 'Mapeamentos ambíguos',
  confirmations: 'Confirmações necessárias',
  warnings: 'Avisos',
  errors: 'Erros',
  pages_processed: 'Páginas processadas',
  layouts_detected: 'Layouts detectados',
  fields_mapped: 'Campos mapeados',
  fields_detected: 'Campos detectados',
  blocks_classified: 'Blocos classificados',
  labels_found: 'Labels encontrados',
  dynamic_fields: 'Campos dinâmicos',
  tables_detected: 'Tabelas detectadas',
  images_extracted: 'Imagens extraídas',
  fonts_identified: 'Fontes identificadas',
  coverage: 'Cobertura',
  api_cost: 'Custo API',
  confidence: 'Confiança (%)',
  corrections: 'Correções automáticas',
  error: 'Erro',
  retries: 'Tentativas',
  blocks_extracted: 'Blocos extraídos',
  html_size_bytes: 'Tamanho do HTML (bytes)',
}

/** Taxa de conversão USD → BRL usada para exibição do custo de API. */
export const USD_TO_BRL_RATE = 5.70

export interface CompletedSummaryData {
  totalTimeSeconds: number
  apiCostEstimate?: number
  visionAiUsed?: boolean  // undefined = desconhecido (retrocompatibilidade com backend sem a feature)
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
