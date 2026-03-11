<template>
  <section class="monaco-tabs">
    <div class="monaco-tabs__bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="monaco-tabs__tab"
        :class="{ 'monaco-tabs__tab--active': activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div ref="editorHost" class="monaco-tabs__editor" />
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

type TabKey = 'html' | 'css' | 'js'

const props = defineProps<{
  html: string
  css: string
  js: string
}>()

const emit = defineEmits<{
  'update:html': [value: string]
  'update:css': [value: string]
  'update:js': [value: string]
}>()

const tabs: Array<{ key: TabKey; label: string; language: 'html' | 'css' | 'javascript' }> = [
  { key: 'html', label: 'index.html', language: 'html' },
  { key: 'css', label: 'style.css', language: 'css' },
  { key: 'js', label: 'base.js', language: 'javascript' },
]

const activeTab = ref<TabKey>('html')
const codeState = ref<{ html: string; css: string; js: string }>({
  html: props.html,
  css: props.css,
  js: props.js,
})

const editorHost = ref<HTMLElement | null>(null)
let monacoApi: any = null
let editor: any = null
let model: any = null

function currentLanguage(tab: TabKey) {
  return tabs.find((item) => item.key === tab)?.language ?? 'html'
}

function emitCurrentCode(tab: TabKey, value: string) {
  if (tab === 'html') emit('update:html', value)
  if (tab === 'css') emit('update:css', value)
  if (tab === 'js') emit('update:js', value)
}

function switchTab(tab: TabKey) {
  if (!editor || !monacoApi || !model) return
  if (activeTab.value === tab) return

  const outgoingTab = activeTab.value
  codeState.value[outgoingTab] = editor.getValue()
  emitCurrentCode(outgoingTab, codeState.value[outgoingTab])

  activeTab.value = tab
  monacoApi.editor.setModelLanguage(model, currentLanguage(tab))
  model.setValue(codeState.value[tab])
}

onMounted(async () => {
  if (!editorHost.value) return

  monacoApi = await import('monaco-editor')
  model = monacoApi.editor.createModel(codeState.value.html, 'html')
  editor = monacoApi.editor.create(editorHost.value, {
    model,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 13,
  })

  editor.onDidChangeModelContent(() => {
    const value = editor.getValue()
    codeState.value[activeTab.value] = value
    emitCurrentCode(activeTab.value, value)
  })
})

onBeforeUnmount(() => {
  editor?.dispose()
  model?.dispose()
})

watch(() => props.html, (value) => {
  codeState.value.html = value
  if (activeTab.value === 'html' && editor) editor.setValue(value)
})

watch(() => props.css, (value) => {
  codeState.value.css = value
  if (activeTab.value === 'css' && editor) editor.setValue(value)
})

watch(() => props.js, (value) => {
  codeState.value.js = value
  if (activeTab.value === 'js' && editor) editor.setValue(value)
})
</script>

<style scoped>
.monaco-tabs {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.75rem;
  overflow: hidden;
}

.monaco-tabs__bar {
  display: flex;
  gap: 0.25rem;
  padding: 0.4rem;
  border-bottom: 1px solid var(--color-neutral-200);
  background: var(--color-neutral-50);
}

.monaco-tabs__tab {
  border: 1px solid transparent;
  border-radius: 0.4rem;
  background: transparent;
  padding: 0.35rem 0.6rem;
  font-size: 0.8rem;
  cursor: pointer;
  color: var(--color-neutral-700);
}

.monaco-tabs__tab--active {
  border-color: var(--color-primary-600);
  color: var(--color-primary-600);
  background: #fff;
}

.monaco-tabs__editor {
  height: 480px;
}
</style>
