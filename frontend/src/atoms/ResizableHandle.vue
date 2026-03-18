<template>
  <div
    class="resizable-handle"
    :class="[`resizable-handle--${direction}`]"
    role="separator"
    :aria-orientation="direction === 'horizontal' ? 'vertical' : 'horizontal'"
    tabindex="0"
    @mousedown="startDrag"
    @keydown="onKeyDown"
  />
</template>

<script setup lang="ts">
import { onUnmounted } from 'vue'

const props = defineProps<{
  direction: 'horizontal' | 'vertical'
}>()

const emit = defineEmits<{
  (e: 'resize', delta: number): void
}>()

let dragging = false
let startPos = 0

function startDrag(event: MouseEvent) {
  dragging = true
  startPos = props.direction === 'horizontal' ? event.clientX : event.clientY
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  event.preventDefault()
}

function onDrag(event: MouseEvent) {
  if (!dragging) return
  const currentPos = props.direction === 'horizontal' ? event.clientX : event.clientY
  const delta = currentPos - startPos
  startPos = currentPos
  emit('resize', delta)
}

function stopDrag() {
  dragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

// Keyboard support: arrow keys move by 10px
function onKeyDown(event: KeyboardEvent) {
  const step = 10
  if (props.direction === 'horizontal') {
    if (event.key === 'ArrowLeft') emit('resize', -step)
    else if (event.key === 'ArrowRight') emit('resize', step)
  } else {
    if (event.key === 'ArrowUp') emit('resize', -step)
    else if (event.key === 'ArrowDown') emit('resize', step)
  }
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})
</script>

<style scoped>
.resizable-handle {
  background: transparent;
  transition: background 0.15s;
  flex-shrink: 0;
}

.resizable-handle:hover,
.resizable-handle:focus {
  background: var(--color-primary-500, #3b82f6);
  outline: none;
}

.resizable-handle--horizontal {
  width: 4px;
  cursor: col-resize;
  height: 100%;
  min-height: 20px;
}

.resizable-handle--vertical {
  height: 4px;
  cursor: row-resize;
  width: 100%;
  min-width: 20px;
}
</style>
