import { describe, it, expect } from 'vitest'
import {
  collectAssetsFromTree,
  buildAssetReferences,
  restoreAssetsIntoTree,
  parseDataUri,
  buildDataUri,
  guessMimeType,
} from './zipAssetUtils'
import type { DocumentTree, TreeNode } from '@/types/template.types'

// ─── Helpers ────────────────────────────────────────────────────────────────

function makeImageNode(
  id: string,
  src?: string,
  assetFilename?: string,
): TreeNode {
  return {
    id,
    type: 'image',
    name: `Image ${id}`,
    children: [],
    properties: {
      ...(src !== undefined && { src }),
      ...(assetFilename !== undefined && { assetFilename }),
    },
    visibility: true,
  }
}

function makeTree(...children: TreeNode[]): DocumentTree {
  return {
    root: {
      id: 'root',
      type: 'document',
      name: 'Document',
      children,
      properties: {},
      visibility: true,
    },
  }
}

/** Create a minimal valid data URI for a 1x1 red PNG pixel */
function makePngDataUri(): string {
  // Tiny valid base64 PNG (1x1 pixel)
  const base64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
  return `data:image/png;base64,${base64}`
}

// ─── parseDataUri ───────────────────────────────────────────────────────────

describe('parseDataUri', () => {
  it('parses a valid base64 data URI', () => {
    const uri = 'data:image/png;base64,AQID'
    const result = parseDataUri(uri)
    expect(result).not.toBeNull()
    expect(result!.mimeType).toBe('image/png')
    expect(result!.data).toBeInstanceOf(Uint8Array)
    expect(result!.data.length).toBe(3) // AQID decodes to [1, 2, 3]
    expect(result!.data[0]).toBe(1)
    expect(result!.data[1]).toBe(2)
    expect(result!.data[2]).toBe(3)
  })

  it('returns null for non-data-uri strings', () => {
    expect(parseDataUri('https://example.com/img.png')).toBeNull()
    expect(parseDataUri('')).toBeNull()
  })

  it('defaults to application/octet-stream when no mime type', () => {
    const result = parseDataUri('data:;base64,AQID')
    expect(result).not.toBeNull()
    expect(result!.mimeType).toBe('application/octet-stream')
  })
})

// ─── buildDataUri ───────────────────────────────────────────────────────────

describe('buildDataUri', () => {
  it('round-trips with parseDataUri', () => {
    const original = new Uint8Array([10, 20, 30, 40])
    const uri = buildDataUri('image/jpeg', original)
    expect(uri.startsWith('data:image/jpeg;base64,')).toBe(true)

    const parsed = parseDataUri(uri)
    expect(parsed).not.toBeNull()
    expect(parsed!.mimeType).toBe('image/jpeg')
    expect(Array.from(parsed!.data)).toEqual([10, 20, 30, 40])
  })
})

// ─── guessMimeType ──────────────────────────────────────────────────────────

describe('guessMimeType', () => {
  it('guesses common image types', () => {
    expect(guessMimeType('logo.png')).toBe('image/png')
    expect(guessMimeType('photo.jpg')).toBe('image/jpeg')
    expect(guessMimeType('photo.jpeg')).toBe('image/jpeg')
    expect(guessMimeType('icon.svg')).toBe('image/svg+xml')
    expect(guessMimeType('banner.webp')).toBe('image/webp')
  })

  it('returns octet-stream for unknown extensions', () => {
    expect(guessMimeType('file.xyz')).toBe('application/octet-stream')
    expect(guessMimeType('noext')).toBe('application/octet-stream')
  })
})

// ─── collectAssetsFromTree ──────────────────────────────────────────────────

describe('collectAssetsFromTree', () => {
  it('returns empty array when tree is null', () => {
    expect(collectAssetsFromTree(null)).toEqual([])
  })

  it('returns empty array when no image nodes exist', () => {
    const tree = makeTree({
      id: 'text1',
      type: 'text',
      name: 'Text',
      children: [],
      properties: {},
      visibility: true,
    })
    expect(collectAssetsFromTree(tree)).toEqual([])
  })

  it('returns empty array when image has non-data-uri src', () => {
    const tree = makeTree(
      makeImageNode('img1', 'https://example.com/logo.png', 'logo.png'),
    )
    expect(collectAssetsFromTree(tree)).toEqual([])
  })

  it('collects assets from image nodes with data URIs', () => {
    const dataUri = makePngDataUri()
    const tree = makeTree(
      makeImageNode('img1', dataUri, 'logo.png'),
    )

    const assets = collectAssetsFromTree(tree)
    expect(assets).toHaveLength(1)
    expect(assets[0].filename).toBe('logo.png')
    expect(assets[0].type).toBe('image/png')
    expect(assets[0].nodeId).toBe('img1')
    expect(assets[0].data).toBeInstanceOf(Uint8Array)
    expect(assets[0].size).toBeGreaterThan(0)
  })

  it('generates filename from nodeId when assetFilename is missing', () => {
    const dataUri = 'data:image/jpeg;base64,AQID'
    const tree = makeTree(makeImageNode('node-42', dataUri))

    const assets = collectAssetsFromTree(tree)
    expect(assets).toHaveLength(1)
    expect(assets[0].filename).toBe('image-node-42.jpg')
  })

  it('deduplicates filenames', () => {
    const dataUri = 'data:image/png;base64,AQID'
    const tree = makeTree(
      makeImageNode('a', dataUri, 'logo.png'),
      makeImageNode('b', dataUri, 'logo.png'),
    )

    const assets = collectAssetsFromTree(tree)
    expect(assets).toHaveLength(2)
    expect(assets[0].filename).toBe('logo.png')
    expect(assets[1].filename).toBe('logo-2.png')
  })

  it('collects from nested nodes', () => {
    const dataUri = 'data:image/png;base64,AQID'
    const tree: DocumentTree = {
      root: {
        id: 'root',
        type: 'document',
        name: 'Doc',
        children: [
          {
            id: 'section1',
            type: 'section',
            name: 'Section',
            children: [makeImageNode('nested-img', dataUri, 'nested.png')],
            properties: {},
            visibility: true,
          },
        ],
        properties: {},
        visibility: true,
      },
    }

    const assets = collectAssetsFromTree(tree)
    expect(assets).toHaveLength(1)
    expect(assets[0].filename).toBe('nested.png')
    expect(assets[0].nodeId).toBe('nested-img')
  })
})

// ─── buildAssetReferences ───────────────────────────────────────────────────

describe('buildAssetReferences', () => {
  it('returns undefined for empty array', () => {
    expect(buildAssetReferences([])).toBeUndefined()
  })

  it('builds references with correct metadata', () => {
    const assets = [
      {
        filename: 'logo.png',
        type: 'image/png',
        data: new Uint8Array([1, 2, 3]),
        size: 3,
        nodeId: 'img1',
      },
    ]
    const refs = buildAssetReferences(assets)
    expect(refs).toEqual([
      { name: 'logo.png', type: 'image/png', size: 3 },
    ])
  })
})

// ─── restoreAssetsIntoTree ──────────────────────────────────────────────────

describe('restoreAssetsIntoTree', () => {
  it('does nothing when tree is null', () => {
    const files = new Map<string, Uint8Array>()
    files.set('logo.png', new Uint8Array([1, 2, 3]))
    // Should not throw
    restoreAssetsIntoTree(null, files)
  })

  it('does nothing when assetFiles is empty', () => {
    const tree = makeTree(makeImageNode('img1', 'old-src', 'logo.png'))
    restoreAssetsIntoTree(tree, new Map())
    expect(tree.root.children[0].properties.src).toBe('old-src')
  })

  it('restores data URI for image nodes matching assetFilename', () => {
    const tree = makeTree(makeImageNode('img1', undefined, 'logo.png'))
    const data = new Uint8Array([1, 2, 3])
    const files = new Map<string, Uint8Array>()
    files.set('logo.png', data)

    restoreAssetsIntoTree(tree, files)

    const src = tree.root.children[0].properties.src as string
    expect(src).toMatch(/^data:image\/png;base64,/)
  })

  it('uses MIME type from assetReferences when available', () => {
    const tree = makeTree(makeImageNode('img1', undefined, 'photo.dat'))
    const data = new Uint8Array([10, 20])
    const files = new Map<string, Uint8Array>()
    files.set('photo.dat', data)

    const refs = [{ name: 'photo.dat', type: 'image/webp', size: 2 }]
    restoreAssetsIntoTree(tree, files, refs)

    const src = tree.root.children[0].properties.src as string
    expect(src).toMatch(/^data:image\/webp;base64,/)
  })

  it('falls back to filename extension for MIME type', () => {
    const tree = makeTree(makeImageNode('img1', undefined, 'banner.jpg'))
    const files = new Map<string, Uint8Array>()
    files.set('banner.jpg', new Uint8Array([5]))

    restoreAssetsIntoTree(tree, files)

    const src = tree.root.children[0].properties.src as string
    expect(src).toMatch(/^data:image\/jpeg;base64,/)
  })

  it('skips non-image nodes', () => {
    const tree: DocumentTree = {
      root: {
        id: 'root',
        type: 'document',
        name: 'Doc',
        children: [
          {
            id: 'text1',
            type: 'text',
            name: 'Text',
            children: [],
            properties: { assetFilename: 'logo.png' },
            visibility: true,
          },
        ],
        properties: {},
        visibility: true,
      },
    }
    const files = new Map<string, Uint8Array>()
    files.set('logo.png', new Uint8Array([1]))

    restoreAssetsIntoTree(tree, files)
    // Text node should NOT get a src injected
    expect(tree.root.children[0].properties.src).toBeUndefined()
  })

  it('restores nested image nodes', () => {
    const tree: DocumentTree = {
      root: {
        id: 'root',
        type: 'document',
        name: 'Doc',
        children: [
          {
            id: 'sec',
            type: 'section',
            name: 'Section',
            children: [makeImageNode('deep-img', undefined, 'deep.png')],
            properties: {},
            visibility: true,
          },
        ],
        properties: {},
        visibility: true,
      },
    }
    const files = new Map<string, Uint8Array>()
    files.set('deep.png', new Uint8Array([7, 8, 9]))

    restoreAssetsIntoTree(tree, files)

    const src = tree.root.children[0].children[0].properties.src as string
    expect(src).toMatch(/^data:image\/png;base64,/)
  })
})
