// ─── FieldNavigator Types (Story 6.4) ─────────────────────────────────────

export type FieldNavType = 'string' | 'array' | 'chart' | 'section' | 'image'
export type FieldNavStatus = 'mapped' | 'unmapped' | 'unconfirmed'
export type FieldNavSortKey = 'name' | 'status' | 'type'

export interface FieldNavItem {
  name: string
  path: string
  type: FieldNavType
  status: FieldNavStatus
  binding?: string
  nodeId?: string
  isOptional: boolean
}

export interface TypeGroupConfig {
  icon: string
  label: string
}

export const TYPE_GROUPS: Record<FieldNavType, TypeGroupConfig> = {
  string: { icon: '📋', label: 'Campos' },
  array: { icon: '📊', label: 'Tabelas' },
  chart: { icon: '📈', label: 'Gráficos' },
  section: { icon: '📐', label: 'Seções' },
  image: { icon: '🖼️', label: 'Recursos' },
}

export const TYPE_ORDER: FieldNavType[] = ['string', 'array', 'chart', 'section', 'image']

export const STATUS_ORDER: Record<FieldNavStatus, number> = {
  unmapped: 0,
  unconfirmed: 1,
  mapped: 2,
}
