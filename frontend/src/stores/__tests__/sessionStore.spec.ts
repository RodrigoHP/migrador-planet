import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '../session'
import { useTemplateStore } from '../templateStore'
import { useMappingStore } from '../mapping'
import { useConfidenceStore } from '../confidenceStore'
import { useCoverageStore } from '../coverageStore'
import { useLayoutStore } from '../layout'
import { useGenerationStore } from '../generation'
import { useInspectorStore } from '../inspectorStore'
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

  // Story 10.6 — Bug A: error boundaries em loadFromPipelineResult
  it('loadFromPipelineResult sets error and does not set analysisCompleted when a store throws', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()
    vi.spyOn(template, 'loadTree').mockImplementation(() => {
      throw new Error('loadTree falhou')
    })
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(session.error).toContain('templateStore')
    expect(session.error).toContain('loadTree falhou')
    expect(session.analysisCompleted).toBe(false)
  })

  it('loadFromPipelineResult sets error to null and analysisCompleted when all stores succeed', async () => {
    const session = useSessionStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(session.error).toBeNull()
    expect(session.analysisCompleted).toBe(true)
  })

  // Story 11.5 — inspectorStore initialization
  it('loadFromPipelineResult initializes inspectorStore with root node', async () => {
    const session = useSessionStore()
    const inspector = useInspectorStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    expect(inspector.selectedNode).not.toBeNull()
    expect(inspector.selectedNode?.id).toBe('root-1')
    expect(inspector.level).toBe('page')
    expect(inspector.hasSelection).toBe(true)
  })

  it('loadFromPipelineResult with empty document_structure does not initialize inspectorStore', async () => {
    const session = useSessionStore()
    const inspector = useInspectorStore()
    const resultWithEmptyStructure = {
      ...mockPipelineResult,
      document_structure: {} as DocumentTree,
    }
    await session.loadFromPipelineResult(resultWithEmptyStructure)
    expect(inspector.selectedNode).toBeNull()
  })

  // Story 14.14 — is_table_cell propagation from field_mappings to tree nodes
  it('loadFromPipelineResult propagates is_table_cell=true to matching tree nodes (AC#1)', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()

    const resultWithTableCells: PipelineResult = {
      ...mockPipelineResult,
      document_structure: {
        root: {
          id: 'root-tc',
          type: 'document',
          name: 'Doc',
          children: [
            {
              id: 'field-tc-1',
              type: 'field',
              name: 'Cell Field',
              children: [
                {
                  id: 'label-tc-1',
                  type: 'field',
                  name: 'label',
                  children: [],
                  properties: {},
                  visibility: true,
                  // block_id is added as unknown property by backend
                } as unknown as import('@/types/template.types').TreeNode & { block_id: string },
                {
                  id: 'value-tc-1',
                  type: 'field',
                  name: 'value',
                  children: [],
                  properties: {},
                  visibility: true,
                } as unknown as import('@/types/template.types').TreeNode & { block_id: string },
              ],
              properties: {},
              visibility: true,
            },
          ],
          properties: {},
          visibility: true,
        },
      } as unknown as DocumentTree,
      field_mappings: [
        {
          name: 'cell_field',
          path: '$.table.item',
          type: 'text',
          status: 'mapped',
          isOptional: false,
          // block_id and is_table_cell added as extra properties from backend
          ...(({ block_id: 'blk-cell-value', is_table_cell: true } as Record<string, unknown>)),
        },
      ],
    }

    // Manually set block_ids on nodes (simulating backend response)
    const root = resultWithTableCells.document_structure.root
    const fieldNode = root.children[0]!
    const valueChild = fieldNode.children[1]!
    ;(valueChild as unknown as Record<string, unknown>)['block_id'] = 'blk-cell-value'

    await session.loadFromPipelineResult(resultWithTableCells)

    // The field node should now have is_table_cell = true because its value child's block_id matches
    const loadedField = template.flatNodes.get('field-tc-1')
    expect(loadedField?.properties['is_table_cell']).toBe(true)
  })

  it('loadFromPipelineResult does not mark non-table-cell nodes with is_table_cell (AC#4)', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()
    await session.loadFromPipelineResult(mockPipelineResult)
    // The root document node should NOT have is_table_cell
    const root = template.flatNodes.get('root-1')
    expect(root?.properties['is_table_cell']).not.toBe(true)
  })

  it('applyTableCellFlags handles node type "cell" — already detected by isTableCell computed (AC#2)', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()

    const resultWithCellType: PipelineResult = {
      ...mockPipelineResult,
      document_structure: {
        root: {
          id: 'root-cell',
          type: 'document',
          name: 'Doc',
          children: [
            {
              id: 'table-node',
              type: 'table',
              name: 'Table',
              children: [
                {
                  id: 'cell-node-1',
                  // "cell" is the type sent by stage3 backend for table cells
                  type: 'cell' as import('@/types/template.types').TreeNode['type'],
                  name: 'Cell',
                  children: [],
                  properties: {},
                  visibility: true,
                },
              ],
              properties: {},
              visibility: true,
            },
          ],
          properties: {},
          visibility: true,
        },
      } as unknown as DocumentTree,
      field_mappings: [],
    }

    await session.loadFromPipelineResult(resultWithCellType)
    // The cell node type "cell" already triggers isTableCell computed via .includes('cell')
    // Verify the tree was loaded correctly
    const cellNode = template.flatNodes.get('cell-node-1')
    expect(cellNode).toBeDefined()
    expect((cellNode?.type as string).toLowerCase()).toContain('cell')
  })

  // Bug fix: trees_by_layout bare root node must be wrapped as {root: node}
  it('loadFromPipelineResult with bare-node trees_by_layout populates flatNodes correctly', async () => {
    setActivePinia(createPinia())
    const session = useSessionStore()
    const template = useTemplateStore()

    // Simulate real backend response: trees_by_layout values are bare root nodes (not {root: node})
    const bareRootNode = {
      id: 'root-bare-1',
      type: 'document',
      name: 'Document',
      children: [
        { id: 'value-blk-001', type: 'value', name: 'Valor', children: [], properties: {}, visibility: true },
      ],
      properties: {},
      visibility: true,
    }
    const resultWithBareTree = {
      ...mockPipelineResult,
      layout_types: [{ id: 'layout_bare', name: 'Bare Layout', pageCount: 1, docCount: 1, representativePages: [1] }],
      trees_by_layout: {
        layout_bare: bareRootNode,  // bare node, NOT {root: bareRootNode}
      },
    }
    await session.loadFromPipelineResult(resultWithBareTree as any)

    // flatNodes must be populated — if trees_by_layout wrapping was wrong, it would be empty
    expect(template.flatNodes.size).toBeGreaterThan(0)
    expect(template.flatNodes.has('root-bare-1')).toBe(true)
    expect(template.flatNodes.has('value-blk-001')).toBe(true)
  })

  // Bug fix: trees_by_layout already wrapped as {root: node} must also work
  it('loadFromPipelineResult with wrapped {root: node} trees_by_layout also populates flatNodes', async () => {
    setActivePinia(createPinia())
    const session = useSessionStore()
    const template = useTemplateStore()

    const wrappedTree = {
      root: {
        id: 'root-wrapped-1',
        type: 'document',
        name: 'Document',
        children: [],
        properties: {},
        visibility: true,
      },
    }
    const resultWithWrappedTree = {
      ...mockPipelineResult,
      layout_types: [{ id: 'layout_wrapped', name: 'Wrapped Layout', pageCount: 1, docCount: 1, representativePages: [1] }],
      trees_by_layout: {
        layout_wrapped: wrappedTree,  // already wrapped as {root: node}
      },
    }
    await session.loadFromPipelineResult(resultWithWrappedTree as any)

    expect(template.flatNodes.size).toBeGreaterThan(0)
    expect(template.flatNodes.has('root-wrapped-1')).toBe(true)
  })

  // Bug fix: unmapped_xsd_fields as string[] must be normalized to UnmappedXsdField[]
  it('loadFromPipelineResult normalizes string[] unmapped_xsd_fields to UnmappedXsdField objects', async () => {
    setActivePinia(createPinia())
    const session = useSessionStore()
    const { useMappingStore: useMappingStoreInner } = await import('../mapping')
    const mapping = useMappingStoreInner()

    const resultWithStringXsd = {
      ...mockPipelineResult,
      validation_result: {
        unmapped_xsd_fields: ['data.beneficiario.nome', 'data.pagador.cpf'],
      },
    }
    await session.loadFromPipelineResult(resultWithStringXsd as any)

    expect(mapping.xsdOnlyFields).toHaveLength(2)
    // Each item must be normalized to an object with xsd_path
    expect(mapping.xsdOnlyFields[0]).toEqual({ xsd_path: 'data.beneficiario.nome', required: false })
    expect(mapping.xsdOnlyFields[1]).toEqual({ xsd_path: 'data.pagador.cpf', required: false })
  })

  // Story 36.3 — Save includes code files, test datasets, XSD flat paths
  it('loadFromSavedProject restores code files from codeFiles field', async () => {
    const session = useSessionStore()
    const { useCodeStore } = await import('../codeStore')
    const codeStore = useCodeStore()

    const savedData = {
      version: '2.1',
      templateName: 'test-template',
      documentTree: null,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: {},
      coverage: {},
      editorState: null,
      codeFiles: {
        html: '<html><body>Custom HTML</body></html>',
        css: 'body { color: red; }',
        js: 'console.log("test");',
      },
    }
    await session.loadFromSavedProject(savedData as any)

    expect(codeStore.fileContents.html).toBe('<html><body>Custom HTML</body></html>')
    expect(codeStore.fileContents.css).toBe('body { color: red; }')
    expect(codeStore.fileContents.js).toBe('console.log("test");')
  })

  it('loadFromSavedProject restores test datasets', async () => {
    const session = useSessionStore()
    const { useTestDataStore } = await import('../testDataStore')
    const testDataStore = useTestDataStore()

    const savedData = {
      version: '2.1',
      templateName: 'test-template',
      documentTree: null,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: {},
      coverage: {},
      editorState: null,
      testDatasets: [
        { id: 'ds-1', name: 'Dataset 1', fields: { nome: 'Teste' }, rawContent: '{}', createdAt: '2026-01-01', size: 100, status: 'unvalidated' },
      ],
    }
    await session.loadFromSavedProject(savedData as any)

    expect(testDataStore.datasets).toHaveLength(1)
    expect(testDataStore.datasets[0]?.name).toBe('Dataset 1')
  })

  it('loadFromSavedProject restores XSD flat paths', async () => {
    const session = useSessionStore()
    const mapping = useMappingStore()

    const savedData = {
      version: '2.1',
      templateName: 'test-template',
      documentTree: null,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: {},
      coverage: {},
      editorState: null,
      xsdFlatPaths: ['data.nome', 'data.cpf', 'data.endereco.rua'],
    }
    await session.loadFromSavedProject(savedData as any)

    expect(mapping.flatPaths).toEqual(['data.nome', 'data.cpf', 'data.endereco.rua'])
  })

  // Story 36.5 — Auto-populate testDataStore from upload data
  it('loadFromPipelineResult populates testDataStore when example_data exists', async () => {
    const session = useSessionStore()
    const { useTestDataStore } = await import('../testDataStore')
    const testDataStore = useTestDataStore()

    const resultWithExampleData = {
      ...mockPipelineResult,
      example_data: { nome: 'Teste', cpf: '123.456.789-00' },
    }
    await session.loadFromPipelineResult(resultWithExampleData as any)

    expect(testDataStore.datasets).toHaveLength(1)
    expect(testDataStore.datasets[0]?.name).toBe('Upload inicial')
    expect(testDataStore.datasets[0]?.status).toBe('unvalidated')
    expect(testDataStore.datasets[0]?.fields).toEqual({ nome: 'Teste', cpf: '123.456.789-00' })
  })

  it('loadFromPipelineResult does not populate testDataStore when no example_data or dataFile', async () => {
    const session = useSessionStore()
    const { useTestDataStore } = await import('../testDataStore')
    const testDataStore = useTestDataStore()

    await session.loadFromPipelineResult(mockPipelineResult)

    expect(testDataStore.datasets).toHaveLength(0)
  })

  it('loadFromPipelineResult does not error when example_data is empty object', async () => {
    const session = useSessionStore()
    const { useTestDataStore } = await import('../testDataStore')
    const testDataStore = useTestDataStore()

    const resultWithEmptyData = {
      ...mockPipelineResult,
      example_data: {},
    }
    await session.loadFromPipelineResult(resultWithEmptyData as any)

    // Empty object should NOT create a dataset
    expect(testDataStore.datasets).toHaveLength(0)
    expect(session.analysisCompleted).toBe(true)
  })

  it('loadFromSavedProject works without new fields (backward compat v2.0)', async () => {
    const session = useSessionStore()

    const savedData = {
      version: '2.0',
      templateName: 'legacy',
      documentTree: null,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: {},
      coverage: {},
      editorState: null,
      // No codeFiles, testDatasets, xsdFlatPaths
    }
    await session.loadFromSavedProject(savedData as any)
    expect(session.analysisCompleted).toBe(true)
  })

  // Story 36.7 — Fix 2: Version validation on load
  it('loadFromSavedProject with unknown version logs warning but still loads', async () => {
    const session = useSessionStore()
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const savedData = {
      version: '99.0',
      templateName: 'future-template',
      documentTree: null,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: {},
      coverage: {},
      editorState: null,
    }
    await session.loadFromSavedProject(savedData as any)

    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Versao desconhecida do projeto: "99.0"'),
    )
    expect(session.analysisCompleted).toBe(true)
    expect(session.template_name).toBe('future-template')

    warnSpy.mockRestore()
  })

  it('loadFromSavedProject with known version 2.0 does not warn', async () => {
    const session = useSessionStore()
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const savedData = {
      version: '2.0',
      templateName: 'legacy',
      documentTree: null,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: {},
      coverage: {},
      editorState: null,
    }
    await session.loadFromSavedProject(savedData as any)

    expect(warnSpy).not.toHaveBeenCalled()
    expect(session.analysisCompleted).toBe(true)

    warnSpy.mockRestore()
  })

  it('loadFromSavedProject with known version 2.1 does not warn', async () => {
    const session = useSessionStore()
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const savedData = {
      version: '2.1',
      templateName: 'current',
      documentTree: null,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: {},
      coverage: {},
      editorState: null,
    }
    await session.loadFromSavedProject(savedData as any)

    expect(warnSpy).not.toHaveBeenCalled()
    expect(session.analysisCompleted).toBe(true)

    warnSpy.mockRestore()
  })

  // Story 36.7 — Fix 3: _parseDataFile no longer exposed as public action
  it('_parseDataFile is not exposed as a public Pinia action', () => {
    const session = useSessionStore()
    expect((session as any)._parseDataFile).toBeUndefined()
  })

  // Story 10.6 — Bug B: error boundary em loadFromSavedProject
  it('loadFromSavedProject throws descriptive error when a store throws', async () => {
    const session = useSessionStore()
    const template = useTemplateStore()
    vi.spyOn(template, 'loadTree').mockImplementation(() => {
      throw new Error('store corrompida')
    })
    const savedData = {
      templateName: 'test',
      documentTree: mockPipelineResult.document_structure as DocumentTree,
      fieldMappings: [],
      layoutTypes: [],
      activeLayoutId: null,
      confidence: null,
      coverage: null,
      editorState: null,
    }
    await expect(session.loadFromSavedProject(savedData as any)).rejects.toThrow('Falha ao restaurar projeto')
  })
})
