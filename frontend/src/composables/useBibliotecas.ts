import { ref } from 'vue'
import { openDB } from 'idb'
import type { IDBPDatabase } from 'idb'
import type { TreeNode } from '@/types/template.types'

// ─── Types ────────────────────────────────────────────────────────────────────

export type BibliotecaTab = 'fonts' | 'css' | 'js' | 'components'

export interface BibliotecaFile {
  id: string
  name: string
  size: number
  category: BibliotecaTab
  /** Data URL or ArrayBuffer stored in IDB */
  data: ArrayBuffer
  system?: boolean
}

export interface BibliotecaComponent {
  id: string
  name: string
  /** Serialized TreeNode + children as JSON */
  data: string
  /** Pre-rendered HTML preview snippet */
  previewHtml: string
  /** Number of nodes (node + descendants) */
  nodeCount: number
  createdAt: number
}

// ─── System (protected) JS libraries ─────────────────────────────────────────

export const SYSTEM_LIBS: readonly string[] = [
  'knockout-3.4.2.js',
  'knockout.mapping.js',
  'Chart.min.js',
  'chartjs-plugin-datalabels.min.js',
  'JsBarcode.all.min.js',
]

// ─── Size limits per category (bytes) ────────────────────────────────────────

export const SIZE_LIMITS: Record<BibliotecaTab, number> = {
  fonts: 5 * 1024 * 1024, // 5 MB
  css: 1 * 1024 * 1024, // 1 MB
  js: 1 * 1024 * 1024, // 1 MB
}

// ─── Allowed extensions per category ─────────────────────────────────────────

export const ALLOWED_EXTENSIONS: Record<BibliotecaTab, string[]> = {
  fonts: ['.ttf', '.woff', '.woff2', '.otf'],
  css: ['.css'],
  js: ['.js'],
}

// ─── IDB setup ────────────────────────────────────────────────────────────────

const DB_NAME = 'migrador-bibliotecas'
const DB_VERSION = 2
const STORE_NAME = 'files'
const COMPONENTS_STORE = 'components'

let _dbPromise: Promise<IDBPDatabase> | null = null

function getDb(): Promise<IDBPDatabase> {
  if (!_dbPromise) {
    _dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
          store.createIndex('category', 'category')
        }
        if (!db.objectStoreNames.contains(COMPONENTS_STORE)) {
          db.createObjectStore(COMPONENTS_STORE, { keyPath: 'id' })
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

// ─── Auto-seed helper ─────────────────────────────────────────────────────

/**
 * Fetch a system lib from /libs/{name} (Vite serves public/ at root).
 * Returns the ArrayBuffer on success, null on failure.
 */
async function _seedSystemLib(name: string): Promise<ArrayBuffer | null> {
  try {
    const response = await fetch(`/libs/${name}`)
    if (!response.ok) return null
    return await response.arrayBuffer()
  } catch {
    return null
  }
}

// ─── Component serialization helpers ─────────────────────────────────────────

/**
 * Deep-serialize a TreeNode + all children, stripping only the `id` field
 * (IDs will be regenerated on insert). Preserves type, name, binding,
 * properties, visibility, children, and all other fields.
 */
export function serializeNode(node: TreeNode): Record<string, unknown> {
  return {
    type: node.type,
    name: node.name,
    binding: node.binding ?? '',
    isOptional: node.isOptional ?? false,
    properties: { ...node.properties },
    visibility: node.visibility,
    block_id: node.block_id,
    suggested_binding: node.suggested_binding,
    children: node.children.map((c) => serializeNode(c)),
  }
}

/** Count total nodes in a subtree (inclusive). */
export function countNodes(node: TreeNode): number {
  let count = 1
  for (const child of node.children) {
    count += countNodes(child)
  }
  return count
}

/** Generate a simple HTML preview string from the node tree (for thumbnail). */
export function generatePreviewHtml(node: TreeNode): string {
  const tag =
    node.type === 'text'
      ? 'span'
      : node.type === 'table'
        ? 'table'
        : node.type === 'image'
          ? 'img'
          : 'div'

  const name = escapeHtml(node.name)

  if (tag === 'img') {
    return `<img alt="${name}" style="max-width:100%;height:auto;display:block;background:#eee;min-height:20px;" />`
  }

  const childrenHtml = node.children.map((c) => generatePreviewHtml(c)).join('')

  if (tag === 'table') {
    return `<table style="border-collapse:collapse;width:100%;font-size:10px;"><tr><td style="border:1px solid #ccc;padding:2px;">${name}</td></tr>${childrenHtml}</table>`
  }

  if (tag === 'span') {
    return `<span style="font-size:10px;">${name}</span>`
  }

  return `<div style="padding:2px;font-size:10px;">${childrenHtml || name}</div>`
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
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

      // Build a map of existing IDB entries keyed by id
      const idbMap = new Map(all.map((f) => [f.id, f]))

      // Auto-seed system libs: for each SYSTEM_LIB, check if IDB has real data.
      // If not, fetch from /libs/{name} (Vite serves public/ at root) and persist.
      const systemEntries: BibliotecaFile[] = []
      for (const name of SYSTEM_LIBS) {
        const id = `system::${name}`
        const existing = idbMap.get(id)

        if (existing && existing.data && existing.data.byteLength > 0) {
          // Already has real data in IDB
          systemEntries.push(existing)
        } else {
          // Try to seed from static asset
          const seeded = await _seedSystemLib(name)
          if (seeded) {
            const entry: BibliotecaFile = {
              id,
              name,
              size: seeded.byteLength,
              category: 'js',
              data: seeded,
              system: true,
            }
            // Persist to IDB so next load is instant
            try {
              await db.put(STORE_NAME, entry)
            } catch {
              /* best-effort */
            }
            systemEntries.push(entry)
          } else {
            // Seed failed — keep virtual entry with empty data
            systemEntries.push({
              id,
              name,
              size: 0,
              category: 'js',
              data: new ArrayBuffer(0),
              system: true,
            })
          }
        }
      }

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

  // ── Components CRUD ──────────────────────────────────────────────────

  const components = ref<BibliotecaComponent[]>([])

  async function loadComponents(): Promise<void> {
    try {
      const db = await getDb()
      components.value = (await db.getAll(COMPONENTS_STORE)) as BibliotecaComponent[]
      components.value.sort((a, b) => b.createdAt - a.createdAt)
    } catch {
      // best-effort
    }
  }

  async function saveComponent(
    name: string,
    node: TreeNode,
  ): Promise<{ success: boolean; message?: string }> {
    error.value = null
    try {
      const serialized = serializeNode(node)
      const data = JSON.stringify(serialized)
      const nodeCount = countNodes(node)
      const previewHtml = generatePreviewHtml(node)
      const entry: BibliotecaComponent = {
        id: `comp::${name}::${Date.now()}`,
        name,
        data,
        previewHtml,
        nodeCount,
        createdAt: Date.now(),
      }
      const db = await getDb()
      await db.put(COMPONENTS_STORE, entry)
      await loadComponents()
      return { success: true }
    } catch (e) {
      const msg = `Erro ao salvar componente: ${String(e)}`
      error.value = msg
      return { success: false, message: msg }
    }
  }

  async function removeComponent(id: string): Promise<{ success: boolean; message?: string }> {
    error.value = null
    try {
      const db = await getDb()
      await db.delete(COMPONENTS_STORE, id)
      await loadComponents()
      return { success: true }
    } catch (e) {
      const msg = `Erro ao remover componente: ${String(e)}`
      error.value = msg
      return { success: false, message: msg }
    }
  }

  function getComponentData(component: BibliotecaComponent): TreeNode {
    return JSON.parse(component.data) as TreeNode
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
    // Components
    components,
    loadComponents,
    saveComponent,
    removeComponent,
    getComponentData,
  }
}
