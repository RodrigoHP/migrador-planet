/**
 * Composable for managing recent colors with localStorage persistence (Story 14.6)
 */
import { ref } from 'vue'

const STORAGE_KEY = 'migrador-planet:recent-colors'
const MAX_RECENT = 8

function loadFromStorage(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.slice(0, MAX_RECENT) : []
  } catch {
    return []
  }
}

function saveToStorage(colors: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(colors))
  } catch {
    // localStorage may be unavailable in some environments
  }
}

const recentColors = ref<string[]>(loadFromStorage())

export function useRecentColors() {
  function addRecentColor(color: string) {
    if (!color || color === 'transparent' || color === 'inherit') return
    const filtered = recentColors.value.filter((c) => c !== color)
    filtered.unshift(color)
    recentColors.value = filtered.slice(0, MAX_RECENT)
    saveToStorage(recentColors.value)
  }

  function clearRecentColors() {
    recentColors.value = []
    saveToStorage([])
  }

  return {
    recentColors,
    addRecentColor,
    clearRecentColors,
  }
}
