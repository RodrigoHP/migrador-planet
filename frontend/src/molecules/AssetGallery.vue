<template>
  <div class="asset-gallery">
    <!-- Loading state -->
    <div v-if="loading" class="asset-gallery__loading">
      <span class="asset-gallery__spinner" aria-label="Carregando assets..." />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="asset-gallery__error">
      {{ error }}
    </div>

    <!-- Empty state -->
    <div v-else-if="assets.length === 0" class="asset-gallery__empty">
      Nenhum asset no projeto
    </div>

    <!-- Grid -->
    <div v-else class="asset-gallery__grid">
      <button
        v-for="asset in assets"
        :key="asset.filename"
        class="asset-gallery__item"
        type="button"
        :title="asset.filename"
        @click="$emit('select', asset)"
      >
        <div class="asset-gallery__thumb-wrapper">
          <img
            :src="asset.thumbnailUrl"
            :alt="asset.filename"
            class="asset-gallery__thumb"
            loading="lazy"
          />
        </div>
        <div class="asset-gallery__meta">
          <span class="asset-gallery__name">{{ asset.filename }}</span>
          <span class="asset-gallery__size">— {{ formatSize(asset.size) }}</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listAssets, type AssetInfo } from '@/services/assetService'

const props = defineProps<{
  templateId: string
}>()

const emit = defineEmits<{
  select: [asset: AssetInfo]
}>()

const assets = ref<AssetInfo[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function loadAssets() {
  loading.value = true
  error.value = null
  try {
    assets.value = await listAssets(props.templateId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erro ao carregar assets.'
  } finally {
    loading.value = false
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(loadAssets)

defineExpose({ loadAssets })
</script>

<style scoped>
.asset-gallery {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.asset-gallery__loading,
.asset-gallery__empty,
.asset-gallery__error {
  padding: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-neutral-400, #9ca3af);
  text-align: center;
}

.asset-gallery__error {
  color: var(--color-red-400, #f87171);
}

.asset-gallery__spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--color-neutral-600, #4b5563);
  border-top-color: var(--color-primary-500, #3b82f6);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.asset-gallery__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(5rem, 1fr));
  gap: 0.375rem;
}

.asset-gallery__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem;
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.25rem;
  background: var(--color-neutral-800, #1f2937);
  cursor: pointer;
  text-align: center;
  transition: border-color 0.1s;
}

.asset-gallery__item:hover {
  border-color: var(--color-primary-500, #3b82f6);
}

.asset-gallery__thumb-wrapper {
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.asset-gallery__thumb {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.asset-gallery__meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.asset-gallery__name {
  font-size: 0.625rem;
  color: var(--color-neutral-300, #d1d5db);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.asset-gallery__size {
  font-size: 0.5625rem;
  color: var(--color-neutral-500, #6b7280);
}
</style>
