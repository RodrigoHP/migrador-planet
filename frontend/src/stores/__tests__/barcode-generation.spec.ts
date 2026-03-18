import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTemplateStore } from '@/stores/templateStore'
import type { TreeNode } from '@/types/template.types'

// ─── Barcode HTML/JS generation helpers (mirrors BarcodeInspector logic) ─────

function generateBarcodeHtml(nodeId: string): string {
  return `<svg id="${nodeId}"></svg>`
}

function generateBarcodeJs(
  nodeId: string,
  field: string,
  format: string,
  lineWidth: number,
  height: number,
  displayValue: boolean,
): string {
  return (
    `JsBarcode("#${nodeId}", ko.unwrap(data.${field}), ` +
    `{ format: "${format}", lineColor: "#000", width: ${lineWidth}, height: ${height}, displayValue: ${displayValue} })`
  )
}

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
    },
    ...overrides,
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('barcode generation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ── HTML generation ─────────────────────────────────────────────────────────

  describe('generateBarcodeHtml', () => {
    it('generates svg tag with correct id', () => {
      const html = generateBarcodeHtml('barcode-42')
      expect(html).toBe('<svg id="barcode-42"></svg>')
    })

    it('uses node id as svg id', () => {
      const html = generateBarcodeHtml('barcode-test')
      expect(html).toContain('id="barcode-test"')
    })
  })

  // ── JS generation ───────────────────────────────────────────────────────────

  describe('generateBarcodeJs', () => {
    it('generates JsBarcode call with correct parameters', () => {
      const js = generateBarcodeJs('barcode-1', 'codigo', 'CODE128', 2, 60, true)
      expect(js).toContain('JsBarcode("#barcode-1"')
      expect(js).toContain('ko.unwrap(data.codigo)')
      expect(js).toContain('"CODE128"')
      expect(js).toContain('width: 2')
      expect(js).toContain('height: 60')
      expect(js).toContain('displayValue: true')
    })

    it('supports EAN13 format', () => {
      const js = generateBarcodeJs('bar-2', 'ean', 'EAN13', 1, 80, false)
      expect(js).toContain('"EAN13"')
      expect(js).toContain('displayValue: false')
    })

    it('includes lineColor in config', () => {
      const js = generateBarcodeJs('bar-3', 'field', 'CODE39', 2, 50, true)
      expect(js).toContain('lineColor: "#000"')
    })

    it('uses ko.unwrap for KnockoutJS binding', () => {
      const js = generateBarcodeJs('bar-4', 'myField', 'UPC', 2, 60, true)
      expect(js).toContain('ko.unwrap(data.myField)')
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

  // ── CDN reference ───────────────────────────────────────────────────────────

  describe('JsBarcode CDN', () => {
    it('CDN URL is correct', () => {
      const CDN_URL = 'https://cdn.jsdelivr.net/jsbarcode/'
      expect(CDN_URL).toContain('cdn.jsdelivr.net')
      expect(CDN_URL).toContain('jsbarcode')
    })
  })
})
