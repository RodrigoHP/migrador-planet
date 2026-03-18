<template>
  <div class="section-inspector">
    <!-- Geral -->
    <InspectorSection title="Geral" :collapsible="true">
      <InspectorField label="Tipo" :value="sectionTypeLabel" type="badge" />
      <InspectorInput
        label="Altura (px)"
        type="number"
        :min="0"
        :model-value="(p['height'] as number)"
        @update:model-value="setProp('height', $event)"
      />
    </InspectorSection>

    <!-- Aparência -->
    <InspectorSection title="Aparência" :collapsible="true">
      <InspectorColorPicker
        label="Cor de Fundo"
        :model-value="(p['background_color'] as string) || ''"
        @update:model-value="setProp('background_color', $event)"
      />
      <div class="section-inspector__file-field">
        <span class="section-inspector__file-label">Imagem de Fundo</span>
        <div class="section-inspector__file-wrap">
          <span class="section-inspector__file-value">
            {{ (p['background_image'] as string) || '—' }}
          </span>
          <label class="section-inspector__file-btn">
            Escolher
            <input
              type="file"
              accept="image/*"
              class="section-inspector__file-input"
              @change="onBgImageChange"
            />
          </label>
        </div>
      </div>
    </InspectorSection>

    <!-- Espaçamento -->
    <InspectorSection title="Espaçamento" :collapsible="true">
      <InspectorInput
        label="Padding Topo (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_top'] as number)"
        @update:model-value="setProp('padding_top', $event)"
      />
      <InspectorInput
        label="Padding Base (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_bottom'] as number)"
        @update:model-value="setProp('padding_bottom', $event)"
      />
      <InspectorInput
        label="Padding Esquerda (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_left'] as number)"
        @update:model-value="setProp('padding_left', $event)"
      />
      <InspectorInput
        label="Padding Direita (px)"
        type="number"
        :min="0"
        :model-value="(p['padding_right'] as number)"
        @update:model-value="setProp('padding_right', $event)"
      />
    </InspectorSection>

    <!-- Comportamento -->
    <InspectorSection title="Comportamento" :collapsible="true">
      <InspectorCheckbox
        label="Repetir por Página"
        :model-value="Boolean(p['repeat_per_page'])"
        @update:model-value="setProp('repeat_per_page', $event)"
      />
      <InspectorCheckbox
        label="Bloquear Seção"
        :model-value="Boolean(p['locked'])"
        @update:model-value="setProp('locked', $event)"
      />
    </InspectorSection>

    <!-- Visibilidade -->
    <InspectorSection title="Visibilidade" :collapsible="true">
      <InspectorSelect
        label="Estado"
        :model-value="(p['visibility'] as string) || 'always'"
        :options="visibilityOptions"
        @update:model-value="setProp('visibility', $event)"
      />
    </InspectorSection>

    <!-- Remover -->
    <div class="section-inspector__remove-wrap">
      <button
        class="section-inspector__remove-btn"
        type="button"
        @click="onRemove"
      >
        Remover do template
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'
import InspectorField from '@/molecules/InspectorField.vue'
import InspectorSection from '@/molecules/InspectorSection.vue'
import InspectorInput from '@/molecules/InspectorInput.vue'
import InspectorSelect from '@/molecules/InspectorSelect.vue'
import InspectorCheckbox from '@/molecules/InspectorCheckbox.vue'
import InspectorColorPicker from '@/molecules/InspectorColorPicker.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useInspectorStore } from '@/stores/inspectorStore'

const props = withDefaults(
  defineProps<{ node?: TreeNode | null }>(),
  { node: null },
)

const templateStore = useTemplateStore()
const inspectorStore = useInspectorStore()

const p = computed(() => (props.node?.properties ?? {}) as Record<string, unknown>)

const sectionTypeLabels: Record<string, string> = {
  header: 'Header',
  flow: 'Flow',
  footer: 'Footer',
}

const sectionTypeLabel = computed(() => {
  const t = (p.value['section_type'] as string) || (props.node?.type as string) || ''
  return sectionTypeLabels[t] ?? (t || '—')
})

const visibilityOptions = [
  { value: 'always', label: 'Sempre visível' },
  { value: 'conditional', label: 'Condicional' },
  { value: 'hidden', label: 'Escondido' },
]

function setProp(key: string, value: unknown) {
  if (props.node?.id) {
    templateStore.updateNodeProperty(props.node.id, key, value)
  }
}

function onBgImageChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  setProp('background_image', url)
}

function onRemove() {
  if (!props.node?.id) return
  const ok = confirm('Remover esta seção do template?')
  if (!ok) return
  templateStore.removeNode(props.node.id)
  inspectorStore.clearSelection()
}
</script>

<style scoped>
.section-inspector {
  display: flex;
  flex-direction: column;
}

.section-inspector__file-field {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.section-inspector__file-label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.section-inspector__file-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-inspector__file-value {
  font-size: 0.75rem;
  color: var(--color-neutral-300, #d1d5db);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-inspector__file-btn {
  font-size: 0.75rem;
  padding: 0.1875rem 0.5rem;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-200, #e5e7eb);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 0.25rem;
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}

.section-inspector__file-input {
  display: none;
}

.section-inspector__remove-wrap {
  padding: 0.75rem 0 0.25rem;
  border-top: 1px solid var(--color-neutral-700, #374151);
  margin-top: 0.5rem;
}

.section-inspector__remove-btn {
  width: 100%;
  padding: 0.375rem;
  font-size: 0.75rem;
  background: transparent;
  color: var(--color-error-400, #f87171);
  border: 1px solid var(--color-error-700, #b91c1c);
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background 0.15s;
}

.section-inspector__remove-btn:hover {
  background: var(--color-error-900, #450a0a);
}
</style>
