import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { CodeFileKey } from '@/types/editor.types'
import { CODE_FILES } from '@/types/editor.types'
import { useTemplateStore } from './templateStore'
import { useChartStore } from './chartStore'
import { useGenerationStore } from './generation'
import { generateChartJsBlock } from './chartCodeGen'

// ─── Default code content placeholders ────────────────────────────────────
const DEFAULT_HTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <link rel="stylesheet" href="css/style.css" />
</head>
<body>
  <!-- SEÇÃO ESTRUTURAL: header -->
  <header id="template-header"></header>

  <!-- SEÇÃO ESTRUTURAL: flow -->
  <main id="template-flow"></main>

  <!-- SEÇÃO ESTRUTURAL: footer -->
  <footer id="template-footer"></footer>

  <script src="js/base.js"><\/script>
</body>
</html>`

const DEFAULT_CSS = `/* Template styles */
body {
  margin: 0;
  font-family: Arial, sans-serif;
}

#template-header,
#template-footer {
  padding: 1rem;
}

#template-flow {
  padding: 1rem;
}
`

const DEFAULT_JS = `// base.js — Template logic
(function () {
  'use strict';
  // Template initialization
})();
`

const DEFAULT_EXEMPLO = `// exemplo.js — Dados de exemplo (READ-ONLY)
// Este arquivo é gerado automaticamente pela Story 8.1.
// Para alterar dados de teste, use o painel "Dados de Teste".
var exampleData = {};
`

/** Generate HTML content from templateStore (simplified client-side) */
function generateHtmlFromStore(templateStore: ReturnType<typeof useTemplateStore>): string {
  if (!templateStore.documentTree) return DEFAULT_HTML
  // Simplified: produce HTML scaffold with structural section comments
  const root = templateStore.documentTree.root
  const header = root.children.find((n) => n.type === 'header')
  const footer = root.children.find((n) => n.type === 'footer')
  const flows = root.children.filter((n) => n.type !== 'header' && n.type !== 'footer')

  const headerComment = header ? `  <!-- SEÇÃO ESTRUTURAL: header -->\n  <header id="template-header"><!-- ${header.name || header.type || 'header'} --></header>` : `  <!-- SEÇÃO ESTRUTURAL: header -->\n  <header id="template-header"></header>`
  const footerComment = footer ? `  <!-- SEÇÃO ESTRUTURAL: footer -->\n  <footer id="template-footer"><!-- ${footer.name || footer.type || 'footer'} --></footer>` : `  <!-- SEÇÃO ESTRUTURAL: footer -->\n  <footer id="template-footer"></footer>`
  const flowLines = flows.map((n) => `    <!-- SEÇÃO ESTRUTURAL: flow -->\n    <section id="${n.id}"><!-- ${n.name || n.type || 'section'} --></section>`).join('\n')

  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <link rel="stylesheet" href="css/style.css" />
</head>
<body>
${headerComment}

  <!-- SEÇÃO ESTRUTURAL: flow -->
  <main id="template-flow">
${flowLines || '    <!-- conteúdo aqui -->'}
  </main>

${footerComment}

  <script src="js/base.js"><\/script>
</body>
</html>`
}

export const useCodeStore = defineStore('code', () => {
  const templateStore = useTemplateStore()
  const chartStore = useChartStore()
  const generationStore = useGenerationStore()

  // ─── State ──────────────────────────────────────────────────────────────
  // Initialize from templateDraft if already loaded (handles the case where the
  // store is instantiated AFTER the pipeline has completed — in that scenario,
  // the watch on templateDraft.html would never fire for the existing value because
  // Vue watchers only fire on changes AFTER registration, not for pre-existing values).
  const fileContents = ref<Record<CodeFileKey, string>>({
    html:    generationStore.templateDraft?.html || DEFAULT_HTML,
    css:     generationStore.templateDraft?.css || DEFAULT_CSS,
    js:      DEFAULT_JS,
    exemplo: DEFAULT_EXEMPLO,
  })

  const activeFile = ref<CodeFileKey>('html')

  /** True when templateStore changed during Monaco debounce — triggers toast */
  const externalChangeDetected = ref(false)

  /** Buffer of pending Monaco edits when external change was detected */
  const pendingMonacoEdit = ref<{ key: CodeFileKey; content: string } | null>(null)

  // ─── Actions ────────────────────────────────────────────────────────────
  function setActiveFile(key: CodeFileKey) {
    activeFile.value = key
  }

  function setFileContent(key: CodeFileKey, content: string) {
    const file = CODE_FILES.find((f) => f.key === key)
    if (file?.readOnly) return // Never overwrite read-only from external
    fileContents.value[key] = content
  }

  /** Inject CSS into generationStore.templateDraft so canvas iframes re-render */
  function injectTemplateCSS(css: string) {
    if (generationStore.templateDraft) {
      generationStore.templateDraft.css = css
    }
  }

  /** Called by Monaco on user edit — applies after 500ms debounce in component */
  function applyMonacoEdit(key: CodeFileKey, content: string) {
    const file = CODE_FILES.find((f) => f.key === key)
    if (file?.readOnly) return

    if (externalChangeDetected.value) {
      // Buffer the edit and show toast — do not overwrite templateStore
      pendingMonacoEdit.value = { key, content }
      return
    }

    fileContents.value[key] = content
    // Sync Código→Visual: basic parse for HTML — update templateStore bindings
    if (key === 'html') {
      _parseHtmlIntoStore(content)
      // Story 29.3: schedule debounced sync of text properties to templateStore
      scheduleHtmlSync(content)
    }
    // Sync CSS→Canvas: inject edited CSS into templateDraft so iframes re-render
    if (key === 'css') {
      templateStore.pushUndoSnapshot()
      injectTemplateCSS(content)
    }
  }

  /** Called when user acknowledges the external change toast */
  function resolveExternalChange(keepMonaco: boolean) {
    if (keepMonaco && pendingMonacoEdit.value) {
      const { key, content } = pendingMonacoEdit.value
      fileContents.value[key] = content
    }
    externalChangeDetected.value = false
    pendingMonacoEdit.value = null
  }

  /** Regenerate code strings from templateStore (Visual→Code sync) */
  function regenerateFromStore() {
    fileContents.value.html = generateHtmlFromStore(templateStore)
    // Inject Chart.js initialization block if charts are registered
    const activeCharts = chartStore.charts.filter((c) => !c.useFallback)
    if (activeCharts.length) {
      const blocks = activeCharts.map((c) => generateChartJsBlock(c)).filter(Boolean)
      if (blocks.length && !fileContents.value.js.includes('initCharts')) {
        const section =
          '\n// Chart.js initialization\nvar initCharts = function (data) {\n  ' +
          blocks.join('\n\n  ') +
          '\n};\n'
        fileContents.value.js = section + fileContents.value.js
      }
    }
  }

  // ─── Story 29.3: Code Editor → Structure Sync (Opção B — DOMParser frontend) ──
  // Debounce timer for HTML sync
  let _htmlSyncTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * Flag to prevent sync loop: code→tree triggers updateNodeProperty which
   * could trigger regenerateFromStore which writes back to fileContents.
   * ADR: flag is set during syncHtmlToTree and cleared after.
   */
  let _isSyncing = false

  /**
   * Schedule a sync of HTML → templateStore after 800ms debounce.
   * Uses DOMParser to extract text content per node (Opção B — MVP).
   */
  function scheduleHtmlSync(html: string) {
    if (_htmlSyncTimer) clearTimeout(_htmlSyncTimer)
    _htmlSyncTimer = setTimeout(() => syncHtmlToTree(html), 800)
  }

  /**
   * Parse a numeric px value from an inline style string.
   * Returns null if the property is absent or not a px value.
   */
  function _parsePx(style: string, prop: string): number | null {
    const m = style.match(new RegExp(`${prop}\\s*:\\s*([\\d.]+)px`))
    return m ? parseFloat(m[1]) : null
  }

  /**
   * Sync HTML string → templateStore.
   * Story 30.3 — full parser: detects add/remove of data-node-id elements
   * and syncs position/size from inline styles, in addition to text/data-field.
   *
   * Phases:
   *   1. Parse HTML, build htmlMap (data-node-id → Element)
   *   2. Safety guard: if no [data-node-id] in HTML, skip add/remove (scaffold protection)
   *   3. Sync existing nodes: text, data-field, position/size
   *   4. Collect + process removals (in store, not in HTML)
   *   5. Process additions (in HTML, not in store)
   *
   * Sets _isSyncing to prevent code→tree→code loops.
   */
  function syncHtmlToTree(html: string) {
    if (_isSyncing) return
    if (typeof DOMParser === 'undefined') return

    try {
      const parser = new DOMParser()
      const doc = parser.parseFromString(html, 'text/html')

      // Check for parse error (invalid HTML)
      if (doc.querySelector('parseerror')) return

      const nodes = templateStore.flatNodes
      if (!nodes || nodes.size === 0) return

      // Phase 1: build htmlMap
      const htmlMap = new Map<string, Element>()
      doc.querySelectorAll('[data-node-id]').forEach((el) => {
        const id = el.getAttribute('data-node-id')
        if (id) htmlMap.set(id, el)
      })

      // Phase 2: safety guard — scaffold HTML has no data-node-id → skip add/remove
      const hasDataNodeIds = htmlMap.size > 0

      _isSyncing = true
      try {
        // Phase 3: sync existing nodes + collect removals
        const toRemove: string[] = []
        nodes.forEach((node, nodeId) => {
          if (!nodeId) return
          const el = htmlMap.get(nodeId)

          if (!el) {
            // Node in store but NOT in HTML
            if (hasDataNodeIds) toRemove.push(nodeId)
            return
          }

          // Sync text content (preserved from MVP)
          const textContent = el.textContent?.trim()
          if (
            textContent !== undefined &&
            textContent !== '' &&
            textContent !== (node.properties?.text as string | undefined)
          ) {
            templateStore.updateNodeProperty(nodeId, 'text', textContent)
          }

          // Sync data-field attribute (preserved from MVP)
          const dataField = el.getAttribute('data-field')
          if (dataField !== null) {
            const current = node.properties?.['data-field'] as string | undefined
            if (dataField !== current) {
              templateStore.updateNodeProperty(nodeId, 'data-field', dataField)
            }
          }

          // Story 30.3 — sync position/size from inline style (AC3)
          const styleAttr = el.getAttribute('style') ?? ''
          const x = _parsePx(styleAttr, 'left')
          const y = _parsePx(styleAttr, 'top')
          const w = _parsePx(styleAttr, 'width')
          const h = _parsePx(styleAttr, 'height')

          const curX = node.properties.x as number | undefined
          const curY = node.properties.y as number | undefined
          const curW = node.properties.width as number | undefined
          const curH = node.properties.height as number | undefined

          const posChanged = (x !== null && x !== curX) || (y !== null && y !== curY)
          const sizeChanged = (w !== null && w !== curW) || (h !== null && h !== curH)

          if (posChanged) {
            templateStore.moveElement(nodeId, (x ?? curX ?? 0) - (curX ?? 0), (y ?? curY ?? 0) - (curY ?? 0))
          }
          if (sizeChanged) {
            templateStore.resizeElement(nodeId, w ?? curW ?? 100, h ?? curH ?? 20)
          }
        })

        // Phase 4: process removals (after forEach to avoid mutation during iteration)
        if (hasDataNodeIds) {
          for (const nodeId of toRemove) {
            templateStore.removeNode(nodeId)
          }
        }

        // Phase 5: process additions — nodes in HTML but NOT in store
        if (hasDataNodeIds) {
          htmlMap.forEach((el, nodeId) => {
            if (nodes.has(nodeId)) return // already in store

            // Find parent by closest ancestor with data-node-id
            let parentEl: Element | null = el.parentElement
            let parentId: string | null = null
            while (parentEl && !parentId) {
              const pid = parentEl.getAttribute('data-node-id')
              if (pid && nodes.has(pid)) parentId = pid
              parentEl = parentEl.parentElement
            }
            if (!parentId) return // no valid parent found — skip

            const rawType = el.getAttribute('data-type') ?? 'field'
            const validTypes = new Set([
              'document','header','footer','flow','section','table','chart',
              'image','container','text','field','barcode','label','value',
              'likely_dynamic','dynamic',
            ])
            const type = (validTypes.has(rawType) ? rawType : 'field') as import('@/types/template.types').NodeType

            const styleAttr = el.getAttribute('style') ?? ''
            const newNode: import('@/types/template.types').TreeNode = {
              id: nodeId,
              type,
              name: el.textContent?.trim().slice(0, 40) || type,
              binding: '',
              isOptional: false,
              children: [],
              properties: {
                x: _parsePx(styleAttr, 'left') ?? 0,
                y: _parsePx(styleAttr, 'top') ?? 0,
                width: _parsePx(styleAttr, 'width') ?? 100,
                height: _parsePx(styleAttr, 'height') ?? 20,
                text: el.textContent?.trim() ?? '',
              },
              visibility: true,
            }

            templateStore.addNodeFromSync(newNode, parentId)
          })
        }
      } finally {
        _isSyncing = false
      }
    } catch (err) {
      _isSyncing = false
      console.warn('[codeStore] syncHtmlToTree failed:', err)
    }
  }

  /** Basic HTML→Store parse: extract section names from comments */
  function _parseHtmlIntoStore(html: string) {
    // Very simplified — just check that the HTML is not completely empty
    // and that structural sections still exist. Full parse out of MVP scope.
    if (!html.trim()) return
    // No-op for MVP: templateStore remains source of truth; full parse is future work
  }

  function dismissExternalChange() {
    externalChangeDetected.value = false
    pendingMonacoEdit.value = null
  }

  // ─── Story 36.1: Selective HTML patch when backend draft exists ─────────
  /**
   * Patch the current HTML by updating text content and data-field attributes
   * for elements identified by data-node-id, instead of full regeneration.
   * This allows structure→code sync even when templateDraft.html is set.
   */
  function patchHtmlFromTree(html: string): string {
    if (typeof DOMParser === 'undefined') return html

    const nodes = templateStore.flatNodes
    if (!nodes || nodes.size === 0) return html

    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    if (doc.querySelector('parsererror')) return html

    let changed = false
    nodes.forEach((node, nodeId) => {
      if (!nodeId) return
      const el = doc.querySelector(`[data-node-id="${nodeId}"]`)
      if (!el) return

      // Sync text content
      const text = node.properties?.text as string | undefined
      if (text !== undefined && el.childNodes.length <= 1) {
        const currentText = el.textContent?.trim() ?? ''
        if (text !== currentText) {
          el.textContent = text
          changed = true
        }
      }

      // Sync data-field attribute
      const binding = node.binding
      if (binding) {
        const current = el.getAttribute('data-field')
        if (binding !== current) {
          el.setAttribute('data-field', binding)
          changed = true
        }
      }

      // Sync name attribute (node name → element id or data-name)
      const name = node.name
      if (name) {
        const currentName = el.getAttribute('data-name')
        if (name !== currentName) {
          el.setAttribute('data-name', name)
          changed = true
        }
      }
    })

    if (!changed) return html

    // Serialize back — use full document to preserve doctype and structure
    const serializer = new XMLSerializer()
    const head = doc.head ? serializer.serializeToString(doc.head) : ''
    const body = doc.body ? serializer.serializeToString(doc.body) : ''

    // Reconstruct a clean HTML string preserving the original structure
    const doctype = html.match(/<!DOCTYPE[^>]*>/i)?.[0] ?? '<!DOCTYPE html>'
    const htmlTag = html.match(/<html[^>]*>/i)?.[0] ?? '<html>'
    return `${doctype}\n${htmlTag}\n${head}\n${body}\n</html>`
  }

  // ─── Watch templateStore for Visual→Code sync ──────────────────────────
  watch(
    () => templateStore.documentTree,
    () => {
      // Story 29.3: guard — quando syncHtmlToTree está em execução (code→tree),
      // não propagar de volta tree→code (previne loop code→tree→code).
      if (_isSyncing) return

      // Story 36.1: When backend HTML exists, use selective patching instead
      // of full regeneration. This preserves the backend's HTML structure while
      // allowing tree changes (text, bindings, names) to flow into the code.
      if (generationStore.templateDraft?.html) {
        _isSyncing = true
        try {
          const patched = patchHtmlFromTree(fileContents.value.html)
          if (patched !== fileContents.value.html) {
            fileContents.value.html = patched
          }
        } finally {
          _isSyncing = false
        }
        return
      }

      // Regenerate HTML when templateStore changes (only when no backend HTML is set)
      const newHtml = generateHtmlFromStore(templateStore)
      if (newHtml !== fileContents.value.html) {
        externalChangeDetected.value = true
        fileContents.value.html = newHtml
      }
    },
    { deep: true },
  )

  // Flag: rastreia se a carga inicial do templateDraft (do backend/pipeline) já foi feita.
  // Começa true se o templateDraft já estava carregado quando o store foi instanciado
  // (cenário: usuário abre aba Código APÓS pipeline completar — store instancia com valor correto).
  // Começa false se o store foi instanciado antes da pipeline (usuário abriu Código antes).
  // Primeira vez que o watch dispara: marca done e NÃO sinaliza conflito (é a carga inicial).
  // Disparos subsequentes: sinalizam conflito (mudança externa durante sessão de edição).
  let templateDraftInitialLoadDone = generationStore.templateDraft != null

  // ─── Watch generationStore.templateDraft.html → sync to Monaco (HTML real do backend) ──
  // IMPORTANTE: não seta externalChangeDetected na primeira carga do backend.
  // Sinalizar "conflito externo" na carga inicial é falso positivo: não há edição
  // manual do usuário em conflito, apenas a chegada do HTML gerado pelo pipeline.
  // O banner de conflito deve aparecer apenas quando o usuário JÁ tinha editado
  // manualmente e uma mudança externa chega depois (ex: layout switch).
  watch(
    () => generationStore.templateDraft?.html,
    (newHtml) => {
      if (newHtml != null && newHtml !== fileContents.value.html) {
        // Só sinaliza conflito após a carga inicial ter sido feita
        if (templateDraftInitialLoadDone) {
          externalChangeDetected.value = true
        }
        fileContents.value.html = newHtml
        templateDraftInitialLoadDone = true
      }
    },
  )

  // ─── Watch generationStore.templateDraft.css → sync back to Monaco ──────
  watch(
    () => generationStore.templateDraft?.css,
    (newCss) => {
      if (newCss != null && newCss !== fileContents.value.css) {
        fileContents.value.css = newCss
      }
    },
  )

  return {
    fileContents,
    activeFile,
    externalChangeDetected,
    pendingMonacoEdit,
    setActiveFile,
    setFileContent,
    applyMonacoEdit,
    injectTemplateCSS,
    resolveExternalChange,
    dismissExternalChange,
    regenerateFromStore,
    // Story 29.3: exposed for testing
    scheduleHtmlSync,
    syncHtmlToTree,
    // Story 36.1: exposed for testing
    patchHtmlFromTree,
  }
})
