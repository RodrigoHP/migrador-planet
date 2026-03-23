<template>
  <div class="box-model" aria-label="Box model visualization">
    <!-- Margin layer -->
    <div class="box-model__layer box-model__layer--margin">
      <span class="box-model__label">margin</span>
      <BoxModelValue
        v-for="side in SIDES" :key="'m-' + side"
        :class="'box-model__val--' + side"
        class="box-model__val"
        :label="'margin ' + side"
        :value="margin[side]"
        @update="$emit('update:margin', { ...margin, [side]: $event })"
      />
      <!-- Border layer -->
      <div class="box-model__layer box-model__layer--border">
        <span class="box-model__label">border</span>
        <BoxModelValue
          v-for="side in SIDES" :key="'b-' + side"
          :class="'box-model__val--' + side"
          class="box-model__val"
          :label="'border ' + side"
          :value="border[side]"
          @update="$emit('update:border', { ...border, [side]: $event })"
        />
        <!-- Padding layer -->
        <div class="box-model__layer box-model__layer--padding">
          <span class="box-model__label">padding</span>
          <BoxModelValue
            v-for="side in SIDES" :key="'p-' + side"
            :class="'box-model__val--' + side"
            class="box-model__val"
            :label="'padding ' + side"
            :value="padding[side]"
            @update="$emit('update:padding', { ...padding, [side]: $event })"
          />
          <!-- Content layer -->
          <div class="box-model__layer box-model__layer--content">
            <span class="box-model__content-label">{{ contentWidth }} × {{ contentHeight }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import BoxModelValue from './BoxModelValue.vue'

export interface BoxSides {
  top: number
  right: number
  bottom: number
  left: number
}

const SIDES = ['top', 'right', 'bottom', 'left'] as const

withDefaults(
  defineProps<{
    margin?: BoxSides
    border?: BoxSides
    padding?: BoxSides
    contentWidth?: number
    contentHeight?: number
  }>(),
  {
    margin: () => ({ top: 0, right: 0, bottom: 0, left: 0 }),
    border: () => ({ top: 0, right: 0, bottom: 0, left: 0 }),
    padding: () => ({ top: 0, right: 0, bottom: 0, left: 0 }),
    contentWidth: 0,
    contentHeight: 0,
  },
)

defineEmits<{
  'update:margin': [value: BoxSides]
  'update:border': [value: BoxSides]
  'update:padding': [value: BoxSides]
}>()
</script>

<style scoped>
.box-model {
  font-size: 0.6875rem;
  user-select: none;
}

.box-model__layer {
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr auto;
  grid-template-rows: auto 1fr auto;
  min-height: 2rem;
  border: 1px dashed;
}

.box-model__layer--margin {
  background: hsla(30, 100%, 50%, 0.12);
  border-color: hsla(30, 100%, 50%, 0.4);
  padding: 0.75rem 1rem;
}

.box-model__layer--border {
  background: hsla(50, 100%, 50%, 0.12);
  border-color: hsla(50, 100%, 50%, 0.4);
  padding: 0.75rem 1rem;
  grid-column: 1 / -1;
  grid-row: 2;
}

.box-model__layer--padding {
  background: hsla(120, 60%, 40%, 0.12);
  border-color: hsla(120, 60%, 40%, 0.4);
  padding: 0.75rem 1rem;
  grid-column: 1 / -1;
  grid-row: 2;
}

.box-model__layer--content {
  background: hsla(210, 80%, 55%, 0.15);
  border-color: hsla(210, 80%, 55%, 0.4);
  grid-column: 1 / -1;
  grid-row: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 1.5rem;
  padding: 0.25rem;
}

.box-model__label {
  position: absolute;
  top: 0.125rem;
  left: 0.25rem;
  font-size: 0.5625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-neutral-400, #9ca3af);
  pointer-events: none;
}

.box-model__content-label {
  font-size: 0.625rem;
  color: var(--color-neutral-300, #d1d5db);
  white-space: nowrap;
}

.box-model__val {
  position: absolute;
  z-index: 1;
}

.box-model__val--top {
  top: 0.125rem;
  left: 50%;
  transform: translateX(-50%);
}

.box-model__val--right {
  right: 0.125rem;
  top: 50%;
  transform: translateY(-50%);
}

.box-model__val--bottom {
  bottom: 0.125rem;
  left: 50%;
  transform: translateX(-50%);
}

.box-model__val--left {
  left: 0.125rem;
  top: 50%;
  transform: translateY(-50%);
}
</style>
