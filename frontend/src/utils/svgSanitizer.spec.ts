import { describe, it, expect } from 'vitest'
import { sanitizeSvg } from './svgSanitizer'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function wrap(inner: string) {
  return `<svg xmlns="http://www.w3.org/2000/svg">${inner}</svg>`
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('sanitizeSvg', () => {
  it('passes through a clean SVG unchanged in structure', () => {
    const svg = wrap('<circle cx="50" cy="50" r="40" />')
    const result = sanitizeSvg(svg)
    expect(result).toContain('<circle')
    expect(result).toContain('r="40"')
  })

  it('removes <script> tags', () => {
    const svg = wrap('<script>alert("xss")</script><rect width="10" height="10"/>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('<script')
    expect(result).not.toContain('alert')
    expect(result).toContain('<rect')
  })

  it('removes on* event attributes', () => {
    const svg = wrap('<rect onclick="alert(1)" onload="steal()" width="10" height="10"/>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('onclick')
    expect(result).not.toContain('onload')
    expect(result).toContain('<rect')
  })

  it('removes onmouseover attribute', () => {
    const svg = wrap('<circle onmouseover="bad()" cx="5" cy="5" r="5"/>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('onmouseover')
  })

  it('removes href with javascript: URL', () => {
    const svg = wrap('<a href="javascript:alert(1)"><text>click</text></a>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('javascript:')
  })

  it('removes href with javascript: URL on anchor', () => {
    // <use> with xlink namespace can cause parse issues in jsdom; test anchor instead
    const svg = wrap('<a href="javascript:alert(2)"><circle r="5"/></a>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('javascript:')
  })

  it('removes <foreignObject> tags', () => {
    const svg = wrap('<foreignObject><div>evil</div></foreignObject>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('foreignObject')
    expect(result).not.toContain('<div>')
  })

  it('removes <use> tags', () => {
    const svg = wrap('<use href="#malicious"/>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('<use')
  })

  it('keeps safe attributes intact', () => {
    const svg = wrap('<rect id="r1" class="shape" width="100" height="50" fill="#ff0000"/>')
    const result = sanitizeSvg(svg)
    expect(result).toContain('id="r1"')
    expect(result).toContain('class="shape"')
    expect(result).toContain('fill="#ff0000"')
  })

  it('throws on invalid SVG', () => {
    expect(() => sanitizeSvg('not-svg-at-all')).toThrow()
  })

  it('handles nested script tags', () => {
    const svg = wrap('<g><script>evil()</script><path d="M0 0"/></g>')
    const result = sanitizeSvg(svg)
    expect(result).not.toContain('<script')
    expect(result).toContain('<path')
  })
})
