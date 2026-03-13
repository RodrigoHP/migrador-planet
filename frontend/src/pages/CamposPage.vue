<template>
  <WizardLayout :show-save="true">
    <template #stepper>
      <WizardStepper :current-step="2" />
    </template>

    <SplitPaneLayout>
      <template #left>
        <PDFViewer
          :pdf-bytes="session.pdfFile?.bytes ?? null"
          :page-ref="selectedField?.pageRef ?? null"
          :bounding-box="selectedField?.boundingBox ?? null"
        />
      </template>

      <template #center>
        <header class="panel-header">
          <h2>Campos mapeados</h2>
          <Button variant="primary" :disabled="hasUnresolvedRequired" @click="confirmMapping">
            Confirmar Mapeamento
          </Button>
        </header>

        <div class="field-stats">
          {{ fieldStats.total }} campos &nbsp;|&nbsp;
          ✅ {{ fieldStats.ok }} ok &nbsp;|&nbsp;
          🟡 {{ fieldStats.ambiguous }} ambiguous &nbsp;|&nbsp;
          🔴 {{ fieldStats.not_found }} não encontrados
        </div>

        <p v-if="hasUnresolvedRequired" class="warning">
          Existem campos required com status <code>not_found</code>. Corrija antes de confirmar.
        </p>

        <FieldMappingTable
          :fields="mapping.fields"
          :selected-field-id="mapping.selectedFieldId"
          @select="selectField"
        />

        <div class="campos-footer">
          <Button variant="ghost" @click="showVoltarModal = true">◀ Voltar</Button>
          <Button variant="secondary" @click="showRestaurarModal = true">↩ Restaurar mapeamento</Button>
        </div>
      </template>

      <template #right>
        <FieldDetailPanel :field="selectedField" @save="saveField" />
      </template>
    </SplitPaneLayout>
  </WizardLayout>

  <!-- Modal: Voltar ao Upload -->
  <div v-if="showVoltarModal" class="modal-overlay" @click.self="showVoltarModal = false">
    <div class="modal" role="dialog" aria-modal="true">
      <p>Voltar ao upload descartará todo o mapeamento atual. Deseja continuar?</p>
      <div class="modal__actions">
        <Button variant="ghost" @click="showVoltarModal = false">Cancelar</Button>
        <Button variant="danger" @click="confirmarVoltar">Voltar ao Upload</Button>
      </div>
    </div>
  </div>

  <!-- Modal: Restaurar mapeamento -->
  <div v-if="showRestaurarModal" class="modal-overlay" @click.self="showRestaurarModal = false">
    <div class="modal" role="dialog" aria-modal="true">
      <p>Isso descartará todos os ajustes manuais feitos. Deseja continuar?</p>
      <div class="modal__actions">
        <Button variant="ghost" @click="showRestaurarModal = false">Cancelar</Button>
        <Button variant="secondary" @click="confirmarRestaurar">Restaurar</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from '@/atoms'
import { FieldDetailPanel, FieldMappingTable, PDFViewer, WizardStepper } from '@/organisms'
import { SplitPaneLayout, WizardLayout } from '@/templates'
import { useMappingStore } from '@/stores/mapping'
import { useSessionStore } from '@/stores/session'
import type { FieldMapping } from '@/types'

const router = useRouter()
const session = useSessionStore()
const mapping = useMappingStore()

const showVoltarModal = ref(false)
const showRestaurarModal = ref(false)
const originalFields = ref<FieldMapping[]>([])

const selectedField = computed(() => mapping.selectedField)
const hasUnresolvedRequired = computed(() =>
  mapping.fields.some((field) => field.status === 'not_found'),
)

const fieldStats = computed(() => ({
  total: mapping.fields.length,
  ok: mapping.fields.filter((f) => f.status === 'ok').length,
  ambiguous: mapping.fields.filter((f) => f.status === 'ambiguous').length,
  not_found: mapping.fields.filter((f) => f.status === 'not_found').length,
}))

onMounted(() => {
  session.currentStep = 2
  if (mapping.fields.length === 0 && session.extraction?.fields?.length) {
    const normalized = session.extraction.fields.map((field, index): FieldMapping => ({
      id: field.id ?? `field_${index + 1}`,
      pdfText: field.pdfText ?? '',
      jsonPath: field.jsonPath ?? '',
      type: field.type ?? 'text',
      confidence: field.confidence ?? 'medium',
      status: field.status ?? 'ambiguous',
      candidates: field.candidates ?? [],
      isManual: field.isManual ?? false,
      pageRef: field.pageRef,
      boundingBox: field.boundingBox,
    }))
    mapping.setFields(normalized)
    mapping.selectedFieldId = normalized[0]?.id ?? null
  } else if (!mapping.selectedFieldId && mapping.fields.length > 0) {
    mapping.selectedFieldId = mapping.fields[0]?.id ?? null
  }
  originalFields.value = JSON.parse(JSON.stringify(mapping.fields))
})

function selectField(fieldId: string) {
  mapping.selectedFieldId = fieldId
}

function saveField(payload: { id: string; jsonPath: string }) {
  mapping.updateField({
    id: payload.id,
    jsonPath: payload.jsonPath,
    isManual: true,
    status: 'ok',
  })
}

function confirmMapping() {
  if (hasUnresolvedRequired.value) return
  mapping.confirmed = true
  router.push('/layout')
}

function confirmarVoltar() {
  mapping.$reset()
  showVoltarModal.value = false
  router.push('/upload')
}

function confirmarRestaurar() {
  mapping.$patch({ fields: JSON.parse(JSON.stringify(originalFields.value)) })
  showRestaurarModal.value = false
}
</script>

<style scoped>
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.panel-header h2 {
  margin: 0;
  font-size: 1rem;
}

.field-stats {
  font-size: 0.8125rem;
  color: var(--color-neutral-600);
  padding: 0.4rem 0;
  margin-bottom: 0.5rem;
}

.warning {
  margin: 0 0 0.75rem;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 0.65rem;
  padding: 0.5rem 0.65rem;
  font-size: 0.875rem;
}

.campos-footer {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-neutral-200);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: #fff;
  border-radius: 0.75rem;
  padding: 1.25rem;
  max-width: 420px;
  width: 90%;
  display: grid;
  gap: 1rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.modal p {
  margin: 0;
  color: var(--color-neutral-800);
}

.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
