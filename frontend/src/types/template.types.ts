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
