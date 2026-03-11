<template>
  <div v-if="open" class="modal">
    <div class="modal__overlay" @click="$emit('close')" />
    <section class="modal__panel" role="dialog" aria-modal="true" aria-label="Bibliotecas disponíveis">
      <header class="modal__header">
        <h3>Bibliotecas disponíveis</h3>
        <button type="button" @click="$emit('close')">Fechar</button>
      </header>

      <p v-if="isLoading">Carregando catálogo...</p>

      <ul v-else class="modal__list">
        <li v-for="item in catalog" :key="item.name" class="modal__item">
          <div class="modal__item-header">
            <strong>{{ item.name }}</strong>
            <span class="badge">Ativa: {{ item.activeVersion }}</span>
          </div>
          <select v-model="selectedVersions[item.name]">
            <option v-for="version in item.versions" :key="version" :value="version">{{ version }}</option>
          </select>
        </li>
      </ul>

      <footer class="modal__footer">
        <button type="button" @click="$emit('close')">Cancelar</button>
        <button type="button" class="apply" @click="applyChanges">Aplicar</button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useBibliotecas } from '@/composables/useBibliotecas'
import { useLayoutStore } from '@/stores/layout'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const layout = useLayoutStore()
const { catalog, isLoading, fetchCatalog, updateVersion } = useBibliotecas()
const selectedVersions = reactive<Record<string, string>>({})

watch(() => props.open, async (isOpen) => {
  if (!isOpen) return
  await fetchCatalog()
  for (const item of catalog.value) {
    selectedVersions[item.name] =
      layout.bibliotecasVersions[item.name] ?? item.activeVersion
  }
}, { immediate: true })

function applyChanges() {
  for (const [name, version] of Object.entries(selectedVersions)) {
    updateVersion(name, version)
  }
  emit('close')
}
</script>

<style scoped>
.modal {
  position: fixed;
  inset: 0;
  z-index: 100;
}

.modal__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
}

.modal__panel {
  position: relative;
  max-width: 720px;
  max-height: 90vh;
  margin: 5vh auto;
  overflow: auto;
  background: #fff;
  border-radius: 0.75rem;
  border: 1px solid var(--color-neutral-200);
  padding: 1rem;
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal__list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
  display: grid;
  gap: 0.75rem;
}

.modal__item {
  border: 1px solid var(--color-neutral-200);
  border-radius: 0.6rem;
  padding: 0.6rem;
  display: grid;
  gap: 0.5rem;
}

.modal__item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.badge {
  font-size: 0.75rem;
  border-radius: 9999px;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 0.15rem 0.45rem;
}

.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.apply {
  background: var(--color-primary-600);
  color: #fff;
  border-color: var(--color-primary-600);
}
</style>
