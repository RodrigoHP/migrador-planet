/**
 * Tests for htmlSanitizer — Story 40.2, SEC-001.
 *
 * Verifies that DOMPurify-based sanitization removes XSS vectors
 * while preserving safe HTML for component previews.
 */

import { describe, it, expect } from 'vitest'
import { sanitizeHtml } from './htmlSanitizer'

describe('sanitizeHtml', () => {
  // ─── XSS prevention ───────────────────────────────────────────────────

  it('removes script tags', () => {
    const dirty = '<div>Hello</div><script>alert("xss")</script>'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('<script')
    expect(clean).toContain('<div>Hello</div>')
  })

  it('removes onerror event handlers', () => {
    const dirty = '<img src="x" onerror="alert(1)" />'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('onerror')
  })

  it('removes onclick event handlers', () => {
    const dirty = '<div onclick="alert(1)">Click</div>'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('onclick')
  })

  it('removes javascript: URLs from href', () => {
    // <a> tags are not in ALLOWED_TAGS, so they should be stripped entirely
    const dirty = '<a href="javascript:alert(1)">Click</a>'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('javascript:')
    expect(clean).not.toContain('<a ')
  })

  it('removes iframe tags', () => {
    const dirty = '<iframe src="https://evil.com"></iframe>'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('<iframe')
  })

  it('removes object/embed tags', () => {
    const dirty = '<object data="evil.swf"></object><embed src="evil.swf">'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('<object')
    expect(clean).not.toContain('<embed')
  })

  it('removes form tags', () => {
    const dirty = '<form action="https://evil.com"><input type="text"></form>'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('<form')
    expect(clean).not.toContain('<input')
  })

  it('removes data attributes', () => {
    const dirty = '<div data-evil="payload">Content</div>'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('data-evil')
    expect(clean).toContain('Content')
  })

  // ─── Safe HTML preservation ────────────────────────────────────────────

  it('preserves safe div/span tags', () => {
    const html = '<div class="preview"><span>Text</span></div>'
    expect(sanitizeHtml(html)).toBe(html)
  })

  it('preserves table structure', () => {
    const html = '<table><thead><tr><th>Header</th></tr></thead><tbody><tr><td>Cell</td></tr></tbody></table>'
    expect(sanitizeHtml(html)).toBe(html)
  })

  it('preserves img tags with src and alt', () => {
    const html = '<img src="data:image/png;base64,abc" alt="preview">'
    const clean = sanitizeHtml(html)
    expect(clean).toContain('<img')
    expect(clean).toContain('src=')
    expect(clean).toContain('alt=')
  })

  it('preserves inline styles', () => {
    const html = '<div style="color: red; font-size: 12px">Styled</div>'
    const clean = sanitizeHtml(html)
    expect(clean).toContain('style=')
    expect(clean).toContain('Styled')
  })

  it('preserves SVG elements', () => {
    const html = '<svg viewBox="0 0 100 100"><rect x="0" y="0" width="100" height="100" fill="red"></rect></svg>'
    const clean = sanitizeHtml(html)
    expect(clean).toContain('<svg')
    expect(clean).toContain('<rect')
  })

  it('preserves text formatting tags', () => {
    const html = '<p><strong>Bold</strong> and <em>italic</em></p>'
    expect(sanitizeHtml(html)).toBe(html)
  })

  // ─── Edge cases ────────────────────────────────────────────────────────

  it('handles empty string', () => {
    expect(sanitizeHtml('')).toBe('')
  })

  it('handles plain text (no HTML)', () => {
    expect(sanitizeHtml('Hello World')).toBe('Hello World')
  })

  it('handles nested dangerous content', () => {
    const dirty = '<div><div onmouseover="alert(1)"><script>evil()</script>Safe text</div></div>'
    const clean = sanitizeHtml(dirty)
    expect(clean).not.toContain('script')
    expect(clean).not.toContain('onmouseover')
    expect(clean).toContain('Safe text')
  })
})
