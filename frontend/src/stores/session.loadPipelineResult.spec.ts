import { describe, it, expect } from 'vitest'
import {
  sanitizeTemplateName,
  applyTableCellFlags,
  extractGridInfoFromTree,
  parseDataFile,
} from './session.loadPipelineResult'
import type { TreeNode } from '@/types/template.types'

describe('session.loadPipelineResult', () => {
  describe('sanitizeTemplateName', () => {
    it('strips HTML tags', () => {
      expect(sanitizeTemplateName('<b>Test</b>')).toBe('Test')
    })

    it('limits to 100 characters', () => {
      const long = 'a'.repeat(200)
      expect(sanitizeTemplateName(long).length).toBe(100)
    })

    it('removes special characters', () => {
      expect(sanitizeTemplateName('test@#$%name')).toBe('testname')
    })

    it('trims whitespace', () => {
      expect(sanitizeTemplateName('  hello world  ')).toBe('hello world')
    })

    it('collapses multiple spaces', () => {
      expect(sanitizeTemplateName('hello   world')).toBe('hello world')
    })
  })

  describe('applyTableCellFlags', () => {
    it('marks node with matching block_id as table cell', () => {
      const node: TreeNode = {
        id: 'n1',
        type: 'field',
        name: 'test',
        block_id: 'b1',
        children: [],
        properties: {},
      }
      const ids = new Set(['b1'])
      applyTableCellFlags(node, ids)
      expect(node.properties.is_table_cell).toBe(true)
    })

    it('does not mark node when block_id is not in set', () => {
      const node: TreeNode = {
        id: 'n1',
        type: 'field',
        name: 'test',
        block_id: 'b1',
        children: [],
        properties: {},
      }
      const ids = new Set(['b99'])
      applyTableCellFlags(node, ids)
      expect(node.properties.is_table_cell).toBeUndefined()
    })

    it('marks parent and child when child block_id matches', () => {
      const child: TreeNode = {
        id: 'c1',
        type: 'value',
        name: 'val',
        block_id: 'b2',
        children: [],
        properties: {},
      }
      const parent: TreeNode = {
        id: 'p1',
        type: 'field',
        name: 'parent',
        children: [child],
        properties: {},
      }
      applyTableCellFlags(parent, new Set(['b2']))
      expect(parent.properties.is_table_cell).toBe(true)
      expect(child.properties.is_table_cell).toBe(true)
    })
  })

  describe('extractGridInfoFromTree', () => {
    it('returns undefined for empty tree', () => {
      expect(extractGridInfoFromTree(undefined)).toBeUndefined()
    })

    it('returns undefined when no column_positions found', () => {
      const tree = {
        root: { id: 'r', type: 'page' as const, name: 'r', children: [], properties: {} },
      }
      expect(extractGridInfoFromTree(tree)).toBeUndefined()
    })

    it('extracts column positions from tree', () => {
      const tree = {
        root: {
          id: 'r',
          type: 'page' as const,
          name: 'r',
          column_positions: [100, 300, 500],
          children: [],
          properties: {},
        },
      }
      const info = extractGridInfoFromTree(tree)
      expect(info).toBeDefined()
      expect(info!.columns).toBe(3)
      expect(info!.columnPositions).toEqual([100, 300, 500])
    })
  })

  describe('parseDataFile', () => {
    it('parses JSON data file', async () => {
      const bytes = new TextEncoder().encode(JSON.stringify({ name: 'test', value: 42 }))
      const result = await parseDataFile({ name: 'test.json', bytes } as any)
      expect(result).toEqual({ name: 'test', value: 42 })
    })

    it('returns null for invalid content', async () => {
      const bytes = new TextEncoder().encode('not json or xml')
      const result = await parseDataFile({ name: 'test.txt', bytes } as any)
      expect(result).toBeNull()
    })
  })
})
