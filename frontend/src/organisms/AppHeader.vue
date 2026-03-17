<template>
  <header class="app-header">
    <div class="app-header__logo">
      <span class="app-header__logo-text">Migrador</span>
      <span class="app-header__logo-sub">Planetexpress</span>
    </div>

    <!-- Step indicator slot -->
    <div class="app-header__stepper">
      <slot name="stepper" />
    </div>

    <div class="app-header__actions">
      <button
        v-if="showSave"
        class="app-header__btn-save"
        type="button"
        :disabled="isSaving"
        @click="handleSave"
      >
        {{ isSaving ? 'Salvando...' : saveStatus === 'success' ? '✓ Salvo' : saveStatus === 'error' ? '✗ Erro ao salvar' : 'Salvar projeto' }}
      </button>
      <button
        class="app-header__btn-bibliotecas"
        type="button"
        :disabled="!showBibliotecas"
        @click="emit('open-bibliotecas')"
      >
        Bibliotecas
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useProject } from '@/composables/useProject'

withDefaults(
  defineProps<{
    showBibliotecas?: boolean
    showSave?: boolean
  }>(),
  { showBibliotecas: false, showSave: false },
)

const emit = defineEmits<{
  'open-bibliotecas': []
}>()

const { save } = useProject()
const isSaving = ref(false)
const saveStatus = ref<'success' | 'error' | null>(null)

async function handleSave() {
  if (isSaving.value) return
  isSaving.value = true
  saveStatus.value = null
  try {
    await save()
    saveStatus.value = 'success'
  } catch {
    saveStatus.value = 'error'
  } finally {
    isSaving.value = false
    setTimeout(() => { saveStatus.value = null }, 2500)
  }
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 56px;
  background-color: #ffffff;
  border-bottom: 1px solid #E5E5E5;
  position: sticky;
  top: 0;
  z-index: 50;
}

.app-header__logo {
  display: flex;
  align-items: baseline;
  gap: 0.375rem;
}

.app-header__logo-text {
  font-size: 1.125rem;
  font-weight: 700;
  color: #2563EB;
}

.app-header__logo-sub {
  font-size: 0.75rem;
  color: #737373;
}

.app-header__stepper {
  flex: 1;
  display: flex;
  justify-content: center;
}

.app-header__btn-bibliotecas {
  padding: 0.375rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #2563EB;
  background: transparent;
  border: 1px solid #2563EB;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.app-header__btn-bibliotecas:hover:not(:disabled) {
  background-color: #EFF6FF;
}

.app-header__btn-bibliotecas:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.app-header__btn-save {
  padding: 0.375rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #ffffff;
  background: #2563EB;
  border: 1px solid #2563EB;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.app-header__btn-save:hover:not(:disabled) {
  background-color: #1D4ED8;
}

.app-header__btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
