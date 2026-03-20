/**
 * Tests for usePdfRenderer composable (Story 10.20 — concern #2).
 *
 * Key assertion: loadPdf() must pass a Uint8Array to pdfjs-dist when given an
 * ArrayBuffer. pdfjs-dist v5.x transfers raw ArrayBuffers to the Web Worker,
 * detaching them on the sender side. Passing Uint8Array avoids the
 * "Cannot perform Construct on a detached ArrayBuffer" error.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// ─── Mocks ────────────────────────────────────────────────────────────────────

const mockDestroy = vi.fn().mockResolvedValue(undefined)
const mockGetDocument = vi.fn()

vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: mockGetDocument,
}))

vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({ default: 'worker.js' }))

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeMockDoc(numPages = 3) {
  return { numPages, destroy: mockDestroy }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('usePdfRenderer', () => {
  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    mockGetDocument.mockReset()
    mockDestroy.mockReset()
  })

  // ── Uint8Array fix (core of Story 10.20 concern #2) ──────────────────────

  it('passes { data: Uint8Array } to pdfjs when given an ArrayBuffer', async () => {
    const capturedArg: unknown[] = []
    mockGetDocument.mockImplementation((arg: unknown) => {
      capturedArg.push(arg)
      return { promise: Promise.resolve(makeMockDoc()) }
    })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf } = usePdfRenderer()

    const buffer = new ArrayBuffer(8)
    await loadPdf(buffer)

    expect(mockGetDocument).toHaveBeenCalledOnce()
    const arg = capturedArg[0] as { data: unknown }
    expect(arg).toHaveProperty('data')
    // Must be Uint8Array, NOT raw ArrayBuffer — raw buffers are transferred
    // (detached) by pdfjs v5.x Web Worker postMessage, causing errors on reuse.
    expect(arg.data).toBeInstanceOf(Uint8Array)
  })

  it('passes string URL directly to pdfjs (not wrapped)', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.resolve(makeMockDoc()) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf } = usePdfRenderer()

    await loadPdf('https://example.com/test.pdf')

    expect(mockGetDocument).toHaveBeenCalledWith('https://example.com/test.pdf')
  })

  // ── State management ─────────────────────────────────────────────────────

  it('sets totalPages after successful load', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.resolve(makeMockDoc(5)) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf, totalPages } = usePdfRenderer()

    await loadPdf(new ArrayBuffer(8))

    expect(totalPages.value).toBe(5)
  })

  it('resets currentPage to 1 after loading a new document', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.resolve(makeMockDoc(3)) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf, currentPage, goToPage } = usePdfRenderer()

    await loadPdf(new ArrayBuffer(8))
    goToPage(3)
    expect(currentPage.value).toBe(3)

    await loadPdf(new ArrayBuffer(8))
    expect(currentPage.value).toBe(1)
  })

  it('sets isLoading to false after load completes', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.resolve(makeMockDoc()) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf, isLoading } = usePdfRenderer()

    await loadPdf(new ArrayBuffer(8))

    expect(isLoading.value).toBe(false)
  })

  it('sets error when getDocument rejects', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.reject(new Error('bad pdf')) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf, error } = usePdfRenderer()

    await loadPdf(new ArrayBuffer(8))

    expect(error.value).toBe('bad pdf')
  })

  // ── Navigation helpers ───────────────────────────────────────────────────

  it('nextPage increments currentPage within bounds', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.resolve(makeMockDoc(3)) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf, currentPage, nextPage } = usePdfRenderer()

    await loadPdf(new ArrayBuffer(8))
    nextPage()
    expect(currentPage.value).toBe(2)
    nextPage()
    expect(currentPage.value).toBe(3)
    nextPage() // at max — should not go past totalPages
    expect(currentPage.value).toBe(3)
  })

  it('prevPage decrements currentPage but not below 1', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.resolve(makeMockDoc(3)) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf, currentPage, goToPage, prevPage } = usePdfRenderer()

    await loadPdf(new ArrayBuffer(8))
    goToPage(2)
    prevPage()
    expect(currentPage.value).toBe(1)
    prevPage() // at min — should not go below 1
    expect(currentPage.value).toBe(1)
  })

  it('goToPage clamps to [1, totalPages]', async () => {
    mockGetDocument.mockReturnValue({ promise: Promise.resolve(makeMockDoc(5)) })

    const { usePdfRenderer } = await import('./usePdfRenderer')
    const { loadPdf, currentPage, goToPage } = usePdfRenderer()

    await loadPdf(new ArrayBuffer(8))

    goToPage(0)
    expect(currentPage.value).toBe(1)

    goToPage(100)
    expect(currentPage.value).toBe(5)

    goToPage(3)
    expect(currentPage.value).toBe(3)
  })
})
