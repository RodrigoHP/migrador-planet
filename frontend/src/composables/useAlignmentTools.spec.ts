import { describe, it, expect } from 'vitest'
import {
  alignLeft, alignCenterH, alignRight,
  alignTop, alignMiddleV, alignBottom,
  distributeH, distributeV,
} from './useAlignmentTools'
import type { BoundingBox } from './useCanvasInteraction'

function makeBoxes(entries: [string, BoundingBox][]): Map<string, BoundingBox> {
  return new Map(entries)
}

describe('Alignment — Horizontal', () => {
  const boxes = makeBoxes([
    ['a', { x: 100, y: 50, width: 80, height: 20 }],
    ['b', { x: 300, y: 55, width: 120, height: 20 }],
    ['c', { x: 520, y: 48, width: 60, height: 20 }],
  ])

  it('alignLeft moves all to min x', () => {
    const deltas = alignLeft(boxes)
    expect(deltas.get('a')!.dx).toBe(0) // already at min
    expect(deltas.get('b')!.dx).toBe(-200) // 100 - 300
    expect(deltas.get('c')!.dx).toBe(-420) // 100 - 520
  })

  it('alignRight aligns to rightmost edge', () => {
    const deltas = alignRight(boxes)
    // max right = 520 + 60 = 580
    expect(deltas.get('a')!.dx).toBe(580 - (100 + 80)) // 400
    expect(deltas.get('b')!.dx).toBe(580 - (300 + 120)) // 160
    expect(deltas.get('c')!.dx).toBe(0)
  })

  it('alignCenterH centers on average center x', () => {
    const deltas = alignCenterH(boxes)
    // centers: 140, 360, 550 → avg = 350
    expect(deltas.get('a')!.dx).toBeCloseTo(350 - 140, 1)
    expect(deltas.get('b')!.dx).toBeCloseTo(350 - 360, 1)
    expect(deltas.get('c')!.dx).toBeCloseTo(350 - 550, 1)
  })
})

describe('Alignment — Vertical', () => {
  const boxes = makeBoxes([
    ['a', { x: 100, y: 50, width: 80, height: 20 }],
    ['b', { x: 300, y: 100, width: 120, height: 30 }],
    ['c', { x: 520, y: 200, width: 60, height: 40 }],
  ])

  it('alignTop moves all to min y', () => {
    const deltas = alignTop(boxes)
    expect(deltas.get('a')!.dy).toBe(0)
    expect(deltas.get('b')!.dy).toBe(-50)
    expect(deltas.get('c')!.dy).toBe(-150)
  })

  it('alignBottom aligns to bottommost edge', () => {
    const deltas = alignBottom(boxes)
    // max bottom = 200 + 40 = 240
    expect(deltas.get('a')!.dy).toBe(240 - 70)
    expect(deltas.get('b')!.dy).toBe(240 - 130)
    expect(deltas.get('c')!.dy).toBe(0)
  })

  it('alignMiddleV centers on average center y', () => {
    const deltas = alignMiddleV(boxes)
    // centers: 60, 115, 220 → avg ≈ 131.67
    const avg = (60 + 115 + 220) / 3
    expect(deltas.get('a')!.dy).toBeCloseTo(avg - 60, 1)
    expect(deltas.get('b')!.dy).toBeCloseTo(avg - 115, 1)
    expect(deltas.get('c')!.dy).toBeCloseTo(avg - 220, 1)
  })
})

describe('Distribution', () => {
  it('distributeH with 3 elements calculates uniform spacing', () => {
    const boxes = makeBoxes([
      ['a', { x: 0, y: 0, width: 40, height: 20 }],
      ['b', { x: 200, y: 0, width: 40, height: 20 }],
      ['c', { x: 100, y: 0, width: 40, height: 20 }], // middle one out of place
    ])
    const deltas = distributeH(boxes)
    // sorted by x: a(0), c(100), b(200)
    // total span: 0 to 240, total width = 120, total space = 120, gap = 60
    // c should be at 0+40+60 = 100 → dx = 0 (already there)
    expect(deltas.size).toBe(1) // only middle elements get deltas
    expect(deltas.get('c')!.dx).toBe(0) // already at correct position
  })

  it('distributeH returns empty for 2 elements', () => {
    const boxes = makeBoxes([
      ['a', { x: 0, y: 0, width: 40, height: 20 }],
      ['b', { x: 200, y: 0, width: 40, height: 20 }],
    ])
    expect(distributeH(boxes).size).toBe(0)
  })

  it('distributeV with 3 elements calculates uniform spacing', () => {
    const boxes = makeBoxes([
      ['a', { x: 0, y: 0, width: 20, height: 30 }],
      ['b', { x: 0, y: 50, width: 20, height: 30 }], // middle
      ['c', { x: 0, y: 180, width: 20, height: 30 }],
    ])
    const deltas = distributeV(boxes)
    // sorted by y: a(0), b(50), c(180)
    // total span: 0 to 210, total height = 90, space = 120, gap = 60
    // b should be at 0+30+60 = 90 → dx = 90 - 50 = 40
    expect(deltas.get('b')!.dy).toBe(40)
  })

  it('distributeV returns empty for 2 elements', () => {
    const boxes = makeBoxes([
      ['a', { x: 0, y: 0, width: 20, height: 30 }],
      ['b', { x: 0, y: 100, width: 20, height: 30 }],
    ])
    expect(distributeV(boxes).size).toBe(0)
  })
})
