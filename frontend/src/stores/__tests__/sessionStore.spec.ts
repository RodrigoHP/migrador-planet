import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '../session'
import { useTemplateStore } from '../templateStore'
import { useMappingStore } from '../mapping'
import { useConfidenceStore } from '../confidenceStore'
import { useCoverageStore } from '../coverageStore'
import { useLayoutStore } from '../layout'
import { useGenerationStore } from '../generation'
import type { PipelineResult } from '@/types/pipeline.types'
import type { DocumentTree } from '@/types/template.types'

const mockPipelineResult: PipelineResult = {
  document_structure: {
    root: {
      id: 'root-1',
      type: 'document',
      name: 'Document',
      children: [],
      properties: {},
      visibility: true,
    },
  } as DocumentTree,
  field_mappings: [
    { name: 'company_name', path: '$.company.name', type: 'text', status: 'mapped', isOptional: false },
    { name: 'invoice_date', path: '$.invoice.date', type: 'date', status: 'mapped', isOptional: false },
    { name: 'optional_note', path: '$.note', type: 'text', status: 'optional', isOptional: true },
  ],
  confidence_scores: {
    layout_a: {
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
      tables: { mapped: 2, total: 2 },
      images: { mapped: 1, total: 1 },
      charts: { mapped: 1, total: 1 },
      percentage: 92.9,
    },
  },
  layout_types: [
    { id: 'layout_a', name: 'Invoice Layout', pageCount: 3, docCount: 1, representativePages: [1, 2] },
  ],
  template_draft: {
    html: '<html><body>{{ company_name }}</body></html>',
    css: 'body { font-family: Inter; }',
  },
  ambiguous_fields: [],
  format_functions: [],
}

describe('sessionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with default values', () => {
    const store = useSessionStore()
    expect(store.currentStep).toBe(0)
    expect(store.jobId).toBeNull()
    expect(store.job_id).toBeNull()
    expect(store.template_name).toBeNull()
    expect(store.uploadedPdfs).toEqual([])
    expect(store.analysisCompleted).toBe(false)
  })

  it('setError updates error field', () => {
    const store = useSessionStore()
    store.setError('Something went wrong')
    expect(store.error).toBe('Something went wrong')
    store.setError(null)
    expect(store.error).toBeNull()
  })

  it('resetProcessing resets fields', () => {
    const store = useSessionStore()
    store.isProcessing = true
    store.jobId = 'job-123'
    store.analysisCompleted = true
    store.processingPct = 50
    store.resetProcessing()
    expect(store.isProcessing).toBe(false)
    expect(store.jobId).toBeNull()
    expect(store.analysisCompleted).toBe(false)
    expect(store.processingPct).toBe(0)
  })

  it('loadFromPipelineResult dispatches to templateStore', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(template.documentTree).toBeDefined()
    expect(template.flatNodes.size).toBeGreaterThan(0)
  })

  it('loadFromPipelineResult dispatches to mappingStore', async () => {
    const session = useSessionStore()
    const mapping = useMappingStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(mapping.fields).toHaveLength(3)
    expect(mapping.fields[0]?.pdfText).toBe('company_name')
  })

  it('loadFromPipelineResult dispatches to confidenceStore', async () => {
    const session = useSessionStore()
    const confidence = useConfidenceStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(confidence.confidenceByLayout.size).toBe(1)
    expect(confidence.getForLayout('layout_a')?.overall).toBe(94)
  })

  it('loadFromPipelineResult dispatches to coverageStore', async () => {
    const session = useSessionStore()
    const coverage = useCoverageStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(coverage.coverageByLayout.size).toBe(1)
    expect(coverage.getForLayout('layout_a')?.percentage).toBeCloseTo(92.9)
  })

  it('loadFromPipelineResult dispatches to layoutStore', async () => {
    const session = useSessionStore()
    const layout = useLayoutStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(layout.layoutTypes).toHaveLength(1)
    expect(layout.layoutTypes[0]?.id).toBe('layout_a')
    expect(layout.activeLayoutId).toBe('layout_a')
  })

  it('loadFromPipelineResult dispatches to generationStore', async () => {
    const session = useSessionStore()
    const generation = useGenerationStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(generation.templateDraft?.html).toContain('company_name')
    expect(generation.templateDraft?.css).toContain('Inter')
  })

  it('loadFromPipelineResult sets analysisCompleted = true', async () => {
    const session = useSessionStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(session.analysisCompleted).toBe(true)
  })

  // Story 10.3 — Bug 2: document_structure vazio não deve lançar exceção
  it('loadFromPipelineResult with document_structure: {} does not throw', async () => {
    const session = useSessionStore()
    const resultWithEmptyStructure = {
      ...mockPipelineResult,
      document_structure: {} as DocumentTree,
    }
    await expect(session.loadFromPipelineResult(resultWithEmptyStructure)).resolves.not.toThrow()
    expect(session.analysisCompleted).toBe(true)
  })

  it('loadFromPipelineResult with document_structure: {} does not populate templateStore', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()
    const resultWithEmptyStructure = {
      ...mockPipelineResult,
      document_structure: {} as DocumentTree,
    }
    await session.loadFromPipelineResult(resultWithEmptyStructure)
    expect(template.documentTree).toBeNull()
  })
})
