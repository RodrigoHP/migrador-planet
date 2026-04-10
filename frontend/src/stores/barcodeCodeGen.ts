/**
 * Barcode code generation helpers — Story 41.9
 * AC1: generateBarcodeHtmlSnippet — <div data-type="barcode"> placeholder
 * AC2: generateBarcodeJsBlock — JsBarcode("#id", ko.unwrap(data.field), {...})
 * AC3: buildBarcodeJsSection — aggregates all active barcode nodes
 *
 * Analogous to chartCodeGen.ts (Story 9.7 pattern).
 */
import type { TreeNode } from '@/types/template.types'

/**
 * Generate placeholder <div> HTML snippet for a barcode node.
 * AC1: <div id="{nodeId}" data-type="barcode" data-format="{format}" data-value="{previewValue}" style="...">
 */
export function generateBarcodeHtmlSnippet(node: TreeNode): string {
  const { id, properties } = node
  const format = (properties['barcodeFormat'] as string) || 'CODE128'
  const value = (properties['barcodeValue'] as string) || ''
  const x = properties['x'] ?? 0
  const y = properties['y'] ?? 0
  const w = properties['width'] ?? 200
  const h = properties['height'] ?? 60
  return `<div id="${id}" data-type="barcode" data-format="${format}" data-value="${value}" style="position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px;"></div>`
}

/**
 * Generate JsBarcode initialization call for base.js.
 * AC2: JsBarcode("#{nodeId}", ko.unwrap(data.{campo}), { format: "{format}", lineColor: "#000", width: {w}, height: {h}, displayValue: {bool} })
 */
export function generateBarcodeJsBlock(node: TreeNode): string {
  const { id, properties } = node
  const field = (properties['barcodeField'] as string) || 'fieldName'
  const format = (properties['barcodeFormat'] as string) || 'CODE128'
  const lineWidth = (properties['barcodeLineWidth'] as number) ?? 2
  const height = (properties['barcodeHeight'] as number) ?? 60
  const displayValue = (properties['barcodeDisplayValue'] as boolean) ?? true
  return `JsBarcode("#${id}", ko.unwrap(data.${field}), { format: "${format}", lineColor: "#000", width: ${lineWidth}, height: ${height}, displayValue: ${displayValue} })`
}

/**
 * Build the JsBarcode initialization section for base.js.
 * AC3: aggregates all nodes where type === 'barcode' and visibility !== false,
 *       wrapped in a "// ── Barcodes ──" comment block.
 */
export function buildBarcodeJsSection(nodes: TreeNode[]): string {
  const active = nodes.filter((n) => n.type === 'barcode' && n.visibility !== false)
  if (active.length === 0) return ''
  const blocks = active.map((n) => generateBarcodeJsBlock(n)).join('\n')
  return `// ── Barcodes ──\n${blocks}`
}
