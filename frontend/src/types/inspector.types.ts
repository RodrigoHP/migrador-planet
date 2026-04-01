// ─── Inspector Store Types ────────────────────────────────────────────────

import type { TreeNode } from './template.types'

// Story 28.6: 'structural' added for header/footer/flow nodes that map to StructuralNodeInfo
export type InspectorLevel = 'page' | 'section' | 'component' | 'element' | 'structural'

export interface InspectorState {
  selectedNode: TreeNode | null
  level: InspectorLevel
  properties: Record<string, unknown>
}
