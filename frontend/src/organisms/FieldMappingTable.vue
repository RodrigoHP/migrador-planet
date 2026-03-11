<template>
  <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>Campo XSD</th>
          <th>Texto PDF</th>
          <th>Tipo</th>
          <th>Confianca</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="field in fields"
          :key="field.id"
          class="table__row"
          :class="{ 'table__row--selected': selectedFieldId === field.id }"
          @click="$emit('select', field.id)"
        >
          <td>{{ field.id }}</td>
          <td>{{ field.pdfText || '-' }}</td>
          <td>{{ field.type }}</td>
          <td>
            <ConfidenceBadge :confidence="field.confidence" />
          </td>
          <td>
            <div class="table__status">
              <FieldStatusBadge :status="field.status" />
              <ManualEditIndicator :visible="field.isManual" />
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { FieldMapping } from '@/types'
import { ConfidenceBadge, FieldStatusBadge, ManualEditIndicator } from '@/atoms'

defineProps<{
  fields: FieldMapping[]
  selectedFieldId: string | null
}>()

defineEmits<{
  select: [fieldId: string]
}>()
</script>

<style scoped>
.table-wrap {
  overflow: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.table th,
.table td {
  text-align: left;
  padding: 0.45rem;
  border-bottom: 1px solid var(--color-neutral-200);
  vertical-align: middle;
}

.table__row {
  cursor: pointer;
}

.table__row:hover {
  background: #f8fafc;
}

.table__row--selected {
  background: #eff6ff;
}

.table__status {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
</style>
