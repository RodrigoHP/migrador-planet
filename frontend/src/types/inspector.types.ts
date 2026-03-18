// ─── Inspector Store Types ────────────────────────────────────────────────

import type { TreeNode } from './template.types'

export type InspectorLevel = 'page' | 'section' | 'component' | 'element'

export interface InspectorState {
  selectedNode: TreeNode | null
  level: InspectorLevel
  properties: Record<string, unknown>
}
