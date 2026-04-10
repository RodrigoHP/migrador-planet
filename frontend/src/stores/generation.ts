import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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

export const useGenerationStore = defineStore('generation', () => {
  const html = ref<string | null>(null)
  const css = ref<string | null>(null)
  const js = ref<string | null>(null)
  const exemplo = ref<string | null>(null)
  const fidelityScore = ref<number | null>(null)
  const fidelityComment = ref<string | null>(null)
  const iaSuggestions = ref<IASuggestion[] | null>(null)
  const monacoEdits = ref<{ html?: string; css?: string; js?: string }>({})
  const chartConfigs = ref<Record<string, ChartjsConfig>>({})
  const previewJobId = ref<string | null>(null)
  const previewExpired = ref(false)
  const rightPanel = ref<'html-preview' | 'monaco' | 'wysiwyg' | 'chartjs-config'>('html-preview')
  const activeChartId = ref<string | null>(null)
  // Epic-6 extensions
  const templateDraft = ref<TemplateDraft | null>(null)

  // Cached parsed document for patchNodeStyle — avoids re-parsing on rapid edits
  let _styleCache: { html: string; doc: Document; root: HTMLElement } | null = null

  const isFidelityLow = computed(() => fidelityScore.value !== null && fidelityScore.value < 70)

  function $reset() {
    html.value = null
    css.value = null
    js.value = null
    exemplo.value = null
    fidelityScore.value = null
    fidelityComment.value = null
    iaSuggestions.value = null
    monacoEdits.value = {}
    chartConfigs.value = {}
    previewJobId.value = null
    previewExpired.value = false
    rightPanel.value = 'html-preview'
    activeChartId.value = null
    templateDraft.value = null
    _styleCache = null
  }

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
  function loadTemplateDraft(draft: TemplateDraftInput) {
    let h: string
    let c: string

    if (Array.isArray(draft)) {
      // Format 3: TemplateDraftPage[] — join all pages into monolithic HTML
      const pages = draft as TemplateDraftPage[]
      c = pages[0]?.css ?? ''
      h = pages.map((p) => p.html).join('\n')
    } else if ('pages' in draft && Array.isArray((draft as { pages: TemplateDraftPage[] }).pages)) {
      // Format 2: { pages: TemplateDraftPage[] }
      const pages = (draft as { pages: TemplateDraftPage[] }).pages
      c = pages[0]?.css ?? ''
      h = pages.map((p) => p.html).join('\n')
    } else {
      // Format 1: { html, css } — canonical monolithic format from Stage 28
      const mono = draft as { html: string; css: string }
      h = mono.html ?? ''
      c = mono.css ?? ''
    }

    templateDraft.value = { html: h, css: c }
    // Also populate html/css fields for backwards compatibility
    html.value = h
    css.value = c
  }

  /**
   * Patches the geometry (position + size) of a node in templateDraft.html.
   * Uses DOMParser for robust, attribute-order-independent matching.
   * ADR-029: Opção C — HTML String Patching.
   * Triggers HTMLCanvas watcher via new templateDraft object reference.
   */
  function patchNodeGeometry(
    nodeId: string,
    x: number,
    y: number,
    width: number,
    height: number,
  ): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    const parser = new DOMParser()
    const doc = parser.parseFromString(
      `<div id="_root">${templateDraft.value.html}</div>`,
      'text/html',
    )
    const root = doc.getElementById('_root')
    if (!root) return

    const el = root.querySelector(`[data-node-id="${nodeId}"]`)
    if (!el) return

    el.setAttribute(
      'style',
      `position:absolute;left:${x}px;top:${y}px;width:${width}px;height:${height}px`,
    )
    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
    }
  }

  /**
   * Patches the text content of a node in templateDraft.html.
   * Uses DOMParser to safely handle HTML escaping (no manual escaping needed).
   * ADR-029: Opção C — HTML String Patching.
   * Triggers HTMLCanvas watcher via new templateDraft object reference.
   */
  function patchNodeText(nodeId: string, text: string): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    const parser = new DOMParser()
    const doc = parser.parseFromString(
      `<div id="_root">${templateDraft.value.html}</div>`,
      'text/html',
    )
    const root = doc.getElementById('_root')
    if (!root) return

    const el = root.querySelector(`[data-node-id="${nodeId}"]`)
    if (!el) return

    el.textContent = text
    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
    }
  }

  /**
   * Removes a node element from templateDraft.html by data-node-id.
   * Prevents "ghost" elements remaining on canvas after tree deletion.
   * Story 29.7 — structural mutation coverage.
   */
  function patchRemoveNode(nodeId: string): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    const parser = new DOMParser()
    const doc = parser.parseFromString(
      `<div id="_root">${templateDraft.value.html}</div>`,
      'text/html',
    )
    const root = doc.getElementById('_root')
    if (!root) return

    const el = root.querySelector(`[data-node-id="${nodeId}"]`)
    if (!el) return

    el.remove()
    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
    }
  }

  /**
   * Inserts minimal HTML for a new node as a child of parentNodeId.
   * Produces a positioned placeholder with data-node-id — sufficient for canvas MVP.
   * The full backend-rendered HTML replaces this on the next loadTemplateDraft call.
   * Story 29.7 — structural mutation coverage.
   */
  function patchAddNode(node: TreeNode, parentNodeId: string): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    const parser = new DOMParser()
    const doc = parser.parseFromString(
      `<div id="_root">${templateDraft.value.html}</div>`,
      'text/html',
    )
    const root = doc.getElementById('_root')
    if (!root) return

    const parentEl = root.querySelector(`[data-node-id="${parentNodeId}"]`)
    if (!parentEl) return

    const nodeHtml = _generateMinimalNodeHtml(node)
    if (!nodeHtml) return

    parentEl.insertAdjacentHTML('beforeend', nodeHtml)
    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
    }
  }

  /**
   * Moves a node element to a new parent in templateDraft.html.
   * For position:absolute elements, visual effect may be neutral — but keeps
   * the DOM synchronized with the templateStore structure.
   * Story 29.7 — structural mutation coverage.
   */
  function patchMoveNode(nodeId: string, newParentId: string): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    const parser = new DOMParser()
    const doc = parser.parseFromString(
      `<div id="_root">${templateDraft.value.html}</div>`,
      'text/html',
    )
    const root = doc.getElementById('_root')
    if (!root) return

    const el = root.querySelector(`[data-node-id="${nodeId}"]`)
    const newParent = root.querySelector(`[data-node-id="${newParentId}"]`)
    if (!el || !newParent) return
    if (newParent.contains(el)) return // already a child, no-op

    newParent.appendChild(el)
    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
    }
  }

  /**
   * Patches an inline style property on a node element in templateDraft.html.
   * Story 33.4: supports font-size, font-weight, font-style, color, background-color.
   * Property names use underscore format (font_size) and are converted to CSS kebab-case.
   */
  function patchNodeStyle(nodeId: string, property: string, value: string): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    // Map underscore property names to CSS property names
    const CSS_MAP: Record<string, string> = {
      font_size: 'font-size',
      font_weight: 'font-weight',
      font_style: 'font-style',
      color: 'color',
      background_color: 'background-color',
    }
    const cssProp = CSS_MAP[property]
    if (!cssProp) return

    // Reuse cached parsed document if HTML hasn't changed
    let root: HTMLElement
    if (_styleCache && _styleCache.html === templateDraft.value.html) {
      root = _styleCache.root
    } else {
      const parser = new DOMParser()
      const doc = parser.parseFromString(
        `<div id="_root">${templateDraft.value.html}</div>`,
        'text/html',
      )
      const r = doc.getElementById('_root')
      if (!r) return
      root = r
      _styleCache = { html: templateDraft.value.html, doc, root }
    }

    const el = root.querySelector(`[data-node-id="${nodeId}"]`) as HTMLElement | null
    if (!el) return

    // Remove existing declaration for this property and add the new one
    const existing = el.getAttribute('style') ?? ''
    const regex = new RegExp(`\\s*${cssProp}\\s*:\\s*[^;]+;?`, 'g')
    let cleaned = existing.replace(regex, '').trim()

    if (value && value !== 'none' && value !== '') {
      // Add unit for font-size if it's a number without unit
      let cssValue = value
      if (cssProp === 'font-size' && /^\d+(\.\d+)?$/.test(value)) {
        cssValue = `${value}px`
      }
      const sep = cleaned.length > 0 && !cleaned.endsWith(';') ? ';' : ''
      cleaned = `${cleaned}${sep}${cssProp}:${cssValue}`
    }

    el.setAttribute('style', cleaned)
    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
      _styleCache = { html: patched, doc: _styleCache!.doc, root }
    }
  }

  /**
   * Adds or removes `display:none` on a node element in templateDraft.html.
   * Preserves all other inline styles (position, left, top, width, height).
   * Story 30.4 — visibility=false should reflect on canvas immediately.
   */
  function patchNodeVisibility(nodeId: string, visible: boolean): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    const parser = new DOMParser()
    const doc = parser.parseFromString(
      `<div id="_root">${templateDraft.value.html}</div>`,
      'text/html',
    )
    const root = doc.getElementById('_root')
    if (!root) return

    const el = root.querySelector(`[data-node-id="${nodeId}"]`)
    if (!el) return

    const existing = el.getAttribute('style') ?? ''
    // Strip any existing display declaration to avoid duplicates
    const withoutDisplay = existing.replace(/\s*display\s*:\s*[^;]+;?/g, '').trim()

    if (!visible) {
      const sep = withoutDisplay.length > 0 && !withoutDisplay.endsWith(';') ? ';' : ''
      el.setAttribute('style', `${withoutDisplay}${sep}display:none`)
    } else {
      el.setAttribute('style', withoutDisplay)
    }

    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
    }
  }

  /**
   * Replaces an existing node element with a minimal <table> placeholder.
   * Preserves the data-node-id and style of the original element so the canvas
   * can continue to target it. The first child row (rowNode) is injected into
   * the table's <tbody>.
   * Story 30.2 — "Converter para Tabela" context menu action.
   */
  function patchConvertNodeToTable(nodeId: string, rowNode: TreeNode): void {
    if (!templateDraft.value?.html) return
    if (typeof DOMParser === 'undefined') return

    const parser = new DOMParser()
    const doc = parser.parseFromString(
      `<div id="_root">${templateDraft.value.html}</div>`,
      'text/html',
    )
    const root = doc.getElementById('_root')
    if (!root) return

    const el = root.querySelector(`[data-node-id="${nodeId}"]`)
    if (!el) return

    // Preserve geometry style from the original element
    const style = el.getAttribute('style') ?? ''
    const rowHtml = _generateMinimalNodeHtml(rowNode)

    // Build replacement <table>
    const tableHtml =
      `<table data-node-id="${nodeId}" data-type="table" ` +
      `style="${style};border-collapse:collapse">` +
      `<tbody>${rowHtml}</tbody>` +
      `</table>`

    el.insertAdjacentHTML('afterend', tableHtml)
    el.remove()

    const patched = root.innerHTML
    if (patched !== templateDraft.value.html) {
      templateDraft.value = { ...templateDraft.value, html: patched }
    }
  }

  return {
    html,
    css,
    js,
    exemplo,
    fidelityScore,
    fidelityComment,
    iaSuggestions,
    monacoEdits,
    chartConfigs,
    previewJobId,
    previewExpired,
    rightPanel,
    activeChartId,
    templateDraft,
    isFidelityLow,
    $reset,
    loadTemplateDraft,
    patchNodeGeometry,
    patchNodeText,
    patchRemoveNode,
    patchAddNode,
    patchMoveNode,
    patchNodeStyle,
    patchNodeVisibility,
    patchConvertNodeToTable,
  }
})
