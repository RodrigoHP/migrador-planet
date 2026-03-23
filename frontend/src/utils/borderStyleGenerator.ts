import type { NodeProperties } from '@/types/template.types'

const BORDER_SIDES = ['top', 'right', 'bottom', 'left'] as const
const RADIUS_CORNERS = [
  ['border_radius_top_left', 'topLeft'],
  ['border_radius_top_right', 'topRight'],
  ['border_radius_bottom_right', 'bottomRight'],
  ['border_radius_bottom_left', 'bottomLeft'],
] as const

/**
 * Generate CSS rules for a single node's border properties.
 * Returns empty string if the node has no border properties.
 */
export function generateNodeBorderCss(nodeId: string, props: NodeProperties): string {
  const rules: string[] = []

  for (const side of BORDER_SIDES) {
    const w = props[`border_${side}_width`] as number | undefined
    const s = props[`border_${side}_style`] as string | undefined
    const c = props[`border_${side}_color`] as string | undefined
    if (w !== undefined && w > 0 && s && s !== 'none') {
      rules.push(`border-${side}: ${w}px ${s} ${c || '#000000'}`)
    } else if (s === 'none' || (w !== undefined && w === 0)) {
      rules.push(`border-${side}: none`)
    }
  }

  const radiusParts: string[] = []
  for (const [propKey] of RADIUS_CORNERS) {
    const v = props[propKey] as number | undefined
    radiusParts.push(v !== undefined && v > 0 ? `${v}px` : '0')
  }
  if (radiusParts.some((p) => p !== '0')) {
    rules.push(`border-radius: ${radiusParts.join(' ')}`)
  }

  if (rules.length === 0) return ''
  return `[data-node-id="${nodeId}"] { ${rules.join('; ')}; }`
}

// ─── Text Property Overrides (Story 14.3) ────────────────────────────────────

const APPEARANCE_CSS_PROPS: [string, string][] = [
  ['background_color', 'background-color'],
  ['padding_top', 'padding-top'],
  ['padding_right', 'padding-right'],
  ['padding_bottom', 'padding-bottom'],
  ['padding_left', 'padding-left'],
]

/**
 * Generate CSS rules for a single node's appearance properties (e.g. background-color).
 * (Story 14.6)
 */
export function generateNodeAppearanceCss(nodeId: string, props: NodeProperties): string {
  const rules: string[] = []
  for (const [propKey, cssProp] of APPEARANCE_CSS_PROPS) {
    const v = props[propKey]
    if (v === undefined || v === null || v === 'inherit') continue
    if (typeof v === 'number') {
      if (v > 0) rules.push(`${cssProp}: ${v}px`)
    } else if (typeof v === 'string' && v) {
      rules.push(`${cssProp}: ${v}`)
    }
  }
  if (rules.length === 0) return ''
  return `[data-node-id="${nodeId}"] { ${rules.join('; ')}; }`
}

const TEXT_CSS_PROPS: [string, string][] = [
  ['text_align', 'text-align'],
  ['vertical_align', 'vertical-align'],
  ['text_decoration', 'text-decoration'],
  ['text_transform', 'text-transform'],
  ['font_style', 'font-style'],
]

/**
 * Generate CSS rules for a single node's text properties.
 */
export function generateNodeTextCss(nodeId: string, props: NodeProperties): string {
  const rules: string[] = []
  for (const [propKey, cssProp] of TEXT_CSS_PROPS) {
    const v = props[propKey] as string | undefined
    if (v && v !== 'none' && v !== 'normal' && v !== 'left') {
      rules.push(`${cssProp}: ${v}`)
    }
  }
  if (rules.length === 0) return ''
  return `[data-node-id="${nodeId}"] { ${rules.join('; ')}; }`
}

// ─── Table Cell Overrides (Story 14.4) ────────────────────────────────────────

interface CellPropsLike {
  border?: {
    top: { width: number; style: string; color: string }
    right: { width: number; style: string; color: string }
    bottom: { width: number; style: string; color: string }
    left: { width: number; style: string; color: string }
    radius: { topLeft: number; topRight: number; bottomRight: number; bottomLeft: number }
  }
  backgroundColor?: string
  padding?: { top: number; right: number; bottom: number; left: number }
}

function generateCellCss(nodeId: string, cellKey: string, cell: CellPropsLike): string {
  const rules: string[] = []
  if (cell.border) {
    const b = cell.border
    for (const side of BORDER_SIDES) {
      const s = b[side]
      if (s && s.width > 0 && s.style && s.style !== 'none') {
        rules.push(`border-${side}: ${s.width}px ${s.style} ${s.color || '#000000'}`)
      }
    }
    const r = b.radius
    if (r) {
      const parts = [r.topLeft, r.topRight, r.bottomRight, r.bottomLeft]
      if (parts.some((v) => v > 0)) {
        rules.push(`border-radius: ${parts.map((v) => (v > 0 ? `${v}px` : '0')).join(' ')}`)
      }
    }
  }
  if (cell.backgroundColor) {
    rules.push(`background-color: ${cell.backgroundColor}`)
  }
  if (cell.padding) {
    const pd = cell.padding
    if (pd.top || pd.right || pd.bottom || pd.left) {
      rules.push(`padding: ${pd.top}px ${pd.right}px ${pd.bottom}px ${pd.left}px`)
    }
  }
  if (rules.length === 0) return ''
  const [row, col] = cellKey.split('-')
  return `[data-node-id="${nodeId}"] tr:nth-child(${Number(row) + 1}) td:nth-child(${Number(col) + 1}) { ${rules.join('; ')}; }`
}

function generateTableOverrides(nodeId: string, props: NodeProperties): string[] {
  const lines: string[] = []
  // border-collapse
  const collapse = props['border_collapse']
  if (collapse === false) {
    lines.push(`[data-node-id="${nodeId}"] table, [data-node-id="${nodeId}"][data-type="table"] { border-collapse: separate; }`)
  }
  // cell properties
  const cells = props['cells'] as Record<string, CellPropsLike> | undefined
  if (cells) {
    for (const [key, cell] of Object.entries(cells)) {
      const css = generateCellCss(nodeId, key, cell)
      if (css) lines.push(css)
    }
  }
  return lines
}

/**
 * Generate CSS override block for all nodes in the flat map that have border or text properties.
 */
export function generateAllBorderOverrides(flatMap: Map<string, { properties: NodeProperties }>): string {
  const lines: string[] = []
  for (const [nodeId, node] of flatMap) {
    const borderCss = generateNodeBorderCss(nodeId, node.properties)
    if (borderCss) lines.push(borderCss)
    const textCss = generateNodeTextCss(nodeId, node.properties)
    if (textCss) lines.push(textCss)
    const appearanceCss = generateNodeAppearanceCss(nodeId, node.properties)
    if (appearanceCss) lines.push(appearanceCss)
    const tableCss = generateTableOverrides(nodeId, node.properties)
    lines.push(...tableCss)
  }
  return lines.length > 0 ? `\n/* Inspector overrides */\n${lines.join('\n')}` : ''
}
