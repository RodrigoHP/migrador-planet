<template>
  <div class="inspector-field">
    <span class="inspector-field__label">{{ label }}</span>
    <div class="inspector-field__value-wrap">
      <!-- Color type: color swatch + hex text -->
      <template v-if="type === 'color'">
        <span
          class="inspector-field__color-swatch"
          :style="{ background: String(value) }"
        />
        <span class="inspector-field__value">{{ value }}</span>
      </template>
      <!-- Badge type -->
      <template v-else-if="type === 'badge'">
        <span class="inspector-field__badge">{{ value }}</span>
      </template>
      <!-- Default: plain text -->
      <template v-else>
        <span class="inspector-field__value">{{ value }}</span>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string | number
    type?: 'text' | 'color' | 'badge'
  }>(),
  { type: 'text' },
)
</script>

<style scoped>
.inspector-field {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
}

.inspector-field__label {
  font-size: 0.6875rem;
  color: var(--color-neutral-400, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  user-select: none;
}

.inspector-field__value-wrap {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.inspector-field__value {
  font-size: 0.8125rem;
  color: var(--color-neutral-100, #f3f4f6);
}

.inspector-field__color-swatch {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border-radius: 0.1875rem;
  border: 1px solid var(--color-neutral-600, #4b5563);
  flex-shrink: 0;
}

.inspector-field__badge {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.4375rem;
  border-radius: 9999px;
  background: var(--color-neutral-700, #374151);
  color: var(--color-neutral-100, #f3f4f6);
}
</style>
