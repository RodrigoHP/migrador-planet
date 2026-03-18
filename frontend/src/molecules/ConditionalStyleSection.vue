<template>
  <div class="css-section">
    <div class="css-section__header">
      <span class="css-section__title">Estilo Condicional</span>
    </div>

    <div class="css-section__body">
      <ConditionalStyleRule
        v-for="(rule, idx) in modelValue"
        :key="idx"
        :modelValue="rule"
        @update:modelValue="updateRule(idx, $event)"
        @remove="removeRule(idx)"
      />

      <button class="css-section__add" type="button" @click="addRule">
        + Regra
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import ConditionalStyleRule from './ConditionalStyleRule.vue'
import type { StyleRule } from '@/utils/formatStringGenerator'

const props = withDefaults(
  defineProps<{
    modelValue: StyleRule[]
  }>(),
  {
    modelValue: () => [],
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: StyleRule[]]
}>()

function addRule() {
  const newRule: StyleRule = {
    fieldPath: '',
    operator: '===',
    value: '',
    property: 'color',
    propertyValue: '#000000',
  }
  emit('update:modelValue', [...props.modelValue, newRule])
}

function updateRule(idx: number, updated: StyleRule) {
  const rules = [...props.modelValue]
  rules[idx] = updated
  emit('update:modelValue', rules)
}

function removeRule(idx: number) {
  const rules = props.modelValue.filter((_, i) => i !== idx)
  emit('update:modelValue', rules)
}
</script>

<style scoped>
.css-section {
  display: flex;
  flex-direction: column;
}

.css-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
}

.css-section__title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-300, #d1d5db);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.css-section__body {
  padding: 0.25rem 0.75rem 0.625rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.css-section__add {
  align-self: flex-start;
  background: none;
  border: 1px dashed var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.css-section__add:hover {
  border-color: var(--color-primary-500, #6366f1);
  color: var(--color-primary-400, #818cf8);
}
</style>
