<template>
  <form class="controls" @submit.prevent>
    <label>
      <span>Page Size</span>
      <select v-model="draft.pageSize">
        <option value="A4">A4</option>
        <option value="Letter">Letter</option>
        <option value="A3">A3</option>
      </select>
    </label>

    <div class="controls__grid">
      <label><span>Margem Top (mm)</span><input v-model.number="draft.marginTop" type="number" min="0" /></label>
      <label><span>Margem Bottom (mm)</span><input v-model.number="draft.marginBottom" type="number" min="0" /></label>
      <label><span>Margem Left (mm)</span><input v-model.number="draft.marginLeft" type="number" min="0" /></label>
      <label><span>Margem Right (mm)</span><input v-model.number="draft.marginRight" type="number" min="0" /></label>
    </div>

    <FontSelector v-model="draft.baseFontFamily" label="Fonte Base" />

    <label>
      <span>Tamanho da Fonte (px)</span>
      <input v-model.number="draft.baseFontSize" type="number" min="8" max="48" />
    </label>

    <ColorPicker v-model="draft.primaryColor" label="Cor Primária" />

    <label>
      <span>Line Height</span>
      <input v-model.number="draft.lineHeight" type="number" min="1" max="3" step="0.1" />
    </label>
  </form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { watchDebounced } from '@vueuse/core'
import { ColorPicker, FontSelector } from '@/atoms'
import type { LayoutStore } from '@/stores/layout'

const props = defineProps<{
  modelValue: LayoutStore
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Partial<LayoutStore>]
}>()

const draft = reactive<LayoutStore>({ ...props.modelValue })

watch(() => props.modelValue, (value) => {
  Object.assign(draft, value)
}, { deep: true })

watchDebounced(
  draft,
  (value) => {
    emit('update:modelValue', { ...value })
  },
  { debounce: 300, deep: true },
)
</script>

<style scoped>
.controls {
  display: grid;
  gap: 0.75rem;
}

.controls__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

label {
  display: grid;
  gap: 0.35rem;
}

span {
  font-size: 0.8125rem;
  color: var(--color-neutral-700);
}

input,
select {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.5rem;
  padding: 0.45rem 0.55rem;
}
</style>
