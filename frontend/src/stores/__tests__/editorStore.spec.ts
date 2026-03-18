import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEditorStore } from '../editorStore'

describe('editorStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with default values', () => {
    const store = useEditorStore()
    expect(store.activeCenterTab).toBe('canvas')
    expect(store.activeLeftTab).toBe('structure')
    expect(store.zoomLevel).toBe(100)
    expect(store.pdfZoom).toBe(100)
    expect(store.selectedElementId).toBeNull()
    expect(store.coverageMode).toBe(false)
    expect(store.diffMode).toBe(false)
    expect(store.snapEnabled).toBe(false)
    expect(store.autoFixEnabled).toBe(false)
    expect(store.showGuides).toBe(false)
  })

  it('setActiveCenterTab changes tab', () => {
    const store = useEditorStore()
    store.setActiveCenterTab('pdf')
    expect(store.activeCenterTab).toBe('pdf')
    store.setActiveCenterTab('code')
    expect(store.activeCenterTab).toBe('code')
  })

  it('setActiveLeftTab changes tab', () => {
    const store = useEditorStore()
    store.setActiveLeftTab('fields')
    expect(store.activeLeftTab).toBe('fields')
  })

  it('setActiveLeftTab accepts files tab', () => {
    const store = useEditorStore()
    store.setActiveLeftTab('files')
    expect(store.activeLeftTab).toBe('files')
  })

  it('setZoom updates zoom level', () => {
    const store = useEditorStore()
    store.setZoom(150)
    expect(store.zoomLevel).toBe(150)
  })

  it('setPdfZoom updates PDF zoom level', () => {
    const store = useEditorStore()
    store.setPdfZoom(75)
    expect(store.pdfZoom).toBe(75)
  })

  it('selectElement updates selectedElementId', () => {
    const store = useEditorStore()
    store.selectElement('node-1')
    expect(store.selectedElementId).toBe('node-1')
    store.selectElement(null)
    expect(store.selectedElementId).toBeNull()
  })

  it('toggleCoverage flips coverageMode', () => {
    const store = useEditorStore()
    store.toggleCoverage()
    expect(store.coverageMode).toBe(true)
    store.toggleCoverage()
    expect(store.coverageMode).toBe(false)
  })

  it('toggleDiff flips diffMode', () => {
    const store = useEditorStore()
    store.toggleDiff()
    expect(store.diffMode).toBe(true)
    store.toggleDiff()
    expect(store.diffMode).toBe(false)
  })

  it('toggleSnap flips snapEnabled', () => {
    const store = useEditorStore()
    store.toggleSnap()
    expect(store.snapEnabled).toBe(true)
  })

  it('toggleAutoFix flips autoFixEnabled', () => {
    const store = useEditorStore()
    store.toggleAutoFix()
    expect(store.autoFixEnabled).toBe(true)
  })

  it('toggleGuides flips showGuides', () => {
    const store = useEditorStore()
    store.toggleGuides()
    expect(store.showGuides).toBe(true)
  })
})
