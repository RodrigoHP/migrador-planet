/**
 * usePreExportValidation — Story 8.5 unit tests
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import {
  extractDataBindValues,
  extractBindingFields,
  extractKoCommentPaths,
  isCssValid,
  isHtmlWellFormed,
  extractBibliotecaRefs,
  extractAssetRefs,
  usePreExportValidation,
} from './usePreExportValidation'
import { useCodeStore } from '@/stores/codeStore'
import { useMappingStore } from '@/stores/mapping'

// ─── Helper: set code store contents ──────────────────────────────────────

function setCode(html: string, css = '', js = '') {
  const codeStore = useCodeStore()
  codeStore.fileContents.html = html
  codeStore.fileContents.css = css
  codeStore.fileContents.js = js
}

// ─── extractDataBindValues ─────────────────────────────────────────────────

describe('extractDataBindValues', () => {
  it('extracts single data-bind attribute', () => {
    const html = '<span data-bind="text: name"></span>'
    expect(extractDataBindValues(html)).toEqual(['text: name'])
  })

  it('extracts multiple data-bind attributes', () => {
    const html = '<span data-bind="text: a"></span><div data-bind="visible: b"></div>'
    expect(extractDataBindValues(html)).toEqual(['text: a', 'visible: b'])
  })

  it('returns empty array when no data-bind', () => {
    expect(extractDataBindValues('<div></div>')).toEqual([])
  })
})

// ─── extractBindingFields ──────────────────────────────────────────────────

describe('extractBindingFields', () => {
  it('extracts simple field name', () => {
    expect(extractBindingFields('text: myField')).toContain('myField')
  })

  it('extracts multiple fields from compound binding', () => {
    const fields = extractBindingFields('text: firstName, visible: isActive')
    expect(fields).toContain('firstName')
    expect(fields).toContain('isActive')
  })

  it('handles nested objects without crashing', () => {
    const fields = extractBindingFields('attr: { class: statusClass }')
    // Should not throw and should return something
    expect(Array.isArray(fields)).toBe(true)
  })
})

// ─── isCssValid ───────────────────────────────────────────────────────────

describe('isCssValid', () => {
  it('valid CSS returns true', () => {
    const css = 'body { margin: 0; } .cls { color: red; }'
    expect(isCssValid(css).valid).toBe(true)
  })

  it('mismatched braces returns false', () => {
    const css = 'body { margin: 0;'
    expect(isCssValid(css).valid).toBe(false)
  })

  it('extra closing brace returns false', () => {
    const css = 'body { margin: 0; }}'
    expect(isCssValid(css).valid).toBe(false)
  })

  it('empty CSS is valid', () => {
    expect(isCssValid('').valid).toBe(true)
  })
})

// ─── isHtmlWellFormed ─────────────────────────────────────────────────────

describe('isHtmlWellFormed', () => {
  it('returns valid:true in non-browser env (DOMParser absent)', () => {
    // In Vitest (jsdom) DOMParser is available — just test it does not throw
    const result = isHtmlWellFormed('<html><body><p>Hello</p></body></html>')
    expect(result.valid).toBe(true)
  })

  it('does not throw on empty string', () => {
    const result = isHtmlWellFormed('')
    expect(typeof result.valid).toBe('boolean')
  })
})

// ─── extractBibliotecaRefs ────────────────────────────────────────────────

describe('extractBibliotecaRefs', () => {
  it('extracts JS library reference', () => {
    const html = '<script src="../Bibliotecas/js/knockout-3.4.2.js"></script>'
    expect(extractBibliotecaRefs(html)).toContain('knockout-3.4.2.js')
  })

  it('extracts CSS library reference', () => {
    const html = '<link href="../Bibliotecas/css/reset.css" />'
    expect(extractBibliotecaRefs(html)).toContain('reset.css')
  })

  it('returns empty for no refs', () => {
    expect(extractBibliotecaRefs('<div></div>')).toEqual([])
  })
})

// ─── extractAssetRefs ─────────────────────────────────────────────────────

describe('extractAssetRefs', () => {
  it('extracts image src', () => {
    const html = '<img src="images/logo.png" />'
    const refs = extractAssetRefs(html)
    expect(refs).toContain('images/logo.png')
  })

  it('ignores http URLs', () => {
    const html = '<img src="https://example.com/img.png" />'
    expect(extractAssetRefs(html)).not.toContain('https://example.com/img.png')
  })

  it('extracts CSS url() references', () => {
    const css = 'body { background: url("images/bg.png"); }'
    const refs = extractAssetRefs(css)
    expect(refs).toContain('images/bg.png')
  })
})

// ─── usePreExportValidation — integration ─────────────────────────────────

describe('usePreExportValidation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('valid template with ##TEMPLATE_DATA## and ko.applyBindings passes', () => {
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##</body></html>',
      'body { margin: 0; }',
      '(function(){ ko.applyBindings({}); })();',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    expect(result.hasBlockingErrors).toBe(false)
    expect(result.errors).toHaveLength(0)
  })

  it('missing ##TEMPLATE_DATA## produces blocking error', () => {
    setCode(
      '<!DOCTYPE html><html><body><p>no placeholder</p></body></html>',
      'body { margin: 0; }',
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    expect(result.hasBlockingErrors).toBe(true)
    const codes = result.errors.map((e) => e.code)
    expect(codes).toContain('MISSING_TEMPLATE_DATA')
  })

  it('missing ko.applyBindings produces blocking error', () => {
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##</body></html>',
      'body {}',
      '(function(){ /* no bindings */ })();',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    expect(result.hasBlockingErrors).toBe(true)
    const codes = result.errors.map((e) => e.code)
    expect(codes).toContain('MISSING_KO_APPLY')
  })

  it('invalid CSS produces blocking error', () => {
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##</body></html>',
      'body { margin: 0;', // missing closing brace
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    expect(result.hasBlockingErrors).toBe(true)
    const codes = result.errors.map((e) => e.code)
    expect(codes).toContain('CSS_INVALID')
  })

  it('asset refs produce warnings (not blocking errors)', () => {
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##<img src="images/logo.png" /></body></html>',
      'body {}',
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    // Should have warning for unverified asset, not blocking
    const warnCodes = result.warnings.map((w) => w.code)
    expect(warnCodes).toContain('ASSET_NOT_VERIFIED')
    // warnings don't set hasBlockingErrors
    expect(result.hasBlockingErrors).toBe(false)
  })

  it('unknown library reference produces warning', () => {
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##<script src="../Bibliotecas/js/unknown-lib.js"></script></body></html>',
      'body {}',
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    const warnCodes = result.warnings.map((w) => w.code)
    expect(warnCodes).toContain('LIBRARY_NOT_IN_CATALOG')
    expect(result.hasBlockingErrors).toBe(false)
  })

  it('data-bind field not in mapping store produces blocking error', () => {
    // Set up mapping store with known fields
    const mappingStore = useMappingStore()
    mappingStore.setFields([
      {
        id: '1',
        pdfText: 'Nome',
        jsonPath: 'cliente.nome',
        type: 'text',
        confidence: 'high',
        status: 'ok',
        isManual: false,
      },
    ])
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##<span data-bind="text: campoDesconhecido"></span></body></html>',
      'body {}',
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    const codes = result.errors.map((e) => e.code)
    expect(codes).toContain('BINDING_FIELD_NOT_FOUND')
  })

  it('both ##TEMPLATE_DATA## and ko.applyBindings missing: two blocking errors', () => {
    setCode(
      '<html><body><p>nothing</p></body></html>',
      'body {}',
      '// no bindings',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    expect(result.hasBlockingErrors).toBe(true)
    const codes = result.errors.map((e) => e.code)
    expect(codes).toContain('MISSING_TEMPLATE_DATA')
    expect(codes).toContain('MISSING_KO_APPLY')
  })

  it('KO comment with invalid path produces blocking error', () => {
    const mappingStore = useMappingStore()
    mappingStore.setFields([
      { id: '1', pdfText: 'Nome', jsonPath: 'cliente.nome', type: 'text', confidence: 'high', status: 'ok', isManual: false },
    ])
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##<!-- ko if: secao_invalida -->test<!-- /ko --></body></html>',
      'body {}',
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    const codes = result.errors.map((e) => e.code)
    expect(codes).toContain('KO_COMMENT_BINDING_INVALID')
  })

  it('KO comment with valid path passes', () => {
    const mappingStore = useMappingStore()
    mappingStore.setFields([
      { id: '1', pdfText: 'Nome', jsonPath: 'cliente.nome', type: 'text', confidence: 'high', status: 'ok', isManual: false },
    ])
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##<!-- ko if: cliente.nome -->test<!-- /ko --></body></html>',
      'body {}',
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    const codes = result.errors.map((e) => e.code)
    expect(codes).not.toContain('KO_COMMENT_BINDING_INVALID')
  })

  it('KO comment with $data/$parent/$root is skipped (not validated)', () => {
    setCode(
      '<!DOCTYPE html><html><body>##TEMPLATE_DATA##<!-- ko if: $data -->a<!-- /ko --><!-- ko with: $parent -->b<!-- /ko --></body></html>',
      'body {}',
      'ko.applyBindings({});',
    )
    const { validate } = usePreExportValidation()
    const result = validate()
    const codes = result.errors.map((e) => e.code)
    expect(codes).not.toContain('KO_COMMENT_BINDING_INVALID')
  })
})

// ─── extractKoCommentPaths ──────────────────────────────────────────────────

describe('extractKoCommentPaths', () => {
  it('extracts if binding', () => {
    const paths = extractKoCommentPaths('<!-- ko if: secao -->content<!-- /ko -->')
    expect(paths).toEqual([{ type: 'if', path: 'secao' }])
  })

  it('extracts foreach binding', () => {
    const paths = extractKoCommentPaths('<!-- ko foreach: items --><!-- /ko -->')
    expect(paths).toEqual([{ type: 'foreach', path: 'items' }])
  })

  it('extracts multiple bindings', () => {
    const html = '<!-- ko if: a --><!-- ko foreach: b --><!-- /ko --><!-- /ko -->'
    const paths = extractKoCommentPaths(html)
    expect(paths).toHaveLength(2)
    expect(paths[0]).toEqual({ type: 'if', path: 'a' })
    expect(paths[1]).toEqual({ type: 'foreach', path: 'b' })
  })

  it('handles dot notation paths', () => {
    const paths = extractKoCommentPaths('<!-- ko with: dados.cliente.nome -->')
    expect(paths).toEqual([{ type: 'with', path: 'dados.cliente.nome' }])
  })

  it('returns empty for no KO comments', () => {
    expect(extractKoCommentPaths('<div>no comments</div>')).toEqual([])
  })
})
