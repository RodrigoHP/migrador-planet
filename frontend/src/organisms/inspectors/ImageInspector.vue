<template>
  <div class="image-inspector">
    <!-- Dimensões -->
    <InspectorSection title="Dimensões" :collapsible="true">
      <InspectorField label="Largura" :value="pxValue('width')" />
      <InspectorField label="Altura" :value="pxValue('height')" />
      <InspectorField label="Escala" :value="strValue('scale')" />
    </InspectorSection>

    <!-- Posição -->
    <InspectorSection title="Posição" :collapsible="true">
      <InspectorField label="Alinhamento" :value="alignLabel" />
    </InspectorSection>

    <!-- Fonte -->
    <InspectorSection title="Fonte" :collapsible="true">
      <InspectorField label="URL / Path" :value="strValue('src')" />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <VisibilityControl :model-value="visibilityConfig" @update:model-value="updateVisibility" />
    </InspectorSection>

    <!-- Ações -->
    <InspectorSection title="Ações">
      <div class="image-inspector__actions">
        <!-- Hidden file input -->
        <input
          ref="fileInputRef"
          type="file"
          class="image-inspector__file-input"
          accept="image/png,image/jpeg,image/webp,image/svg+xml"
          @change="onFileSelected"
        />

        <button
          class="image-inspector__btn image-inspector__btn--primary"
          type="button"
          :disabled="uploading || !props.node"
          @click="fileInputRef?.click()"
        >
          <span v-if="uploading" class="image-inspector__spinner" />
          {{ uploading ? 'Enviando…' : 'Substituir' }}
        </button>

        <button
          class="image-inspector__btn"
          type="button"
          :disabled="!currentSrc"
          @click="downloadAsset"
        >
          Baixar
        </button>

        <button
          class="image-inspector__btn image-inspector__btn--danger"
          type="button"
          :disabled="uploading || !props.node"
          title="Remover imagem"
          @click="confirmRemove = true"
        >
          🗑
        </button>
      </div>

      <!-- Validation errors -->
      <div v-if="validationErrors.length" class="image-inspector__errors">
        <p v-for="(err, idx) in validationErrors" :key="idx" class="image-inspector__error-msg">
          {{ err }}
        </p>
      </div>

      <!-- Toast feedback -->
      <AppToast
        v-if="toastMessage"
        :message="toastMessage"
        :variant="toastVariant"
        @dismiss="toastMessage = ''"
      />
    </InspectorSection>

    <!-- SVG inline toggle (only when src is .svg) -->
    <InspectorSection v-if="isSvgSource" title="SVG" :collapsible="true">
      <label class="image-inspector__toggle-row">
        <input
          v-model="svgInline"
          type="checkbox"
          class="image-inspector__checkbox"
          @change="onSvgInlineToggle"
        />
        <span class="image-inspector__toggle-label">Incorporar como SVG inline</span>
      </label>
    </InspectorSection>

    <!-- Assets do projeto (collapsible gallery) -->
    <InspectorSection title="Assets do projeto" :collapsible="true">
      <AssetGallery
        v-if="templateId"
        ref="galleryRef"
        :template-id="templateId"
        @select="onGallerySelect"
      />
      <p v-else class="image-inspector__no-template">Nenhum template carregado</p>
    </InspectorSection>

    <!-- Replace preview modal -->
    <Teleport to="body">
      <div v-if="showPreview && pendingFile" class="image-inspector__modal-backdrop">
        <div class="image-inspector__modal">
          <h3 class="image-inspector__modal-title">Confirmar substituição</h3>
          <ImageReplacePreview
            :current-image-url="currentSrc || ''"
            :new-image-file="pendingFile"
            :current-dimensions="currentDims"
            :new-dimensions="newDims"
            @confirm="doUpload"
            @cancel="cancelPreview"
          />
        </div>
      </div>
    </Teleport>

    <!-- Confirm remove modal -->
    <Teleport to="body">
      <div v-if="confirmRemove" class="image-inspector__modal-backdrop">
        <div class="image-inspector__modal image-inspector__modal--sm">
          <h3 class="image-inspector__modal-title">Remover imagem?</h3>
          <p class="image-inspector__modal-body">
            Esta ação removerá a imagem do template, da árvore de estrutura e do servidor (se
            aplicável). Esta operação não pode ser desfeita facilmente.
          </p>
          <div class="image-inspector__modal-actions">
            <button
              class="image-inspector__btn image-inspector__btn--danger"
              type="button"
              @click="doRemove"
            >
              Remover
            </button>
            <button class="image-inspector__btn" type="button" @click="confirmRemove = false">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import ImageReplacePreview from '@/molecules/ImageReplacePreview.vue'
import AssetGallery from '@/molecules/AssetGallery.vue'
import AppToast from '@/organisms/AppToast.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { validateImageFile } from '@/utils/imageValidation'
import { sanitizeSvg } from '@/utils/svgSanitizer'
import { uploadAsset, deleteAsset, type AssetInfo } from '@/services/assetService'

// ─── Props ─────────────────────────────────────────────────────────────────────
const props = withDefaults(defineProps<{ node?: TreeNode | null }>(), { node: null })

// ─── Store ─────────────────────────────────────────────────────────────────────
const templateStore = useTemplateStore()

// ─── Computed helpers ──────────────────────────────────────────────────────────
const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

function pxValue(key: string): string {
  const v = p.value[key]
  return v !== undefined ? `${v}px` : '—'
}

function strValue(key: string): string {
  const v = p.value[key]
  return v !== undefined && v !== null ? String(v) : '—'
}

const alignLabels: Record<string, string> = {
  left: 'Esquerda',
  center: 'Centro',
  right: 'Direita',
}

const alignLabel = computed(() => {
  const a = p.value['align'] as string | undefined
  return alignLabels[a ?? ''] ?? a ?? '—'
})

const visibilityConfig = computed<VisibilityConfig>(() => {
  const raw = p.value['visibility']
  if (raw && typeof raw === 'object' && 'mode' in (raw as object)) {
    return raw as VisibilityConfig
  }
  const mode = (raw as string) || 'always'
  return { mode: mode as VisibilityConfig['mode'] }
})

function updateVisibility(config: VisibilityConfig) {
  if (props.node?.id) {
    templateStore.updateNodeProperty(props.node.id, 'visibility', config)
  }
}

// ─── Current state ─────────────────────────────────────────────────────────────
const currentSrc = computed(() => {
  const src = p.value['src']
  return src ? String(src) : null
})

const currentDims = computed<{ width: number; height: number } | null>(() => {
  const w = p.value['width']
  const h = p.value['height']
  if (w !== undefined && h !== undefined) {
    return { width: Number(w), height: Number(h) }
  }
  return null
})

const isSvgSource = computed(() => {
  const src = currentSrc.value
  const assetFilename = p.value['assetFilename'] as string | undefined
  return (
    (src ? src.toLowerCase().endsWith('.svg') : false) ||
    (assetFilename ? assetFilename.toLowerCase().endsWith('.svg') : false)
  )
})

// Template ID from store
const templateId = computed<string>(() => {
  const tree = templateStore.documentTree
  if (tree && 'id' in tree && typeof (tree as Record<string, unknown>).id === 'string') {
    return (tree as Record<string, unknown>).id as string
  }
  return 'default'
})

// ─── Refs ──────────────────────────────────────────────────────────────────────
const fileInputRef = ref<HTMLInputElement | null>(null)
const galleryRef = ref<InstanceType<typeof AssetGallery> | null>(null)

const uploading = ref(false)
const validationErrors = ref<string[]>([])
const pendingFile = ref<File | null>(null)
const showPreview = ref(false)
const newDims = ref<{ width: number; height: number } | null>(null)
const confirmRemove = ref(false)
const svgInline = ref(false)

const toastMessage = ref('')
const toastVariant = ref<'success' | 'error' | 'warning' | 'neutral'>('neutral')

function showToast(msg: string, variant: 'success' | 'error' | 'warning' | 'neutral' = 'neutral') {
  toastMessage.value = msg
  toastVariant.value = variant
}

// ─── File selected ─────────────────────────────────────────────────────────────
async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''
  validationErrors.value = []

  const result = await validateImageFile(file)
  if (!result.valid) {
    validationErrors.value = result.errors
    return
  }

  newDims.value = await loadFileDimensions(file).catch(() => null)
  pendingFile.value = file
  showPreview.value = true
}

async function loadFileDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    if (file.type === 'image/svg+xml') {
      resolve({ width: 0, height: 0 })
      return
    }
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Não foi possível carregar a imagem.'))
    }
    img.src = url
  })
}

function cancelPreview() {
  showPreview.value = false
  pendingFile.value = null
  newDims.value = null
}

// ─── Upload ────────────────────────────────────────────────────────────────────
async function doUpload() {
  if (!pendingFile.value) return
  showPreview.value = false
  uploading.value = true

  try {
    const response = await uploadAsset(templateId.value, pendingFile.value)
    if (props.node?.id) {
      templateStore.updateNodeProperty(props.node.id, 'src', response.path)
      templateStore.updateNodeProperty(props.node.id, 'assetFilename', response.filename)
      if (response.dimensions.width && response.dimensions.height) {
        templateStore.updateNodeProperty(props.node.id, 'width', response.dimensions.width)
        templateStore.updateNodeProperty(props.node.id, 'height', response.dimensions.height)
      }
    }
    galleryRef.value?.loadAssets()
    showToast('Imagem substituída com sucesso!', 'success')
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Erro ao enviar imagem.'
    showToast(msg, 'error')
  } finally {
    uploading.value = false
    pendingFile.value = null
    newDims.value = null
  }
}

// ─── Download ──────────────────────────────────────────────────────────────────
function downloadAsset() {
  if (!currentSrc.value) return
  const a = document.createElement('a')
  a.href = currentSrc.value
  a.download = currentSrc.value.split('/').pop() ?? 'imagem'
  a.click()
}

// ─── Remove ────────────────────────────────────────────────────────────────────
async function doRemove() {
  if (!props.node?.id) return
  confirmRemove.value = false

  const assetFilename = p.value['assetFilename'] as string | undefined
  try {
    if (assetFilename) {
      await deleteAsset(templateId.value, assetFilename)
    }
  } catch (err) {
    console.warn('Erro ao remover asset do servidor:', err)
  }

  templateStore.removeNode(props.node.id)
  galleryRef.value?.loadAssets()
  showToast('Imagem removida.', 'success')
}

// ─── SVG inline ────────────────────────────────────────────────────────────────
async function onSvgInlineToggle() {
  if (!svgInline.value || !currentSrc.value || !props.node?.id) return

  try {
    const res = await fetch(currentSrc.value)
    if (!res.ok) throw new Error('Não foi possível carregar o SVG.')
    const raw = await res.text()
    const sanitized = sanitizeSvg(raw)
    templateStore.updateNodeProperty(props.node.id, 'svgInlineContent', sanitized)
    templateStore.updateNodeProperty(props.node.id, 'svgInline', true)
    showToast('SVG incorporado com sucesso!', 'success')
  } catch (err) {
    svgInline.value = false
    const msg = err instanceof Error ? err.message : 'Erro ao incorporar SVG.'
    showToast(msg, 'error')
  }
}

// ─── Gallery select ────────────────────────────────────────────────────────────
function onGallerySelect(asset: AssetInfo) {
  if (!props.node?.id) return
  templateStore.updateNodeProperty(props.node.id, 'src', asset.dataUri)
  templateStore.updateNodeProperty(props.node.id, 'assetFilename', asset.filename)
  showToast(`Asset "${asset.filename}" selecionado.`, 'success')
}
</script>

<style scoped>
.image-inspector {
  display: flex;
  flex-direction: column;
}

.image-inspector__actions {
  display: flex;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.image-inspector__file-input {
  display: none;
}

.image-inspector__btn {
  flex: 1;
  padding: 0.3125rem 0.5rem;
  font-size: 0.75rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-300, #d1d5db);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  transition: background 0.1s;
}

.image-inspector__btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.image-inspector__btn:not(:disabled):hover {
  background: var(--color-neutral-600, #4b5563);
}

.image-inspector__btn--primary {
  background: var(--color-primary-600, #2563eb);
  color: #fff;
  border-color: var(--color-primary-700, #1d4ed8);
}

.image-inspector__btn--primary:not(:disabled):hover {
  background: var(--color-primary-700, #1d4ed8);
}

.image-inspector__btn--danger {
  background: var(--color-red-700, #b91c1c);
  color: #fff;
  border-color: var(--color-red-800, #991b1b);
  flex: 0 0 auto;
  padding: 0.3125rem 0.625rem;
}

.image-inspector__btn--danger:not(:disabled):hover {
  background: var(--color-red-800, #991b1b);
}

.image-inspector__spinner {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.image-inspector__errors {
  margin-top: 0.375rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.image-inspector__error-msg {
  font-size: 0.6875rem;
  color: var(--color-red-400, #f87171);
  margin: 0;
}

.image-inspector__toggle-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.image-inspector__checkbox {
  accent-color: var(--color-primary-500, #3b82f6);
}

.image-inspector__toggle-label {
  font-size: 0.75rem;
  color: var(--color-neutral-300, #d1d5db);
}

.image-inspector__no-template {
  font-size: 0.75rem;
  color: var(--color-neutral-500, #6b7280);
  margin: 0;
}

.image-inspector__modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.image-inspector__modal {
  background: var(--color-neutral-900, #111827);
  border: 1px solid var(--color-neutral-700, #374151);
  border-radius: 0.5rem;
  padding: 1.25rem;
  width: 90%;
  max-width: 28rem;
}

.image-inspector__modal--sm {
  max-width: 20rem;
}

.image-inspector__modal-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
  margin: 0 0 1rem;
}

.image-inspector__modal-body {
  font-size: 0.8125rem;
  color: var(--color-neutral-300, #d1d5db);
  margin: 0 0 1rem;
  line-height: 1.5;
}

.image-inspector__modal-actions {
  display: flex;
  gap: 0.5rem;
}
</style>
