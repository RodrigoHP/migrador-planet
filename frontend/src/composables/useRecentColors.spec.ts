import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useRecentColors } from './useRecentColors'

describe('useRecentColors', () => {
  beforeEach(() => {
    localStorage.clear()
    // Reset the module-level state by clearing and re-initializing
    const { clearRecentColors } = useRecentColors()
    clearRecentColors()
  })

  it('starts with empty recent colors', () => {
    const { recentColors } = useRecentColors()
    expect(recentColors.value).toEqual([])
  })

  it('adds a color to recent list', () => {
    const { recentColors, addRecentColor } = useRecentColors()
    addRecentColor('#ff0000')
    expect(recentColors.value).toContain('#ff0000')
  })

  it('removes duplicates and puts most recent first', () => {
    const { recentColors, addRecentColor } = useRecentColors()
    addRecentColor('#ff0000')
    addRecentColor('#00ff00')
    addRecentColor('#ff0000')
    expect(recentColors.value[0]).toBe('#ff0000')
    expect(recentColors.value.filter((c) => c === '#ff0000')).toHaveLength(1)
  })

  it('limits to 8 colors', () => {
    const { recentColors, addRecentColor } = useRecentColors()
    for (let i = 0; i < 10; i++) {
      addRecentColor(`#${i.toString().padStart(6, '0')}`)
    }
    expect(recentColors.value).toHaveLength(8)
  })

  it('persists to localStorage', () => {
    const { addRecentColor } = useRecentColors()
    addRecentColor('#abcdef')
    const stored = JSON.parse(localStorage.getItem('migrador-planet:recent-colors') ?? '[]')
    expect(stored).toContain('#abcdef')
  })

  it('ignores transparent and inherit', () => {
    const { recentColors, addRecentColor } = useRecentColors()
    addRecentColor('transparent')
    addRecentColor('inherit')
    expect(recentColors.value).toHaveLength(0)
  })

  it('clears all recent colors', () => {
    const { recentColors, addRecentColor, clearRecentColors } = useRecentColors()
    addRecentColor('#ff0000')
    clearRecentColors()
    expect(recentColors.value).toHaveLength(0)
  })
})
