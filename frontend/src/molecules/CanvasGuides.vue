<template>
  <div v-if="showGuides" class="canvas-guides" aria-hidden="true" data-testid="canvas-guides">
    <!-- Margin guides (dashed blue lines on each side) -->
    <div class="canvas-guides__margin canvas-guides__margin--top" :style="marginTopStyle" />
    <div class="canvas-guides__margin canvas-guides__margin--bottom" :style="marginBottomStyle" />
    <div class="canvas-guides__margin canvas-guides__margin--left" :style="marginLeftStyle" />
    <div class="canvas-guides__margin canvas-guides__margin--right" :style="marginRightStyle" />

    <!-- Header zone guide (blue) -->
    <div
      v-if="headerHeight > 0"
      class="canvas-guides__zone canvas-guides__zone--header"
      :style="{ top: `${margins.top}px`, height: `${headerHeight}px` }"
    />

    <!-- Footer zone guide (orange) -->
    <div
      v-if="footerHeight > 0"
      class="canvas-guides__zone canvas-guides__zone--footer"
      :style="{ bottom: `${margins.bottom}px`, height: `${footerHeight}px` }"
    />

    <!-- Column guides (vertical gray dashed lines) -->
    <div
      v-for="col in columnPositions"
      :key="`col-${col}`"
      class="canvas-guides__column"
      :style="{ left: `${col}px` }"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useEditorStore } from '@/stores/editorStore'

interface Margins {
  top: number
  bottom: number
  left: number
  right: number
}

interface GuideProps {
  pageWidth?: number
  pageHeight?: number
  margins?: Margins
  headerHeight?: number
  footerHeight?: number
  columnPositions?: number[]
}

const props = withDefaults(defineProps<GuideProps>(), {
  pageWidth: 794,
  pageHeight: 1123,
  margins: () => ({ top: 40, bottom: 40, left: 40, right: 40 }),
  headerHeight: 80,
  footerHeight: 60,
  columnPositions: () => [],
})

const editorStore = useEditorStore()
const showGuides = computed(() => editorStore.showGuides)

const margins = computed(() => props.margins)

const marginTopStyle = computed(() => ({
  top: `${margins.value.top}px`,
  left: 0,
  right: 0,
  height: '1px',
}))

const marginBottomStyle = computed(() => ({
  bottom: `${margins.value.bottom}px`,
  left: 0,
  right: 0,
  height: '1px',
}))

const marginLeftStyle = computed(() => ({
  left: `${margins.value.left}px`,
  top: 0,
  bottom: 0,
  width: '1px',
}))

const marginRightStyle = computed(() => ({
  right: `${margins.value.right}px`,
  top: 0,
  bottom: 0,
  width: '1px',
}))
</script>

<style scoped>
.canvas-guides {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 10;
  overflow: hidden;
}

/* Margin guides */
.canvas-guides__margin {
  position: absolute;
  background: transparent;
  border-color: rgba(59, 130, 246, 0.5); /* blue-400 @50% */
  border-style: dashed;
  border-width: 0;
}

.canvas-guides__margin--top,
.canvas-guides__margin--bottom {
  border-top-width: 1px;
  left: 0;
  right: 0;
}

.canvas-guides__margin--bottom {
  border-top-width: 0;
  border-bottom-width: 1px;
}

.canvas-guides__margin--left,
.canvas-guides__margin--right {
  border-left-width: 1px;
  top: 0;
  bottom: 0;
}

.canvas-guides__margin--right {
  border-left-width: 0;
  border-right-width: 1px;
}

/* Zone highlight guides */
.canvas-guides__zone {
  position: absolute;
  left: 0;
  right: 0;
  opacity: 0.12;
  border-top: 2px solid;
  border-bottom: 2px solid;
}

.canvas-guides__zone--header {
  background: rgba(59, 130, 246, 0.15); /* blue */
  border-color: rgb(59, 130, 246);
}

.canvas-guides__zone--footer {
  background: rgba(249, 115, 22, 0.15); /* orange */
  border-color: rgb(249, 115, 22);
}

/* Column guides */
.canvas-guides__column {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: transparent;
  border-left: 1px dashed rgba(107, 114, 128, 0.6); /* gray */
}
</style>
