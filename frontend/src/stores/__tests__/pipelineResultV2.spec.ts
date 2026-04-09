import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '../session'
import { useTemplateStore } from '../templateStore'
import { useLayoutStore } from '../layout'
import { useCoverageStore } from '../coverageStore'
import { useMultiDocStore } from '../multiDocStore'
import { useConfidenceStore } from '../confidenceStore'
import type { PipelineResult } from '@/types/pipeline.types'
import type { DocumentTree, TreeNode } from '@/types/template.types'

function makeTree(id: string): DocumentTree {
  return {
    root: {
      id,
      type: 'document',
      name: 'Document',
      children: [],
      properties: {},
      visibility: true,
    } as TreeNode,
  }
}

const mockV2Result: PipelineResult = {
  document_structure: makeTree('root-a'),
  field_mappings: [
    { name: 'field1', path: '$.f1', type: 'text', status: 'mapped', isOptional: false },
  ],
  confidence_scores: {
    layout_a: {
      layout_stability: 90,
      anchor_detection: 85,
      grid_quality: 88,
      field_variability: 82,
      vision_agreement: 91,
      overall: 87,
    },
    layout_b: {
      layout_stability: 95,
      anchor_detection: 92,
      grid_quality: 97,
      field_variability: 90,
      vision_agreement: 96,
      overall: 94,
    },
  },
  coverage: {
    layout_a: {
      fields: { mapped: 9, total: 10 },
      tables: { mapped: 2, total: 4 },
      images: { mapped: 4, total: 5 },
      charts: { mapped: 0, total: 0 },
      percentage: 85,
    },
    layout_b: {
      fields: { mapped: 10, total: 10 },
      tables: { mapped: 4, total: 4 },
      images: { mapped: 5, total: 5 },
      charts: { mapped: 1, total: 1 },
      percentage: 100,
    },
  },
  layout_types: [
    { id: 'layout_a', name: 'Invoice', pageCount: 2, docCount: 1, representativePages: [1] },
    { id: 'layout_b', name: 'Receipt', pageCount: 1, docCount: 1, representativePages: [3] },
  ],
  template_draft: { html: '<div></div>', css: '' },
  ambiguous_fields: [],
  format_functions: [],
  // v2 fields
  trees_by_layout: {
    layout_a: makeTree('tree-a'),
    layout_b: makeTree('tree-b'),
  },
  validation_result: { warnings: ['W1'], errors: [] },
  intelligence: {
    layout_a: { block_classifications: { 'block-1': 'header' }, classification_quality: 0.9 },
  },
  block_classifications_confirmed: true,
  multi_doc: {
    pdfs: [
      {
        id: 'pdf1',
        name: 'doc1.pdf',
        role: 'base',
        sizeKB: 200,
        pages: 3,
        uploadedAt: '2026-01-01',
      },
      {
        id: 'pdf2',
        name: 'doc2.pdf',
        role: 'variation',
        sizeKB: 150,
        pages: 2,
        uploadedAt: '2026-01-02',
      },
    ],
    matrix: { layoutIds: ['layout_a'], variationIds: ['pdf2'], cells: {} },
    detections: [
      { id: 'det-1', pdfId: 'pdf1', type: 'required', description: 'test', confidence: 1.0 },
    ],
  },
  page_config: { width: 595, height: 842, margin_top: 20, margin_bottom: 20 },
  document_type_confidence: 0.95,
  visual_analysis: {
    layout_a: {
      regions: [{ id: 'r1', type: 'header', bbox: { x: 0, y: 0, w: 595, h: 100 } }],
      consistency_score: 0.92,
    },
  },
}

describe('PipelineResult v2 integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('parses PipelineResult v2 with all 8 new fields', () => {
    const result = mockV2Result
    expect(result.trees_by_layout).toBeDefined()
    expect(result.validation_result).toBeDefined()
    expect(result.intelligence).toBeDefined()
    expect(result.block_classifications_confirmed).toBe(true)
    expect(result.multi_doc).toBeDefined()
    expect(result.page_config).toBeDefined()
    expect(result.document_type_confidence).toBe(0.95)
    expect(result.visual_analysis).toBeDefined()
  })

  it('all layouts are pre-populated after loadFromPipelineResult (AC4)', async () => {
    const session = useSessionStore()
    const layout = useLayoutStore()
    await session.loadFromPipelineResult(mockV2Result)
    expect(layout.layoutTypes).toHaveLength(2)
    // Both layouts should have documentTree populated from trees_by_layout
    expect(layout.layoutTypes[0]?.documentTree).toBeDefined()
    expect(layout.layoutTypes[0]?.documentTree?.root.id).toBe('tree-a')
    expect(layout.layoutTypes[1]?.documentTree).toBeDefined()
    expect(layout.layoutTypes[1]?.documentTree?.root.id).toBe('tree-b')
    // Both layouts should have confidence populated
    expect(layout.layoutTypes[0]?.confidence?.overall).toBe(87)
    expect(layout.layoutTypes[1]?.confidence?.overall).toBe(94)
    // Both layouts should have coverage populated
    expect(layout.layoutTypes[0]?.coverage?.percentage).toBe(85)
    expect(layout.layoutTypes[1]?.coverage?.percentage).toBe(100)
  })

  it('layout switch uses pre-populated data without re-fetch (AC4)', async () => {
    const session = useSessionStore()
    const layout = useLayoutStore()
    const template = useTemplateStore()
    await session.loadFromPipelineResult(mockV2Result)
    // Active layout should be layout_a
    expect(layout.activeLayoutId).toBe('layout_a')
    expect(template.documentTree?.root.id).toBe('tree-a')
    // Switch to layout_b — should use pre-populated data
    layout.setActiveLayout('layout_b')
    expect(layout.activeLayoutId).toBe('layout_b')
    expect(template.documentTree?.root.id).toBe('tree-b')
  })

  it('templateStore receives trees_by_layout from active layout (AC6)', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()
    await session.loadFromPipelineResult(mockV2Result)
    // Active layout_a should load tree-a
    expect(template.documentTree?.root.id).toBe('tree-a')
  })

  it('multiDocStore is populated from pipeline result (AC5)', async () => {
    const session = useSessionStore()
    const multiDoc = useMultiDocStore()
    await session.loadFromPipelineResult(mockV2Result)
    expect(multiDoc.pdfList).toHaveLength(2)
    expect(multiDoc.variationMatrix).toBeDefined()
    expect(multiDoc.detections).toHaveLength(1)
  })

  it('coverage multidimensional data is loaded per layout (AC7)', async () => {
    const session = useSessionStore()
    const coverage = useCoverageStore()
    await session.loadFromPipelineResult(mockV2Result)
    const layoutACov = coverage.getForLayout('layout_a')
    expect(layoutACov).toBeDefined()
    expect(layoutACov?.fields.mapped).toBe(9)
    expect(layoutACov?.fields.total).toBe(10)
    expect(layoutACov?.tables.mapped).toBe(2)
    expect(layoutACov?.tables.total).toBe(4)
    expect(layoutACov?.images.mapped).toBe(4)
    expect(layoutACov?.images.total).toBe(5)
    expect(layoutACov?.percentage).toBe(85)
  })

  it('backward compatibility: v1 result without new fields loads correctly', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()
    const v1Result: PipelineResult = {
      document_structure: makeTree('root-v1'),
      field_mappings: [],
      confidence_scores: {},
      coverage: {},
      layout_types: [
        { id: 'L1', name: 'Default', pageCount: 1, docCount: 1, representativePages: [1] },
      ],
      template_draft: { html: '', css: '' },
      ambiguous_fields: [],
      format_functions: [],
      // No v2 fields
    }
    await session.loadFromPipelineResult(v1Result)
    expect(session.analysisCompleted).toBe(true)
    expect(template.documentTree?.root.id).toBe('root-v1')
  })

  it('overlay items with overlay_type are loaded correctly (AC9)', async () => {
    const session = useSessionStore()
    const coverage = useCoverageStore()
    const resultWithOverlays: PipelineResult = {
      ...mockV2Result,
      overlay_items: {
        layout_a: [
          {
            node_id: 'table-1',
            xsd_path: null,
            label: 'Table',
            value: '',
            status: 'mapped',
            page_number: 1,
            bbox_canvas: { left: 10, top: 20, width: 300, height: 200 },
            bbox_pdf: { left: 10, top: 20, width: 300, height: 200 },
            overlay_type: 'table_container',
          },
          {
            node_id: 'cell-1',
            xsd_path: null,
            label: 'Cell',
            value: 'val',
            status: 'mapped',
            page_number: 1,
            bbox_canvas: { left: 10, top: 20, width: 100, height: 30 },
            bbox_pdf: { left: 10, top: 20, width: 100, height: 30 },
            overlay_type: 'table_cell',
          },
        ],
      },
    }
    await session.loadFromPipelineResult(resultWithOverlays)
    const canvasItems = coverage.getOverlayData('layout_a', 'canvas')
    expect(canvasItems).toHaveLength(2)
    expect(canvasItems[0]?.overlay_type).toBe('table_container')
    expect(canvasItems[1]?.overlay_type).toBe('table_cell')
  })
})
