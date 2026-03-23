/**
 * Color conversion utilities for InspectorColorPicker (Story 14.6)
 */

/** Convert hex color + opacity (0-100) to rgba string */
export function hexToRgba(hex: string, opacity: number): string {
  const clean = hex.replace('#', '')
  const r = parseInt(clean.slice(0, 2), 16)
  const g = parseInt(clean.slice(2, 4), 16)
  const b = parseInt(clean.slice(4, 6), 16)
  const a = Math.round(Math.max(0, Math.min(100, opacity))) / 100
  return `rgba(${r}, ${g}, ${b}, ${a.toFixed(2)})`
}

/** Parse an rgba string into { hex, opacity } */
export function parseRgba(rgba: string): { hex: string; opacity: number } | null {
  const match = rgba.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)/)
  if (!match) return null
  const r = parseInt(match[1]!, 10)
  const g = parseInt(match[2]!, 10)
  const b = parseInt(match[3]!, 10)
  const a = match[4] !== undefined ? parseFloat(match[4]) : 1
  const hex = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
  return { hex, opacity: Math.round(a * 100) }
}

/** Parse any color string into { hex, opacity }. Returns null for non-color values */
export function parseColor(value: string): { hex: string; opacity: number } | null {
  if (!value) return null
  const trimmed = value.trim()
  if (trimmed === 'transparent' || trimmed === 'inherit') return null
  if (trimmed.startsWith('rgba') || trimmed.startsWith('rgb')) return parseRgba(trimmed)
  if (trimmed.startsWith('#') && (trimmed.length === 7 || trimmed.length === 4)) {
    let hex = trimmed
    if (hex.length === 4) {
      hex = `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
    }
    return { hex, opacity: 100 }
  }
  return null
}

/** Check if a string is a valid color value (hex, rgb, rgba, transparent, inherit) */
export function isValidColor(value: string): boolean {
  if (!value) return false
  const t = value.trim().toLowerCase()
  if (t === 'transparent' || t === 'inherit') return true
  if (t.startsWith('#')) return /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(t)
  if (t.startsWith('rgb')) return parseRgba(t) !== null
  return false
}
