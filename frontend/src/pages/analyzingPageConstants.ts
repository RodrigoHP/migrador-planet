// Constants for AnalyzingPage — exported separately since <script setup> cannot use ES exports

export const PIPELINE_BLOCKS = [
  { id: 1, name: 'Aquisição', stages: ['Upload & Storage'] },
  { id: 2, name: 'PDF Parsing', stages: ['Extração de Texto', 'Reconstrução', 'Fontes', 'Imagens', 'Grid'] },
  { id: 3, name: 'Descoberta de Layout', stages: ['Skeleton', 'Clustering', 'Representantes', 'Fingerprint', 'Registry'] },
  { id: 4, name: 'Inteligência', stages: ['Alinhamento', 'Multi-Example', 'Estabilidade', 'Variantes', 'Normalização'] },
  { id: 5, name: 'Tabelas', stages: ['Detecção', 'Estruturação'] },
  { id: 6, name: 'Semântica + Visão', stages: ['Análise Semântica', 'Segmentação Visual', 'Interpretação', 'Self-Check'] },
  { id: 7, name: 'Mapeamento', stages: ['Field Matching', 'Detecção de Formato'] },
  { id: 8, name: 'Validação', stages: ['Confiança', 'Consistência', 'Template Draft'] },
] as const

export type PipelineBlock = typeof PIPELINE_BLOCKS[number]

export const TOTAL_STAGES = 27

/**
 * Returns the flat 0-based stage index for a given block and intra-block stage index.
 */
export function getStageIndex(block: PipelineBlock, idx: number): number {
  let offset = 0
  for (const b of PIPELINE_BLOCKS) {
    if (b.id === block.id) break
    offset += b.stages.length
  }
  return offset + idx
}
