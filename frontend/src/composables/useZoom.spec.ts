import { describe, it, expect } from 'vitest'
import { useZoom } from './useZoom'

describe('useZoom', () => {
  it('initializes with default zoom of 100', () => {
    const { zoomLevel } = useZoom()
    expect(zoomLevel.value).toBe(100)
  })

  it('initializes with custom zoom value', () => {
    const { zoomLevel } = useZoom(75)
    expect(zoomLevel.value).toBe(75)
  })

  it('zoomIn increases zoom by ZOOM_STEP', () => {
    const { zoomLevel, zoomIn, ZOOM_STEP } = useZoom(100)
    zoomIn()
    expect(zoomLevel.value).toBe(100 + ZOOM_STEP)
  })

  it('zoomOut decreases zoom by ZOOM_STEP', () => {
    const { zoomLevel, zoomOut, ZOOM_STEP } = useZoom(100)
    zoomOut()
    expect(zoomLevel.value).toBe(100 - ZOOM_STEP)
  })

  it('zoomIn does not exceed ZOOM_MAX', () => {
    const { zoomLevel, zoomIn, ZOOM_MAX } = useZoom(200)
    zoomIn()
    expect(zoomLevel.value).toBe(ZOOM_MAX)
  })

  it('zoomOut does not go below ZOOM_MIN', () => {
    const { zoomLevel, zoomOut, ZOOM_MIN } = useZoom(50)
    zoomOut()
    expect(zoomLevel.value).toBe(ZOOM_MIN)
  })

  it('setZoom clamps to ZOOM_MIN when below range', () => {
    const { zoomLevel, setZoom, ZOOM_MIN } = useZoom()
    setZoom(10)
    expect(zoomLevel.value).toBe(ZOOM_MIN)
  })

  it('setZoom clamps to ZOOM_MAX when above range', () => {
    const { zoomLevel, setZoom, ZOOM_MAX } = useZoom()
    setZoom(9999)
    expect(zoomLevel.value).toBe(ZOOM_MAX)
  })

  it('setZoom accepts values within range', () => {
    const { zoomLevel, setZoom } = useZoom()
    setZoom(120)
    expect(zoomLevel.value).toBe(120)
  })

  it('creates independent instances per call', () => {
    const zoom1 = useZoom(100)
    const zoom2 = useZoom(100)
    zoom1.zoomIn()
    // zoom2 must remain unaffected
    expect(zoom2.zoomLevel.value).toBe(100)
    expect(zoom1.zoomLevel.value).not.toBe(zoom2.zoomLevel.value)
  })

  it('two independent instances track separate state', () => {
    const zoomCanvas = useZoom(100)
    const zoomPdf = useZoom(100)
    zoomCanvas.zoomIn()
    zoomCanvas.zoomIn()
    zoomPdf.zoomOut()
    expect(zoomCanvas.zoomLevel.value).toBe(120)
    expect(zoomPdf.zoomLevel.value).toBe(90)
  })
})
