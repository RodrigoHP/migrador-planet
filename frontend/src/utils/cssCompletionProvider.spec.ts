import { describe, it, expect } from 'vitest'
import { extractSelectors } from './cssCompletionProvider'

describe('extractSelectors', () => {
  it('extracts IDs from HTML', () => {
    const html = '<div id="template-header"><span id="logo"></span></div>'
    const { ids } = extractSelectors(html)
    expect(ids).toContain('template-header')
    expect(ids).toContain('logo')
  })

  it('extracts classes from HTML', () => {
    const html = '<div class="field-group field-value"><span class="label"></span></div>'
    const { classes } = extractSelectors(html)
    expect(classes).toContain('field-group')
    expect(classes).toContain('field-value')
    expect(classes).toContain('label')
  })

  it('deduplicates IDs and classes', () => {
    const html = '<div id="x" class="a b"><span id="x" class="a c"></span></div>'
    const { ids, classes } = extractSelectors(html)
    expect(ids).toEqual(['x'])
    expect(classes).toEqual(['a', 'b', 'c'])
  })

  it('handles empty HTML', () => {
    const { ids, classes } = extractSelectors('')
    expect(ids).toEqual([])
    expect(classes).toEqual([])
  })
})
