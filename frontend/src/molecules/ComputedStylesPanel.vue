<template>
  <aside
    v-if="editorStore.selectedElementId && codeStore.activeFile === 'css'"
    class="computed-styles"
    data-testid="computed-styles-panel"
  >
    <header class="computed-styles__header">
      <span class="computed-styles__title">Computed Styles</span>
      <span class="computed-styles__element">{{ editorStore.selectedElementId }}</span>
    </header>
    <div class="computed-styles__body">
      <div
        v-for="(value, prop) in computedStyles"
        :key="prop"
        class="computed-styles__row"
      >
        <span class="computed-styles__prop">{{ prop }}</span>
        <span class="computed-styles__value">{{ value }}</span>
      </div>
      <div v-if="Object.keys(computedStyles).length === 0" class="computed-styles__empty">
        Nenhum estilo aplicado
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useEditorStore } from '@/stores/editorStore'
import { useCodeStore } from '@/stores/codeStore'
import { useTemplateStore } from '@/stores/templateStore'

const editorStore = useEditorStore()
const codeStore = useCodeStore()
const templateStore = useTemplateStore()

/** Extract inline styles from the selected element in the document tree. */
const computedStyles = computed<Record<string, string>>(() => {
  const id = editorStore.selectedElementId
  if (!id || !templateStore.documentTree) return {}

  // Traverse flat map to find node
  const node = templateStore.flatMap?.[id]
  if (!node) return {}

  const styles: Record<string, string> = {}

  // Inline styles from node properties
  const inlineStyle = node.properties?.style
  if (typeof inlineStyle === 'string') {
    for (const decl of inlineStyle.split(';')) {
      const [prop, val] = decl.split(':')
      if (prop?.trim() && val?.trim()) {
        styles[prop.trim()] = val.trim()
      }
    }
  }

  // Object-style properties
  if (typeof inlineStyle === 'object' && inlineStyle) {
    for (const [k, v] of Object.entries(inlineStyle)) {
      styles[k] = String(v)
    }
  }

  return styles
})
</script>

<style scoped>
.computed-styles {
  border-top: 1px solid var(--color-neutral-200, #e5e7eb);
  background: var(--color-neutral-50, #f9fafb);
  max-height: 200px;
  overflow-y: auto;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.computed-styles__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.375rem 0.5rem;
  background: var(--color-neutral-100, #f3f4f6);
  border-bottom: 1px solid var(--color-neutral-200, #e5e7eb);
}

.computed-styles__title {
  font-weight: 600;
  color: var(--color-neutral-700, #374151);
}

.computed-styles__element {
  font-family: monospace;
  color: var(--color-primary-600, #2563eb);
}

.computed-styles__body {
  padding: 0.375rem 0.5rem;
}

.computed-styles__row {
  display: flex;
  gap: 0.5rem;
  padding: 0.125rem 0;
}

.computed-styles__prop {
  color: var(--color-neutral-600, #4b5563);
  font-family: monospace;
  min-width: 120px;
}

.computed-styles__value {
  color: var(--color-neutral-800, #1f2937);
  font-family: monospace;
}

.computed-styles__empty {
  color: var(--color-neutral-400, #9ca3af);
  font-style: italic;
  padding: 0.25rem 0;
}
</style>
