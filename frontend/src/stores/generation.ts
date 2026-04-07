import { defineStore } from 'pinia'
import type { IASuggestion, ChartjsConfig } from '@/types'
import type { TreeNode } from '@/types/template.types'

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

/**
 * Generates minimal placeholder HTML for a new node.
 * Positioned with data-node-id so canvas patch functions can target it.
 * Full backend-rendered HTML replaces this on the next loadTemplateDraft call.
 * Story 29.7 — used by patchAddNode.
 */
function _generateMinimalNodeHtml(node: TreeNode): string {
  const id = node.id
  const type = node.type
  const x = (node.properties.x as number) ?? 0
  const y = (node.properties.y as number) ?? 0
  const w = (node.properties.width as number) ?? 100
  const h = (node.properties.height as number) ?? 20
  const text = (node.properties.text as string) ?? node.name ?? type
  const style = `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px`

  switch (type) {
    case 'label':
    case 'field':
    case 'value':
    case 'likely_dynamic':
    case 'dynamic':
      return `<span data-node-id="${id}" data-type="${type}" style="${style}">${text}</span>`
    case 'section':
      return `<div data-node-id="${id}" data-type="section" style="${style}"></div>`
    case 'table':
      // Story 30.2 — minimal table placeholder; full render on next loadTemplateDraft
      return `<table data-node-id="${id}" data-type="table" style="${style};border-collapse:collapse"><tbody></tbody></table>`
    default:
      // Unsupported types in MVP (chart, image, barcode) — placeholder div
      return `<div data-node-id="${id}" data-type="${type}" style="${style}"></div>`
  }
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

    /**
     * Removes a node element from templateDraft.html by data-node-id.
     * Prevents "ghost" elements remaining on canvas after tree deletion.
     * Story 29.7 — structural mutation coverage.
     */
    patchRemoveNode(nodeId: string): void {
      if (!this.templateDraft?.html) return
      if (typeof DOMParser === 'undefined') return

      const parser = new DOMParser()
      const doc = parser.parseFromString(`<div id="_root">${this.templateDraft.html}</div>`, 'text/html')
      const root = doc.getElementById('_root')
      if (!root) return

      const el = root.querySelector(`[data-node-id="${nodeId}"]`)
      if (!el) return

      el.remove()
      const patched = root.innerHTML
      if (patched !== this.templateDraft.html) {
        this.templateDraft = { ...this.templateDraft, html: patched }
      }
    },

    /**
     * Inserts minimal HTML for a new node as a child of parentNodeId.
     * Produces a positioned placeholder with data-node-id — sufficient for canvas MVP.
     * The full backend-rendered HTML replaces this on the next loadTemplateDraft call.
     * Story 29.7 — structural mutation coverage.
     */
    patchAddNode(node: TreeNode, parentNodeId: string): void {
      if (!this.templateDraft?.html) return
      if (typeof DOMParser === 'undefined') return

      const parser = new DOMParser()
      const doc = parser.parseFromString(`<div id="_root">${this.templateDraft.html}</div>`, 'text/html')
      const root = doc.getElementById('_root')
      if (!root) return

      const parentEl = root.querySelector(`[data-node-id="${parentNodeId}"]`)
      if (!parentEl) return

      const html = _generateMinimalNodeHtml(node)
      if (!html) return

      parentEl.insertAdjacentHTML('beforeend', html)
      const patched = root.innerHTML
      if (patched !== this.templateDraft.html) {
        this.templateDraft = { ...this.templateDraft, html: patched }
      }
    },

    /**
     * Moves a node element to a new parent in templateDraft.html.
     * For position:absolute elements, visual effect may be neutral — but keeps
     * the DOM synchronized with the templateStore structure.
     * Story 29.7 — structural mutation coverage.
     */
    patchMoveNode(nodeId: string, newParentId: string): void {
      if (!this.templateDraft?.html) return
      if (typeof DOMParser === 'undefined') return

      const parser = new DOMParser()
      const doc = parser.parseFromString(`<div id="_root">${this.templateDraft.html}</div>`, 'text/html')
      const root = doc.getElementById('_root')
      if (!root) return

      const el = root.querySelector(`[data-node-id="${nodeId}"]`)
      const newParent = root.querySelector(`[data-node-id="${newParentId}"]`)
      if (!el || !newParent) return
      if (newParent.contains(el)) return // already a child, no-op

      newParent.appendChild(el)
      const patched = root.innerHTML
      if (patched !== this.templateDraft.html) {
        this.templateDraft = { ...this.templateDraft, html: patched }
      }
    },

    /**
     * Replaces an existing node element with a minimal <table> placeholder.
     * Preserves the data-node-id and style of the original element so the canvas
     * can continue to target it. The first child row (rowNode) is injected into
     * the table's <tbody>.
     * Story 30.2 — "Converter para Tabela" context menu action.
     */
    patchConvertNodeToTable(nodeId: string, rowNode: TreeNode): void {
      if (!this.templateDraft?.html) return
      if (typeof DOMParser === 'undefined') return

      const parser = new DOMParser()
      const doc = parser.parseFromString(`<div id="_root">${this.templateDraft.html}</div>`, 'text/html')
      const root = doc.getElementById('_root')
      if (!root) return

      const el = root.querySelector(`[data-node-id="${nodeId}"]`)
      if (!el) return

      // Preserve geometry style from the original element
      const style = el.getAttribute('style') ?? ''
      const rowHtml = _generateMinimalNodeHtml(rowNode)

      // Build replacement <table>
      const tableHtml = `<table data-node-id="${nodeId}" data-type="table" ` +
        `style="${style};border-collapse:collapse">` +
        `<tbody>${rowHtml}</tbody>` +
        `</table>`

      el.insertAdjacentHTML('afterend', tableHtml)
      el.remove()

      const patched = root.innerHTML
      if (patched !== this.templateDraft.html) {
        this.templateDraft = { ...this.templateDraft, html: patched }
      }
    },
  },
})
