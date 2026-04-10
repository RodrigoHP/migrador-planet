import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTemplateStore } from '@/stores/templateStore'
import type { TreeNode } from '@/types/template.types'
import {
  generateBarcodeHtmlSnippet,
  generateBarcodeJsBlock,
  buildBarcodeJsSection,
} from '@/stores/barcodeCodeGen'

// ─── Test helpers ─────────────────────────────────────────────────────────────

function buildBarcodeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    id: 'barcode-1',
    type: 'barcode',
    name: 'Barcode 1',
    children: [],
    visibility: true,
    properties: {
      barcodeFormat: 'CODE128',
      barcodeField: 'codigoBarras',
      barcodeLineWidth: 2,
      barcodeHeight: 60,
      barcodeDisplayValue: true,
      x: 10,
      y: 20,
      width: 200,
      height: 60,
    },
    ...overrides,
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('barcode generation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ── generateBarcodeHtmlSnippet (AC1) ────────────────────────────────────────

  describe('generateBarcodeHtmlSnippet', () => {
    it('generates div with correct id and data attributes', () => {
      const node = buildBarcodeNode()
      const html = generateBarcodeHtmlSnippet(node)
      expect(html).toContain('id="barcode-1"')
      expect(html).toContain('data-type="barcode"')
      expect(html).toContain('data-format="CODE128"')
      expect(html).toContain('data-value="')
    })

    it('uses position:absolute style with node coordinates', () => {
      const node = buildBarcodeNode()
      const html = generateBarcodeHtmlSnippet(node)
      expect(html).toContain('position:absolute')
      expect(html).toContain('left:10px')
      expect(html).toContain('top:20px')
      expect(html).toContain('width:200px')
      expect(html).toContain('height:60px')
    })

    it('defaults to CODE128 format when barcodeFormat not set', () => {
      const node = buildBarcodeNode({ properties: {} })
      const html = generateBarcodeHtmlSnippet(node)
      expect(html).toContain('data-format="CODE128"')
    })

    it('uses node id', () => {
      const node = buildBarcodeNode({ id: 'barcode-42' })
      const html = generateBarcodeHtmlSnippet(node)
      expect(html).toContain('id="barcode-42"')
    })
  })

  // ── generateBarcodeJsBlock (AC2) ────────────────────────────────────────────

  describe('generateBarcodeJsBlock', () => {
    it('generates JsBarcode call with correct parameters', () => {
      const node = buildBarcodeNode()
      const js = generateBarcodeJsBlock(node)
      expect(js).toContain('JsBarcode("#barcode-1"')
      expect(js).toContain('ko.unwrap(data.codigoBarras)')
      expect(js).toContain('"CODE128"')
      expect(js).toContain('width: 2')
      expect(js).toContain('height: 60')
      expect(js).toContain('displayValue: true')
    })

    it('supports EAN13 format', () => {
      const node = buildBarcodeNode({
        properties: {
          barcodeFormat: 'EAN13',
          barcodeField: 'ean',
          barcodeLineWidth: 1,
          barcodeHeight: 80,
          barcodeDisplayValue: false,
        },
      })
      const js = generateBarcodeJsBlock(node)
      expect(js).toContain('"EAN13"')
      expect(js).toContain('displayValue: false')
    })

    it('includes lineColor in config', () => {
      const node = buildBarcodeNode()
      const js = generateBarcodeJsBlock(node)
      expect(js).toContain('lineColor: "#000"')
    })

    it('uses ko.unwrap for KnockoutJS binding', () => {
      const node = buildBarcodeNode({
        properties: {
          barcodeField: 'myField',
        },
      })
      const js = generateBarcodeJsBlock(node)
      expect(js).toContain('ko.unwrap(data.myField)')
    })

    it('defaults to fieldName when barcodeField not set', () => {
      const node = buildBarcodeNode({ properties: {} })
      const js = generateBarcodeJsBlock(node)
      expect(js).toContain('ko.unwrap(data.fieldName)')
    })
  })

  // ── buildBarcodeJsSection (AC3) ─────────────────────────────────────────────

  describe('buildBarcodeJsSection', () => {
    it('returns empty string when no barcode nodes', () => {
      const result = buildBarcodeJsSection([])
      expect(result).toBe('')
    })

    it('returns empty string when only non-barcode nodes', () => {
      const textNode: TreeNode = {
        id: 'text-1',
        type: 'text',
        name: 'Text',
        children: [],
        visibility: true,
        properties: {},
      }
      const result = buildBarcodeJsSection([textNode])
      expect(result).toBe('')
    })

    it('generates section header comment for single barcode node', () => {
      const node = buildBarcodeNode()
      const result = buildBarcodeJsSection([node])
      expect(result).toContain('// ── Barcodes ──')
      expect(result).toContain('JsBarcode("#barcode-1"')
    })

    it('aggregates multiple barcode nodes', () => {
      const node1 = buildBarcodeNode({ id: 'barcode-1' })
      const node2 = buildBarcodeNode({ id: 'barcode-2' })
      const result = buildBarcodeJsSection([node1, node2])
      expect(result).toContain('JsBarcode("#barcode-1"')
      expect(result).toContain('JsBarcode("#barcode-2"')
    })

    it('excludes hidden barcode nodes (visibility === false)', () => {
      const visible = buildBarcodeNode({ id: 'barcode-visible', visibility: true })
      const hidden = buildBarcodeNode({ id: 'barcode-hidden', visibility: false })
      const result = buildBarcodeJsSection([visible, hidden])
      expect(result).toContain('barcode-visible')
      expect(result).not.toContain('barcode-hidden')
    })

    it('returns empty string when all barcode nodes are hidden', () => {
      const hidden = buildBarcodeNode({ visibility: false })
      const result = buildBarcodeJsSection([hidden])
      expect(result).toBe('')
    })
  })

  // ── TemplateStore integration ───────────────────────────────────────────────

  describe('templateStore barcode node', () => {
    it('can load a tree with a barcode node', () => {
      const store = useTemplateStore()
      store.loadTree({
        root: {
          id: 'root',
          type: 'document',
          name: 'Document',
          children: [buildBarcodeNode()],
          properties: {},
          visibility: true,
        },
      })
      const nodes = store.getNodesByType('barcode')
      expect(nodes).toHaveLength(1)
      expect(nodes[0]!.properties['barcodeFormat']).toBe('CODE128')
    })

    it('can update barcode format property', () => {
      const store = useTemplateStore()
      store.loadTree({
        root: {
          id: 'root',
          type: 'document',
          name: 'Document',
          children: [buildBarcodeNode()],
          properties: {},
          visibility: true,
        },
      })
      store.updateNodeProperty('barcode-1', 'barcodeFormat', 'EAN13')
      const node = store.getNodeById('barcode-1')
      expect(node?.properties['barcodeFormat']).toBe('EAN13')
    })

    it('can update barcode field binding', () => {
      const store = useTemplateStore()
      store.loadTree({
        root: {
          id: 'root',
          type: 'document',
          name: 'Document',
          children: [buildBarcodeNode()],
          properties: {},
          visibility: true,
        },
      })
      store.updateNodeProperty('barcode-1', 'barcodeField', 'numeroPedido')
      const node = store.getNodeById('barcode-1')
      expect(node?.properties['barcodeField']).toBe('numeroPedido')
    })
  })
})
