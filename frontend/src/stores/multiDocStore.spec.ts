import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMultiDocStore } from './multiDocStore'
import type { PdfDocument, PipelineResult } from '@/types/multi-doc.types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makePdf(id: string, role: 'base' | 'variation' = 'base'): PdfDocument {
  return {
    id,
    name: `doc-${id}.pdf`,
    role,
    sizeKB: 100,
    pages: 2,
    uploadedAt: '2024-01-01T00:00:00Z',
  }
}

function makePipeline(pdfIds: string[]): PipelineResult {
  const pdfs = pdfIds.map((id, idx) => makePdf(id, idx === 0 ? 'base' : 'variation'))
  return {
    pdfs,
    matrix: {
      layoutIds: ['field1', 'field2', 'field3'],
      variationIds: pdfIds.slice(1),
      cells: {
        field1: { [pdfIds[0]!]: true, [pdfIds[1] ?? '']: true },
        field2: { [pdfIds[0]!]: true, [pdfIds[1] ?? '']: false },
        field3: { [pdfIds[0]!]: false, [pdfIds[1] ?? '']: false },
      },
    },
    detections: [
      {
        id: 'det-1',
        pdfId: pdfIds[0]!,
        type: 'required',
        description: 'Campo obrigatório',
        confidence: 1.0,
        nodeBinding: 'field1',
      },
      {
        id: 'det-2',
        pdfId: pdfIds[0]!,
        type: 'optional_field',
        description: 'Campo opcional',
        confidence: 0.5,
        nodeBinding: 'field2',
      },
    ],
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('multiDocStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── hasMultiplePdfs ────────────────────────────────────────────────────

  describe('hasMultiplePdfs', () => {
    it('returns false when no PDFs', () => {
      const store = useMultiDocStore()
      expect(store.hasMultiplePdfs).toBe(false)
    })

    it('returns false with only 1 PDF', () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('a'))
      expect(store.hasMultiplePdfs).toBe(false)
    })

    it('returns true with 2 or more PDFs', () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('a'))
      store.addPdf(makePdf('b', 'variation'))
      expect(store.hasMultiplePdfs).toBe(true)
    })
  })

  // ─── populateFromPipeline ───────────────────────────────────────────────

  describe('populateFromPipeline', () => {
    it('fills pdfList, variationMatrix, and detections', () => {
      const store = useMultiDocStore()
      const pipeline = makePipeline(['p1', 'p2'])

      store.populateFromPipeline(pipeline)

      expect(store.pdfList).toHaveLength(2)
      expect(store.variationMatrix).not.toBeNull()
      expect(store.detections).toHaveLength(2)
    })

    it('resets confirmedDetections on populate', () => {
      const store = useMultiDocStore()
      const pipeline = makePipeline(['p1', 'p2'])
      store.populateFromPipeline(pipeline)
      store.confirmDetection('det-1')
      expect(store.confirmedDetections.size).toBe(1)

      // Re-populate — should reset
      store.populateFromPipeline(pipeline)
      expect(store.confirmedDetections.size).toBe(0)
    })
  })

  // ─── confirmDetection ───────────────────────────────────────────────────

  describe('confirmDetection', () => {
    it('adds id to confirmedDetections', () => {
      const store = useMultiDocStore()
      store.populateFromPipeline(makePipeline(['p1', 'p2']))

      store.confirmDetection('det-1')

      expect(store.confirmedDetections.has('det-1')).toBe(true)
    })

    it('does not remove detection from list', () => {
      const store = useMultiDocStore()
      store.populateFromPipeline(makePipeline(['p1', 'p2']))

      store.confirmDetection('det-1')

      expect(store.detections).toHaveLength(2)
    })

    it('ignores unknown ids gracefully', () => {
      const store = useMultiDocStore()
      expect(() => store.confirmDetection('unknown-id')).not.toThrow()
    })
  })

  // ─── rejectDetection ────────────────────────────────────────────────────

  describe('rejectDetection', () => {
    it('removes detection from list', () => {
      const store = useMultiDocStore()
      store.populateFromPipeline(makePipeline(['p1', 'p2']))

      store.rejectDetection('det-1')

      expect(store.detections.find((d) => d.id === 'det-1')).toBeUndefined()
      expect(store.detections).toHaveLength(1)
    })

    it('removes id from confirmedDetections if previously confirmed', () => {
      const store = useMultiDocStore()
      store.populateFromPipeline(makePipeline(['p1', 'p2']))
      store.confirmDetection('det-1')

      store.rejectDetection('det-1')

      expect(store.confirmedDetections.has('det-1')).toBe(false)
    })
  })

  // ─── addDetection (Story 14.13) ─────────────────────────────────────────

  describe('addDetection', () => {
    it('appends a detection to the list', () => {
      const store = useMultiDocStore()
      expect(store.detections).toHaveLength(0)
      store.addDetection({
        id: 'vis-1',
        pdfId: '',
        type: 'optional_section',
        description: 'Seção "Header" marcada como condicional pelo operador',
        confidence: 1.0,
      })
      expect(store.detections).toHaveLength(1)
      expect(store.detections[0]!.id).toBe('vis-1')
    })
  })

  // ─── removeDetectionByLabel (Story 14.13) ──────────────────────────────

  describe('removeDetectionByLabel', () => {
    it('removes detection whose description contains the label', () => {
      const store = useMultiDocStore()
      store.addDetection({
        id: 'vis-1',
        pdfId: '',
        type: 'optional_section',
        description: 'Seção "Header" marcada como condicional pelo operador',
        confidence: 1.0,
      })
      store.addDetection({
        id: 'vis-2',
        pdfId: '',
        type: 'optional_section',
        description: 'Seção "Footer" marcada como condicional pelo operador',
        confidence: 1.0,
      })
      store.removeDetectionByLabel('Header')
      expect(store.detections).toHaveLength(1)
      expect(store.detections[0]!.id).toBe('vis-2')
    })

    it('does nothing when label not found', () => {
      const store = useMultiDocStore()
      store.addDetection({
        id: 'vis-1',
        pdfId: '',
        type: 'optional_section',
        description: 'Test',
        confidence: 1.0,
      })
      store.removeDetectionByLabel('Nonexistent')
      expect(store.detections).toHaveLength(1)
    })
  })

  // ─── analyzeVariations ──────────────────────────────────────────────────

  describe('analyzeVariations', () => {
    it('generates required detection for field present in all docs', async () => {
      const store = useMultiDocStore()
      // 2 docs: field1 present in both
      store.pdfList = [makePdf('p1'), makePdf('p2', 'variation')]
      store.variationMatrix = {
        layoutIds: ['field1'],
        variationIds: ['p2'],
        cells: { field1: { p1: true, p2: true } },
      }

      await store.analyzeVariations()

      expect(store.detections[0]?.type).toBe('required')
    })

    it('generates optional_field detection for field present in some docs', async () => {
      const store = useMultiDocStore()
      // Need at least 3 docs so "present in 2 out of 3" hits optional_field (not conditional_section)
      store.pdfList = [makePdf('p1'), makePdf('p2', 'variation'), makePdf('p3', 'variation')]
      store.variationMatrix = {
        layoutIds: ['field2'],
        variationIds: ['p2', 'p3'],
        cells: { field2: { p1: true, p2: true, p3: false } },
      }

      await store.analyzeVariations()

      expect(store.detections[0]?.type).toBe('optional_field')
    })

    it('generates conditional_section for field present in only 1 doc', async () => {
      const store = useMultiDocStore()
      store.pdfList = [makePdf('p1'), makePdf('p2', 'variation'), makePdf('p3', 'variation')]
      store.variationMatrix = {
        layoutIds: ['field3'],
        variationIds: ['p2', 'p3'],
        cells: { field3: { p1: true, p2: false, p3: false } },
      }

      await store.analyzeVariations()

      expect(store.detections[0]?.type).toBe('conditional_section')
    })

    it('returns immediately if no matrix set', async () => {
      const store = useMultiDocStore()
      store.variationMatrix = null
      await expect(store.analyzeVariations()).resolves.toBeUndefined()
    })
  })
})
