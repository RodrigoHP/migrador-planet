<template>
  <ol class="stepper" aria-label="Progresso do wizard">
    <li v-for="(label, index) in labels" :key="label" class="stepper__item" :class="{ 'stepper__item--active': currentStep === index + 1 }">
      <span class="stepper__dot">{{ index + 1 }}</span>
      <span class="stepper__label">{{ label }}</span>
    </li>
  </ol>
</template>

<script setup lang="ts">
const props = defineProps<{
  currentStep: 1 | 2 | 3 | 4 | 5
}>()

const labels = ['Upload', 'Campos', 'Layout', 'Geração', 'Exportar']
const currentStep = props.currentStep
</script>

<style scoped>
.stepper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.stepper__item {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  color: var(--color-neutral-500);
  font-size: 0.75rem;
}

.stepper__item--active {
  color: var(--color-primary-600);
  font-weight: 700;
}

.stepper__dot {
  width: 1.125rem;
  height: 1.125rem;
  border-radius: 9999px;
  background: var(--color-neutral-200);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6875rem;
}

.stepper__item--active .stepper__dot {
  background: var(--color-primary-600);
  color: #fff;
}

@media (max-width: 768px) {
  .stepper__label {
    display: none;
  }
}
</style>
