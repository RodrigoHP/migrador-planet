import { ref } from 'vue'
import { openDB } from 'idb'
import type { IDBPDatabase } from 'idb'

// ─── Types ────────────────────────────────────────────────────────────────────

export type BibliotecaTab = 'fonts' | 'css' | 'js'

export interface BibliotecaFile {
  id: string
  name: string
  size: number
  category: BibliotecaTab
  /** Data URL or ArrayBuffer stored in IDB */
  data: ArrayBuffer
  system?: boolean
}

// ─── System (protected) JS libraries ─────────────────────────────────────────

export const SYSTEM_LIBS: readonly string[] = [
  'knockout-3.4.2.js',
  'knockout.mapping.js',
  'Chart.min.js',
  'chartjs-plugin-datalabels.min.js',
]

// ─── Size limits per category (bytes) ────────────────────────────────────────

export const SIZE_LIMITS: Record<BibliotecaTab, number> = {
  fonts: 5 * 1024 * 1024,   // 5 MB
  css:   1 * 1024 * 1024,   // 1 MB
  js:    1 * 1024 * 1024,   // 1 MB
}

// ─── Allowed extensions per category ─────────────────────────────────────────

export const ALLOWED_EXTENSIONS: Record<BibliotecaTab, string[]> = {
  fonts: ['.ttf', '.woff', '.woff2', '.otf'],
  css:   ['.css'],
  js:    ['.js'],
}

// ─── IDB setup ────────────────────────────────────────────────────────────────

const DB_NAME = 'migrador-bibliotecas'
const DB_VERSION = 1
const STORE_NAME = 'files'

let _dbPromise: Promise<IDBPDatabase> | null = null

function getDb(): Promise<IDBPDatabase> {
  if (!_dbPromise) {
    _dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
          store.createIndex('category', 'category')
        }
      },
    })
  }
  return _dbPromise
}

// ─── Utility ──────────────────────────────────────────────────────────────────

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function getExtension(filename: string): string {
  const idx = filename.lastIndexOf('.')
  if (idx === -1) return ''
  return filename.slice(idx).toLowerCase()
}

// ─── Composable ───────────────────────────────────────────────────────────────

export function useBibliotecas() {
  const files = ref<BibliotecaFile[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // ── Load all files from IDB ─────────────────────────────────────────────

  async function loadFiles(): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      const db = await getDb()
      const all = (await db.getAll(STORE_NAME)) as BibliotecaFile[]
      // Add system libs that are not yet persisted (they are virtual)
      const systemEntries = SYSTEM_LIBS.map<BibliotecaFile>((name) => ({
        id: `system::${name}`,
        name,
        size: 0,
        category: 'js',
        data: new ArrayBuffer(0),
        system: true,
      }))
      const userFiles = all.filter((f) => !f.system)
      files.value = [...systemEntries, ...userFiles]
    } finally {
      isLoading.value = false
    }
  }

  // ── Add a file ─────────────────────────────────────────────────────────

  async function addFile(
    file: File,
    category: BibliotecaTab,
  ): Promise<{ success: boolean; message?: string }> {
    error.value = null

    // Extension check
    const ext = getExtension(file.name)
    if (!ALLOWED_EXTENSIONS[category].includes(ext)) {
      const allowed = ALLOWED_EXTENSIONS[category].join(', ')
      const msg = `Extensão não permitida para ${category}. Extensões aceitas: ${allowed}`
      error.value = msg
      return { success: false, message: msg }
    }

    // Size check
    const limit = SIZE_LIMITS[category]
    if (file.size > limit) {
      const msg = `Arquivo excede o tamanho máximo permitido (${formatFileSize(limit)})`
      error.value = msg
      return { success: false, message: msg }
    }

    const data = await file.arrayBuffer()
    const entry: BibliotecaFile = {
      id: `${category}::${file.name}`,
      name: file.name,
      size: file.size,
      category,
      data,
    }

    try {
      const db = await getDb()
      await db.put(STORE_NAME, entry)
      await loadFiles()
      return { success: true }
    } catch (e) {
      const msg = `Erro ao salvar arquivo: ${String(e)}`
      error.value = msg
      return { success: false, message: msg }
    }
  }

  // ── Remove a file ─────────────────────────────────────────────────────

  async function removeFile(id: string): Promise<{ success: boolean; message?: string }> {
    error.value = null
    // Prevent removal of system libs
    const target = files.value.find((f) => f.id === id)
    if (target?.system) {
      const msg = 'Não é possível remover bibliotecas do sistema'
      error.value = msg
      return { success: false, message: msg }
    }
    try {
      const db = await getDb()
      await db.delete(STORE_NAME, id)
      await loadFiles()
      return { success: true }
    } catch (e) {
      const msg = `Erro ao remover arquivo: ${String(e)}`
      error.value = msg
      return { success: false, message: msg }
    }
  }

  // ── Get files by category ─────────────────────────────────────────────

  function getByCategory(category: BibliotecaTab): BibliotecaFile[] {
    return files.value
      .filter((f) => f.category === category)
      .sort((a, b) => {
        // System libs first, then alphabetical
        if (a.system && !b.system) return -1
        if (!a.system && b.system) return 1
        return a.name.localeCompare(b.name)
      })
  }

  // ── Check if a file is referenced by active template ─────────────────

  function isFileReferenced(filename: string, activeTemplateContent?: string): boolean {
    if (!activeTemplateContent) return false
    return activeTemplateContent.includes(filename)
  }

  return {
    files,
    isLoading,
    error,
    loadFiles,
    addFile,
    removeFile,
    getByCategory,
    isFileReferenced,
    formatFileSize,
  }
}
