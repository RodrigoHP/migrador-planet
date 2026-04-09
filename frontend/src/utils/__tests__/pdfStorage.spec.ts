/**
 * Tests for pdfStorage.ts — IndexedDB helpers for PDF bytes persistence.
 * Story 12.10 AC4: edge cases covered.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// In-memory store mock for IndexedDB
const _store: Map<string, unknown> = new Map()

vi.mock('idb', () => ({
  openDB: vi.fn(() =>
    Promise.resolve({
      put: vi.fn((storeName: string, value: unknown, key: string) => {
        _store.set(key, value)
        return Promise.resolve()
      }),
      get: vi.fn((storeName: string, key: string) => {
        return Promise.resolve(_store.get(key) ?? undefined)
      }),
      transaction: vi.fn((storeName: string, mode: string) => {
        const tx = {
          objectStore: vi.fn(() => ({
            getAllKeys: vi.fn(() => Promise.resolve([..._store.keys()])),
            delete: vi.fn((key: string) => {
              _store.delete(key)
              return Promise.resolve()
            }),
          })),
          done: Promise.resolve(),
        }
        return tx
      }),
    }),
  ),
}))

import { savePdfBytes, loadPdfBytes, clearPdfBytes } from '../pdfStorage'

describe('pdfStorage', () => {
  beforeEach(() => {
    _store.clear()
  })

  describe('savePdfBytes', () => {
    it('stores bytes under jobId-index key', async () => {
      const bytes = new Uint8Array([1, 2, 3])
      await savePdfBytes('job-1', 0, bytes)
      expect(_store.get('job-1-0')).toEqual(bytes)
    })

    it('stores multiple PDFs for the same job', async () => {
      const bytes0 = new Uint8Array([10, 20])
      const bytes1 = new Uint8Array([30, 40])
      await savePdfBytes('job-2', 0, bytes0)
      await savePdfBytes('job-2', 1, bytes1)
      expect(_store.get('job-2-0')).toEqual(bytes0)
      expect(_store.get('job-2-1')).toEqual(bytes1)
    })
  })

  describe('loadPdfBytes', () => {
    it('returns stored bytes', async () => {
      const bytes = new Uint8Array([5, 6, 7])
      _store.set('job-3-0', bytes)
      const result = await loadPdfBytes('job-3', 0)
      expect(result).toEqual(bytes)
    })

    it('returns null when key not found', async () => {
      const result = await loadPdfBytes('nonexistent', 0)
      expect(result).toBeNull()
    })
  })

  describe('clearPdfBytes', () => {
    it('removes all keys for a given job', async () => {
      _store.set('job-4-0', new Uint8Array([1]))
      _store.set('job-4-1', new Uint8Array([2]))
      _store.set('other-job-0', new Uint8Array([3]))
      await clearPdfBytes('job-4')
      expect(_store.has('job-4-0')).toBe(false)
      expect(_store.has('job-4-1')).toBe(false)
      // Other jobs not affected
      expect(_store.has('other-job-0')).toBe(true)
    })

    it('does not throw when no keys exist for job', async () => {
      await expect(clearPdfBytes('nonexistent-job')).resolves.not.toThrow()
    })
  })
})
