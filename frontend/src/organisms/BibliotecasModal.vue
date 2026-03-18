<template>
  <div v-if="open" class="bm">
    <div class="bm__overlay" @click="$emit('close')" />
    <section
      class="bm__panel"
      role="dialog"
      aria-modal="true"
      aria-label="Gerenciamento de Bibliotecas"
    >
      <!-- Header -->
      <header class="bm__header">
        <h3 class="bm__title">📚 Bibliotecas</h3>
        <button type="button" class="bm__btn-close" aria-label="Fechar" @click="$emit('close')">
          ✕
        </button>
      </header>

      <!-- Tabs -->
      <nav class="bm__tabs" role="tablist" aria-label="Categorias de bibliotecas">
        <button
          v-for="tab in TABS"
          :key="tab.id"
          role="tab"
          type="button"
          class="bm__tab"
          :class="{ 'bm__tab--active': activeTab === tab.id }"
          :aria-selected="activeTab === tab.id"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
          <span class="bm__tab-count">{{ getByCategory(tab.id).length }}</span>
        </button>
      </nav>

      <!-- Tab content -->
      <div class="bm__content" role="tabpanel">
        <!-- Error message -->
        <div v-if="uploadError" class="bm__error" role="alert">
          {{ uploadError }}
        </div>

        <!-- Loading -->
        <p v-if="isLoading" class="bm__loading">Carregando...</p>

        <template v-else>
          <BibliotecaFileList
            :items="getByCategory(activeTab)"
            @remove="handleRemoveRequest"
          />
        </template>
      </div>

      <!-- Footer -->
      <footer class="bm__footer">
        <button type="button" class="bm__btn-add" @click="triggerUpload">
          + Adicionar {{ currentTabLabel }}
        </button>
        <button type="button" class="bm__btn-cancel" @click="$emit('close')">
          Fechar
        </button>
      </footer>

      <!-- Hidden file input -->
      <input
        ref="fileInputRef"
        type="file"
        class="bm__file-input"
        :accept="currentAccept"
        @change="handleFileSelected"
      />
    </section>

    <!-- Confirmation dialog -->
    <div v-if="confirmDialog.visible" class="bm__confirm-overlay">
      <div class="bm__confirm" role="alertdialog" aria-modal="true">
        <p class="bm__confirm-msg">{{ confirmDialog.message }}</p>
        <div class="bm__confirm-actions">
          <button type="button" class="bm__btn-confirm-cancel" @click="confirmDialog.visible = false">
            Cancelar
          </button>
          <button type="button" class="bm__btn-confirm-ok" @click="executeRemove">
            Remover
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { useBibliotecas, ALLOWED_EXTENSIONS } from '@/composables/useBibliotecas'
import type { BibliotecaTab } from '@/composables/useBibliotecas'
import BibliotecaFileList from '@/molecules/BibliotecaFileList.vue'

// ─── Props / Emits ────────────────────────────────────────────────────────────

const props = defineProps<{
  open: boolean
  /** Optional serialized template content used to detect referenced files */
  activeTemplateContent?: string
}>()

defineEmits<{
  close: []
}>()

// ─── Tab config ───────────────────────────────────────────────────────────────

const TABS: { id: BibliotecaTab; label: string }[] = [
  { id: 'fonts', label: 'Fontes' },
  { id: 'css',   label: 'CSS' },
  { id: 'js',    label: 'JS' },
]

const activeTab = ref<BibliotecaTab>('fonts')

const currentTabLabel = computed(() => TABS.find((t) => t.id === activeTab.value)?.label ?? '')

const currentAccept = computed(() =>
  ALLOWED_EXTENSIONS[activeTab.value].join(','),
)

// ─── Composable ───────────────────────────────────────────────────────────────

const { isLoading, loadFiles, addFile, removeFile, getByCategory, isFileReferenced } = useBibliotecas()

const uploadError = ref<string | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

// ─── Load on open ─────────────────────────────────────────────────────────────

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    uploadError.value = null
    await loadFiles()
  },
  { immediate: true },
)

// ─── Upload ───────────────────────────────────────────────────────────────────

function triggerUpload() {
  uploadError.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
    fileInputRef.value.click()
  }
}

async function handleFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploadError.value = null
  const result = await addFile(file, activeTab.value)
  if (!result.success) {
    uploadError.value = result.message ?? 'Erro desconhecido ao adicionar arquivo'
  }
  // Reset so same file can be re-selected if needed
  input.value = ''
}

// ─── Remove with confirmation ─────────────────────────────────────────────────

const confirmDialog = reactive({
  visible: false,
  message: '',
  pendingId: '',
})

function handleRemoveRequest(id: string, name: string) {
  uploadError.value = null
  const referenced = isFileReferenced(name, props.activeTemplateContent)
  if (referenced) {
    confirmDialog.message = `O arquivo "${name}" está referenciado no template ativo. Deseja remover mesmo assim?`
    confirmDialog.pendingId = id
    confirmDialog.visible = true
    return
  }
  confirmDialog.pendingId = id
  executeRemove()
}

async function executeRemove() {
  confirmDialog.visible = false
  const result = await removeFile(confirmDialog.pendingId)
  if (!result.success) {
    uploadError.value = result.message ?? 'Erro ao remover arquivo'
  }
  confirmDialog.pendingId = ''
}
</script>

<style scoped>
/* ── Overlay + panel ─────────────────────────────────────────────── */
.bm {
  position: fixed;
  inset: 0;
  z-index: 200;
}

.bm__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
}

.bm__panel {
  position: relative;
  width: min(720px, 95vw);
  max-height: 85vh;
  margin: 5vh auto;
  overflow: auto;
  background: #fff;
  border-radius: 0.75rem;
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  padding: 1.25rem 1.25rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.bm__file-input {
  display: none;
}

/* ── Header ──────────────────────────────────────────────────────── */
.bm__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-neutral-100, #f5f5f5);
}

.bm__title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-neutral-800, #262626);
  margin: 0;
}

.bm__btn-close {
  background: transparent;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  color: var(--color-neutral-500, #737373);
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  transition: background-color 150ms ease;
}

.bm__btn-close:hover {
  background: var(--color-neutral-100, #f5f5f5);
}

/* ── Tabs ────────────────────────────────────────────────────────── */
.bm__tabs {
  display: flex;
  gap: 0.25rem;
  padding: 0.75rem 0 0;
  border-bottom: 2px solid var(--color-neutral-100, #f5f5f5);
}

.bm__tab {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.4rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  color: var(--color-neutral-600, #525252);
  transition: color 150ms ease, border-color 150ms ease;
}

.bm__tab:hover {
  color: var(--color-primary-600, #2563eb);
}

.bm__tab--active {
  color: var(--color-primary-600, #2563eb);
  border-bottom-color: var(--color-primary-600, #2563eb);
}

.bm__tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 0.3rem;
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--color-neutral-100, #f5f5f5);
  color: var(--color-neutral-600, #525252);
  border-radius: 9999px;
}

.bm__tab--active .bm__tab-count {
  background: #eff6ff;
  color: #1d4ed8;
}

/* ── Content area ────────────────────────────────────────────────── */
.bm__content {
  flex: 1;
  overflow: auto;
  padding: 1rem 0;
  min-height: 120px;
}

.bm__loading {
  color: var(--color-neutral-500, #737373);
  font-size: 0.875rem;
  margin: 0;
}

.bm__error {
  padding: 0.5rem 0.75rem;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 0.5rem;
  color: #dc2626;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

/* ── Footer ──────────────────────────────────────────────────────── */
.bm__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-neutral-100, #f5f5f5);
}

.bm__btn-add {
  padding: 0.4rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #fff;
  background: var(--color-primary-600, #2563eb);
  border: 1px solid var(--color-primary-600, #2563eb);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.bm__btn-add:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

.bm__btn-cancel {
  padding: 0.4rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-neutral-700, #404040);
  background: transparent;
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.bm__btn-cancel:hover {
  background: var(--color-neutral-50, #fafafa);
}

/* ── Confirmation dialog ────────────────────────────────────────── */
.bm__confirm-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
}

.bm__confirm {
  background: #fff;
  border-radius: 0.625rem;
  padding: 1.25rem 1.5rem;
  max-width: 420px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.bm__confirm-msg {
  font-size: 0.9rem;
  color: var(--color-neutral-800, #262626);
  margin: 0;
  line-height: 1.5;
}

.bm__confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.bm__btn-confirm-cancel {
  padding: 0.375rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-neutral-700, #404040);
  background: transparent;
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  border-radius: 0.375rem;
  cursor: pointer;
}

.bm__btn-confirm-ok {
  padding: 0.375rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #fff;
  background: #dc2626;
  border: 1px solid #dc2626;
  border-radius: 0.375rem;
  cursor: pointer;
}

.bm__btn-confirm-ok:hover {
  background: #b91c1c;
  border-color: #b91c1c;
}
</style>
