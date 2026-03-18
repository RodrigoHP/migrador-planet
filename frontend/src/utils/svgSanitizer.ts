// ─── SVG Sanitizer ────────────────────────────────────────────────────────────
// Removes potentially dangerous content from SVG strings before inline insertion.

const DANGEROUS_TAGS = ['script', 'foreignObject', 'use']

/**
 * Sanitize an SVG string for safe inline insertion into HTML.
 * Removes <script> tags, on* event attributes, and javascript: URLs.
 *
 * @param svgString - Raw SVG text content
 * @returns Sanitized SVG string
 */
export function sanitizeSvg(svgString: string): string {
  const parser = new DOMParser()
  const doc = parser.parseFromString(svgString, 'image/svg+xml')

  // Check for parse errors
  const parseError = doc.querySelector('parsererror')
  if (parseError) {
    throw new Error('SVG inválido: não foi possível analisar o conteúdo.')
  }

  const svgEl = doc.documentElement

  // Remove dangerous tags
  for (const tag of DANGEROUS_TAGS) {
    const elements = svgEl.querySelectorAll(tag)
    elements.forEach((el) => el.remove())
  }

  // Walk all elements and sanitize attributes
  const allElements = svgEl.querySelectorAll('*')
  const toRemove: Array<{ el: Element; attr: string }> = []

  // Also sanitize the root SVG element itself
  sanitizeElement(svgEl, toRemove)
  allElements.forEach((el) => sanitizeElement(el, toRemove))

  for (const { el, attr } of toRemove) {
    el.removeAttribute(attr)
  }

  return svgEl.outerHTML
}

function sanitizeElement(el: Element, toRemove: Array<{ el: Element; attr: string }>) {
  for (let i = 0; i < el.attributes.length; i++) {
    const attr = el.attributes[i]
    if (!attr) continue
    const name = attr.name.toLowerCase()
    const value = attr.value.toLowerCase().trim()

    // Remove on* event handlers
    if (name.startsWith('on')) {
      toRemove.push({ el, attr: attr.name })
      continue
    }

    // Remove javascript: URLs
    if (value.startsWith('javascript:') || value.startsWith('data:text/html')) {
      toRemove.push({ el, attr: attr.name })
      continue
    }
  }
}
