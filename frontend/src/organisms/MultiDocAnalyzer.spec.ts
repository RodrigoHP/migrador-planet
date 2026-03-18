import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import MultiDocAnalyzer from './MultiDocAnalyzer.vue'
import { useMultiDocStore } from '@/stores/multiDocStore'
import type { PdfDocument } from '@/types/multi-doc.types'

function makePdf(id: string, role: 'base' | 'variation' = 'base'): PdfDocument {
  return {
    id,
    name: `doc-${id}.pdf`,
    role,
    sizeKB: 50,
    pages: 1,
    uploadedAt: '2024-01-01T00:00:00Z',
  }
}

describe('MultiDocAnalyzer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ─── Collapse/expand ───────────────────────────────────────────────────────

  describe('collapse/expand', () => {
    it('renders body by default (expanded)', () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      expect(wrapper.find('.multi-doc-analyzer__body').exists()).toBe(true)
    })

    it('hides body after clicking title bar', async () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      await wrapper.find('.multi-doc-analyzer__titlebar').trigger('click')
      expect(wrapper.find('.multi-doc-analyzer__body').exists()).toBe(false)
    })

    it('shows body again after second click', async () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      const titlebar = wrapper.find('.multi-doc-analyzer__titlebar')
      await titlebar.trigger('click')
      await titlebar.trigger('click')
      expect(wrapper.find('.multi-doc-analyzer__body').exists()).toBe(true)
    })

    it('toggle button shows → when collapsed and ↓ when expanded', async () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      expect(wrapper.find('.multi-doc-analyzer__toggle-icon').text()).toBe('↓')

      await wrapper.find('.multi-doc-analyzer__titlebar').trigger('click')
      expect(wrapper.find('.multi-doc-analyzer__toggle-icon').text()).toBe('→')
    })
  })

  // ─── PDF list rendering ────────────────────────────────────────────────────

  describe('PDF list', () => {
    it('shows all PDFs with their names', () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      const text = wrapper.text()
      expect(text).toContain('doc-p1.pdf')
      expect(text).toContain('doc-p2.pdf')
    })

    it('shows base label for base PDF', () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1', 'base'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      expect(wrapper.text()).toContain('base')
    })

    it('shows variação label for variation PDF', () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1', 'base'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      expect(wrapper.text()).toContain('variação')
    })

    it('shows ✔ indicator for each PDF', () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))

      const wrapper = mount(MultiDocAnalyzer)
      const checks = wrapper.findAll('.multi-doc-analyzer__pdf-check')
      expect(checks).toHaveLength(2)
    })
  })

  // ─── PDF count badge ───────────────────────────────────────────────────────

  it('shows PDF count in title bar', () => {
    const store = useMultiDocStore()
    store.addPdf(makePdf('p1'))
    store.addPdf(makePdf('p2', 'variation'))

    const wrapper = mount(MultiDocAnalyzer)
    expect(wrapper.find('.multi-doc-analyzer__pdf-count').text()).toContain('2 PDFs')
  })

  // ─── Detection actions ────────────────────────────────────────────────────

  describe('detection actions', () => {
    it('calls confirmDetection on confirm event from DetectionCard', async () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))
      store.setDetections([
        { id: 'det-1', pdfId: 'p1', type: 'required', description: 'Required', confidence: 1.0 },
      ])

      const wrapper = mount(MultiDocAnalyzer)
      await wrapper.find('[aria-label="Confirmar inferência"]').trigger('click')
      expect(store.confirmedDetections.has('det-1')).toBe(true)
    })

    it('calls rejectDetection on reject event from DetectionCard', async () => {
      const store = useMultiDocStore()
      store.addPdf(makePdf('p1'))
      store.addPdf(makePdf('p2', 'variation'))
      store.setDetections([
        { id: 'det-1', pdfId: 'p1', type: 'required', description: 'Required', confidence: 1.0 },
      ])

      const wrapper = mount(MultiDocAnalyzer)
      await wrapper.find('[aria-label="Rejeitar inferência"]').trigger('click')
      expect(store.detections.find((d) => d.id === 'det-1')).toBeUndefined()
    })
  })

  // ─── Empty state ────────────────────────────────────────────────────────────

  it('shows empty message when no detections', () => {
    const store = useMultiDocStore()
    store.addPdf(makePdf('p1'))
    store.addPdf(makePdf('p2', 'variation'))

    const wrapper = mount(MultiDocAnalyzer)
    expect(wrapper.find('.multi-doc-analyzer__empty').exists()).toBe(true)
  })
})
