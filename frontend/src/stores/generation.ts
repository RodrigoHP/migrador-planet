import { defineStore } from 'pinia'
import type { IASuggestion, ChartjsConfig } from '@/types'

export interface GenerationStore {
  html: string | null
  css: string | null
  js: string | null
  exemplo: string | null
  fidelityScore: number | null
  fidelityComment: string | null
  iaSuggestions: IASuggestion[] | null
  monacoEdits: { html?: string; css?: string; js?: string }
  chartConfigs: Record<string, ChartjsConfig>
  previewJobId: string | null
  previewExpired: boolean
  rightPanel: 'html-preview' | 'monaco' | 'wysiwyg' | 'chartjs-config'
  activeChartId: string | null
}

export const useGenerationStore = defineStore('generation', {
  state: (): GenerationStore => ({
    html: null,
    css: null,
    js: null,
    exemplo: null,
    fidelityScore: null,
    fidelityComment: null,
    iaSuggestions: null,
    monacoEdits: {},
    chartConfigs: {},
    previewJobId: null,
    previewExpired: false,
    rightPanel: 'html-preview',
    activeChartId: null,
  }),
  getters: {
    isFidelityLow: (state) =>
      state.fidelityScore !== null && state.fidelityScore < 70,
  },
})
