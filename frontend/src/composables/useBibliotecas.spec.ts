import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ─── Mock idb ─────────────────────────────────────────────────────────────────

interface MockStore {
  [key: string]: unknown
}

const mockStore: MockStore = {}

vi.mock('idb', () => ({
  openDB: vi.fn().mockResolvedValue({
    getAll: vi.fn((_store: string) => Promise.resolve(Object.values(mockStore))),
    put: vi.fn((_store: string, value: unknown) => {
      const entry = value as { id: string }
      mockStore[entry.id] = entry
      return Promise.resolve(entry.id)
    }),
    delete: vi.fn((_store: string, id: string) => {
      delete mockStore[id]
      return Promise.resolve()
    }),
    createObjectStore: vi.fn(),
  }),
}))

// ─── Imports (after mock) ─────────────────────────────────────────────────────

import {
  useBibliotecas,
  SYSTEM_LIBS,
  SIZE_LIMITS,
  ALLOWED_EXTENSIONS,
  formatFileSize,
  getExtension,
} from './useBibliotecas'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeFile(name: string, size: number, type = 'application/octet-stream'): File {
  const buf = new ArrayBuffer(size)
  return new File([buf], name, { type })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('useBibliotecas', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Clear mock store
    for (const key of Object.keys(mockStore)) {
      delete mockStore[key]
    }
  })

  // ── formatFileSize ──────────────────────────────────────────────────────────

  describe('formatFileSize', () => {
    it('formata bytes', () => {
      expect(formatFileSize(512)).toBe('512 B')
    })
    it('formata KB', () => {
      expect(formatFileSize(2048)).toBe('2.0 KB')
    })
    it('formata MB', () => {
      expect(formatFileSize(2 * 1024 * 1024)).toBe('2.00 MB')
    })
  })

  // ── getExtension ───────────────────────────────────────────────────────────

  describe('getExtension', () => {
    it('retorna extensão lowercase', () => {
      expect(getExtension('fonte.TTF')).toBe('.ttf')
      expect(getExtension('style.CSS')).toBe('.css')
    })
    it('retorna string vazia sem extensão', () => {
      expect(getExtension('arquivo')).toBe('')
    })
  })

  // ── loadFiles ──────────────────────────────────────────────────────────────

  describe('loadFiles', () => {
    it('carrega arquivos incluindo libs de sistema', async () => {
      const { files, loadFiles } = useBibliotecas()
      await loadFiles()

      // System libs should always be present
      const names = files.value.map((f) => f.name)
      for (const lib of SYSTEM_LIBS) {
        expect(names).toContain(lib)
      }
    })

    it('libs de sistema são marcadas com system=true', async () => {
      const { files, loadFiles } = useBibliotecas()
      await loadFiles()
      const sysFiles = files.value.filter((f) => f.system)
      expect(sysFiles.length).toBe(SYSTEM_LIBS.length)
    })
  })

  // ── addFile ────────────────────────────────────────────────────────────────

  describe('addFile', () => {
    it('adiciona fonte .ttf com sucesso', async () => {
      const { addFile, getByCategory } = useBibliotecas()
      const file = makeFile('test.ttf', 1024)
      const result = await addFile(file, 'fonts')
      expect(result.success).toBe(true)
      const fonts = getByCategory('fonts')
      expect(fonts.some((f) => f.name === 'test.ttf')).toBe(true)
    })

    it('rejeita extensão não permitida para fonts', async () => {
      const { addFile } = useBibliotecas()
      const file = makeFile('bad.exe', 100)
      const result = await addFile(file, 'fonts')
      expect(result.success).toBe(false)
      expect(result.message).toContain('Extensão não permitida')
    })

    it('rejeita arquivo .css na categoria fonts', async () => {
      const { addFile } = useBibliotecas()
      const file = makeFile('style.css', 100)
      const result = await addFile(file, 'fonts')
      expect(result.success).toBe(false)
    })

    it('rejeita fonte acima de 5MB', async () => {
      const { addFile } = useBibliotecas()
      const bigFile = makeFile('big.ttf', SIZE_LIMITS.fonts + 1)
      const result = await addFile(bigFile, 'fonts')
      expect(result.success).toBe(false)
      expect(result.message).toContain('tamanho máximo')
    })

    it('rejeita CSS acima de 1MB', async () => {
      const { addFile } = useBibliotecas()
      const bigFile = makeFile('big.css', SIZE_LIMITS.css + 1)
      const result = await addFile(bigFile, 'css')
      expect(result.success).toBe(false)
      expect(result.message).toContain('tamanho máximo')
    })

    it('rejeita JS acima de 1MB', async () => {
      const { addFile } = useBibliotecas()
      const bigFile = makeFile('big.js', SIZE_LIMITS.js + 1)
      const result = await addFile(bigFile, 'js')
      expect(result.success).toBe(false)
      expect(result.message).toContain('tamanho máximo')
    })

    it('aceita CSS de 100KB', async () => {
      const { addFile } = useBibliotecas()
      const file = makeFile('style.css', 100 * 1024)
      const result = await addFile(file, 'css')
      expect(result.success).toBe(true)
    })

    it('aceita JS de 500KB', async () => {
      const { addFile } = useBibliotecas()
      const file = makeFile('script.js', 500 * 1024)
      const result = await addFile(file, 'js')
      expect(result.success).toBe(true)
    })
  })

  // ── removeFile ─────────────────────────────────────────────────────────────

  describe('removeFile', () => {
    it('remove arquivo de usuário com sucesso', async () => {
      const { addFile, removeFile, getByCategory } = useBibliotecas()
      const file = makeFile('test.ttf', 512)
      await addFile(file, 'fonts')
      const id = 'fonts::test.ttf'
      const result = await removeFile(id)
      expect(result.success).toBe(true)
      const fonts = getByCategory('fonts')
      expect(fonts.some((f) => f.id === id)).toBe(false)
    })

    it('não remove libs de sistema', async () => {
      const { loadFiles, removeFile } = useBibliotecas()
      await loadFiles()
      const result = await removeFile('system::knockout-3.4.2.js')
      expect(result.success).toBe(false)
      expect(result.message).toContain('sistema')
    })
  })

  // ── getByCategory ──────────────────────────────────────────────────────────

  describe('getByCategory', () => {
    it('retorna apenas fontes quando pedido fonts', async () => {
      const { addFile, getByCategory } = useBibliotecas()
      await addFile(makeFile('a.ttf', 100), 'fonts')
      await addFile(makeFile('b.css', 100), 'css')
      const fonts = getByCategory('fonts')
      expect(fonts.every((f) => f.category === 'fonts')).toBe(true)
    })

    it('JS inclui libs de sistema', async () => {
      const { loadFiles, getByCategory } = useBibliotecas()
      await loadFiles()
      const jsFiles = getByCategory('js')
      const sysNames = jsFiles.filter((f) => f.system).map((f) => f.name)
      for (const lib of SYSTEM_LIBS) {
        expect(sysNames).toContain(lib)
      }
    })

    it('ordena libs de sistema primeiro e depois alfabeticamente', async () => {
      const { addFile, loadFiles, getByCategory } = useBibliotecas()
      await loadFiles()
      await addFile(makeFile('z-user.js', 100), 'js')
      await addFile(makeFile('a-user.js', 100), 'js')
      const js = getByCategory('js')
      const sysIdx = js.filter((f) => f.system).map((_, i) => i)
      // All system entries come before user entries
      const firstUserIdx = js.findIndex((f) => !f.system)
      if (firstUserIdx > -1) {
        expect(sysIdx.every((i) => i < firstUserIdx)).toBe(true)
      }
    })
  })

  // ── isFileReferenced ───────────────────────────────────────────────────────

  describe('isFileReferenced', () => {
    it('retorna true quando arquivo está no conteúdo do template', () => {
      const { isFileReferenced } = useBibliotecas()
      expect(isFileReferenced('minha-fonte.ttf', '<link href="minha-fonte.ttf">')).toBe(true)
    })

    it('retorna false quando não está referenciado', () => {
      const { isFileReferenced } = useBibliotecas()
      expect(isFileReferenced('minha-fonte.ttf', '<link href="outra.css">')).toBe(false)
    })

    it('retorna false quando templateContent é undefined', () => {
      const { isFileReferenced } = useBibliotecas()
      expect(isFileReferenced('qualquer.ttf', undefined)).toBe(false)
    })
  })

  // ── Constants ──────────────────────────────────────────────────────────────

  describe('ALLOWED_EXTENSIONS', () => {
    it('fonts aceita .ttf .woff .woff2 .otf', () => {
      expect(ALLOWED_EXTENSIONS.fonts).toContain('.ttf')
      expect(ALLOWED_EXTENSIONS.fonts).toContain('.woff')
      expect(ALLOWED_EXTENSIONS.fonts).toContain('.woff2')
      expect(ALLOWED_EXTENSIONS.fonts).toContain('.otf')
    })

    it('css aceita apenas .css', () => {
      expect(ALLOWED_EXTENSIONS.css).toEqual(['.css'])
    })

    it('js aceita apenas .js', () => {
      expect(ALLOWED_EXTENSIONS.js).toEqual(['.js'])
    })
  })

  describe('SYSTEM_LIBS', () => {
    it('inclui as 4 libs padrão', () => {
      expect(SYSTEM_LIBS).toContain('knockout-3.4.2.js')
      expect(SYSTEM_LIBS).toContain('knockout.mapping.js')
      expect(SYSTEM_LIBS).toContain('Chart.min.js')
      expect(SYSTEM_LIBS).toContain('chartjs-plugin-datalabels.min.js')
    })
  })
})
