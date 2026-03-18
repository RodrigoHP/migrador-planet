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
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useCodeStore } from '@/stores/codeStore'
import { CODE_FILES } from '@/types/editor.types'
import type { CodeFileKey } from '@/types/editor.types'
import { useEditorStore } from '@/stores/editorStore'

const codeStore = useCodeStore()
const editorStore = useEditorStore()

const editorHost = ref<HTMLElement | null>(null)

let monacoApi: any = null
let editor: any = null
let model: any = null
let decorations: any[] = []
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let suppressWatch = false

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

  applyStructuralWarnings()

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
    }, 500)
  })
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  editor?.dispose()
  model?.dispose()
})

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
