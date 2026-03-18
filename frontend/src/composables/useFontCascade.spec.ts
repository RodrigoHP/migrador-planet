import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ─── Mock idb ─────────────────────────────────────────────────────────────────

vi.mock('idb', () => ({
  openDB: vi.fn().mockResolvedValue({
    getAll: vi.fn().mockResolvedValue([]),
    put: vi.fn().mockResolvedValue(undefined),
    delete: vi.fn().mockResolvedValue(undefined),
    createObjectStore: vi.fn(),
  }),
}))

// ─── Mock fetch ───────────────────────────────────────────────────────────────

const mockFetch = vi.fn()
global.fetch = mockFetch

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useFontCascade, normalizeFont, FONT_NORMALIZATION_MAP } from './useFontCascade'

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('useFontCascade', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockFetch.mockReset()
  })

  // ── normalizeFont ───────────────────────────────────────────────────────────

  describe('normalizeFont', () => {
    it('normalizes Helvetica → Arial', () => {
      expect(normalizeFont('Helvetica')).toBe('Arial')
    })

    it('normalizes Helvetica Neue → Arial (case-insensitive)', () => {
      expect(normalizeFont('helvetica neue')).toBe('Arial')
    })

    it('normalizes Times → Times New Roman', () => {
      expect(normalizeFont('Times')).toBe('Times New Roman')
    })

    it('normalizes Courier → Courier New', () => {
      expect(normalizeFont('Courier')).toBe('Courier New')
    })

    it('returns the font unchanged when not in map', () => {
      expect(normalizeFont('Roboto')).toBe('Roboto')
      expect(normalizeFont('Open Sans')).toBe('Open Sans')
    })

    it('handles leading/trailing whitespace', () => {
      expect(normalizeFont('  Helvetica  ')).toBe('Arial')
    })
  })

  // ── FONT_NORMALIZATION_MAP ─────────────────────────────────────────────────

  describe('FONT_NORMALIZATION_MAP', () => {
    it('contains expected keys', () => {
      expect(FONT_NORMALIZATION_MAP).toHaveProperty('helvetica')
      expect(FONT_NORMALIZATION_MAP).toHaveProperty('times')
      expect(FONT_NORMALIZATION_MAP).toHaveProperty('courier')
    })
  })

  // ── resolveFontCascade — normalization step ─────────────────────────────────

  describe('resolveFontCascade', () => {
    it('returns fallback status for Helvetica (normalization map)', async () => {
      const { resolveFontCascade } = useFontCascade()
      const result = await resolveFontCascade('Helvetica')
      expect(result.fontStatus).toBe('fallback')
      expect(result.suggestedAlternative).toBe('Arial')
    })

    it('returns fallback status for Times (normalization map)', async () => {
      const { resolveFontCascade } = useFontCascade()
      const result = await resolveFontCascade('Times')
      expect(result.fontStatus).toBe('fallback')
      expect(result.suggestedAlternative).toBe('Times New Roman')
    })

    it('returns not_found when font not in catalog and backend fails', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'))
      const { resolveFontCascade } = useFontCascade()
      const result = await resolveFontCascade('SomeUnknownFont123')
      expect(result.fontStatus).toBe('not_found')
      expect(result.suggestedAlternative).toBeNull()
    })

    it('returns fallback when backend returns suggestions', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          original: 'CustomFont',
          suggestions: [
            { name: 'Roboto', similarity: 0.9, source: 'Google Fonts' },
          ],
        }),
      })

      const { resolveFontCascade } = useFontCascade()
      const result = await resolveFontCascade('CustomFont')
      expect(result.fontStatus).toBe('fallback')
      expect(result.suggestedAlternative).toBe('Roboto')
      expect(result.suggestions).toHaveLength(1)
    })

    it('returns not_found when backend returns empty suggestions', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ original: 'CustomFont', suggestions: [] }),
      })

      const { resolveFontCascade } = useFontCascade()
      const result = await resolveFontCascade('CustomFont')
      expect(result.fontStatus).toBe('not_found')
    })

    it('returns not_found when backend response is not ok', async () => {
      mockFetch.mockResolvedValue({ ok: false })
      const { resolveFontCascade } = useFontCascade()
      const result = await resolveFontCascade('CustomFont')
      expect(result.fontStatus).toBe('not_found')
    })

    it('updates reactive fontStatus ref after call', async () => {
      mockFetch.mockRejectedValue(new Error('fail'))
      const { fontStatus, resolveFontCascade } = useFontCascade()
      await resolveFontCascade('UnknownFont99')
      expect(fontStatus.value).toBe('not_found')
    })

    it('updates reactive suggestedAlternative ref after fallback', async () => {
      const { suggestedAlternative, resolveFontCascade } = useFontCascade()
      await resolveFontCascade('Helvetica')
      expect(suggestedAlternative.value).toBe('Arial')
    })

    it('sets isLoading to false after resolution', async () => {
      mockFetch.mockRejectedValue(new Error('fail'))
      const { isLoading, resolveFontCascade } = useFontCascade()
      await resolveFontCascade('AnyFont')
      expect(isLoading.value).toBe(false)
    })
  })
})
