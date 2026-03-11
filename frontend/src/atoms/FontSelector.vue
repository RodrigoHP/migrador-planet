<template>
  <label class="font-selector">
    <span class="font-selector__label">{{ label }}</span>
    <select :value="modelValue" @change="onChange">
      <option v-for="font in fonts" :key="font" :value="font">{{ font }}</option>
    </select>
  </label>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: string
    label?: string
    fonts?: string[]
  }>(),
  {
    label: 'Fonte base',
    fonts: () => ['Inter', 'Roboto', 'Open Sans'],
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.font-selector {
  display: grid;
  gap: 0.35rem;
}

.font-selector__label {
  font-size: 0.8125rem;
  color: var(--color-neutral-700);
}

select {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.5rem;
  padding: 0.45rem 0.55rem;
  background: #fff;
}
</style>
