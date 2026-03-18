// ─── Editor Store Types ───────────────────────────────────────────────────

export type CenterTab = 'canvas' | 'pdf' | 'code' | 'sync'
export type LeftTab = 'structure' | 'fields' | 'files'

// ─── Code Store Types ──────────────────────────────────────────────────────
export type CodeFileKey = 'html' | 'css' | 'js' | 'exemplo'

export interface CodeFile {
  key: CodeFileKey
  label: string
  path: string
  language: 'html' | 'css' | 'javascript'
  readOnly: boolean
}

export const CODE_FILES: CodeFile[] = [
  { key: 'html',   label: 'index.html',  path: 'Template/index.html',  language: 'html',       readOnly: false },
  { key: 'css',    label: 'style.css',   path: 'css/style.css',         language: 'css',        readOnly: false },
  { key: 'js',     label: 'base.js',     path: 'js/base.js',            language: 'javascript', readOnly: false },
  { key: 'exemplo',label: 'exemplo.js',  path: 'js/exemplo.js',         language: 'javascript', readOnly: true  },
]
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
