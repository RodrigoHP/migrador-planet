<template>
  <section class="panel">
    <h3>Detalhes do Campo</h3>

    <p v-if="!field" class="panel__empty">Selecione um campo na tabela para editar.</p>

    <template v-else>
      <dl class="panel__list">
        <div><dt>ID</dt><dd>{{ field.id }}</dd></div>
        <div><dt>Texto PDF</dt><dd>{{ field.pdfText || '-' }}</dd></div>
        <div><dt>Tipo</dt><dd>{{ field.type }}</dd></div>
        <div><dt>Status</dt><dd>{{ field.status }}</dd></div>
      </dl>

      <label class="panel__label" for="jsonPath">jsonPath</label>
      <input id="jsonPath" v-model="editedPath" class="panel__input" type="text" />
      <button class="panel__save" type="button" @click="savePath">Salvar</button>

      <div v-if="field.candidates?.length" class="panel__candidates">
        <strong>Candidatos alternativos</strong>
        <ul>
          <li v-for="candidate in field.candidates" :key="candidate">
            <button type="button" @click="selectCandidate(candidate)">{{ candidate }}</button>
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { FieldMapping } from '@/types'

const props = defineProps<{
  field: FieldMapping | null
}>()

const emit = defineEmits<{
  save: [payload: { id: string; jsonPath: string }]
}>()

const editedPath = ref('')

watch(() => props.field, (field) => {
  editedPath.value = field?.jsonPath ?? ''
}, { immediate: true })

function savePath() {
  if (!props.field) return
  emit('save', { id: props.field.id, jsonPath: editedPath.value.trim() })
}

function selectCandidate(candidate: string) {
  editedPath.value = candidate
  savePath()
}
</script>

<style scoped>
.panel {
  display: grid;
  gap: 0.75rem;
}

.panel h3 {
  margin: 0;
}

.panel__empty {
  margin: 0;
  color: var(--color-neutral-700);
}

.panel__list {
  margin: 0;
  display: grid;
  gap: 0.5rem;
}

.panel__list div {
  display: grid;
  gap: 0.125rem;
}

.panel__list dt {
  font-size: 0.75rem;
  color: var(--color-neutral-500);
}

.panel__list dd {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-neutral-900);
}

.panel__label {
  font-size: 0.8125rem;
  color: var(--color-neutral-700);
}

.panel__input {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.5rem;
  padding: 0.45rem 0.55rem;
}

.panel__save {
  border: 1px solid var(--color-primary-600);
  color: var(--color-primary-600);
  background: #fff;
  border-radius: 0.5rem;
  padding: 0.4rem 0.65rem;
  cursor: pointer;
}

.panel__save:hover {
  background: #eff6ff;
}

.panel__candidates ul {
  margin: 0.35rem 0 0;
  padding-left: 1rem;
}

.panel__candidates button {
  border: none;
  background: transparent;
  color: var(--color-primary-600);
  padding: 0;
  cursor: pointer;
}
</style>
