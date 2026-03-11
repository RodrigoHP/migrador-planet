<template>
  <section class="preview">
    <header class="preview__header" :style="{ backgroundColor: previewState.primaryColor }">
      <strong>Preview</strong>
    </header>
    <article
      class="preview__paper"
      :style="paperStyle"
    >
      <p class="preview__title">Template de Exemplo</p>
      <p class="preview__body">
        Este preview simula margens, fonte base, line-height e cor primária.
      </p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { watchDebounced } from '@vueuse/core'
import type { LayoutStore } from '@/stores/layout'

const props = defineProps<{
  layout: LayoutStore
}>()

const previewState = reactive({ ...props.layout })

watchDebounced(
  () => props.layout,
  (value) => {
    Object.assign(previewState, value)
  },
  { debounce: 300, deep: true },
)

const paperStyle = computed(() => ({
  fontFamily: previewState.baseFontFamily,
  fontSize: `${previewState.baseFontSize}px`,
  lineHeight: String(previewState.lineHeight),
  paddingTop: `${previewState.marginTop}px`,
  paddingBottom: `${previewState.marginBottom}px`,
  paddingLeft: `${previewState.marginLeft}px`,
  paddingRight: `${previewState.marginRight}px`,
  borderColor: previewState.primaryColor,
}))
</script>

<style scoped>
.preview {
  display: grid;
  gap: 0.5rem;
}

.preview__header {
  border-radius: 0.6rem;
  color: #fff;
  padding: 0.55rem 0.75rem;
}

.preview__paper {
  min-height: 420px;
  border: 2px solid;
  border-radius: 0.75rem;
  background: #fff;
}

.preview__title {
  margin: 0 0 0.5rem;
  font-weight: 700;
}

.preview__body {
  margin: 0;
  color: var(--color-neutral-700);
}
</style>
