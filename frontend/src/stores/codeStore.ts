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
  const fileContents = ref<Record<CodeFileKey, string>>({
    html:    DEFAULT_HTML,
    css:     DEFAULT_CSS,
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

  // ─── Watch templateStore for Visual→Code sync ──────────────────────────
  watch(
    () => templateStore.documentTree,
    () => {
      // Se o backend já forneceu HTML via templateDraft, o HTML do backend tem
      // prioridade sobre o scaffold gerado pelo cliente. O watch de templateDraft.html
      // (abaixo) já sincronizou fileContents.html com o HTML real.
      // Sem essa guarda, reconcileFieldBindings() (que muta nós da árvore após
      // loadTemplateDraft) acionaria este watch deep novamente e sobrescreveria
      // o HTML do backend com o scaffold simplificado do cliente.
      if (generationStore.templateDraft?.html) return

      // Regenerate HTML when templateStore changes (only when no backend HTML is set)
      const newHtml = generateHtmlFromStore(templateStore)
      if (newHtml !== fileContents.value.html) {
        externalChangeDetected.value = true
        fileContents.value.html = newHtml
      }
    },
    { deep: true },
  )

  // ─── Watch generationStore.templateDraft.html → sync to Monaco (HTML real do backend) ──
  watch(
    () => generationStore.templateDraft?.html,
    (newHtml) => {
      if (newHtml != null && newHtml !== fileContents.value.html) {
        externalChangeDetected.value = true
        fileContents.value.html = newHtml
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
  }
})
