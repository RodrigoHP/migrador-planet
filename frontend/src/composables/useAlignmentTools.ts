import type { BoundingBox } from './useCanvasInteraction'

export type Delta = { dx: number; dy: number }

// ─── Alignment Functions ──────────────────────────────────────────────────────

export function alignLeft(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  const minX = Math.min(...[...boxes.values()].map((b) => b.x))
  for (const [id, box] of boxes) {
    deltas.set(id, { dx: minX - box.x, dy: 0 })
  }
  return deltas
}

export function alignCenterH(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  const centers = [...boxes.values()].map((b) => b.x + b.width / 2)
  const avgCenter = centers.reduce((a, b) => a + b, 0) / centers.length
  for (const [id, box] of boxes) {
    deltas.set(id, { dx: avgCenter - (box.x + box.width / 2), dy: 0 })
  }
  return deltas
}

export function alignRight(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  const maxRight = Math.max(...[...boxes.values()].map((b) => b.x + b.width))
  for (const [id, box] of boxes) {
    deltas.set(id, { dx: maxRight - (box.x + box.width), dy: 0 })
  }
  return deltas
}

export function alignTop(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  const minY = Math.min(...[...boxes.values()].map((b) => b.y))
  for (const [id, box] of boxes) {
    deltas.set(id, { dx: 0, dy: minY - box.y })
  }
  return deltas
}

export function alignMiddleV(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  const centers = [...boxes.values()].map((b) => b.y + b.height / 2)
  const avgCenter = centers.reduce((a, b) => a + b, 0) / centers.length
  for (const [id, box] of boxes) {
    deltas.set(id, { dx: 0, dy: avgCenter - (box.y + box.height / 2) })
  }
  return deltas
}

export function alignBottom(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  const maxBottom = Math.max(...[...boxes.values()].map((b) => b.y + b.height))
  for (const [id, box] of boxes) {
    deltas.set(id, { dx: 0, dy: maxBottom - (box.y + box.height) })
  }
  return deltas
}

// ─── Distribution Functions ───────────────────────────────────────────────────

export function distributeH(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  if (boxes.size < 3) return deltas

  const sorted = [...boxes.entries()].sort((a, b) => a[1].x - b[1].x)
  const first = sorted[0]![1]
  const last = sorted[sorted.length - 1]![1]
  const totalWidth = sorted.reduce((sum, [, b]) => sum + b.width, 0)
  const totalSpace = last.x + last.width - first.x - totalWidth
  const gap = totalSpace / (sorted.length - 1)

  let currentX = first.x + first.width + gap
  for (let i = 1; i < sorted.length - 1; i++) {
    const [id, box] = sorted[i]!
    deltas.set(id, { dx: currentX - box.x, dy: 0 })
    currentX += box.width + gap
  }
  return deltas
}

export function distributeV(boxes: Map<string, BoundingBox>): Map<string, Delta> {
  const deltas = new Map<string, Delta>()
  if (boxes.size < 3) return deltas

  const sorted = [...boxes.entries()].sort((a, b) => a[1].y - b[1].y)
  const first = sorted[0]![1]
  const last = sorted[sorted.length - 1]![1]
  const totalHeight = sorted.reduce((sum, [, b]) => sum + b.height, 0)
  const totalSpace = last.y + last.height - first.y - totalHeight
  const gap = totalSpace / (sorted.length - 1)

  let currentY = first.y + first.height + gap
  for (let i = 1; i < sorted.length - 1; i++) {
    const [id, box] = sorted[i]!
    deltas.set(id, { dx: 0, dy: currentY - box.y })
    currentY += box.height + gap
  }
  return deltas
}

export function useAlignmentTools() {
  return {
    alignLeft,
    alignCenterH,
    alignRight,
    alignTop,
    alignMiddleV,
    alignBottom,
    distributeH,
    distributeV,
  }
}
