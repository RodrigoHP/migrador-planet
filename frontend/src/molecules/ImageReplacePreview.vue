<template>
  <div class="image-replace-preview">
    <div class="image-replace-preview__columns">
      <!-- Current image -->
      <div class="image-replace-preview__col">
        <span class="image-replace-preview__label">Atual</span>
        <div class="image-replace-preview__thumb-wrapper">
          <img
            v-if="currentImageUrl"
            :src="currentImageUrl"
            class="image-replace-preview__thumb"
            alt="Imagem atual"
          />
          <div v-else class="image-replace-preview__thumb image-replace-preview__thumb--empty">
            —
          </div>
        </div>
        <span class="image-replace-preview__dims">
          {{
            currentDimensions ? `${currentDimensions.width} × ${currentDimensions.height} px` : '—'
          }}
        </span>
      </div>

      <div class="image-replace-preview__arrow">→</div>

      <!-- New image -->
      <div class="image-replace-preview__col">
        <span class="image-replace-preview__label">Nova</span>
        <div class="image-replace-preview__thumb-wrapper">
          <img
            v-if="newPreviewUrl"
            :src="newPreviewUrl"
            class="image-replace-preview__thumb"
            alt="Nova imagem"
          />
          <div v-else class="image-replace-preview__thumb image-replace-preview__thumb--empty">
            Carregando...
          </div>
        </div>
        <span class="image-replace-preview__dims">
          {{ newDimensions ? `${newDimensions.width} × ${newDimensions.height} px` : '—' }}
        </span>
      </div>
    </div>

    <div class="image-replace-preview__actions">
      <button
        class="image-replace-preview__btn image-replace-preview__btn--primary"
        type="button"
        @click="$emit('confirm')"
      >
        Confirmar substituição
      </button>
      <button
        class="image-replace-preview__btn image-replace-preview__btn--secondary"
        type="button"
        @click="$emit('cancel')"
      >
        Cancelar
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watchEffect, onUnmounted } from 'vue'

const props = defineProps<{
  currentImageUrl: string
  newImageFile: File
  currentDimensions?: { width: number; height: number } | null
  newDimensions?: { width: number; height: number } | null
}>()

defineEmits<{
  confirm: []
  cancel: []
}>()

const newPreviewUrl = ref<string | null>(null)
let objectUrl: string | null = null

watchEffect(() => {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
  if (props.newImageFile) {
    objectUrl = URL.createObjectURL(props.newImageFile)
    newPreviewUrl.value = objectUrl
  }
})

onUnmounted(() => {
  if (objectUrl) URL.revokeObjectURL(objectUrl)
})
</script>

<style scoped>
.image-replace-preview {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.image-replace-preview__columns {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.image-replace-preview__col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
}

.image-replace-preview__label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-300, #d1d5db);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.image-replace-preview__thumb-wrapper {
  width: 100%;
  aspect-ratio: 4/3;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.375rem;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-replace-preview__thumb {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.image-replace-preview__thumb--empty {
  color: var(--color-neutral-500, #525252);
  font-size: 0.75rem;
}

.image-replace-preview__dims {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
}

.image-replace-preview__arrow {
  font-size: 1.25rem;
  color: var(--color-neutral-500, #525252);
  flex-shrink: 0;
}

.image-replace-preview__actions {
  display: flex;
  gap: 0.5rem;
}

.image-replace-preview__btn {
  flex: 1;
  padding: 0.4375rem 0.75rem;
  font-size: 0.75rem;
  border-radius: 0.25rem;
  cursor: pointer;
  font-weight: 500;
  border: 1px solid transparent;
}

.image-replace-preview__btn--primary {
  background: var(--color-primary-600, #2563eb);
  color: #fff;
  border-color: var(--color-primary-700, #1d4ed8);
}

.image-replace-preview__btn--primary:hover {
  background: var(--color-primary-700, #1d4ed8);
}

.image-replace-preview__btn--secondary {
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-200, #e5e7eb);
  border-color: var(--color-neutral-600, #4b5563);
}

.image-replace-preview__btn--secondary:hover {
  background: var(--color-neutral-600, #4b5563);
}
</style>
