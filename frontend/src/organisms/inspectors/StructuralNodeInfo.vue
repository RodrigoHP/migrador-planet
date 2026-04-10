<template>
  <div class="structural-node-info">
    <!-- Type heading -->
    <div class="structural-node-info__header">
      <span class="structural-node-info__icon">{{ typeIcon }}</span>
      <h3 class="structural-node-info__title">{{ humanizedType }}</h3>
    </div>

    <!-- Info fields -->
    <div class="structural-node-info__fields">
      <div class="structural-node-info__field">
        <span class="structural-node-info__label">TIPO</span>
        <span class="structural-node-info__value"
          >{{ humanizedType }} ({{ node?.type ?? '—' }})</span
        >
      </div>

      <div class="structural-node-info__field">
        <span class="structural-node-info__label">NOME</span>
        <span class="structural-node-info__value">{{ node?.name || '—' }}</span>
      </div>

      <div class="structural-node-info__field">
        <span class="structural-node-info__label">FILHOS DIRETOS</span>
        <span class="structural-node-info__value">{{ childCount }} elementos</span>
      </div>

      <div class="structural-node-info__field">
        <span class="structural-node-info__label">COM BINDING</span>
        <span class="structural-node-info__value">
          <span :class="bindingClass">{{ boundCount }}</span>
          <span class="structural-node-info__sep"> de </span>
          <span>{{ bindableCount }}</span>
          <span class="structural-node-info__desc"> bindáveis</span>
        </span>
      </div>
    </div>

    <!-- Hint -->
    <p class="structural-node-info__hint">
      ⓘ Propriedades de layout são configuradas no nó Documento.
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from '@/types/template.types'

interface Props {
  node?: TreeNode | null
}

const props = withDefaults(defineProps<Props>(), { node: null })

const TYPE_LABELS: Record<string, string> = {
  header: 'Cabeçalho',
  footer: 'Rodapé',
  flow: 'Fluxo',
  section: 'Seção',
  container: 'Contêiner',
}

const TYPE_ICONS: Record<string, string> = {
  header: '⬆',
  footer: '⬇',
  flow: '↕',
  section: '📦',
  container: '📦',
}

const humanizedType = computed<string>(
  () => TYPE_LABELS[props.node?.type ?? ''] ?? props.node?.type ?? '—',
)

const typeIcon = computed<string>(() => TYPE_ICONS[props.node?.type ?? ''] ?? '📦')

const childCount = computed<number>(() => props.node?.children?.length ?? 0)

/** Recursively collect all descendants */
function getAllDescendants(node: TreeNode): TreeNode[] {
  const result: TreeNode[] = []
  for (const child of node.children ?? []) {
    result.push(child)
    result.push(...getAllDescendants(child))
  }
  return result
}

const bindableCount = computed<number>(() => {
  if (!props.node) return 0
  return getAllDescendants(props.node).filter((n) => n.type === 'text' || n.type === 'field').length
})

const boundCount = computed<number>(() => {
  if (!props.node) return 0
  return getAllDescendants(props.node).filter(
    (n) => (n.type === 'text' || n.type === 'field') && !!n.binding,
  ).length
})

const bindingClass = computed<string>(() =>
  boundCount.value === bindableCount.value && bindableCount.value > 0
    ? 'structural-node-info__value--all-bound'
    : boundCount.value > 0
      ? 'structural-node-info__value--partial'
      : 'structural-node-info__value--none',
)
</script>

<style scoped>
.structural-node-info {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.structural-node-info__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.structural-node-info__icon {
  font-size: 1.25rem;
}

.structural-node-info__title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-neutral-100, #f3f4f6);
}

.structural-node-info__fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.structural-node-info__field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.structural-node-info__label {
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-neutral-400, #9ca3af);
}

.structural-node-info__value {
  font-size: 0.8125rem;
  color: var(--color-neutral-200, #e5e7eb);
}

.structural-node-info__value--all-bound {
  color: var(--color-green-500, #22c55e);
  font-weight: 600;
}

.structural-node-info__value--partial {
  color: var(--color-yellow-400, #facc15);
  font-weight: 600;
}

.structural-node-info__value--none {
  color: var(--color-red-500, #ef4444);
}

.structural-node-info__sep,
.structural-node-info__desc {
  color: var(--color-neutral-400, #9ca3af);
  font-size: 0.75rem;
}

.structural-node-info__hint {
  margin: 0;
  font-size: 0.6875rem;
  color: var(--color-neutral-500, #525252);
  font-style: italic;
  line-height: 1.4;
  border-top: 1px solid var(--color-neutral-700, #374151);
  padding-top: 8px;
}
</style>
