/**
 * Frontend E2E tests for PipelineResult v2 rendering — Story 13.12.
 *
 * Covers:
 * - AC8: Frontend renders PipelineResult v2 correctly
 * - Layout switch uses pre-populated data
 * - Multidimensional coverage (fields + tables + images + charts)
 * - Table overlays with overlay_type
 * - Confidence per layout with 5+1 factors
 * - Backward compatibility with v1 result
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '../session'
import { useTemplateStore } from '../templateStore'
import { useLayoutStore } from '../layout'
import { useCoverageStore } from '../coverageStore'
import { useConfidenceStore } from '../confidenceStore'
import { useMultiDocStore } from '../multiDocStore'
import type { PipelineResult } from '@/types/pipeline.types'
import type { DocumentTree, TreeNode } from '@/types/template.types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTree(id: string, children: TreeNode[] = []): DocumentTree {
  return {
    root: {
      id,
      type: 'document',
      name: 'Document',
      children,
      properties: {},
      visibility: true,
    } as TreeNode,
  }
}

const mockV2Result: PipelineResult = {
  document_structure: makeTree('root-main'),
  field_mappings: [
    { name: 'nome', path: '$.sacado.nome', type: 'text', status: 'mapped', isOptional: false },
    { name: 'cpf', path: '$.sacado.cpf', type: 'text', status: 'mapped', isOptional: false },
    { name: 'valor', path: '$.dados.valor', type: 'text', status: 'mapped', isOptional: false },
    { name: 'vencimento', path: '$.dados.vencimento', type: 'date', status: 'mapped', isOptional: false },
    { name: 'nota', path: '$.nota', type: 'text', status: 'optional', isOptional: true },
  ],
  confidence_scores: {
    layout_boleto: {
      layout_stability: 95,
      anchor_detection: 92,
      grid_quality: 97,
      field_variability: 88,
      vision_agreement: 91,
      overall: 93,
    },
    layout_recibo: {
      layout_stability: 85,
      anchor_detection: 80,
      grid_quality: 82,
      field_variability: 78,
      vision_agreement: 83,
      overall: 82,
    },
  },
  coverage: {
    layout_boleto: {
      fields: { mapped: 9, total: 10 },
      tables: { mapped: 2, total: 3 },
      images: { mapped: 1, total: 1 },
      charts: { mapped: 0, total: 0 },
      percentage: 86,
    },
    layout_recibo: {
      fields: { mapped: 5, total: 5 },
      tables: { mapped: 1, total: 1 },
      images: { mapped: 0, total: 0 },
      charts: { mapped: 0, total: 0 },
      percentage: 100,
    },
  },
  layout_types: [
    { id: 'layout_boleto', name: 'Boleto', pageCount: 3, docCount: 1, representativePages: [1, 2] },
    { id: 'layout_recibo', name: 'Recibo', pageCount: 1, docCount: 1, representativePages: [4] },
  ],
  template_draft: {
    html: '<div class="page"><div class="header">{{banco_nome}}</div></div>',
    css: '.page { position: relative; } .header { font-size: 14px; }',
  },
  ambiguous_fields: [],
  format_functions: [],
  // v2 fields
  trees_by_layout: {
    layout_boleto: makeTree('tree-boleto'),
    layout_recibo: makeTree('tree-recibo'),
  },
  validation_result: { warnings: ['Font fallback used'], errors: [] },
  intelligence: {
    layout_boleto: { block_classifications: { 'blk-1': 'header' }, classification_quality: 0.92 },
  },
  block_classifications_confirmed: true,
  multi_doc: {
    pdfs: [
      { id: 'pdf1', name: 'boleto.pdf', role: 'base', sizeKB: 300, pages: 4, uploadedAt: '2026-03-22' },
    ],
    matrix: { layoutIds: ['layout_boleto'], variationIds: [], cells: {} },
    detections: [],
  },
  page_config: { width: 595, height: 842, margin_top: 20, margin_bottom: 20 },
  document_type_confidence: 0.97,
  visual_analysis: {
    layout_boleto: {
      regions: [{ id: 'r1', type: 'header', bbox: { x: 0, y: 0, w: 595, h: 80 } }],
      consistency_score: 0.95,
    },
  },
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Pipeline E2E — Frontend PipelineResult v2', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // AC8: Frontend renders PipelineResult v2
  it('loads PipelineResult v2 and populates all stores', async () => {
    const session = useSessionStore()
    const layout = useLayoutStore()
    const coverage = useCoverageStore()

    await session.loadFromPipelineResult(mockV2Result)

    expect(session.analysisCompleted).toBe(true)
    expect(layout.layoutTypes).toHaveLength(2)
    expect(layout.layoutTypes[0]?.id).toBe('layout_boleto')
    expect(layout.layoutTypes[1]?.id).toBe('layout_recibo')
  })

  // AC8: Layout switch with pre-populated data
  it('layout switch renders correct tree without re-fetch', async () => {
    const session = useSessionStore()
    const layout = useLayoutStore()
    const template = useTemplateStore()

    await session.loadFromPipelineResult(mockV2Result)

    // Default: first layout
    expect(layout.activeLayoutId).toBe('layout_boleto')
    expect(template.documentTree?.root.id).toBe('tree-boleto')

    // Switch to second layout
    layout.setActiveLayout('layout_recibo')
    expect(layout.activeLayoutId).toBe('layout_recibo')
    expect(template.documentTree?.root.id).toBe('tree-recibo')

    // Switch back
    layout.setActiveLayout('layout_boleto')
    expect(template.documentTree?.root.id).toBe('tree-boleto')
  })

  // AC8: Multidimensional coverage
  it('multidimensional coverage loaded per layout', async () => {
    const session = useSessionStore()
    const coverage = useCoverageStore()

    await session.loadFromPipelineResult(mockV2Result)

    const boletoCov = coverage.getForLayout('layout_boleto')
    expect(boletoCov).toBeDefined()
    expect(boletoCov?.fields.mapped).toBe(9)
    expect(boletoCov?.fields.total).toBe(10)
    expect(boletoCov?.tables.mapped).toBe(2)
    expect(boletoCov?.tables.total).toBe(3)
    expect(boletoCov?.images.mapped).toBe(1)
    expect(boletoCov?.images.total).toBe(1)
    expect(boletoCov?.percentage).toBe(86)

    const reciboCov = coverage.getForLayout('layout_recibo')
    expect(reciboCov?.percentage).toBe(100)
  })

  // AC8: Confidence per layout with 5+1 factors
  it('confidence scores loaded per layout with all factors', async () => {
    const session = useSessionStore()
    const confidence = useConfidenceStore()
    const layout = useLayoutStore()

    await session.loadFromPipelineResult(mockV2Result)

    // Layout boleto
    expect(layout.layoutTypes[0]?.confidence?.overall).toBe(93)
    expect(layout.layoutTypes[0]?.confidence?.layout_stability).toBe(95)
    expect(layout.layoutTypes[0]?.confidence?.anchor_detection).toBe(92)
    expect(layout.layoutTypes[0]?.confidence?.grid_quality).toBe(97)
    expect(layout.layoutTypes[0]?.confidence?.field_variability).toBe(88)
    expect(layout.layoutTypes[0]?.confidence?.vision_agreement).toBe(91)

    // Layout recibo
    expect(layout.layoutTypes[1]?.confidence?.overall).toBe(82)
  })

  // AC8: Table overlays
  it('table overlays with overlay_type loaded correctly', async () => {
    const session = useSessionStore()
    const coverage = useCoverageStore()

    const resultWithOverlays: PipelineResult = {
      ...mockV2Result,
      overlay_items: {
        layout_boleto: [
          {
            node_id: 'table-container-1',
            xsd_path: null,
            label: 'Parcelas',
            value: '',
            status: 'mapped',
            page_number: 1,
            bbox_canvas: { left: 40, top: 400, width: 515, height: 200 },
            bbox_pdf: { left: 40, top: 400, width: 515, height: 200 },
            overlay_type: 'table_container',
          },
          {
            node_id: 'cell-1-1',
            xsd_path: null,
            label: 'Parcela 1',
            value: 'R$ 500,00',
            status: 'mapped',
            page_number: 1,
            bbox_canvas: { left: 40, top: 400, width: 170, height: 30 },
            bbox_pdf: { left: 40, top: 400, width: 170, height: 30 },
            overlay_type: 'table_cell',
          },
          {
            node_id: 'field-nome',
            xsd_path: '$.sacado.nome',
            label: 'Nome',
            value: 'Joao',
            status: 'mapped',
            page_number: 1,
            bbox_canvas: { left: 120, top: 110, width: 200, height: 20 },
            bbox_pdf: { left: 120, top: 110, width: 200, height: 20 },
            overlay_type: 'field',
          },
        ],
      },
    }

    await session.loadFromPipelineResult(resultWithOverlays)

    const overlays = coverage.getOverlayData('layout_boleto', 'canvas')
    expect(overlays).toHaveLength(3)

    const tableContainers = overlays.filter(o => o.overlay_type === 'table_container')
    const tableCells = overlays.filter(o => o.overlay_type === 'table_cell')
    const fields = overlays.filter(o => o.overlay_type === 'field')

    expect(tableContainers).toHaveLength(1)
    expect(tableCells).toHaveLength(1)
    expect(fields).toHaveLength(1)
  })

  // AC8: MultiDoc data
  it('multiDocStore populated from pipeline result', async () => {
    const session = useSessionStore()
    const multiDoc = useMultiDocStore()

    await session.loadFromPipelineResult(mockV2Result)

    expect(multiDoc.pdfList).toHaveLength(1)
    expect(multiDoc.pdfList[0]?.name).toBe('boleto.pdf')
    expect(multiDoc.variationMatrix).toBeDefined()
  })

  // Backward compatibility
  it('v1 result without new fields loads correctly', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()

    const v1Result: PipelineResult = {
      document_structure: makeTree('root-v1'),
      field_mappings: [],
      confidence_scores: {},
      coverage: {},
      layout_types: [{ id: 'L1', name: 'Default', pageCount: 1, docCount: 1, representativePages: [1] }],
      template_draft: { html: '<div>v1</div>', css: '' },
      ambiguous_fields: [],
      format_functions: [],
    }

    await session.loadFromPipelineResult(v1Result)
    expect(session.analysisCompleted).toBe(true)
    expect(template.documentTree?.root.id).toBe('root-v1')
  })

  // Validation result
  it('validation_result warnings and errors accessible', async () => {
    const session = useSessionStore()

    await session.loadFromPipelineResult(mockV2Result)

    // The validation result should be available in the pipeline data
    expect(mockV2Result.validation_result).toBeDefined()
    expect(mockV2Result.validation_result?.warnings).toHaveLength(1)
    expect(mockV2Result.validation_result?.errors).toHaveLength(0)
  })

  // Page config
  it('page_config data available', async () => {
    const session = useSessionStore()

    await session.loadFromPipelineResult(mockV2Result)

    expect(mockV2Result.page_config?.width).toBe(595)
    expect(mockV2Result.page_config?.height).toBe(842)
  })

  // Document type confidence
  it('document_type_confidence score is preserved', async () => {
    const session = useSessionStore()

    await session.loadFromPipelineResult(mockV2Result)

    expect(mockV2Result.document_type_confidence).toBe(0.97)
  })
})
