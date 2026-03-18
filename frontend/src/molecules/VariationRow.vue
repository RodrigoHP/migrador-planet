<template>
  <div class="variation-row" role="row">
    <!-- Field name cell -->
    <div class="variation-row__field" role="rowheader" :title="fieldName">
      {{ fieldName }}
    </div>

    <!-- Presence cells: one per document -->
    <div
      v-for="(present, docIdx) in presencePerDoc"
      :key="docIdx"
      class="variation-row__cell"
      role="cell"
      :aria-label="`Documento ${docIdx + 1}: ${present ? 'presente' : 'ausente'}`"
    >
      <span :class="present ? 'variation-row__icon--present' : 'variation-row__icon--absent'">
        {{ present ? '✔' : '✖' }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  fieldName: string
  presencePerDoc: boolean[]
}>()
</script>

<style scoped>
.variation-row {
  display: contents;
}

.variation-row__field {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: var(--color-neutral-200, #e5e7eb);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  background: var(--color-neutral-800, #1f2937);
}

.variation-row__cell {
  padding: 0.25rem;
  text-align: center;
  font-size: 0.8125rem;
  border-bottom: 1px solid var(--color-neutral-700, #374151);
  background: var(--color-neutral-800, #1f2937);
}

.variation-row__icon--present {
  color: #22c55e;
  font-weight: 700;
}

.variation-row__icon--absent {
  color: #ef4444;
  font-weight: 700;
}
</style>
