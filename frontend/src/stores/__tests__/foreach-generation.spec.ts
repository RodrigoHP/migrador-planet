/**
 * foreach-generation.spec.ts — Story 9.5
 *
 * Tests for loop detection and Knockout foreach code generation.
 */
import { describe, it, expect } from 'vitest'
import {
  classifyNode,
  generateForeachBlock,
  generateTableForeach,
  detectArrayFields,
} from '../foreachGeneration'
import type { TreeNode } from '@/types/template.types'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    id: 'node-1',
    type: 'field',
    name: 'Field',
    binding: '',
    isOptional: false,
    children: [],
    properties: {},
    visibility: true,
    ...overrides,
  }
}

// ─── classifyNode ─────────────────────────────────────────────────────────────

describe('classifyNode', () => {
  it('classifies a plain field as fixed', () => {
    const node = makeNode({ binding: 'companyName' })
    const result = classifyNode(node)
    expect(result.classification).toBe('fixed')
  })

  it('classifies a binding ending with "Items" as dynamic', () => {
    const node = makeNode({ binding: 'invoiceItems' })
    const result = classifyNode(node)
    expect(result.classification).toBe('dynamic')
    expect(result.arrayField).toBe('invoiceItems')
  })

  it('classifies a binding ending with "List" as dynamic', () => {
    const node = makeNode({ binding: 'productList' })
    const result = classifyNode(node)
    expect(result.classification).toBe('dynamic')
  })

  it('classifies a binding ending with "Rows" as dynamic', () => {
    const node = makeNode({ binding: 'tableRows' })
    const result = classifyNode(node)
    expect(result.classification).toBe('dynamic')
  })

  it('classifies a binding ending with "Array" as dynamic', () => {
    const node = makeNode({ binding: 'dataArray' })
    const result = classifyNode(node)
    expect(result.classification).toBe('dynamic')
  })

  it('classifies node with isArray property as dynamic', () => {
    const node = makeNode({ binding: 'customField', properties: { isArray: true } })
    const result = classifyNode(node)
    expect(result.classification).toBe('dynamic')
  })

  it('uses node id in result', () => {
    const node = makeNode({ id: 'my-node', binding: 'someItems' })
    const result = classifyNode(node)
    expect(result.nodeId).toBe('my-node')
  })

  it('classifies table with multiple section children as dynamic', () => {
    const node = makeNode({
      type: 'table',
      binding: 'unknownBinding',
      children: [makeNode({ id: 'c1', type: 'section' }), makeNode({ id: 'c2', type: 'section' })],
    })
    const result = classifyNode(node)
    expect(result.classification).toBe('dynamic')
  })

  it('classifies table with single child as fixed', () => {
    const node = makeNode({
      type: 'table',
      binding: 'header',
      children: [makeNode({ id: 'c1', type: 'section' })],
    })
    const result = classifyNode(node)
    expect(result.classification).toBe('fixed')
  })
})

// ─── generateForeachBlock ─────────────────────────────────────────────────────

describe('generateForeachBlock', () => {
  it('wraps content with ko foreach comment', () => {
    const block = generateForeachBlock('invoiceItems', '<tr>...</tr>')
    expect(block.open).toBe('<!-- ko foreach: invoiceItems -->')
    expect(block.close).toBe('<!-- /ko -->')
    expect(block.html).toContain('<!-- ko foreach: invoiceItems -->')
    expect(block.html).toContain('<!-- /ko -->')
    expect(block.html).toContain('<tr>...</tr>')
  })

  it('includes the content between open and close', () => {
    const content = '<span data-bind="text: name"></span>'
    const block = generateForeachBlock('items', content)
    const openIdx = block.html.indexOf(block.open)
    const closeIdx = block.html.indexOf(block.close)
    const contentIdx = block.html.indexOf(content)
    expect(contentIdx).toBeGreaterThan(openIdx)
    expect(contentIdx).toBeLessThan(closeIdx)
  })

  it('uses the arrayField as foreach binding name', () => {
    const block = generateForeachBlock('myArray', '')
    expect(block.open).toBe('<!-- ko foreach: myArray -->')
  })
})

// ─── generateTableForeach ────────────────────────────────────────────────────

describe('generateTableForeach', () => {
  it('generates a table with thead and tbody', () => {
    const html = generateTableForeach('rows', ['Name', 'Amount'], '<tr>...</tr>')
    expect(html).toContain('<table>')
    expect(html).toContain('</table>')
    expect(html).toContain('<thead>')
    expect(html).toContain('</thead>')
    expect(html).toContain('<tbody>')
    expect(html).toContain('</tbody>')
  })

  it('includes header cells', () => {
    const html = generateTableForeach('rows', ['Name', 'Amount'], '')
    expect(html).toContain('<th>Name</th>')
    expect(html).toContain('<th>Amount</th>')
  })

  it('wraps row template in ko foreach', () => {
    const html = generateTableForeach('invoiceItems', ['Col'], '<tr data-bind="...">')
    expect(html).toContain('<!-- ko foreach: invoiceItems -->')
    expect(html).toContain('<!-- /ko -->')
  })

  it('thead appears before tbody', () => {
    const html = generateTableForeach('rows', ['A'], '<tr/>')
    const theadIdx = html.indexOf('<thead>')
    const tbodyIdx = html.indexOf('<tbody>')
    expect(theadIdx).toBeLessThan(tbodyIdx)
  })
})

// ─── detectArrayFields ────────────────────────────────────────────────────────

describe('detectArrayFields', () => {
  it('detects dynamic nodes in a flat tree', () => {
    const root = makeNode({
      id: 'root',
      type: 'document',
      binding: '',
      children: [
        makeNode({ id: 'f1', binding: 'invoiceItems' }),
        makeNode({ id: 'f2', binding: 'companyName' }),
        makeNode({ id: 'f3', binding: 'lineItems' }),
      ],
    })
    const results = detectArrayFields(root)
    const ids = results.map((r) => r.nodeId)
    expect(ids).toContain('f1')
    expect(ids).toContain('f3')
    expect(ids).not.toContain('f2')
  })

  it('detects dynamic nodes recursively', () => {
    const root = makeNode({
      id: 'root',
      type: 'document',
      children: [
        makeNode({
          id: 'section',
          type: 'section',
          children: [makeNode({ id: 'nested', binding: 'dataRows' })],
        }),
      ],
    })
    const results = detectArrayFields(root)
    expect(results.map((r) => r.nodeId)).toContain('nested')
  })

  it('returns empty array when no dynamic nodes', () => {
    const root = makeNode({
      id: 'root',
      type: 'document',
      children: [
        makeNode({ id: 'f1', binding: 'name' }),
        makeNode({ id: 'f2', binding: 'address' }),
      ],
    })
    const results = detectArrayFields(root)
    expect(results).toHaveLength(0)
  })
})
