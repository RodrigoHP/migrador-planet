import { defineStore } from 'pinia'
import type { IASuggestion, ChartjsConfig } from '@/types'

export interface TemplateDraft {
  html: string
  css: string
}

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
  // Epic-6 extensions
  templateDraft: TemplateDraft | null
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
    templateDraft: null,
  }),
  getters: {
    isFidelityLow: (state) =>
      state.fidelityScore !== null && state.fidelityScore < 70,
  },
  actions: {
    loadTemplateDraft(draft: { html: string; css: string }) {
      this.templateDraft = { html: draft.html, css: draft.css }
      // Also populate html/css fields for backwards compatibility
      this.html = draft.html
      this.css = draft.css
    },
  },
})
