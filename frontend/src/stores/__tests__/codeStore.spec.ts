import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCodeStore } from '../codeStore'
import { CODE_FILES } from '@/types/editor.types'

// Mock templateStore to avoid circular imports and deep watchers
vi.mock('../templateStore', () => ({
  useTemplateStore: () => ({
    documentTree: null,
    flatNodes: new Map(),
  }),
}))

describe('codeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes with default file contents', () => {
    const store = useCodeStore()
    expect(store.fileContents.html).toContain('DOCTYPE html')
    expect(store.fileContents.css).toContain('Template styles')
    expect(store.fileContents.js).toContain('base.js')
    expect(store.fileContents.exemplo).toContain('exemplo.js')
  })

  it('initializes with html as active file', () => {
    const store = useCodeStore()
    expect(store.activeFile).toBe('html')
  })

  it('setActiveFile changes active file', () => {
    const store = useCodeStore()
    store.setActiveFile('css')
    expect(store.activeFile).toBe('css')
  })

  it('setFileContent updates writable file content', () => {
    const store = useCodeStore()
    store.setFileContent('html', '<html>new</html>')
    expect(store.fileContents.html).toBe('<html>new</html>')
  })

  it('setFileContent does NOT update read-only file (exemplo)', () => {
    const store = useCodeStore()
    const original = store.fileContents.exemplo
    store.setFileContent('exemplo', 'hacked content')
    expect(store.fileContents.exemplo).toBe(original)
  })

  it('applyMonacoEdit updates html content', () => {
    const store = useCodeStore()
    store.applyMonacoEdit('html', '<html>edited</html>')
    expect(store.fileContents.html).toBe('<html>edited</html>')
  })

  it('applyMonacoEdit does NOT update read-only exemplo file', () => {
    const store = useCodeStore()
    const original = store.fileContents.exemplo
    store.applyMonacoEdit('exemplo', 'hacked')
    expect(store.fileContents.exemplo).toBe(original)
  })

  it('applyMonacoEdit buffers edit when externalChangeDetected is true', () => {
    const store = useCodeStore()
    store.externalChangeDetected = true
    store.applyMonacoEdit('css', 'buffered content')
    expect(store.fileContents.css).not.toBe('buffered content')
    expect(store.pendingMonacoEdit).toEqual({ key: 'css', content: 'buffered content' })
  })

  it('resolveExternalChange with keepMonaco=true applies pending edit', () => {
    const store = useCodeStore()
    store.externalChangeDetected = true
    store.applyMonacoEdit('css', '.foo { color: red; }')
    store.resolveExternalChange(true)
    expect(store.fileContents.css).toBe('.foo { color: red; }')
    expect(store.externalChangeDetected).toBe(false)
    expect(store.pendingMonacoEdit).toBeNull()
  })

  it('resolveExternalChange with keepMonaco=false discards pending edit', () => {
    const store = useCodeStore()
    const originalCss = store.fileContents.css
    store.externalChangeDetected = true
    store.pendingMonacoEdit = { key: 'css', content: 'something' }
    store.resolveExternalChange(false)
    expect(store.fileContents.css).toBe(originalCss)
    expect(store.externalChangeDetected).toBe(false)
    expect(store.pendingMonacoEdit).toBeNull()
  })

  it('dismissExternalChange clears state', () => {
    const store = useCodeStore()
    store.externalChangeDetected = true
    store.pendingMonacoEdit = { key: 'html', content: 'x' }
    store.dismissExternalChange()
    expect(store.externalChangeDetected).toBe(false)
    expect(store.pendingMonacoEdit).toBeNull()
  })

  it('CODE_FILES has 4 entries', () => {
    expect(CODE_FILES).toHaveLength(4)
  })

  it('CODE_FILES exemplo.js is readOnly', () => {
    const exemploFile = CODE_FILES.find((f) => f.key === 'exemplo')
    expect(exemploFile?.readOnly).toBe(true)
  })

  it('CODE_FILES other files are not readOnly', () => {
    const editableFiles = CODE_FILES.filter((f) => f.key !== 'exemplo')
    editableFiles.forEach((f) => {
      expect(f.readOnly).toBe(false)
    })
  })

  it('CODE_FILES have correct languages', () => {
    const htmlFile = CODE_FILES.find((f) => f.key === 'html')
    const cssFile = CODE_FILES.find((f) => f.key === 'css')
    const jsFile = CODE_FILES.find((f) => f.key === 'js')
    const exemploFile = CODE_FILES.find((f) => f.key === 'exemplo')
    expect(htmlFile?.language).toBe('html')
    expect(cssFile?.language).toBe('css')
    expect(jsFile?.language).toBe('javascript')
    expect(exemploFile?.language).toBe('javascript')
  })
})
