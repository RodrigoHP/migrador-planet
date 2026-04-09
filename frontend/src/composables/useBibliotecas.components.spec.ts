import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { TreeNode } from '@/types/template.types'

// ─── Mock idb ─────────────────────────────────────────────────────────────────

interface MockStore {
  [key: string]: unknown
}

const mockFileStore: MockStore = {}
const mockComponentStore: MockStore = {}

vi.mock('idb', () => ({
  openDB: vi.fn().mockResolvedValue({
    getAll: vi.fn((storeName: string) => {
      const store = storeName === 'components' ? mockComponentStore : mockFileStore
      return Promise.resolve(Object.values(store))
    }),
    put: vi.fn((storeName: string, value: unknown) => {
      const store = storeName === 'components' ? mockComponentStore : mockFileStore
      const entry = value as { id: string }
      store[entry.id] = entry
      return Promise.resolve(entry.id)
    }),
    delete: vi.fn((storeName: string, id: string) => {
      const store = storeName === 'components' ? mockComponentStore : mockFileStore
      delete store[id]
      return Promise.resolve()
    }),
    createObjectStore: vi.fn(),
  }),
}))

// ─── Imports (after mock) ─────────────────────────────────────────────────────

import {
  useBibliotecas,
  serializeNode,
  countNodes,
  generatePreviewHtml,
} from './useBibliotecas'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    id: 'node-1',
    type: 'container',
    name: 'Test Container',
    binding: '',
    isOptional: false,
    children: [],
    properties: { width: 100 },
    visibility: true,
    ...overrides,
  }
}

function makeTree(): TreeNode {
  return makeNode({
    id: 'root',
    name: 'Root',
    type: 'container',
    children: [
      makeNode({
        id: 'child-1',
        name: 'Header',
        type: 'text',
        children: [],
      }),
      makeNode({
        id: 'child-2',
        name: 'Table',
        type: 'table',
        children: [
          makeNode({
            id: 'grandchild-1',
            name: 'Cell',
            type: 'text',
            children: [],
          }),
        ],
      }),
    ],
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('useBibliotecas — Components', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    for (const key of Object.keys(mockComponentStore)) {
      delete mockComponentStore[key]
    }
    for (const key of Object.keys(mockFileStore)) {
      delete mockFileStore[key]
    }
  })

  // ── serializeNode ──────────────────────────────────────────────────────────

  describe('serializeNode', () => {
    it('serializa um no simples sem filhos', () => {
      const node = makeNode()
      const result = serializeNode(node)
      expect(result.type).toBe('container')
      expect(result.name).toBe('Test Container')
      expect(result.binding).toBe('')
      expect(result.visibility).toBe(true)
      expect(result.properties).toEqual({ width: 100 })
      expect(result.children).toEqual([])
      // Should NOT include id
      expect(result).not.toHaveProperty('id')
    })

    it('serializa recursivamente nos filhos', () => {
      const tree = makeTree()
      const result = serializeNode(tree)
      expect((result.children as any[]).length).toBe(2)
      expect((result.children as any[])[0].name).toBe('Header')
      expect((result.children as any[])[1].name).toBe('Table')
      expect((result.children as any[])[1].children.length).toBe(1)
      expect((result.children as any[])[1].children[0].name).toBe('Cell')
    })

    it('round-trip: serializar e deserializar preserva dados', () => {
      const tree = makeTree()
      const serialized = serializeNode(tree)
      const json = JSON.stringify(serialized)
      const parsed = JSON.parse(json)
      expect(parsed.type).toBe(tree.type)
      expect(parsed.name).toBe(tree.name)
      expect(parsed.properties).toEqual(tree.properties)
      expect(parsed.children.length).toBe(tree.children.length)
      expect(parsed.children[1].children[0].name).toBe('Cell')
    })

    it('preserva binding e isOptional', () => {
      const node = makeNode({ binding: 'data.field', isOptional: true })
      const result = serializeNode(node)
      expect(result.binding).toBe('data.field')
      expect(result.isOptional).toBe(true)
    })
  })

  // ── countNodes ──────────────────────────────────────────────────────────────

  describe('countNodes', () => {
    it('conta 1 para no folha', () => {
      expect(countNodes(makeNode())).toBe(1)
    })

    it('conta todos os nos da arvore', () => {
      const tree = makeTree()
      expect(countNodes(tree)).toBe(4) // root + 2 children + 1 grandchild
    })
  })

  // ── generatePreviewHtml ────────────────────────────────────────────────────

  describe('generatePreviewHtml', () => {
    it('gera HTML para no texto', () => {
      const node = makeNode({ type: 'text', name: 'Hello' })
      const html = generatePreviewHtml(node)
      expect(html).toContain('<span')
      expect(html).toContain('Hello')
    })

    it('gera HTML para no imagem', () => {
      const node = makeNode({ type: 'image', name: 'Logo' })
      const html = generatePreviewHtml(node)
      expect(html).toContain('<img')
      expect(html).toContain('Logo')
    })

    it('gera HTML para tabela', () => {
      const node = makeNode({ type: 'table', name: 'Tabela' })
      const html = generatePreviewHtml(node)
      expect(html).toContain('<table')
    })

    it('gera HTML para container com filhos', () => {
      const tree = makeTree()
      const html = generatePreviewHtml(tree)
      expect(html).toContain('<div')
      expect(html).toContain('Header')
    })

    it('escapa HTML no nome do no', () => {
      const node = makeNode({ name: '<script>alert("xss")</script>' })
      const html = generatePreviewHtml(node)
      expect(html).not.toContain('<script>')
      expect(html).toContain('&lt;script&gt;')
    })
  })

  // ── CRUD operations ────────────────────────────────────────────────────────

  describe('saveComponent / loadComponents / removeComponent', () => {
    it('salva e lista um componente', async () => {
      const { saveComponent, loadComponents, components } = useBibliotecas()
      const node = makeTree()
      const result = await saveComponent('My Header', node)
      expect(result.success).toBe(true)

      await loadComponents()
      expect(components.value.length).toBe(1)
      expect(components.value[0].name).toBe('My Header')
      expect(components.value[0].nodeCount).toBe(4)
    })

    it('remove um componente', async () => {
      const { saveComponent, loadComponents, removeComponent, components } = useBibliotecas()
      const node = makeNode()
      await saveComponent('Comp1', node)
      await loadComponents()
      expect(components.value.length).toBe(1)

      const id = components.value[0].id
      const result = await removeComponent(id)
      expect(result.success).toBe(true)
      expect(components.value.length).toBe(0)
    })

    it('getComponentData deserializa corretamente', async () => {
      const { saveComponent, loadComponents, components, getComponentData } = useBibliotecas()
      const tree = makeTree()
      await saveComponent('Tree Comp', tree)
      await loadComponents()

      const data = getComponentData(components.value[0])
      expect(data.type).toBe('container')
      expect(data.name).toBe('Root')
      expect(data.children.length).toBe(2)
    })
  })

  // ── Existing categories not affected ───────────────────────────────────────

  describe('regressao: categorias existentes nao afetadas', () => {
    it('getByCategory continua funcionando para fonts/css/js', async () => {
      const { getByCategory, loadFiles } = useBibliotecas()
      await loadFiles()
      // Should not throw and should return array
      expect(Array.isArray(getByCategory('fonts'))).toBe(true)
      expect(Array.isArray(getByCategory('css'))).toBe(true)
      expect(Array.isArray(getByCategory('js'))).toBe(true)
    })
  })
})
