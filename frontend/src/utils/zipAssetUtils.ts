// ─── ZIP Asset Utilities (Story 36.6) ──────────────────────────────────────
// Collects image assets from the document tree for ZIP save,
// and restores them on ZIP open.

import type { TreeNode, DocumentTree } from '@/types/template.types'

export interface AssetEntry {
  /** Filename inside assets/ folder (e.g. "logo.png") */
  filename: string
  /** MIME type (e.g. "image/png") */
  type: string
  /** Binary data as Uint8Array */
  data: Uint8Array
  /** Size in bytes */
  size: number
  /** Node ID that references this asset */
  nodeId: string
}

export interface AssetReference {
  name: string
  type: string
  size?: number
}

/**
 * Walk tree recursively, collecting image nodes that have data URIs or blob URLs as src.
 * Returns asset entries ready to write into ZIP assets/ folder.
 */
export function collectAssetsFromTree(tree: DocumentTree | null): AssetEntry[] {
  if (!tree?.root) return []

  const assets: AssetEntry[] = []
  const seenFilenames = new Set<string>()

  function walk(node: TreeNode) {
    if (node.type === 'image') {
      const src = node.properties?.src as string | undefined
      const assetFilename = node.properties?.assetFilename as string | undefined

      if (src && isDataUri(src)) {
        const parsed = parseDataUri(src)
        if (parsed) {
          const filename = deduplicateFilename(
            assetFilename || generateFilename(node.id, parsed.mimeType),
            seenFilenames,
          )
          seenFilenames.add(filename)

          assets.push({
            filename,
            type: parsed.mimeType,
            data: parsed.data,
            size: parsed.data.byteLength,
            nodeId: node.id,
          })
        }
      }
    }

    for (const child of node.children ?? []) {
      walk(child)
    }
  }

  walk(tree.root)
  return assets
}

/**
 * Build assetReferences metadata array from collected assets.
 */
export function buildAssetReferences(assets: AssetEntry[]): AssetReference[] | undefined {
  if (assets.length === 0) return undefined
  return assets.map((a) => ({
    name: a.filename,
    type: a.type,
    size: a.size,
  }))
}

/**
 * After loading a ZIP, restore data URIs into image nodes from assets/ folder entries.
 * Mutates the tree in place.
 *
 * @param tree - The document tree to patch
 * @param assetFiles - Map of filename -> Uint8Array from ZIP assets/ folder
 * @param assetRefs - Optional asset references from project.json for MIME type hints
 */
export function restoreAssetsIntoTree(
  tree: DocumentTree | null,
  assetFiles: Map<string, Uint8Array>,
  assetRefs?: AssetReference[],
): void {
  if (!tree?.root || assetFiles.size === 0) return

  const refMap = new Map<string, AssetReference>()
  if (assetRefs) {
    for (const ref of assetRefs) {
      refMap.set(ref.name, ref)
    }
  }

  function walk(node: TreeNode) {
    if (node.type === 'image') {
      const assetFilename = node.properties?.assetFilename as string | undefined

      if (assetFilename && assetFiles.has(assetFilename)) {
        const data = assetFiles.get(assetFilename)!
        const ref = refMap.get(assetFilename)
        const mimeType = ref?.type || guessMimeType(assetFilename)
        const dataUri = buildDataUri(mimeType, data)
        node.properties = { ...node.properties, src: dataUri }
      }
    }

    for (const child of node.children ?? []) {
      walk(child)
    }
  }

  walk(tree.root)
}

// ─── Internal helpers ───────────────────────────────────────────────────────

function isDataUri(src: string): boolean {
  return src.startsWith('data:')
}

interface ParsedDataUri {
  mimeType: string
  data: Uint8Array
}

export function parseDataUri(uri: string): ParsedDataUri | null {
  // Format: data:[<mediatype>][;base64],<data>
  const match = uri.match(/^data:([^;,]+)?(?:;base64)?,(.*)$/)
  if (!match) return null

  const mimeType = match[1] || 'application/octet-stream'
  const base64Data = match[2]

  try {
    const binaryStr = atob(base64Data)
    const bytes = new Uint8Array(binaryStr.length)
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i)
    }
    return { mimeType, data: bytes }
  } catch {
    return null
  }
}

export function buildDataUri(mimeType: string, data: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < data.length; i++) {
    binary += String.fromCharCode(data[i])
  }
  const base64 = btoa(binary)
  return `data:${mimeType};base64,${base64}`
}

function generateFilename(nodeId: string, mimeType: string): string {
  const ext = mimeExtension(mimeType)
  return `image-${nodeId}.${ext}`
}

function mimeExtension(mimeType: string): string {
  const map: Record<string, string> = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
    'image/svg+xml': 'svg',
    'image/gif': 'gif',
  }
  return map[mimeType] || 'bin'
}

export function guessMimeType(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()
  const map: Record<string, string> = {
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    webp: 'image/webp',
    svg: 'image/svg+xml',
    gif: 'image/gif',
  }
  return map[ext ?? ''] || 'application/octet-stream'
}

function deduplicateFilename(name: string, existing: Set<string>): string {
  if (!existing.has(name)) return name
  const dot = name.lastIndexOf('.')
  const base = dot > 0 ? name.slice(0, dot) : name
  const ext = dot > 0 ? name.slice(dot) : ''
  let counter = 2
  while (existing.has(`${base}-${counter}${ext}`)) {
    counter++
  }
  return `${base}-${counter}${ext}`
}
