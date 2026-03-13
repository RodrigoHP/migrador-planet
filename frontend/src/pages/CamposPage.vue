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

        <p v-if="hasUnresolvedRequired" class="warning">
          Existem campos required com status <code>not_found</code>. Corrija antes de confirmar.
        </p>

        <FieldMappingTable
          :fields="mapping.fields"
          :selected-field-id="mapping.selectedFieldId"
          @select="selectField"
        />
      </template>

      <template #right>
        <FieldDetailPanel :field="selectedField" @save="saveField" />
      </template>
    </SplitPaneLayout>
  </WizardLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
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

const selectedField = computed(() => mapping.selectedField)
const hasUnresolvedRequired = computed(() =>
  mapping.fields.some((field) => field.status === 'not_found'),
)

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
</script>

<style scoped>
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.panel-header h2 {
  margin: 0;
  font-size: 1rem;
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
</style>
