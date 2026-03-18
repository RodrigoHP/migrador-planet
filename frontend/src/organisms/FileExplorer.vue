<template>
  <div class="file-explorer" role="tree" aria-label="Explorador de arquivos do template">
    <div class="file-explorer__section">
      <button
        type="button"
        class="file-explorer__group"
        aria-expanded="true"
        @click="toggleGroup('template')"
      >
        <span class="file-explorer__chevron" :class="{ 'file-explorer__chevron--open': openGroups.template }">›</span>
        <span class="file-explorer__folder-icon" aria-hidden="true">📁</span>
        <span class="file-explorer__group-label">Template</span>
      </button>

      <ul v-if="openGroups.template" class="file-explorer__list" role="group">
        <!-- index.html -->
        <li role="treeitem">
          <button
            type="button"
            class="file-explorer__item"
            :class="{ 'file-explorer__item--active': codeStore.activeFile === 'html' }"
            @click="openFile('html')"
          >
            <span class="file-explorer__file-icon" aria-hidden="true">📄</span>
            <span class="file-explorer__file-label">index.html</span>
          </button>
        </li>

        <!-- css/ -->
        <li role="treeitem">
          <button
            type="button"
            class="file-explorer__group file-explorer__group--nested"
            :aria-expanded="openGroups.css"
            @click="toggleGroup('css')"
          >
            <span class="file-explorer__chevron" :class="{ 'file-explorer__chevron--open': openGroups.css }">›</span>
            <span class="file-explorer__folder-icon" aria-hidden="true">📁</span>
            <span class="file-explorer__group-label">css</span>
          </button>
          <ul v-if="openGroups.css" class="file-explorer__list file-explorer__list--nested" role="group">
            <li role="treeitem">
              <button
                type="button"
                class="file-explorer__item file-explorer__item--nested"
                :class="{ 'file-explorer__item--active': codeStore.activeFile === 'css' }"
                @click="openFile('css')"
              >
                <span class="file-explorer__file-icon" aria-hidden="true">🎨</span>
                <span class="file-explorer__file-label">style.css</span>
              </button>
            </li>
          </ul>
        </li>

        <!-- js/ -->
        <li role="treeitem">
          <button
            type="button"
            class="file-explorer__group file-explorer__group--nested"
            :aria-expanded="openGroups.js"
            @click="toggleGroup('js')"
          >
            <span class="file-explorer__chevron" :class="{ 'file-explorer__chevron--open': openGroups.js }">›</span>
            <span class="file-explorer__folder-icon" aria-hidden="true">📁</span>
            <span class="file-explorer__group-label">js</span>
          </button>
          <ul v-if="openGroups.js" class="file-explorer__list file-explorer__list--nested" role="group">
            <li role="treeitem">
              <button
                type="button"
                class="file-explorer__item file-explorer__item--nested"
                :class="{ 'file-explorer__item--active': codeStore.activeFile === 'js' }"
                @click="openFile('js')"
              >
                <span class="file-explorer__file-icon" aria-hidden="true">📜</span>
                <span class="file-explorer__file-label">base.js</span>
              </button>
            </li>
            <li role="treeitem">
              <button
                type="button"
                class="file-explorer__item file-explorer__item--nested"
                :class="{ 'file-explorer__item--active': codeStore.activeFile === 'exemplo' }"
                @click="openFile('exemplo')"
              >
                <span class="file-explorer__file-icon" aria-hidden="true">📜</span>
                <span class="file-explorer__file-label">exemplo.js</span>
                <span class="file-explorer__badge file-explorer__badge--readonly" title="Somente leitura">RO</span>
              </button>
            </li>
          </ul>
        </li>

        <!-- assets/ -->
        <li role="treeitem">
          <button
            type="button"
            class="file-explorer__group file-explorer__group--nested"
            :aria-expanded="openGroups.assets"
            @click="toggleGroup('assets')"
          >
            <span class="file-explorer__chevron" :class="{ 'file-explorer__chevron--open': openGroups.assets }">›</span>
            <span class="file-explorer__folder-icon" aria-hidden="true">📁</span>
            <span class="file-explorer__group-label">assets</span>
          </button>
          <ul v-if="openGroups.assets" class="file-explorer__list file-explorer__list--nested" role="group">
            <li role="treeitem">
              <span class="file-explorer__item file-explorer__item--nested file-explorer__item--disabled">
                <span class="file-explorer__file-icon" aria-hidden="true">📁</span>
                <span class="file-explorer__file-label">images</span>
              </span>
            </li>
            <li role="treeitem">
              <span class="file-explorer__item file-explorer__item--nested file-explorer__item--disabled">
                <span class="file-explorer__file-icon" aria-hidden="true">📁</span>
                <span class="file-explorer__file-label">fonts</span>
              </span>
            </li>
          </ul>
        </li>
      </ul>
    </div>

    <!-- MVP info -->
    <div class="file-explorer__footer">
      <span class="file-explorer__hint">Criar/excluir/renomear: bloqueado (MVP)</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useCodeStore } from '@/stores/codeStore'
import type { CodeFileKey } from '@/types/editor.types'
import { useEditorStore } from '@/stores/editorStore'

const codeStore = useCodeStore()
const editorStore = useEditorStore()

const openGroups = reactive({
  template: true,
  css: true,
  js: true,
  assets: false,
})

function toggleGroup(group: keyof typeof openGroups) {
  openGroups[group] = !openGroups[group]
}

function openFile(key: CodeFileKey) {
  codeStore.setActiveFile(key)
  // Ensure code tab is active in center panel
  editorStore.setActiveCenterTab('code')
}
</script>

<style scoped>
.file-explorer {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  font-size: 0.8125rem;
  color: var(--color-neutral-200, #e5e7eb);
}

.file-explorer__section {
  flex: 1;
  padding: 0.5rem 0;
}

.file-explorer__group {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  color: var(--color-neutral-300, #d1d5db);
  font-size: 0.8125rem;
  font-weight: 600;
  text-align: left;
  border-radius: 0.25rem;
  transition: background 0.1s;
}

.file-explorer__group:hover {
  background: var(--color-neutral-700, #374151);
}

.file-explorer__group--nested {
  padding-left: 1.25rem;
  font-weight: 500;
}

.file-explorer__chevron {
  display: inline-block;
  font-size: 0.75rem;
  transition: transform 0.15s;
  transform: rotate(0deg);
  width: 0.75rem;
  flex-shrink: 0;
}

.file-explorer__chevron--open {
  transform: rotate(90deg);
}

.file-explorer__folder-icon {
  font-size: 0.875rem;
}

.file-explorer__group-label {
  flex: 1;
}

.file-explorer__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.file-explorer__list--nested {
  padding-left: 0.75rem;
}

.file-explorer__item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.275rem 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.8rem;
  text-align: left;
  border-radius: 0.25rem;
  transition: background 0.1s, color 0.1s;
}

.file-explorer__item:hover {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
}

.file-explorer__item--active {
  background: var(--color-primary-800, #1e40af);
  color: var(--color-primary-200, #bfdbfe);
}

.file-explorer__item--nested {
  padding-left: 1.5rem;
}

.file-explorer__item--disabled {
  cursor: default;
  opacity: 0.5;
}

.file-explorer__item--disabled:hover {
  background: none;
  color: var(--color-neutral-400, #9ca3af);
}

.file-explorer__file-icon {
  font-size: 0.75rem;
  flex-shrink: 0;
}

.file-explorer__file-label {
  flex: 1;
  font-family: 'Courier New', monospace;
}

.file-explorer__badge {
  font-size: 0.625rem;
  font-weight: 700;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  flex-shrink: 0;
}

.file-explorer__badge--readonly {
  background: var(--color-neutral-600, #4b5563);
  color: var(--color-neutral-300, #d1d5db);
}

.file-explorer__footer {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid var(--color-neutral-700, #374151);
  margin-top: auto;
}

.file-explorer__hint {
  font-size: 0.7rem;
  color: var(--color-neutral-600, #4b5563);
  font-style: italic;
}
</style>
