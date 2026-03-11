<template>
  <div
    class="dropzone"
    :class="{ 'dropzone--drag': isDragging }"
    @dragenter.prevent="isDragging = true"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="onDrop"
  >
    <p class="dropzone__label">{{ label }}</p>

    <p v-if="modelValue" class="dropzone__file">
      {{ modelValue.name }} ({{ formatSize(modelValue.size) }})
    </p>
    <p v-else class="dropzone__hint">Arraste o arquivo aqui ou selecione manualmente</p>

    <div class="dropzone__actions">
      <button class="dropzone__button" type="button" @click="openPicker">Selecionar arquivo</button>
      <button v-if="modelValue" class="dropzone__clear" type="button" @click="$emit('update:modelValue', null)">Limpar</button>
    </div>

    <input ref="inputRef" class="dropzone__input" type="file" :accept="accept" @change="onInputChange" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  accept: string
  label: string
  modelValue: File | null
}>()

const emit = defineEmits<{
  'update:modelValue': [File | null]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

function parseAccept(value: string): { mimes: string[]; exts: string[] } {
  const tokens = value.split(',').map((v) => v.trim()).filter(Boolean)
  const mimes: string[] = []
  const exts: string[] = []
  for (const token of tokens) {
    if (token.startsWith('.')) exts.push(token)
    else if (token.includes('/')) mimes.push(token)
  }
  return { mimes, exts }
}

async function openPicker() {
  if ('showOpenFilePicker' in window) {
    try {
      const parsed = parseAccept(props.accept)
      const acceptRecord: Record<string, string[]> = {}
      if (parsed.mimes.length > 0) {
        for (const mime of parsed.mimes) acceptRecord[mime] = parsed.exts
      } else {
        acceptRecord['application/octet-stream'] = parsed.exts
      }
      const [handle] = await (window as any).showOpenFilePicker({
        multiple: false,
        types: [{ description: props.label, accept: acceptRecord }],
      })
      const file = await handle.getFile()
      emit('update:modelValue', file)
      return
    } catch (error: any) {
      if (error?.name === 'AbortError') return
    }
  }
  inputRef.value?.click()
}

function onInputChange(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.files?.[0] ?? null)
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0] ?? null
  emit('update:modelValue', file)
}

function formatSize(size: number) {
  return `${(size / 1024).toFixed(1)} KB`
}
</script>

<style scoped>
.dropzone {
  border: 2px dashed var(--color-neutral-200);
  border-radius: 0.75rem;
  padding: 1rem;
  background: #fff;
}

.dropzone--drag {
  border-color: var(--color-primary-600);
  background: #eff6ff;
}

.dropzone__label {
  margin: 0;
  font-weight: 600;
  color: var(--color-neutral-900);
}

.dropzone__hint,
.dropzone__file {
  margin: 0.5rem 0;
  color: var(--color-neutral-700);
}

.dropzone__actions {
  display: flex;
  gap: 0.5rem;
}

.dropzone__button,
.dropzone__clear {
  border: 1px solid var(--color-neutral-200);
  background: #fff;
  color: var(--color-neutral-900);
  border-radius: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.dropzone__button:hover,
.dropzone__clear:hover {
  background: var(--color-neutral-100);
}

.dropzone__input {
  display: none;
}
</style>
