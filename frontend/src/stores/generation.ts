import { defineStore } from 'pinia'
import type { IASuggestion, ChartjsConfig } from '@/types'

export interface TemplateDraft {
  html: string
  css: string
}

/**
 * Paginated format — one entry per document page.
 * HTMLCanvas consumes this format for multi-page rendering.
 */
export interface TemplateDraftPage {
  pageNum: number
  html: string
  css: string
}

/**
 * Input formats accepted by loadTemplateDraft().
 *
 * - Monolítico (backend atual): `{ html: string, css: string }`
 * - Paginado (future / pre-adapted): `{ pages: TemplateDraftPage[] }`
 * - Paginado legado: `TemplateDraftPage[]`
 */
export type TemplateDraftInput =
  | { html: string; css: string }
  | { pages: TemplateDraftPage[] }
  | TemplateDraftPage[]

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
    /**
     * Adaptador de formato para template_draft.
     *
     * Aceita 3 formatos de entrada:
     * 1. Monolítico `{ html, css }` — formato atual do backend (Stage 28)
     * 2. Objeto paginado `{ pages: [{pageNum, html, css}] }` — formato futuro
     * 3. Array paginado `[{pageNum, html, css}]` — formato legado alternativo
     *
     * Sempre converte para TemplateDraft `{ html, css }` internamente.
     * O HTMLCanvas.vue converte `{html, css}` → pages[] via DOMParser autonomamente.
     *
     * Fallback: se `template_draft` vier como string monolítica ou páginas vazias,
     * armazena `{html: '', css: ''}` sem quebrar.
     */
    loadTemplateDraft(draft: TemplateDraftInput) {
      let html = ''
      let css = ''

      if (Array.isArray(draft)) {
        // Format 3: TemplateDraftPage[] — join all pages into monolithic HTML
        const pages = draft as TemplateDraftPage[]
        css = pages[0]?.css ?? ''
        html = pages.map((p) => p.html).join('\n')
      } else if ('pages' in draft && Array.isArray((draft as { pages: TemplateDraftPage[] }).pages)) {
        // Format 2: { pages: TemplateDraftPage[] }
        const pages = (draft as { pages: TemplateDraftPage[] }).pages
        css = pages[0]?.css ?? ''
        html = pages.map((p) => p.html).join('\n')
      } else {
        // Format 1: { html, css } — canonical monolithic format from Stage 28
        const mono = draft as { html: string; css: string }
        html = mono.html ?? ''
        css = mono.css ?? ''
      }

      this.templateDraft = { html, css }
      // Also populate html/css fields for backwards compatibility
      this.html = html
      this.css = css
    },

    /**
     * Patches the geometry (position + size) of a node in templateDraft.html.
     * Uses DOMParser for robust, attribute-order-independent matching.
     * ADR-029: Opção C — HTML String Patching.
     * Triggers HTMLCanvas watcher via new templateDraft object reference.
     */
    patchNodeGeometry(nodeId: string, x: number, y: number, width: number, height: number): void {
      if (!this.templateDraft?.html) return
      if (typeof DOMParser === 'undefined') return

      const parser = new DOMParser()
      const doc = parser.parseFromString(`<div id="_root">${this.templateDraft.html}</div>`, 'text/html')
      const root = doc.getElementById('_root')
      if (!root) return

      const el = root.querySelector(`[data-node-id="${nodeId}"]`)
      if (!el) return

      el.setAttribute('style', `position:absolute;left:${x}px;top:${y}px;width:${width}px;height:${height}px`)
      const patched = root.innerHTML
      if (patched !== this.templateDraft.html) {
        this.templateDraft = { ...this.templateDraft, html: patched }
      }
    },

    /**
     * Patches the text content of a node in templateDraft.html.
     * Uses DOMParser to safely handle HTML escaping (no manual escaping needed).
     * ADR-029: Opção C — HTML String Patching.
     * Triggers HTMLCanvas watcher via new templateDraft object reference.
     */
    patchNodeText(nodeId: string, text: string): void {
      if (!this.templateDraft?.html) return
      if (typeof DOMParser === 'undefined') return

      const parser = new DOMParser()
      const doc = parser.parseFromString(`<div id="_root">${this.templateDraft.html}</div>`, 'text/html')
      const root = doc.getElementById('_root')
      if (!root) return

      const el = root.querySelector(`[data-node-id="${nodeId}"]`)
      if (!el) return

      el.textContent = text
      const patched = root.innerHTML
      if (patched !== this.templateDraft.html) {
        this.templateDraft = { ...this.templateDraft, html: patched }
      }
    },
  },
})
