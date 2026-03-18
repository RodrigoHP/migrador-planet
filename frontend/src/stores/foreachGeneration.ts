/**
 * foreachGeneration.ts — Story 9.5
 *
 * Loop detection and Knockout foreach generation:
 * - classifyNodeDynamic: classify a node as 'fixed' or 'dynamic'
 * - generateForeachBlock: wrap content in <!-- ko foreach: field --> ... <!-- /ko -->
 * - generateTableForeach: generate a full table with foreach on tbody rows
 * - detectArrayFields: scan a tree for nodes bound to array fields
 */
import type { TreeNode } from '@/types/template.types'

// ─── Types ───────────────────────────────────────────────────────────────────

export type NodeClassification = 'fixed' | 'dynamic'

export interface ClassifiedNode {
  nodeId: string
  classification: NodeClassification
  arrayField?: string
}

export interface ForeachBlock {
  /** The ko foreach comment open */
  open: string
  /** Inner HTML/content */
  content: string
  /** The ko foreach comment close */
  close: string
  /** Full assembled block */
  html: string
}

// ─── Constants ───────────────────────────────────────────────────────────────

/** Patterns that indicate a binding is an array field */
const ARRAY_PATTERNS = [
  /Items$/i,
  /List$/i,
  /Array$/i,
  /Rows?$/i,
  /Entries$/i,
  /Records?$/i,
  /Lines?$/i,
]

// ─── classifyNodeDynamic ─────────────────────────────────────────────────────

/**
 * Classify a node as 'dynamic' (array/loop source) or 'fixed' (scalar).
 *
 * A node is dynamic when:
 * 1. Its binding matches known array naming patterns (XSD arrays)
 * 2. Its type is 'table' and it has child rows that look repetitive
 * 3. It has an explicit 'isArray' property set to true
 */
export function classifyNode(node: TreeNode): ClassifiedNode {
  const binding = node.binding ?? ''

  // Explicit override
  if (node.properties['isArray'] === true) {
    return { nodeId: node.id, classification: 'dynamic', arrayField: binding || undefined }
  }

  // Pattern matching on binding
  for (const pattern of ARRAY_PATTERNS) {
    if (pattern.test(binding)) {
      return { nodeId: node.id, classification: 'dynamic', arrayField: binding }
    }
  }

  // Table with multiple child rows → dynamic
  if (node.type === 'table' && node.children.length > 1) {
    const rowLikeChildren = node.children.filter(
      (c) => c.type === 'section' || c.type === 'container' || c.type === 'field',
    )
    if (rowLikeChildren.length > 1) {
      return { nodeId: node.id, classification: 'dynamic', arrayField: binding || undefined }
    }
  }

  return { nodeId: node.id, classification: 'fixed' }
}

// ─── generateForeachBlock ────────────────────────────────────────────────────

/**
 * Wrap content in a Knockout foreach binding comment block.
 *
 * @param arrayField  - name of the observable array (e.g. "invoiceItems")
 * @param content     - inner HTML to repeat for each item
 */
export function generateForeachBlock(arrayField: string, content: string): ForeachBlock {
  const open = `<!-- ko foreach: ${arrayField} -->`
  const close = `<!-- /ko -->`
  const html = `${open}\n${content}\n${close}`
  return { open, close, content, html }
}

// ─── generateTableForeach ────────────────────────────────────────────────────

/**
 * Generate a complete table HTML with:
 * - Static <thead>
 * - Dynamic <tbody> using ko foreach
 *
 * @param tableBinding  - observable array field name
 * @param headers       - column header labels
 * @param rowTemplate   - HTML for a single row (will be wrapped in foreach)
 */
export function generateTableForeach(
  tableBinding: string,
  headers: string[],
  rowTemplate: string,
): string {
  const theadCells = headers.map((h) => `    <th>${h}</th>`).join('\n')
  const thead = `  <thead>\n    <tr>\n${theadCells}\n    </tr>\n  </thead>`
  const foreach = generateForeachBlock(tableBinding, rowTemplate)
  const tbody = `  <tbody>\n    ${foreach.html}\n  </tbody>`
  return `<table>\n${thead}\n${tbody}\n</table>`
}

// ─── detectArrayFields ────────────────────────────────────────────────────────

/**
 * Walk a node tree and collect all nodes classified as 'dynamic'.
 */
export function detectArrayFields(root: TreeNode): ClassifiedNode[] {
  const results: ClassifiedNode[] = []

  function walk(node: TreeNode) {
    const classified = classifyNode(node)
    if (classified.classification === 'dynamic') {
      results.push(classified)
    }
    for (const child of node.children) {
      walk(child)
    }
  }

  walk(root)
  return results
}
