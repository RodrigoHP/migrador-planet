<template>
  <section class="monaco-tabs" aria-label="Editor de código Monaco">
    <!-- File tabs bar -->
    <div class="monaco-tabs__bar" role="tablist" aria-label="Arquivos do template">
      <button
        v-for="file in CODE_FILES"
        :key="file.key"
        type="button"
        role="tab"
        class="monaco-tabs__tab"
        :class="{
          'monaco-tabs__tab--active': codeStore.activeFile === file.key,
          'monaco-tabs__tab--readonly': file.readOnly,
        }"
        :aria-selected="codeStore.activeFile === file.key"
        @click="switchFile(file.key)"
      >
        {{ file.label }}
        <span v-if="file.readOnly" class="monaco-tabs__readonly-badge" title="Somente leitura">RO</span>
        <span
          v-if="file.key === 'css' && cssErrorCount > 0"
          class="monaco-tabs__error-badge"
          :title="`${cssErrorCount} CSS error(s)`"
        >{{ cssErrorCount }}</span>
      </button>
    </div>

    <!-- Read-only banner -->
    <div
      v-if="activeFileInfo?.readOnly"
      class="monaco-tabs__readonly-banner"
      role="status"
      aria-live="polite"
    >
      Somente leitura — exemplo.js gerado automaticamente. Edite dados via painel "Dados de Teste".
    </div>

    <!-- External change toast -->
    <div
      v-if="codeStore.externalChangeDetected"
      class="monaco-tabs__conflict-banner"
      role="alert"
      aria-live="assertive"
    >
      <span>Alteracao externa detectada - revisar codigo</span>
      <button type="button" class="monaco-tabs__conflict-btn" @click="codeStore.dismissExternalChange()">
        OK
      </button>
    </div>

    <!-- Monaco editor host -->
    <div ref="editorHost" class="monaco-tabs__editor" />

    <!-- Computed Styles Panel (AC6) -->
    <ComputedStylesPanel />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useCodeStore } from '@/stores/codeStore'
import { CODE_FILES } from '@/types/editor.types'
import type { CodeFileKey } from '@/types/editor.types'
import { useEditorStore } from '@/stores/editorStore'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useTemplateStore } from '@/stores/templateStore'
import { registerCssCompletionProvider } from '@/utils/cssCompletionProvider'
import { applyCssMarkers } from '@/utils/cssValidator'
import ComputedStylesPanel from '@/molecules/ComputedStylesPanel.vue'

const codeStore = useCodeStore()
const editorStore = useEditorStore()
const inspectorStore = useInspectorStore()
const templateStore = useTemplateStore()

const editorHost = ref<HTMLElement | null>(null)

let monacoApi: any = null
let editor: any = null
let model: any = null
let decorations: any[] = []
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let suppressWatch = false
let cssCompletionDisposable: { dispose: () => void } | null = null

const cssErrorCount = ref(0)

const activeFileInfo = computed(() => CODE_FILES.find((f) => f.key === codeStore.activeFile))

// ─── Structural warning decoration patterns ────────────────────────────────
const STRUCTURAL_SECTION_PATTERN = /SEÇÃO ESTRUTURAL/i

// ─── Init editor ─────────────────────────────────────────────────────────
onMounted(async () => {
  if (!editorHost.value) return

  monacoApi = await import('monaco-editor')

  const initialFile = activeFileInfo.value!
  model = monacoApi.editor.createModel(
    codeStore.fileContents[initialFile.key],
    initialFile.language,
  )

  editor = monacoApi.editor.create(editorHost.value, {
    model,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 13,
    lineNumbers: 'on',
    readOnly: initialFile.readOnly,
    scrollBeyondLastLine: false,
    find: {
      addExtraSpaceOnTop: false,
    },
  })

  // ─── Post-mount sync: garante que Monaco exibe o valor atual do store ────
  // O `await import('monaco-editor')` acima pode durar vários ticks de microtask.
  // Durante esse período, watches Pinia podem ter disparado e atualizado
  // `codeStore.fileContents[initialFile.key]` (ex: templateDraft.html chegou do backend),
  // mas o callback do watch no componente retornou imediatamente porque `model` era null.
  // O `monacoApi.editor.createModel(codeStore.fileContents[initialFile.key])` já leu o valor
  // mais recente APÓS o await — portanto normalmente está correto. Este check é uma salvaguarda
  // adicional para o caso onde múltiplas mutações do store ocorrem no mesmo flush Vue e o valor
  // lido no createModel não é o definitivo.
  {
    const currentStoreValue = codeStore.fileContents[initialFile.key]
    if (model.getValue() !== currentStoreValue) {
      suppressWatch = true
      model.setValue(currentStoreValue)
      suppressWatch = false
    }
  }

  applyStructuralWarnings()

  // Register CSS autocomplete provider (AC4)
  cssCompletionDisposable = registerCssCompletionProvider(
    monacoApi,
    computed(() => codeStore.fileContents.html),
  )

  // Apply CSS validation on initial load
  if (codeStore.activeFile === 'css') {
    cssErrorCount.value = applyCssMarkers(monacoApi, model, codeStore.fileContents.css)
  }

  editor.onDidChangeModelContent(() => {
    if (suppressWatch) return
    const key = codeStore.activeFile
    const file = CODE_FILES.find((f) => f.key === key)
    if (file?.readOnly) return

    // Debounce 500ms before applying to store (AC #14)
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      codeStore.applyMonacoEdit(key, editor.getValue())
      applyStructuralWarnings()
      // CSS validation (AC5)
      if (key === 'css' && monacoApi && model) {
        cssErrorCount.value = applyCssMarkers(monacoApi, model, editor.getValue())
      }
    }, 500)
  })

  // ─── Story 36.2: Click in Monaco → select tree node ────────────────────
  editor.onDidChangeCursorPosition((e: { position: { lineNumber: number } }) => {
    // Only for HTML files
    if (codeStore.activeFile !== 'html') return
    if (!model) return

    const lineNumber = e.position.lineNumber
    const nodeId = findNodeIdAtLine(lineNumber)
    if (!nodeId) return

    // Select in editorStore (highlights in canvas + tree)
    editorStore.selectElement(nodeId)

    // Select in inspectorStore (opens inspector panel)
    const node = templateStore.flatNodes?.get(nodeId)
    if (node) {
      inspectorStore.selectNode(node as import('@/types/template.types').TreeNode)
    }
  })
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  cssCompletionDisposable?.dispose()
  editor?.dispose()
  model?.dispose()
})

// ─── Story 36.2: Find data-node-id at or above the given line ─────────────
const DATA_NODE_ID_RE = /data-node-id=["']([^"']+)["']/

/**
 * Search from the given line upward to find the closest data-node-id attribute.
 * Returns the node ID string or null if none found.
 */
function findNodeIdAtLine(lineNumber: number): string | null {
  if (!model) return null
  const totalLines = model.getLineCount()
  if (lineNumber < 1 || lineNumber > totalLines) return null

  // Search current line and upward
  for (let line = lineNumber; line >= 1; line--) {
    const content = model.getLineContent(line)
    const match = DATA_NODE_ID_RE.exec(content)
    if (match?.[1]) return match[1]
  }
  return null
}

// ─── File switching ────────────────────────────────────────────────────────
function switchFile(key: CodeFileKey) {
  if (!editor || !monacoApi || !model) {
    codeStore.setActiveFile(key)
    return
  }
  if (codeStore.activeFile === key) return

  codeStore.setActiveFile(key)
  const file = CODE_FILES.find((f) => f.key === key)!

  suppressWatch = true
  monacoApi.editor.setModelLanguage(model, file.language)
  model.setValue(codeStore.fileContents[key])
  editor.updateOptions({ readOnly: file.readOnly })
  applyStructuralWarnings()
  // CSS validation on file switch
  if (key === 'css') {
    cssErrorCount.value = applyCssMarkers(monacoApi, model, codeStore.fileContents[key])
  } else {
    cssErrorCount.value = 0
    monacoApi.editor.setModelMarkers(model, 'css-validator', [])
  }
  suppressWatch = false
}

// ─── Structural warning decorations (AC #6) ──────────────────────────────
function applyStructuralWarnings() {
  if (!editor || !monacoApi || !model) return
  if (codeStore.activeFile !== 'html') {
    decorations = editor.deltaDecorations(decorations, [])
    return
  }

  const lines = model.getLinesContent() as string[]
  const newDecorations: any[] = []
  lines.forEach((line: string, idx: number) => {
    if (STRUCTURAL_SECTION_PATTERN.test(line)) {
      newDecorations.push({
        range: new monacoApi.Range(idx + 1, 1, idx + 1, 1),
        options: {
          isWholeLine: true,
          className: 'monaco-structural-warning',
          glyphMarginClassName: 'monaco-structural-glyph',
          hoverMessage: { value: 'Secao estrutural — nao remova este comentario' },
        },
      })
    }
  })
  decorations = editor.deltaDecorations(decorations, newDecorations)
}

// ─── Watch codeStore file changes → update Monaco (Visual→Code sync, AC #8)
watch(
  () => codeStore.fileContents[codeStore.activeFile],
  (newContent) => {
    if (!editor || !model || suppressWatch) return
    const current = editor.getValue()
    if (current !== newContent) {
      suppressWatch = true
      model.setValue(newContent)
      suppressWatch = false
      applyStructuralWarnings()
    }
  },
)

// ─── Watch active file change from FileExplorer ───────────────────────────
watch(
  () => codeStore.activeFile,
  (newKey) => {
    if (!editor || !monacoApi || !model) return
    const file = CODE_FILES.find((f) => f.key === newKey)!
    suppressWatch = true
    monacoApi.editor.setModelLanguage(model, file.language)
    model.setValue(codeStore.fileContents[newKey])
    editor.updateOptions({ readOnly: file.readOnly })
    applyStructuralWarnings()
    suppressWatch = false
  },
)

// ─── Watch selectedElementId → scroll to section in HTML (AC #10) ────────
watch(
  () => editorStore.selectedElementId,
  (nodeId) => {
    if (!editor || !model || codeStore.activeFile !== 'html' || !nodeId) return
    const lines = model.getLinesContent() as string[]
    const targetIdx = lines.findIndex((l: string) => l.includes(nodeId))
    if (targetIdx >= 0) {
      editor.revealLineInCenter(targetIdx + 1)
    }
  },
)
</script>

<style scoped>
.monaco-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.monaco-tabs__bar {
  display: flex;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem;
  border-bottom: 1px solid var(--color-neutral-200, #e5e7eb);
  background: var(--color-neutral-50, #f9fafb);
  flex-shrink: 0;
  overflow-x: auto;
}

.monaco-tabs__tab {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  border: 1px solid transparent;
  border-radius: 0.375rem;
  background: transparent;
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
  font-family: 'Courier New', monospace;
  cursor: pointer;
  color: var(--color-neutral-600, #4b5563);
  white-space: nowrap;
  transition: background 0.1s, color 0.1s, border-color 0.1s;
}

.monaco-tabs__tab:hover {
  background: var(--color-neutral-100, #f3f4f6);
  color: var(--color-neutral-800, #1f2937);
}

.monaco-tabs__tab--active {
  border-color: var(--color-primary-400, #60a5fa);
  color: var(--color-primary-700, #1d4ed8);
  background: #fff;
  font-weight: 600;
}

.monaco-tabs__tab--readonly {
  color: var(--color-neutral-400, #9ca3af);
}

.monaco-tabs__readonly-badge {
  font-size: 0.6rem;
  font-weight: 700;
  background: var(--color-neutral-200, #e5e7eb);
  color: var(--color-neutral-500, #6b7280);
  padding: 0.0625rem 0.25rem;
  border-radius: 3px;
  font-family: sans-serif;
}

.monaco-tabs__error-badge {
  font-size: 0.6rem;
  font-weight: 700;
  background: #ef4444;
  color: #fff;
  padding: 0.0625rem 0.3rem;
  border-radius: 9999px;
  font-family: sans-serif;
  min-width: 1rem;
  text-align: center;
}

.monaco-tabs__readonly-banner {
  background: var(--color-neutral-100, #f3f4f6);
  border-bottom: 1px solid var(--color-neutral-300, #d1d5db);
  color: var(--color-neutral-600, #4b5563);
  font-size: 0.75rem;
  padding: 0.375rem 0.75rem;
  flex-shrink: 0;
  font-style: italic;
}

.monaco-tabs__conflict-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fef3c7;
  border-bottom: 1px solid #fde68a;
  color: #92400e;
  font-size: 0.75rem;
  padding: 0.375rem 0.75rem;
  flex-shrink: 0;
  gap: 0.5rem;
}

.monaco-tabs__conflict-btn {
  background: #f59e0b;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  font-weight: 600;
  flex-shrink: 0;
}

.monaco-tabs__conflict-btn:hover {
  background: #d97706;
}

.monaco-tabs__editor {
  flex: 1;
  min-height: 0;
}
</style>

<style>
/* Global styles for Monaco decorations — cannot be scoped */
.monaco-structural-warning {
  background: rgba(234, 179, 8, 0.08) !important;
  border-left: 3px solid #eab308 !important;
}

.monaco-structural-glyph::before {
  content: '⚠';
  color: #eab308;
  font-size: 12px;
}
</style>
