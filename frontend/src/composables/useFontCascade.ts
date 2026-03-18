import { ref } from 'vue'
import { useBibliotecas } from './useBibliotecas'

// ─── Types ─────────────────────────────────────────────────────────────────────

export type FontStatus = 'found' | 'fallback' | 'not_found'

export interface FontSuggestion {
  name: string
  similarity: number
  source: string
}

export interface FontCascadeResult {
  fontStatus: FontStatus
  suggestedAlternative: string | null
  suggestions: FontSuggestion[]
}

// ─── Normalization Map ─────────────────────────────────────────────────────────

export const FONT_NORMALIZATION_MAP: Record<string, string> = {
  helvetica: 'Arial',
  'helvetica neue': 'Arial',
  times: 'Times New Roman',
  'times roman': 'Times New Roman',
  courier: 'Courier New',
  'courier ps': 'Courier New',
}

export function normalizeFont(fontName: string): string {
  const key = fontName.trim().toLowerCase()
  return FONT_NORMALIZATION_MAP[key] ?? fontName
}

// ─── Composable ───────────────────────────────────────────────────────────────

export function useFontCascade() {
  const fontStatus = ref<FontStatus>('not_found')
  const suggestedAlternative = ref<string | null>(null)
  const suggestions = ref<FontSuggestion[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function resolveFontCascade(fontName: string): Promise<FontCascadeResult> {
    isLoading.value = true
    error.value = null
    fontStatus.value = 'not_found'
    suggestedAlternative.value = null
    suggestions.value = []

    try {
      // Step 1: Check normalization map first
      const normalized = normalizeFont(fontName)
      if (normalized !== fontName) {
        fontStatus.value = 'fallback'
        suggestedAlternative.value = normalized
        return {
          fontStatus: 'fallback',
          suggestedAlternative: normalized,
          suggestions: [{ name: normalized, similarity: 1.0, source: 'normalization' }],
        }
      }

      // Step 2: Check Bibliotecas catalog (IndexedDB)
      const { loadFiles, getByCategory } = useBibliotecas()
      await loadFiles()
      const fontFiles = getByCategory('fonts')
      const fontNameLower = fontName.toLowerCase()
      const foundInCatalog = fontFiles.some(
        (f) =>
          f.name.toLowerCase().replace(/\.(ttf|otf|woff|woff2)$/, '') === fontNameLower ||
          f.name.toLowerCase().includes(fontNameLower),
      )

      if (foundInCatalog) {
        fontStatus.value = 'found'
        suggestedAlternative.value = null
        return { fontStatus: 'found', suggestedAlternative: null, suggestions: [] }
      }

      // Step 3: Call backend to get AI suggestions
      try {
        const response = await fetch('/api/font-identify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ font_name: fontName }),
        })

        if (response.ok) {
          const data = (await response.json()) as {
            original: string
            suggestions: FontSuggestion[]
          }
          if (data.suggestions && data.suggestions.length > 0) {
            const best = data.suggestions[0]!
            suggestions.value = data.suggestions
            suggestedAlternative.value = best.name
            fontStatus.value = 'fallback'
            return {
              fontStatus: 'fallback',
              suggestedAlternative: best.name,
              suggestions: data.suggestions,
            }
          }
        }
      } catch {
        // Backend unavailable — proceed to not_found
      }

      fontStatus.value = 'not_found'
      return { fontStatus: 'not_found', suggestedAlternative: null, suggestions: [] }
    } finally {
      isLoading.value = false
    }
  }

  return {
    fontStatus,
    suggestedAlternative,
    suggestions,
    isLoading,
    error,
    resolveFontCascade,
    normalizeFont,
  }
}
