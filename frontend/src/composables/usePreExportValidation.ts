/**
 * usePreExportValidation — Story 8.5
 *
 * Validates the current editor state before export.
 * Checks: ##TEMPLATE_DATA##, ko.applyBindings, data-bind integrity,
 * HTML well-formedness, CSS syntax, and library availability.
 */
import { useCodeStore } from '@/stores/codeStore'
import { useMappingStore } from '@/stores/mapping'
import { SYSTEM_LIBS } from './useBibliotecas'

// ─── Types ─────────────────────────────────────────────────────────────────

export interface PreExportError {
  code: string
  message: string
  blocking: boolean
}

export interface PreExportValidationResult {
  hasBlockingErrors: boolean
  errors: PreExportError[]
  warnings: PreExportError[]
}

// ─── Helpers ───────────────────────────────────────────────────────────────

/** Extract all data-bind attribute values from HTML string */
export function extractDataBindValues(html: string): string[] {
  const results: string[] = []
  const re = /data-bind="([^"]+)"/g
  let m: RegExpExecArray | null
  while ((m = re.exec(html)) !== null) {
    if (m[1]) results.push(m[1])
  }
  return results
}

/**
 * Parse a single Knockout binding expression like "text: fieldName, visible: flag"
 * and return all referenced field/property names.
 */
export function extractBindingFields(bindingExpr: string): string[] {
  const fields: string[] = []
  // Split by comma at top-level (ignoring nested {} or [])
  const parts = splitTopLevel(bindingExpr)
  for (const part of parts) {
    const colonIdx = part.indexOf(':')
    if (colonIdx === -1) continue
    const value = part.slice(colonIdx + 1).trim()
    // Extract identifier — the first word (handles simple "field", "$parent.field")
    const identMatch = value.match(/^[\w.$]+/)
    if (identMatch) {
      fields.push(identMatch[0])
    }
  }
  return fields
}

/** Split a string by commas that are at depth 0 of {}/[] nesting */
function splitTopLevel(expr: string): string[] {
  const parts: string[] = []
  let depth = 0
  let start = 0
  for (let i = 0; i < expr.length; i++) {
    const ch = expr[i]
    if (ch === '{' || ch === '[' || ch === '(') depth++
    else if (ch === '}' || ch === ']' || ch === ')') depth--
    else if (ch === ',' && depth === 0) {
      parts.push(expr.slice(start, i).trim())
      start = i + 1
    }
  }
  parts.push(expr.slice(start).trim())
  return parts
}

/** KO internal variables that should be skipped during validation */
const KO_INTERNAL_VARS = new Set([
  '$data',
  '$parent',
  '$root',
  '$index',
  '$parentContext',
  '$parents',
  '$element',
])

/** Extract paths from KO comment bindings (<!-- ko if: path -->, etc.) */
export function extractKoCommentPaths(html: string): Array<{ type: string; path: string }> {
  const results: Array<{ type: string; path: string }> = []
  const re = /<!--\s*ko\s+(if|foreach|with|ifnot)\s*:\s*([\w.$]+)\s*-->/g
  let m: RegExpExecArray | null
  while ((m = re.exec(html)) !== null) {
    if (m[1] && m[2]) {
      results.push({ type: m[1], path: m[2] })
    }
  }
  return results
}

/** Check if HTML is well-formed using DOMParser */
export function isHtmlWellFormed(html: string): { valid: boolean; error?: string } {
  // In non-browser env (tests), DOMParser may not be available
  if (typeof DOMParser === 'undefined') {
    return { valid: true }
  }
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  const parserError = doc.querySelector('parsererror')
  if (parserError) {
    return { valid: false, error: parserError.textContent ?? 'HTML mal-formado' }
  }
  return { valid: true }
}

/** Basic CSS syntax check: count braces must match */
export function isCssValid(css: string): { valid: boolean; error?: string } {
  let open = 0
  let close = 0
  let inString = false
  let stringChar = ''
  for (let i = 0; i < css.length; i++) {
    const ch = css[i]
    if (inString) {
      if (ch === stringChar && css[i - 1] !== '\\') inString = false
    } else {
      if (ch === '"' || ch === "'") {
        inString = true
        stringChar = ch
      } else if (ch === '{') {
        open++
      } else if (ch === '}') {
        close++
        if (close > open) {
          return { valid: false, error: `Chave de fechamento inesperada na posição ${i}` }
        }
      }
    }
  }
  if (open !== close) {
    return {
      valid: false,
      error: `CSS mal-formado: ${open} chaves abertas, ${close} fechadas`,
    }
  }
  return { valid: true }
}

/** Extract all ../Bibliotecas/ references from HTML content */
export function extractBibliotecaRefs(html: string): string[] {
  const refs: string[] = []
  // Match src="../Bibliotecas/js/foo.js" or href="../Bibliotecas/css/bar.css"
  const re = /(?:src|href)=["']\.\.\/Bibliotecas\/(?:js|css|fonts)\/([^"']+)["']/g
  let m: RegExpExecArray | null
  while ((m = re.exec(html)) !== null) {
    if (m[1]) refs.push(m[1])
  }
  return refs
}

/** Extract asset references (images, fonts) from HTML/CSS */
export function extractAssetRefs(content: string): string[] {
  const refs: string[] = []
  // src="..." or url(...)
  const srcRe = /(?:src)=["'](?!https?:\/\/)(?!\.\.\/Bibliotecas\/)([^"']+)["']/g
  const urlRe = /url\(["']?(?!https?:\/\/)(?!data:)([^"')]+)["']?\)/g
  let m: RegExpExecArray | null
  while ((m = srcRe.exec(content)) !== null) {
    if (m[1] && !m[1].startsWith('js/') && !m[1].startsWith('css/')) refs.push(m[1])
  }
  while ((m = urlRe.exec(content)) !== null) {
    if (m[1]) refs.push(m[1])
  }
  return refs
}

// ─── Composable ────────────────────────────────────────────────────────────

export function usePreExportValidation() {
  /**
   * Validate the current editor state before export.
   * Returns a result with hasBlockingErrors, errors (blocking), and warnings.
   */
  function validate(): PreExportValidationResult {
    const codeStore = useCodeStore()
    const mappingStore = useMappingStore()

    const html = codeStore.fileContents.html ?? ''
    const css = codeStore.fileContents.css ?? ''
    const js = codeStore.fileContents.js ?? ''

    const errors: PreExportError[] = []
    const warnings: PreExportError[] = []

    // ── AC2: ##TEMPLATE_DATA## in HTML ─────────────────────────────────────
    if (!html.includes('##TEMPLATE_DATA##')) {
      errors.push({
        code: 'MISSING_TEMPLATE_DATA',
        message: 'Placeholder ##TEMPLATE_DATA## não encontrado no index.html',
        blocking: true,
      })
    }

    // ── AC3: ko.applyBindings in base.js ───────────────────────────────────
    if (!js.includes('ko.applyBindings')) {
      errors.push({
        code: 'MISSING_KO_APPLY',
        message: 'Chamada ko.applyBindings não encontrada no base.js',
        blocking: true,
      })
    }

    // ── Shared: known paths from XSD mapping ────────────────────────────────
    const knownPaths = new Set(mappingStore.fields.map((f) => f.jsonPath))

    // ── AC4: data-bind fields exist in mappingStore ─────────────────────────
    if (html) {
      const bindingValues = extractDataBindValues(html)
      // KO built-in properties to skip
      const koBuiltins = new Set([
        '$data',
        '$parent',
        '$parents',
        '$root',
        '$index',
        '$element',
        'true',
        'false',
        'null',
        'undefined',
      ])

      for (const bindExpr of bindingValues) {
        const fields = extractBindingFields(bindExpr)
        for (const field of fields) {
          if (koBuiltins.has(field)) continue
          if (field.startsWith('$')) continue
          if (!knownPaths.has(field)) {
            // Check if any path ends with this field name (dot notation)
            const found = [...knownPaths].some(
              (p) => p === field || p.endsWith(`.${field}`) || p.endsWith(`/${field}`),
            )
            if (!found) {
              // Determine if optional or required
              const isOptional = mappingStore.fields.some(
                (f) => f.status === 'optional' && (f.jsonPath === field || f.pdfText === field),
              )
              if (isOptional) {
                warnings.push({
                  code: 'BINDING_OPTIONAL_NOT_MAPPED',
                  message: `Campo opcional não mapeado: "${field}"`,
                  blocking: false,
                })
              } else {
                errors.push({
                  code: 'BINDING_FIELD_NOT_FOUND',
                  message: `Campo "${field}" usado em data-bind não encontrado no XSD`,
                  blocking: true,
                })
              }
            }
          }
        }
      }
    }

    // ── AC9-11: KO comment bindings (Story 14.9) ──────────────────────────
    if (html) {
      const koCommentPaths = extractKoCommentPaths(html)
      for (const { type, path } of koCommentPaths) {
        if (KO_INTERNAL_VARS.has(path)) continue
        if (path.startsWith('$')) continue
        if (!knownPaths.has(path)) {
          const found = [...knownPaths].some(
            (p) => p === path || p.endsWith(`.${path}`) || p.endsWith(`/${path}`),
          )
          if (!found) {
            errors.push({
              code: 'KO_COMMENT_BINDING_INVALID',
              message: `KO comment binding '<!-- ko ${type}: ${path} -->' referencia path '${path}' que não existe no XSD`,
              blocking: true,
            })
          }
        }
      }
    }

    // ── AC6: HTML well-formed ───────────────────────────────────────────────
    if (html) {
      const htmlCheck = isHtmlWellFormed(html)
      if (!htmlCheck.valid) {
        errors.push({
          code: 'HTML_MALFORMED',
          message: `HTML mal-formado: ${htmlCheck.error ?? 'estrutura inválida'}`,
          blocking: true,
        })
      }
    }

    // ── AC9: CSS syntax valid ───────────────────────────────────────────────
    if (css) {
      const cssCheck = isCssValid(css)
      if (!cssCheck.valid) {
        errors.push({
          code: 'CSS_INVALID',
          message: `CSS inválido: ${cssCheck.error ?? 'erro de sintaxe'}`,
          blocking: true,
        })
      }
    }

    // ── AC10: Libraries referenced in HTML exist in catalog ─────────────────
    if (html) {
      const libRefs = extractBibliotecaRefs(html)
      const allLibNames = new Set([
        ...SYSTEM_LIBS,
        // User-uploaded libs follow pattern "category::name" — extract name portion
      ])
      for (const ref of libRefs) {
        const libName = ref.split('/').pop() ?? ref
        if (!allLibNames.has(libName)) {
          warnings.push({
            code: 'LIBRARY_NOT_IN_CATALOG',
            message: `Biblioteca referenciada não encontrada no catálogo: "${libName}"`,
            blocking: false,
          })
        }
      }
    }

    // ── AC5: Asset references ───────────────────────────────────────────────
    if (html || css) {
      const assetRefs = [...extractAssetRefs(html), ...extractAssetRefs(css)]
      for (const ref of assetRefs) {
        // Assets in assets/ folder — we can only warn since we can't verify at runtime
        if (!ref.startsWith('data:') && !ref.startsWith('http')) {
          warnings.push({
            code: 'ASSET_NOT_VERIFIED',
            message: `Referência a asset não verificada: "${ref}"`,
            blocking: false,
          })
        }
      }
    }

    return {
      hasBlockingErrors: errors.length > 0,
      errors,
      warnings,
    }
  }

  return { validate }
}
