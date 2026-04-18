/**
 * conditionalStyle.spec.ts — Story 38.2
 *
 * Tests for generateApplyConditionalStyleFn (base.js code generator in baseJsGenerators).
 * Pattern follows reposition.spec.ts.
 */
import { describe, it, expect } from 'vitest'
import { generateApplyConditionalStyleFn } from '@/stores/baseJsGenerators'
import { injectConditionalStyleFunction } from '@/composables/useExport'
import type { TemplateStoreLike } from '@/composables/useExport'
import type { StyleRule } from '@/utils/formatStringGenerator'

// Helper: create a minimal rules JSON string
function makeRulesJson(
  rules: Array<{
    fieldPath: string
    operator: string
    value: string
    property: string
    propertyValue: string
  }>,
): string {
  return JSON.stringify(rules)
}

// ─── generateApplyConditionalStyleFn ────────────────────────────────────────

describe('generateApplyConditionalStyleFn', () => {
  const simpleRulesJson = makeRulesJson([
    {
      fieldPath: 'Status',
      operator: '===',
      value: 'active',
      property: 'color',
      propertyValue: '#00ff00',
    },
  ])

  it('returns a non-empty string', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(typeof fn).toBe('string')
    expect(fn.length).toBeGreaterThan(0)
  })

  it('contains the function name applyConditionalStyle', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(fn).toContain('function applyConditionalStyle(data)')
  })

  it('embeds the rules JSON in the generated code', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(fn).toContain('"Status"')
    expect(fn).toContain('"active"')
    expect(fn).toContain('"#00ff00"')
  })

  it('is valid JavaScript syntax that can be parsed', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(() => new Function(fn)).not.toThrow()
  })

  it('handles empty rules array without errors', () => {
    const fn = generateApplyConditionalStyleFn('[]')
    expect(() => new Function(fn)).not.toThrow()
  })

  it('supports all operator types in generated code', () => {
    const rules = makeRulesJson([
      { fieldPath: 'A', operator: '===', value: 'x', property: 'color', propertyValue: '#111' },
      { fieldPath: 'B', operator: '!==', value: 'y', property: 'color', propertyValue: '#222' },
      { fieldPath: 'C', operator: '>', value: '5', property: 'color', propertyValue: '#333' },
      { fieldPath: 'D', operator: '<', value: '3', property: 'color', propertyValue: '#444' },
      {
        fieldPath: 'E',
        operator: 'contains',
        value: 'z',
        property: 'color',
        propertyValue: '#555',
      },
      { fieldPath: 'F', operator: 'notEmpty', value: '', property: 'color', propertyValue: '#666' },
      { fieldPath: 'G', operator: 'empty', value: '', property: 'color', propertyValue: '#777' },
      { fieldPath: 'H', operator: '>=', value: '10', property: 'color', propertyValue: '#888' },
      { fieldPath: 'I', operator: '<=', value: '2', property: 'color', propertyValue: '#999' },
    ])
    const fn = generateApplyConditionalStyleFn(rules)
    expect(() => new Function(fn)).not.toThrow()
  })

  it('supports all CSS property types in generated code', () => {
    const rules = makeRulesJson([
      { fieldPath: 'F', operator: '===', value: 'x', property: 'color', propertyValue: '#f00' },
      {
        fieldPath: 'F',
        operator: '===',
        value: 'x',
        property: 'background',
        propertyValue: '#0f0',
      },
      { fieldPath: 'F', operator: '===', value: 'x', property: 'image', propertyValue: 'logo.png' },
      {
        fieldPath: 'F',
        operator: '===',
        value: 'x',
        property: 'visibility',
        propertyValue: 'hidden',
      },
      {
        fieldPath: 'F',
        operator: '===',
        value: 'x',
        property: 'border-color',
        propertyValue: '#00f',
      },
      {
        fieldPath: 'F',
        operator: '===',
        value: 'x',
        property: 'font-weight',
        propertyValue: 'bold',
      },
      {
        fieldPath: 'F',
        operator: '===',
        value: 'x',
        property: 'text-decoration',
        propertyValue: 'underline',
      },
      { fieldPath: 'F', operator: '===', value: 'x', property: 'opacity', propertyValue: '0.5' },
    ])
    const fn = generateApplyConditionalStyleFn(rules)
    expect(fn).toContain('el.style.color')
    expect(fn).toContain('el.style.backgroundColor')
    expect(fn).toContain('setAttribute("src"')
    expect(fn).toContain('el.style.visibility')
    expect(fn).toContain('el.style.borderColor')
    expect(fn).toContain('el.style.fontWeight')
    expect(fn).toContain('el.style.textDecoration')
    expect(fn).toContain('el.style.opacity')
  })

  it('contains guard for null data', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(fn).toContain('if (!rules || !rules.length || !data) return')
  })

  it('queries elements by data-conditional-style attribute', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(fn).toContain('data-conditional-style')
    expect(fn).toContain('querySelectorAll')
  })

  it('handles knockout observable fields (calls fieldVal as function)', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(fn).toContain('typeof fieldVal === "function"')
    expect(fn).toContain('fieldVal = fieldVal()')
  })

  it('handles image property with img child elements', () => {
    const fn = generateApplyConditionalStyleFn(simpleRulesJson)
    expect(fn).toContain('querySelectorAll("img")')
    expect(fn).toContain('el.tagName === "IMG"')
  })
})

// ─── injectConditionalStyleFunction ─────────────────────────────────────────

describe('injectConditionalStyleFunction', () => {
  function makeMockStore(
    nodes: Array<{ id: string; styleRules?: StyleRule[] }>,
  ): TemplateStoreLike {
    const map = new Map<string, { id: string; properties: Record<string, unknown> }>()
    for (const n of nodes) {
      map.set(n.id, {
        id: n.id,
        properties: n.styleRules ? { styleRules: n.styleRules } : {},
      })
    }
    return { flatNodes: map }
  }

  const baseHtml =
    '<html><head></head><body><div data-node-id="n1" style="color:black">Hello</div></body></html>'
  const baseJs = '"use strict"; var ViewModel = function() {};'

  it('does not modify JS or HTML when no rules exist', () => {
    const store = makeMockStore([{ id: 'n1' }])
    const result = injectConditionalStyleFunction(baseHtml, baseJs, store)
    expect(result.js).toBe(baseJs)
    expect(result.html).toBe(baseHtml)
  })

  it('injects applyConditionalStyle function into JS when rules exist', () => {
    const store = makeMockStore([
      {
        id: 'n1',
        styleRules: [
          {
            fieldPath: 'Status',
            operator: '===',
            value: 'ok',
            property: 'color',
            propertyValue: 'green',
          },
        ],
      },
    ])
    const result = injectConditionalStyleFunction(baseHtml, baseJs, store)
    expect(result.js).toContain('applyConditionalStyle')
    expect(result.js).toContain('Story 38.2')
  })

  it('injects data-conditional-style attribute into HTML elements', () => {
    const store = makeMockStore([
      {
        id: 'n1',
        styleRules: [
          {
            fieldPath: 'Status',
            operator: '===',
            value: 'ok',
            property: 'color',
            propertyValue: 'green',
          },
        ],
      },
    ])
    const result = injectConditionalStyleFunction(baseHtml, baseJs, store)
    expect(result.html).toContain('data-conditional-style="0"')
  })

  it('injects DOMContentLoaded script before </body>', () => {
    const store = makeMockStore([
      {
        id: 'n1',
        styleRules: [
          {
            fieldPath: 'X',
            operator: '===',
            value: '1',
            property: 'background',
            propertyValue: '#fff',
          },
        ],
      },
    ])
    const result = injectConditionalStyleFunction(baseHtml, baseJs, store)
    expect(result.html).toContain('DOMContentLoaded')
    expect(result.html).toContain('applyConditionalStyle(data)')
  })

  it('handles multiple nodes with rules', () => {
    const html =
      '<html><head></head><body>' +
      '<div data-node-id="n1">A</div>' +
      '<div data-node-id="n2">B</div>' +
      '</body></html>'
    const store = makeMockStore([
      {
        id: 'n1',
        styleRules: [
          { fieldPath: 'A', operator: '===', value: '1', property: 'color', propertyValue: '#f00' },
        ],
      },
      {
        id: 'n2',
        styleRules: [
          {
            fieldPath: 'B',
            operator: '!==',
            value: '2',
            property: 'background',
            propertyValue: '#0f0',
          },
        ],
      },
    ])
    const result = injectConditionalStyleFunction(html, baseJs, store)
    expect(result.html).toContain('data-conditional-style="0"')
    expect(result.html).toContain('data-conditional-style="1"')
  })

  it('skips nodes without valid rules (empty fieldPath)', () => {
    const store = makeMockStore([
      {
        id: 'n1',
        styleRules: [
          { fieldPath: '', operator: '===', value: 'x', property: 'color', propertyValue: '#f00' },
        ],
      },
    ])
    const result = injectConditionalStyleFunction(baseHtml, baseJs, store)
    // No valid rules → no injection
    expect(result.js).toBe(baseJs)
    expect(result.html).toBe(baseHtml)
  })

  it('returns unchanged JS/HTML for empty inputs', () => {
    const store = makeMockStore([])
    expect(injectConditionalStyleFunction('', baseJs, store)).toEqual({ html: '', js: baseJs })
    expect(injectConditionalStyleFunction(baseHtml, '', store)).toEqual({ html: baseHtml, js: '' })
  })

  it('handles node with multiple rules producing multiple indices', () => {
    const store = makeMockStore([
      {
        id: 'n1',
        styleRules: [
          { fieldPath: 'A', operator: '===', value: '1', property: 'color', propertyValue: '#f00' },
          {
            fieldPath: 'B',
            operator: '>',
            value: '5',
            property: 'background',
            propertyValue: '#0f0',
          },
        ],
      },
    ])
    const result = injectConditionalStyleFunction(baseHtml, baseJs, store)
    expect(result.html).toContain('data-conditional-style="0,1"')
  })
})
