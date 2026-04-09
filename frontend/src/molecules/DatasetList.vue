<template>
  <div class="dataset-list" role="listbox" aria-label="Datasets de teste">
    <!-- Upload button area -->
    <div class="dataset-list__header">
      <button
        class="dataset-list__upload-btn"
        type="button"
        :disabled="hasReachedLimit"
        :title="
          hasReachedLimit
            ? `Máximo de ${maxDatasets} datasets atingido`
            : 'Carregar arquivo .xml ou .json'
        "
        data-testid="upload-dataset-btn"
        @click="triggerUpload"
      >
        <span>+ Upload Dataset</span>
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept=".xml,.json"
        class="dataset-list__file-input"
        data-testid="dataset-file-input"
        @change="onFileChange"
      />
    </div>

    <!-- Limit message -->
    <div v-if="hasReachedLimit" class="dataset-list__limit-msg" data-testid="dataset-limit-msg">
      Limite de {{ maxDatasets }} datasets atingido
    </div>

    <!-- Dataset items -->
    <div class="dataset-list__items">
      <DatasetItem
        v-for="dataset in datasets"
        :key="dataset.id"
        :dataset="dataset"
        :is-active="dataset.id === activeDatasetId"
        @select="emit('select', $event)"
        @delete="emit('delete', $event)"
      />

      <div v-if="datasets.length === 0" class="dataset-list__empty">Nenhum dataset carregado</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import DatasetItem from './DatasetItem.vue'
import type { Dataset } from '@/types/test-data.types'
import { MAX_DATASETS } from '@/stores/testDataStore'

const props = defineProps<{
  datasets: Dataset[]
  activeDatasetId: string | null
}>()

const emit = defineEmits<{
  select: [id: string]
  delete: [id: string]
  upload: [file: File]
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const maxDatasets = MAX_DATASETS

const hasReachedLimit = computed(() => props.datasets.length >= maxDatasets)

function triggerUpload() {
  if (hasReachedLimit.value) return
  fileInputRef.value?.click()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    emit('upload', file)
    // Reset so same file can be re-uploaded
    input.value = ''
  }
}
</script>

<style scoped>
.dataset-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.dataset-list__header {
  flex-shrink: 0;
  padding: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.dataset-list__upload-btn {
  width: 100%;
  padding: 0.375rem 0.5rem;
  background: var(--color-primary-700, #1d4ed8);
  color: #fff;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s;
  text-align: center;
}

.dataset-list__upload-btn:hover:not(:disabled) {
  background: var(--color-primary-600, #2563eb);
}

.dataset-list__upload-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dataset-list__file-input {
  display: none;
}

.dataset-list__limit-msg {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: var(--color-warning-400, #fb923c);
  text-align: center;
}

.dataset-list__items {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.dataset-list__empty {
  font-size: 0.8125rem;
  color: var(--color-neutral-500, #6b7280);
  text-align: center;
  padding: 1rem 0.5rem;
}
</style>
