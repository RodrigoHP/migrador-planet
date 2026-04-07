// ─── Template Store Types ─────────────────────────────────────────────────

export type NodeType =
  | 'document'
  | 'header'
  | 'footer'
  | 'flow'
  | 'section'
  | 'table'
  | 'chart'
  | 'image'
  | 'container'
  | 'text'
  | 'field'
  | 'barcode'
  | 'label'
  | 'value'
  | 'likely_dynamic'
  | 'dynamic'

export interface NodeProperties {
  [key: string]: unknown
}

export interface TreeNode {
  id: string
  type: NodeType
  name: string
  binding?: string
  isOptional?: boolean
  children: TreeNode[]
  properties: NodeProperties
  visibility: boolean
}

export interface DocumentTree {
  root: TreeNode
}

// ─── Border Types (Story 14.2) ─────────────────────────────────────────────

export type BorderStyleOption = 'solid' | 'dashed' | 'dotted' | 'double' | 'none'

export interface BorderSideConfig {
  width: number
  color: string
  style: BorderStyleOption
}

export interface BorderRadiusConfig {
  topLeft: number
  topRight: number
  bottomRight: number
  bottomLeft: number
}

export interface BorderConfig {
  top: BorderSideConfig
  right: BorderSideConfig
  bottom: BorderSideConfig
  left: BorderSideConfig
  radius: BorderRadiusConfig
  uniform: boolean
}

export const BORDER_STYLE_OPTIONS: { value: BorderStyleOption; label: string }[] = [
  { value: 'none', label: 'Nenhuma' },
  { value: 'solid', label: 'Sólida' },
  { value: 'dashed', label: 'Tracejada' },
  { value: 'dotted', label: 'Pontilhada' },
  { value: 'double', label: 'Dupla' },
]

export const DEFAULT_BORDER_SIDE: BorderSideConfig = { width: 0, color: '#000000', style: 'none' }
export const DEFAULT_BORDER_RADIUS: BorderRadiusConfig = { topLeft: 0, topRight: 0, bottomRight: 0, bottomLeft: 0 }

// ─── Text Types (Story 14.3) ──────────────────────────────────────────────

export type TextAlign = 'left' | 'center' | 'right' | 'justify'
export type VerticalAlign = 'top' | 'middle' | 'bottom'
export type TextTransform = 'none' | 'uppercase' | 'lowercase' | 'capitalize'
export type FontStyle = 'normal' | 'italic'

export const TEXT_ALIGN_OPTIONS: { value: TextAlign; icon: string; label: string }[] = [
  { value: 'left', icon: '⫷', label: 'Esquerda' },
  { value: 'center', icon: '⫶', label: 'Centro' },
  { value: 'right', icon: '⫸', label: 'Direita' },
  { value: 'justify', icon: '☰', label: 'Justificado' },
]

export const VERTICAL_ALIGN_OPTIONS: { value: VerticalAlign; icon: string; label: string }[] = [
  { value: 'top', icon: '⬆', label: 'Topo' },
  { value: 'middle', icon: '⬌', label: 'Meio' },
  { value: 'bottom', icon: '⬇', label: 'Base' },
]

export const TEXT_DECORATION_OPTIONS: { value: string; icon: string; label: string }[] = [
  { value: 'underline', icon: 'U̲', label: 'Sublinhado' },
  { value: 'overline', icon: 'O̅', label: 'Overline' },
  { value: 'line-through', icon: 'S̶', label: 'Tachado' },
]

export const TEXT_TRANSFORM_OPTIONS: { value: TextTransform; icon: string; label: string }[] = [
  { value: 'none', icon: '—', label: 'Nenhuma' },
  { value: 'uppercase', icon: 'AA', label: 'Maiúsculas' },
  { value: 'lowercase', icon: 'aa', label: 'Minúsculas' },
  { value: 'capitalize', icon: 'Aa', label: 'Capitalizar' },
]

// ─── Table Cell Types (Story 14.4) ────────────────────────────────────────────

export interface CellPadding {
  top: number
  right: number
  bottom: number
  left: number
}

export interface CellProperties {
  border?: BorderConfig
  backgroundColor?: string
  padding?: CellPadding
}

export function createDefaultCellProperties(): CellProperties {
  return {
    border: createDefaultBorderConfig(),
    backgroundColor: '',
    padding: { top: 0, right: 0, bottom: 0, left: 0 },
  }
}

export function getCellKey(row: number, col: number): string {
  return `${row}-${col}`
}

export function createDefaultBorderConfig(): BorderConfig {
  return {
    top: { ...DEFAULT_BORDER_SIDE },
    right: { ...DEFAULT_BORDER_SIDE },
    bottom: { ...DEFAULT_BORDER_SIDE },
    left: { ...DEFAULT_BORDER_SIDE },
    radius: { ...DEFAULT_BORDER_RADIUS },
    uniform: true,
  }
}
