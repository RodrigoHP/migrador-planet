// ─── Editor Store Types ───────────────────────────────────────────────────

export type CenterTab = 'canvas' | 'pdf' | 'code' | 'sync'
export type LeftTab = 'structure' | 'fields'
export type SidebarTab = string

export interface ToggleStates {
  coverageMode: boolean
  diffMode: boolean
  snapEnabled: boolean
  autoFixEnabled: boolean
  showGuides: boolean
}

export interface EditorState {
  activeCenterTab: CenterTab
  activeLeftTab: LeftTab
  zoomLevel: number
  selectedElementId: string | null
  activeSidebarTab: SidebarTab
  pdfZoom: number
  toggles: ToggleStates
}
