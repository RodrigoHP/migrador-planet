<template>
  <span
    v-if="!editing"
    :role="'spinbutton'"
    :aria-label="label"
    :aria-valuenow="value"
    :aria-valuemin="0"
    :tabindex="0"
    class="bmv"
    @click="startEdit"
    @keydown="onKeydown"
    >{{ value }}</span
  >
  <input
    v-else
    ref="inputRef"
    class="bmv bmv--editing"
    type="number"
    min="0"
    :aria-label="label"
    :value="value"
    @blur="commit"
    @keydown.enter.prevent="commit"
    @keydown.escape.prevent="cancel"
  />
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

const props = defineProps<{
  label: string
  value: number
}>()

const emit = defineEmits<{
  update: [value: number]
}>()

const editing = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)

function startEdit() {
  editing.value = true
  nextTick(() => inputRef.value?.select())
}

function commit() {
  if (!editing.value) return
  const raw = inputRef.value?.value ?? ''
  const num = parseFloat(raw)
  editing.value = false
  if (!isNaN(num) && num >= 0) {
    emit('update', num)
  }
}

function cancel() {
  editing.value = false
}

function onKeydown(e: KeyboardEvent) {
  const step = e.shiftKey ? 10 : 1
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    emit('update', props.value + step)
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    emit('update', Math.max(0, props.value - step))
  } else if (e.key === 'Enter') {
    startEdit()
  }
}
</script>

<style scoped>
.bmv {
  display: inline-block;
  min-width: 1rem;
  text-align: center;
  font-size: 0.625rem;
  color: var(--color-neutral-200, #e5e7eb);
  cursor: pointer;
  border-radius: 0.125rem;
  padding: 0 0.125rem;
  line-height: 1.25;
}

.bmv:hover,
.bmv:focus {
  background: rgba(255, 255, 255, 0.1);
  outline: 1px solid var(--color-primary-500, #6366f1);
}

.bmv--editing {
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-primary-500, #6366f1);
  color: var(--color-neutral-100, #f3f4f6);
  width: 2.5rem;
  padding: 0 0.125rem;
  outline: none;
}
</style>
