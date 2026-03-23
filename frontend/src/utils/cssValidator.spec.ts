import { describe, it, expect } from 'vitest'
import { validateCss } from './cssValidator'

describe('validateCss', () => {
  it('returns no markers for valid CSS', () => {
    const css = `body { margin: 0; }\n.test { color: red; }`
    const markers = validateCss(css)
    expect(markers).toEqual([])
  })

  it('detects unclosed brace', () => {
    const css = `body {\n  margin: 0;\n.test { color: red; }`
    const markers = validateCss(css)
    expect(markers.length).toBeGreaterThan(0)
    expect(markers.some((m) => m.severity === 'error' && m.message.includes('Unclosed'))).toBe(true)
  })

  it('detects unexpected closing brace', () => {
    const css = `body { margin: 0; }}`
    const markers = validateCss(css)
    expect(markers.some((m) => m.severity === 'error' && m.message.includes('Unexpected'))).toBe(true)
  })

  it('detects missing semicolons', () => {
    const css = `.test {\n  color: red\n  margin: 0;\n}`
    const markers = validateCss(css)
    expect(markers.some((m) => m.severity === 'warning' && m.message.includes('semicolon'))).toBe(true)
  })

  it('handles empty CSS', () => {
    expect(validateCss('')).toEqual([])
  })
})
