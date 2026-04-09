/**
 * reposition.spec.ts — Story 9.6
 *
 * Tests for:
 * - repositionFixedElement (Layout Engine mirror in usePagination)
 * - generateReposicionarElementoFixoFn (base.js code generator in baseJsGenerators)
 *
 * These are pure unit tests — no DOM required.
 */
import { describe, it, expect } from 'vitest'
import { repositionFixedElement } from '@/composables/usePagination'
import type { FixedElementDescriptor, DynamicElementDescriptor } from '@/composables/usePagination'
import { generateReposicionarElementoFixoFn } from '@/stores/baseJsGenerators'

// ─── repositionFixedElement (Layout Engine) ──────────────────────────────────

describe('repositionFixedElement', () => {
  it('places fixed element immediately below reference element', () => {
    const fixedEl: FixedElementDescriptor = { id: 'fixed-1', top: 0, height: 50 }
    const refEl: DynamicElementDescriptor = { id: 'ref-1', top: 100, height: 200 }
    // expected: refEl.top + refEl.height + gap = 100 + 200 + 0 = 300
    expect(repositionFixedElement(fixedEl, refEl)).toBe(300)
  })

  it('respects gap value from fixedEl.gap', () => {
    const fixedEl: FixedElementDescriptor = { id: 'fixed-1', top: 0, height: 50, gap: 20 }
    const refEl: DynamicElementDescriptor = { id: 'ref-1', top: 100, height: 200 }
    // expected: 100 + 200 + 20 = 320
    expect(repositionFixedElement(fixedEl, refEl)).toBe(320)
  })

  it('defaults gap to 0 when not provided', () => {
    const fixedEl: FixedElementDescriptor = { id: 'fixed-1', top: 500, height: 30 }
    const refEl: DynamicElementDescriptor = { id: 'ref-1', top: 50, height: 75 }
    // expected: 50 + 75 + 0 = 125
    expect(repositionFixedElement(fixedEl, refEl)).toBe(125)
  })

  it('works when reference element is at top of page (top=0)', () => {
    const fixedEl: FixedElementDescriptor = { id: 'fixed-1', top: 0, height: 40 }
    const refEl: DynamicElementDescriptor = { id: 'ref-1', top: 0, height: 150 }
    // expected: 0 + 150 + 0 = 150
    expect(repositionFixedElement(fixedEl, refEl)).toBe(150)
  })

  it('works with large gap values', () => {
    const fixedEl: FixedElementDescriptor = { id: 'fixed-1', top: 0, height: 40, gap: 100 }
    const refEl: DynamicElementDescriptor = { id: 'ref-1', top: 200, height: 300 }
    // expected: 200 + 300 + 100 = 600
    expect(repositionFixedElement(fixedEl, refEl)).toBe(600)
  })

  it('handles zero-height reference element', () => {
    const fixedEl: FixedElementDescriptor = { id: 'fixed-1', top: 0, height: 40, gap: 10 }
    const refEl: DynamicElementDescriptor = { id: 'ref-1', top: 50, height: 0 }
    // expected: 50 + 0 + 10 = 60
    expect(repositionFixedElement(fixedEl, refEl)).toBe(60)
  })

  it('returns same result as base.js algorithm formula', () => {
    // The formula: el.style.top = referenceEl.offsetTop + referenceEl.offsetHeight + gap
    const gap = 15
    const refTop = 400
    const refHeight = 350
    const expected = refTop + refHeight + gap

    const fixedEl: FixedElementDescriptor = { id: 'f', top: 100, height: 40, gap }
    const refEl: DynamicElementDescriptor = { id: 'r', top: refTop, height: refHeight }
    expect(repositionFixedElement(fixedEl, refEl)).toBe(expected)
  })
})

// ─── generateReposicionarElementoFixoFn ─────────────────────────────────────

describe('generateReposicionarElementoFixoFn', () => {
  it('returns a non-empty string', () => {
    const fn = generateReposicionarElementoFixoFn()
    expect(typeof fn).toBe('string')
    expect(fn.length).toBeGreaterThan(0)
  })

  it('contains the function name reposicionarElementoFixo', () => {
    const fn = generateReposicionarElementoFixoFn()
    expect(fn).toContain('reposicionarElementoFixo')
  })

  it('contains el and referenceEl parameters', () => {
    const fn = generateReposicionarElementoFixoFn()
    expect(fn).toContain('el')
    expect(fn).toContain('referenceEl')
  })

  it('contains guard for null/undefined elements', () => {
    const fn = generateReposicionarElementoFixoFn()
    expect(fn).toContain('if (!el || !referenceEl) return')
  })

  it('contains gap calculation from data-gap attribute', () => {
    const fn = generateReposicionarElementoFixoFn()
    expect(fn).toContain('dataset.gap')
    expect(fn).toContain('parseInt')
  })

  it('contains the repositioning formula (offsetTop + offsetHeight + gap)', () => {
    const fn = generateReposicionarElementoFixoFn()
    expect(fn).toContain('offsetTop')
    expect(fn).toContain('offsetHeight')
    expect(fn).toContain('el.style.top')
  })

  it('is valid JavaScript syntax that can be parsed', () => {
    const fn = generateReposicionarElementoFixoFn()
    // Wrap in a IIFE and parse via Function constructor (no eval)
    expect(() => new Function(fn)).not.toThrow()
  })

  it('generated function sets top to referenceEl position + height + gap', () => {
    const code = generateReposicionarElementoFixoFn()
    // Create a scope-safe wrapper to test runtime behavior
    const wrapper = new Function(
      'return (function() {' + code + '; return reposicionarElementoFixo; })();',
    )
    const reposicionarElementoFixo = wrapper()

    // Mock elements
    const refEl = { offsetTop: 200, offsetHeight: 150 }
    const fixedEl = { dataset: { gap: '10' }, style: { top: '' } }

    reposicionarElementoFixo(fixedEl, refEl)
    // expected: 200 + 150 + 10 = 360px
    expect(fixedEl.style.top).toBe('360px')
  })

  it('generated function uses gap=0 when data-gap is not set', () => {
    const code = generateReposicionarElementoFixoFn()
    const wrapper = new Function(
      'return (function() {' + code + '; return reposicionarElementoFixo; })();',
    )
    const reposicionarElementoFixo = wrapper()

    const refEl = { offsetTop: 100, offsetHeight: 80 }
    const fixedEl = { dataset: {}, style: { top: '' } }

    reposicionarElementoFixo(fixedEl, refEl)
    // expected: 100 + 80 + 0 = 180px
    expect(fixedEl.style.top).toBe('180px')
  })

  it('generated function returns early when el is null', () => {
    const code = generateReposicionarElementoFixoFn()
    const wrapper = new Function(
      'return (function() {' + code + '; return reposicionarElementoFixo; })();',
    )
    const reposicionarElementoFixo = wrapper()

    const refEl = { offsetTop: 100, offsetHeight: 80 }
    // Should not throw when el is null
    expect(() => reposicionarElementoFixo(null, refEl)).not.toThrow()
  })

  it('generated function returns early when referenceEl is null', () => {
    const code = generateReposicionarElementoFixoFn()
    const wrapper = new Function(
      'return (function() {' + code + '; return reposicionarElementoFixo; })();',
    )
    const reposicionarElementoFixo = wrapper()

    const fixedEl = { dataset: {}, style: { top: '' } }
    // Should not throw when referenceEl is null
    expect(() => reposicionarElementoFixo(fixedEl, null)).not.toThrow()
    // top should remain unchanged
    expect(fixedEl.style.top).toBe('')
  })
})

// ─── Algorithm parity: Layout Engine vs base.js ──────────────────────────────

describe('algorithm parity: repositionFixedElement matches generated JS', () => {
  it('both produce the same result for identical inputs', () => {
    const code = generateReposicionarElementoFixoFn()
    const wrapper = new Function(
      'return (function() {' + code + '; return reposicionarElementoFixo; })();',
    )
    const jsFunc = wrapper()

    const gap = 25
    const refTop = 300
    const refHeight = 200

    // Layout Engine (pure TS)
    const fixedEl: FixedElementDescriptor = { id: 'f', top: 0, height: 50, gap }
    const refEl: DynamicElementDescriptor = { id: 'r', top: refTop, height: refHeight }
    const tsResult = repositionFixedElement(fixedEl, refEl)

    // Generated JS function
    const mockFixed = { dataset: { gap: String(gap) }, style: { top: '' } }
    const mockRef = { offsetTop: refTop, offsetHeight: refHeight }
    jsFunc(mockFixed, mockRef)
    const jsResult = parseInt(mockFixed.style.top, 10)

    expect(tsResult).toBe(jsResult)
  })
})
