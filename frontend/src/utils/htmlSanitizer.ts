/**
 * HTML Sanitizer — DOMPurify wrapper for safe v-html rendering.
 *
 * Story 40.2 — SEC-001: Sanitize v-html usage to prevent XSS attacks.
 * Uses DOMPurify with a strict allowlist of tags and attributes.
 */

import DOMPurify from 'dompurify'

/**
 * Allowed HTML tags for preview rendering in BibliotecaComponentList.
 * Only structural and styling tags are permitted — no scripts, forms, or embeds.
 */
const ALLOWED_TAGS = [
  // Structural
  'div',
  'span',
  'p',
  'br',
  'hr',
  // Text formatting
  'b',
  'i',
  'em',
  'strong',
  'u',
  'sub',
  'sup',
  'small',
  // Lists
  'ul',
  'ol',
  'li',
  // Tables
  'table',
  'thead',
  'tbody',
  'tfoot',
  'tr',
  'th',
  'td',
  'caption',
  'colgroup',
  'col',
  // Media (images only, no iframes/embeds)
  'img',
  'svg',
  'path',
  'rect',
  'circle',
  'line',
  'polyline',
  'polygon',
  'text',
  'g',
  // Headings
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
]

/**
 * Allowed HTML attributes — only safe styling and layout attributes.
 */
const ALLOWED_ATTR = [
  'class',
  'style',
  'id',
  'src',
  'alt',
  'width',
  'height',
  'colspan',
  'rowspan',
  // SVG attributes
  'd',
  'fill',
  'stroke',
  'stroke-width',
  'viewBox',
  'xmlns',
  'x',
  'y',
  'rx',
  'ry',
  'cx',
  'cy',
  'r',
  'x1',
  'y1',
  'x2',
  'y2',
  'points',
  'transform',
  'opacity',
  'font-size',
  'text-anchor',
]

/**
 * Sanitize an HTML string for safe use with v-html.
 *
 * @param dirty - Untrusted HTML string
 * @returns Sanitized HTML string safe for rendering
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false,
  })
}
