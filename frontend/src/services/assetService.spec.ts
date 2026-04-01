import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { uploadAsset, deleteAsset, listAssets } from './assetService'

// apiFetch wraps fetch with auth headers; in tests we bypass auth and delegate to global fetch
vi.mock('@/services/apiFetch', () => ({
  apiFetch: (url: string, options?: RequestInit) =>
    options !== undefined ? fetch(url, options) : fetch(url),
}))

// Helper to create a minimal mock Response
function mockResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response
}

describe('assetService', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ─── uploadAsset ──────────────────────────────────────────────────────────

  describe('uploadAsset', () => {
    it('sends POST multipart/form-data and returns AssetResponse', async () => {
      const mockData = {
        filename: 'logo.png',
        path: 'assets/logo.png',
        size: 1024,
        dimensions: { width: 200, height: 100 },
      }
      fetchMock.mockResolvedValueOnce(mockResponse(mockData))

      const file = new File(['content'], 'logo.png', { type: 'image/png' })
      const result = await uploadAsset('tmpl-1', file)

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/templates/tmpl-1/assets',
        expect.objectContaining({ method: 'POST' }),
      )
      expect(result).toEqual(mockData)
    })

    it('throws on HTTP error with detail message', async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({ detail: 'Tipo não suportado.' }, 400),
      )

      const file = new File(['x'], 'bad.bmp', { type: 'image/bmp' })
      await expect(uploadAsset('tmpl-1', file)).rejects.toThrow('Tipo não suportado.')
    })

    it('throws generic error when no detail in response', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({}, 500))

      const file = new File(['x'], 'img.png', { type: 'image/png' })
      await expect(uploadAsset('tmpl-1', file)).rejects.toThrow('Erro HTTP 500')
    })
  })

  // ─── deleteAsset ──────────────────────────────────────────────────────────

  describe('deleteAsset', () => {
    it('sends DELETE request', async () => {
      fetchMock.mockResolvedValueOnce({ ok: true, status: 200 } as unknown as Response)

      await deleteAsset('tmpl-1', 'logo.png')

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/templates/tmpl-1/assets/logo.png',
        expect.objectContaining({ method: 'DELETE' }),
      )
    })

    it('throws on 404', async () => {
      fetchMock.mockResolvedValueOnce(
        mockResponse({ detail: "Asset 'logo.png' não encontrado." }, 404),
      )

      await expect(deleteAsset('tmpl-1', 'logo.png')).rejects.toThrow("Asset 'logo.png' não encontrado.")
    })

    it('URL-encodes filename with special characters', async () => {
      fetchMock.mockResolvedValueOnce({ ok: true, status: 200 } as unknown as Response)

      await deleteAsset('tmpl-1', 'my image.png')

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/templates/tmpl-1/assets/my%20image.png',
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  // ─── listAssets ───────────────────────────────────────────────────────────

  describe('listAssets', () => {
    it('sends GET request and returns array', async () => {
      const mockList = [
        {
          filename: 'logo.png',
          path: 'assets/logo.png',
          size: 2048,
          thumbnailUrl: '/api/templates/tmpl-1/assets/logo.png/thumbnail',
          dataUri: 'data:image/png;base64,abc123',
        },
      ]
      fetchMock.mockResolvedValueOnce(mockResponse(mockList))

      const result = await listAssets('tmpl-1')

      expect(fetchMock).toHaveBeenCalledWith('/api/templates/tmpl-1/assets')
      expect(result).toEqual(mockList)
    })

    it('returns empty array when no assets', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse([]))

      const result = await listAssets('tmpl-1')
      expect(result).toEqual([])
    })

    it('throws on server error', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({ detail: 'Erro interno.' }, 500))

      await expect(listAssets('tmpl-1')).rejects.toThrow('Erro interno.')
    })
  })
})
