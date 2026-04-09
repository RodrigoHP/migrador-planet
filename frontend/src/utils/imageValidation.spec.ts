import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { validateImageFile, MAX_IMAGE_SIZE_BYTES } from './imageValidation'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeFile(name: string, type: string, size = 1024): File {
  const content = new Uint8Array(size)
  return new File([content], name, { type })
}

// Stub URL globally once
vi.stubGlobal('URL', {
  createObjectURL: vi.fn(() => 'blob:mock-url'),
  revokeObjectURL: vi.fn(),
})

// Mock Image class with configurable dimensions
function mockImageLoad(width: number, height: number) {
  const MockImage = vi.fn(function (this: Record<string, unknown>) {
    this['naturalWidth'] = width
    this['naturalHeight'] = height
    this['onload'] = null
    this['onerror'] = null

    Object.defineProperty(this, 'src', {
      configurable: true,
      set: (_val: string) => {
        setTimeout(() => {
          if (typeof this['onload'] === 'function') {
            ;(this['onload'] as () => void)()
          }
        }, 0)
      },
    })
  })
  vi.stubGlobal('Image', MockImage)
}

function mockImageError() {
  const MockImage = vi.fn(function (this: Record<string, unknown>) {
    this['naturalWidth'] = 0
    this['naturalHeight'] = 0
    this['onload'] = null
    this['onerror'] = null

    Object.defineProperty(this, 'src', {
      configurable: true,
      set: (_val: string) => {
        setTimeout(() => {
          if (typeof this['onerror'] === 'function') {
            ;(this['onerror'] as () => void)()
          }
        }, 0)
      },
    })
  })
  vi.stubGlobal('Image', MockImage)
}

// ─── Setup ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.unstubAllGlobals()
  // Restore URL stub after unstubbing
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn(() => 'blob:mock-url'),
    revokeObjectURL: vi.fn(),
  })
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('validateImageFile', () => {
  describe('MIME type validation', () => {
    it('accepts image/png', async () => {
      mockImageLoad(100, 100)
      const file = makeFile('img.png', 'image/png')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('accepts image/jpeg', async () => {
      mockImageLoad(100, 100)
      const file = makeFile('img.jpg', 'image/jpeg')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(true)
    })

    it('accepts image/webp', async () => {
      mockImageLoad(100, 100)
      const file = makeFile('img.webp', 'image/webp')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(true)
    })

    it('accepts image/svg+xml without dimension check', async () => {
      // No Image mock needed — SVG skips dimension check
      const file = makeFile('icon.svg', 'image/svg+xml')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(true)
    })

    it('rejects image/bmp with PT-BR error', async () => {
      const file = makeFile('img.bmp', 'image/bmp')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(false)
      expect(result.errors[0]).toContain('Tipo de arquivo não suportado')
      expect(result.errors[0]).toContain('image/bmp')
    })

    it('rejects image/gif', async () => {
      const file = makeFile('img.gif', 'image/gif')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(false)
      expect(result.errors[0]).toContain('Tipo de arquivo não suportado')
    })
  })

  describe('file size validation', () => {
    it('accepts file exactly at limit', async () => {
      mockImageLoad(100, 100)
      const file = makeFile('img.png', 'image/png', MAX_IMAGE_SIZE_BYTES)
      const result = await validateImageFile(file)
      expect(result.valid).toBe(true)
    })

    it('rejects file exceeding 5 MB', async () => {
      const file = makeFile('big.png', 'image/png', MAX_IMAGE_SIZE_BYTES + 1)
      const result = await validateImageFile(file)
      expect(result.valid).toBe(false)
      expect(result.errors[0]).toContain('Arquivo muito grande')
      expect(result.errors[0]).toContain('5 MB')
    })
  })

  describe('dimension validation', () => {
    it('accepts image with dimensions >= 10x10', async () => {
      mockImageLoad(10, 10)
      const file = makeFile('img.png', 'image/png')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(true)
    })

    it('rejects image smaller than 10x10', async () => {
      mockImageLoad(9, 9)
      const file = makeFile('img.png', 'image/png')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(false)
      expect(result.errors[0]).toContain('Dimensões muito pequenas')
      expect(result.errors[0]).toContain('9×9 px')
    })

    it('rejects image with width < 10', async () => {
      mockImageLoad(5, 100)
      const file = makeFile('img.png', 'image/png')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(false)
    })

    it('adds error when image fails to load', async () => {
      mockImageError()
      const file = makeFile('img.png', 'image/png')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(false)
      expect(result.errors[0]).toContain('verificar as dimensões')
    })

    it('skips dimension check for SVG files', async () => {
      // No Image mock needed — SVG should not trigger dimension check
      const file = makeFile('icon.svg', 'image/svg+xml')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(true)
    })
  })

  describe('multiple errors', () => {
    it('reports type error first, skips dimension check on invalid type', async () => {
      const file = makeFile('img.bmp', 'image/bmp')
      const result = await validateImageFile(file)
      expect(result.valid).toBe(false)
      // Only type error — dimension check is skipped when there are already errors
      expect(result.errors).toHaveLength(1)
      expect(result.errors[0]).toContain('Tipo de arquivo não suportado')
    })
  })
})
