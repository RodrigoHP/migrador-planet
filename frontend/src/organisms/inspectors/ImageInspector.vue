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
      <VisibilityControl
        :model-value="visibilityConfig"
        @update:model-value="updateVisibility"
      />
    </InspectorSection>

    <!-- Ações (placeholder) -->
    <InspectorSection title="Ações">
      <div class="image-inspector__actions">
        <button class="image-inspector__btn" type="button" disabled>Substituir</button>
        <button class="image-inspector__btn" type="button" disabled>Download</button>
      </div>
    </InspectorSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import VisibilityControl from '@/molecules/VisibilityControl.vue'
import type { VisibilityConfig } from '@/molecules/VisibilityControl.vue'
import { useTemplateStore } from '@/stores/templateStore'

const props = withDefaults(
  defineProps<{ node?: TreeNode | null }>(),
  { node: null },
)

const templateStore = useTemplateStore()

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
  return alignLabels[a ?? ''] ?? (a ?? '—')
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
</script>

<style scoped>
.image-inspector {
  display: flex;
  flex-direction: column;
}

.image-inspector__actions {
  display: flex;
  gap: 0.5rem;
}

.image-inspector__btn {
  flex: 1;
  padding: 0.3125rem 0.5rem;
  font-size: 0.75rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-300, #d1d5db);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
