<template>
  <div
    class="diff-highlight"
    :class="`diff-highlight--${type}`"
    :style="{
      left: `${bounds.x}px`,
      top: `${bounds.y}px`,
      width: `${bounds.w}px`,
      height: `${bounds.h}px`,
    }"
    :aria-label="`Diff highlight: ${type}`"
  />
</template>

<script setup lang="ts">
import type { DiffType, DiffBounds } from '@/stores/diffStore'

defineProps<{
  type: DiffType
  bounds: DiffBounds
}>()
</script>

<style scoped>
.diff-highlight {
  position: absolute;
  pointer-events: none;
  border-radius: 2px;
}

/* Identical — green */
.diff-highlight--identical {
  background: rgba(34, 197, 94, 0.10);
  border: 1px solid rgba(34, 197, 94, 0.5);
}

/* Moved — yellow */
.diff-highlight--moved {
  background: rgba(234, 179, 8, 0.10);
  border: 1px solid rgba(234, 179, 8, 0.5);
}

/* Added — red (present only in doc B) */
.diff-highlight--added {
  background: rgba(239, 68, 68, 0.10);
  border: 1px solid rgba(239, 68, 68, 0.5);
}

/* Removed — red (present only in doc A) */
.diff-highlight--removed {
  background: rgba(239, 68, 68, 0.10);
  border: 1px dashed rgba(239, 68, 68, 0.5);
}
</style>
