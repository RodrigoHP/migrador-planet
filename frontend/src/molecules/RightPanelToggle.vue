<template>
  <div class="toggle" role="tablist" aria-label="Modo do painel direito">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="toggle__btn"
      :class="{ 'toggle__btn--active': modelValue === option.value }"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
type RightPanel = 'html-preview' | 'monaco' | 'wysiwyg' | 'chartjs-config'

defineProps<{
  modelValue: RightPanel
}>()

defineEmits<{
  'update:modelValue': [value: RightPanel]
}>()

const options: Array<{ label: string; value: RightPanel }> = [
  { label: 'HTML Preview', value: 'html-preview' },
  { label: 'Monaco', value: 'monaco' },
  { label: 'WYSIWYG', value: 'wysiwyg' },
  { label: 'Chart.js Config', value: 'chartjs-config' },
]
</script>

<style scoped>
.toggle {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.toggle__btn {
  border: 1px solid var(--color-neutral-200);
  background: #fff;
  border-radius: 0.45rem;
  padding: 0.3rem 0.6rem;
  font-size: 0.82rem;
  color: var(--color-neutral-700);
  cursor: pointer;
}

.toggle__btn--active {
  color: #fff;
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
}
</style>
