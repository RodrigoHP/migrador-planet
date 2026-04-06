<template>
  <div class="field-navigator">
    <!-- Summary header (Story 28.2: dual count) -->
    <div class="field-navigator__summary">
      <span class="field-navigator__summary-text">{{ summaryText }}</span>
      <ProgressBar :value="progressPct" :animated="false" class="field-navigator__progress" />
    </div>

    <!-- Groups (Story 28.2: status-first grouping) -->
    <div class="field-navigator__groups">
      <!-- XSD-only fields group -->
      <div
        v-if="xsdOnlyFields.length > 0"
        class="field-navigator__group"
      >
        <button
          class="field-navigator__group-header field-navigator__group-header--xsd"
          type="button"
          :aria-expanded="!collapsedStatusGroups.has('xsd-only')"
          @click="toggleStatusGroup('xsd-only')"
        >
          <span class="field-navigator__group-icon" aria-hidden="true">🔴</span>
          <span class="field-navigator__group-label">XSD obrigatórios sem match</span>
          <span class="field-navigator__group-count">({{ xsdOnlyFields.length }})</span>
          <span class="field-navigator__group-toggle" aria-hidden="true">
            {{ collapsedStatusGroups.has('xsd-only') ? '▶' : '▼' }}
          </span>
        </button>
        <div v-if="!collapsedStatusGroups.has('xsd-only')" class="field-navigator__group-items">
          <XsdOnlyField
            v-for="field in xsdOnlyFields"
            :key="field.xsd_path"
            :field="field"
            :is-selected="selectedXsdPath === field.xsd_path"
            @select="onSelectXsdField"
          />
        </div>
        <!-- XSD field detail panel (shown when one is selected) -->
        <div v-if="selectedXsdField && !collapsedStatusGroups.has('xsd-only')" class="field-navigator__xsd-detail">
          <div class="field-navigator__xsd-detail-header">
            <span class="field-navigator__xsd-detail-title">{{ selectedXsdFieldName }}</span>
            <button class="field-navigator__xsd-detail-close" @click="selectedXsdPath = null" aria-label="Fechar">✕</button>
          </div>
          <div class="field-navigator__xsd-detail-path">{{ selectedXsdField.xsd_path }}</div>
          <div class="field-navigator__xsd-detail-msg">
            {{ selectedXsdField.reason || 'Este campo XSD não possui correspondência no PDF.' }}
            Para incluí-lo, crie uma regra de formato condicional.
          </div>
        </div>
      </div>

      <!-- Status-based groups -->
      <div
        v-for="group in statusGroups"
        :key="group.key"
        class="field-navigator__group"
      >
        <button
          class="field-navigator__group-header"
          type="button"
          :aria-expanded="!collapsedStatusGroups.has(group.key)"
          @click="toggleStatusGroup(group.key)"
        >
          <span class="field-navigator__group-icon" aria-hidden="true">{{ group.badge }}</span>
          <span class="field-navigator__group-label">{{ group.label }}</span>
          <span class="field-navigator__group-count">({{ group.fields.length }})</span>
          <span class="field-navigator__group-toggle" aria-hidden="true">
            {{ collapsedStatusGroups.has(group.key) ? '▶' : '▼' }}
          </span>
        </button>
        <div v-if="!collapsedStatusGroups.has(group.key)" class="field-navigator__group-items">
          <FieldNavItemVue
            v-for="field in group.fields"
            :key="fieldKey(field)"
            :field="field"
            :is-selected="selectedFieldKey === fieldKey(field)"
            @select="onSelectField"
            @open-ambiguous="onOpenAmbiguous"
            @open-binding="onOpenBinding"
          />
          <!-- Hint when Vincular → clicked but no template node exists -->
          <div
            v-if="bindHintFieldKey && group.fields.some(f => fieldKey(f) === bindHintFieldKey)"
            class="field-navigator__bind-hint"
          >
            ✏️ Campo selecionado. Clique em um elemento no canvas para vincular.
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="statusGroups.every(g => g.fields.length === 0) && xsdOnlyFields.length === 0" class="field-navigator__empty">
        <span>Nenhum campo disponível</span>
      </div>
    </div>

    <!-- Story 28.3: AmbiguousFieldModal -->
    <AmbiguousFieldModal
      v-if="ambiguousModalField"
      :field="ambiguousModalField"
      @resolve="onResolveAmbiguous"
      @cancel="onCancelAmbiguous"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMappingStore } from '@/stores/mapping'
import { useInspectorStore } from '@/stores/inspectorStore'
import { useEditorStore } from '@/stores/editorStore'
import { useTemplateStore } from '@/stores/templateStore'
import ProgressBar from '@/atoms/ProgressBar.vue'
import FieldNavItemVue from '@/molecules/FieldNavItem.vue'
import XsdOnlyField from '@/molecules/XsdOnlyField.vue'
import AmbiguousFieldModal from '@/molecules/AmbiguousFieldModal.vue'
import type { FieldNavItem } from '@/types/field-navigator.types'
import type { UnmappedXsdField } from '@/types/pipeline.types'

// ─── XSD-only field selection ─────────────────────────────────────────────────
const selectedXsdPath = ref<string | null>(null)
const selectedXsdField = computed<UnmappedXsdField | undefined>(
  () => xsdOnlyFields.value.find((f) => f.xsd_path === selectedXsdPath.value),
)
const selectedXsdFieldName = computed<string>(() => {
  const path = selectedXsdField.value?.xsd_path ?? ''
  const seg = path.split('.').pop() ?? path
  return seg.charAt(0).toUpperCase() + seg.slice(1)
})

const mappingStore = useMappingStore()
const inspectorStore = useInspectorStore()
const editorStore = useEditorStore()
const templateStore = useTemplateStore()

// ─── Status group state (Story 28.2) ──────────────────────────────────────
// 'mapped' group starts collapsed (AC6)
const collapsedStatusGroups = ref<Set<string>>(new Set(['mapped']))
const selectedFieldKey = ref<string | null>(null)
// Hint shown when Vincular → is clicked but no template node is found
const bindHintFieldKey = ref<string | null>(null)

// Unique key per field: XSD path when available, fallback to PDF name.
// path can be '' for unmapped PDF-only fields — using '' as key highlights all of them.
function fieldKey(field: FieldNavItem): string {
  return field.path || field.name
}

function toggleStatusGroup(key: string) {
  if (collapsedStatusGroups.value.has(key)) {
    collapsedStatusGroups.value.delete(key)
  } else {
    collapsedStatusGroups.value.add(key)
  }
  collapsedStatusGroups.value = new Set(collapsedStatusGroups.value)
}

// ─── Computed counts ───────────────────────────────────────────────────────
const fields = computed<FieldNavItem[]>(() => mappingStore.fieldNavItems)
const xsdOnlyFields = computed<UnmappedXsdField[]>(() => mappingStore.xsdOnlyFields)

const mappedCount = computed(() => fields.value.filter((f) => f.status === 'mapped').length)
const totalCount = computed(() => fields.value.length)

const progressPct = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((mappedCount.value / totalCount.value) * 100)
})

// Story 28.2 — dual count header: "X de Y PDF · Z XSD obrigatórios"
const summaryText = computed<string>(() => {
  const pdfPart = `${mappedCount.value} de ${totalCount.value} PDF`
  const xsdCount = xsdOnlyFields.value.length
  if (xsdCount === 0) return pdfPart
  return `${pdfPart} · ${xsdCount} XSD obrigatórios`
})

// ─── Status-based groups (Story 28.2) ─────────────────────────────────────
interface StatusGroup {
  key: string
  badge: string
  label: string
  fields: FieldNavItem[]
}

const STATUS_GROUP_DEFS = [
  { key: 'unmapped',    badge: '🟥', label: 'Sem binding' },
  { key: 'unconfirmed', badge: '🟨', label: 'Ambíguos' },
  { key: 'mapped',      badge: '🟩', label: 'Mapeados' },
] as const

const statusGroups = computed<StatusGroup[]>(() =>
  STATUS_GROUP_DEFS.map((def) => ({
    ...def,
    fields: fields.value.filter((f) => f.status === def.key),
  })).filter((g) => g.fields.length > 0),
)

// ─── Selection ─────────────────────────────────────────────────────────────
// Returns true if a matching template node was found and selected.
function onSelectField(field: FieldNavItem): boolean {
  selectedFieldKey.value = fieldKey(field)
  bindHintFieldKey.value = null

  // If the field has a nodeId, resolve the node in templateStore
  if (field.nodeId) {
    const node = templateStore.getNodeById(field.nodeId)
    if (node) {
      inspectorStore.selectNode(node)
      editorStore.selectElement(node.id)
      return true
    }
  }

  // Fallback: search by binding in flatNodes
  if (field.binding) {
    for (const node of templateStore.flatNodes.values()) {
      if (node.binding === field.binding) {
        inspectorStore.selectNode(node)
        editorStore.selectElement(node.id)
        return true
      }
    }
  }

  // Fallback: search by XSD path (field.path)
  if (field.path) {
    for (const node of templateStore.flatNodes.values()) {
      if (node.binding === field.path) {
        inspectorStore.selectNode(node)
        editorStore.selectElement(node.id)
        return true
      }
    }
  }

  return false
}

// Story 28.2 — [Vincular →] opens Inspector for the field's node.
// If the field has no template node yet, show an inline hint guiding the user.
function onOpenBinding(field: FieldNavItem) {
  const found = onSelectField(field)
  if (!found) {
    bindHintFieldKey.value = fieldKey(field)
  }
}

// Story 28.3 — ambiguous field state for modal
const ambiguousModalField = ref<FieldNavItem | null>(null)

function onOpenAmbiguous(field: FieldNavItem) {
  ambiguousModalField.value = field
}

function onResolveAmbiguous(chosenPath: string | null) {
  if (ambiguousModalField.value) {
    mappingStore.resolveAmbiguous(ambiguousModalField.value.path, chosenPath)
  }
  ambiguousModalField.value = null
}

function onCancelAmbiguous() {
  ambiguousModalField.value = null
}

// ─── XSD-only field selection ────────────────────────────────────────────────
function onSelectXsdField(field: UnmappedXsdField) {
  selectedXsdPath.value = selectedXsdPath.value === field.xsd_path ? null : field.xsd_path
}
</script>

<style scoped>
.field-navigator {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-size: 0.8125rem;
}

/* Summary */
.field-navigator__summary {
  flex-shrink: 0;
  padding: 0.625rem 0.75rem 0.5rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
}

.field-navigator__summary-text {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-neutral-200, #e5e7eb);
  margin-bottom: 0.375rem;
}

.field-navigator__progress {
  height: 0.375rem;
}

/* Groups */
.field-navigator__groups {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.field-navigator__group {
  border-bottom: 1px solid var(--color-neutral-750, #2d3748);
}

.field-navigator__group-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
  padding: 0.375rem 0.75rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-neutral-200, #e5e7eb);
  text-align: left;
  transition: background-color 0.1s;
}

.field-navigator__group-header:hover {
  background-color: var(--color-neutral-750, #2d3748);
}

.field-navigator__group-header--xsd {
  color: var(--color-red-400, #f87171);
}

.field-navigator__group-icon {
  font-size: 0.875rem;
}

.field-navigator__group-label {
  flex: 1;
}

.field-navigator__group-count {
  font-size: 0.6875rem;
  font-weight: 400;
  color: var(--color-neutral-500, #6b7280);
}

.field-navigator__group-toggle {
  font-size: 0.5rem;
  color: var(--color-neutral-500, #6b7280);
}

.field-navigator__group-items {
  padding-bottom: 0.25rem;
}

/* XSD detail panel */
.field-navigator__xsd-detail {
  margin: 4px 8px;
  padding: 8px 10px;
  border-radius: 4px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  font-size: 0.75rem;
}

.field-navigator__xsd-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
}

.field-navigator__xsd-detail-title {
  font-weight: 600;
  color: var(--color-red-400, #f87171);
  font-size: 0.8125rem;
}

.field-navigator__xsd-detail-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.75rem;
  padding: 0 2px;
  line-height: 1;
}

.field-navigator__xsd-detail-close:hover {
  color: var(--color-neutral-200, #e5e7eb);
}

.field-navigator__xsd-detail-path {
  font-family: monospace;
  font-size: 0.625rem;
  color: var(--color-neutral-400, #9ca3af);
  margin-bottom: 4px;
  word-break: break-all;
}

.field-navigator__xsd-detail-msg {
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.6875rem;
  line-height: 1.4;
}

/* Bind hint */
.field-navigator__bind-hint {
  margin: 4px 8px 6px;
  padding: 6px 10px;
  border-radius: 4px;
  background: rgba(96, 165, 250, 0.08);
  border: 1px solid rgba(96, 165, 250, 0.25);
  font-size: 0.6875rem;
  color: var(--color-primary-300, #93c5fd);
  line-height: 1.4;
}

/* Empty state */
.field-navigator__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  color: var(--color-neutral-500, #6b7280);
  font-size: 0.8125rem;
}
</style>
