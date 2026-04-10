<template>
  <Teleport to="body">
    <div
      v-if="visible"
      ref="menuRef"
      class="context-menu"
      :style="{ top: position.y + 'px', left: position.x + 'px' }"
      role="menu"
      aria-label="Menu de contexto"
      @keydown.escape="$emit('close')"
    >
      <template v-for="item in items" :key="item.id">
        <!-- Separator -->
        <div v-if="item.type === 'separator'" class="context-menu__separator" role="separator" />

        <!-- Item with submenu -->
        <div
          v-else-if="item.submenu && item.submenu.length > 0"
          class="context-menu__item context-menu__item--has-submenu"
          :class="{ 'context-menu__item--disabled': item.disabled }"
          role="menuitem"
          tabindex="0"
          @mouseenter="openSubmenu(item.id)"
          @mouseleave="closeSubmenu"
          @keydown.enter="!item.disabled && openSubmenu(item.id)"
          @click.stop
        >
          <span class="context-menu__icon">{{ item.icon }}</span>
          <span class="context-menu__label">{{ item.label }}</span>
          <span class="context-menu__arrow">▶</span>

          <!-- Submenu -->
          <div v-if="activeSubmenu === item.id" class="context-menu context-menu--submenu">
            <div
              v-for="sub in item.submenu"
              :key="sub.id"
              class="context-menu__item"
              :class="{ 'context-menu__item--disabled': sub.disabled }"
              role="menuitem"
              tabindex="0"
              @click.stop="handleSubItemClick(sub)"
              @keydown.enter="handleSubItemClick(sub)"
            >
              <span class="context-menu__icon">{{ sub.icon }}</span>
              <span class="context-menu__label">{{ sub.label }}</span>
            </div>
          </div>
        </div>

        <!-- Regular item -->
        <div
          v-else
          class="context-menu__item"
          :class="{
            'context-menu__item--disabled': item.disabled,
            'context-menu__item--danger': item.danger,
          }"
          role="menuitem"
          tabindex="0"
          @click.stop="handleItemClick(item)"
          @keydown.enter="handleItemClick(item)"
        >
          <span class="context-menu__icon">{{ item.icon }}</span>
          <span class="context-menu__label">{{ item.label }}</span>
        </div>
      </template>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useClickOutside } from '@/composables/useClickOutside'

// ─── Types ────────────────────────────────────────────────────────────────────
export interface ContextMenuItem {
  id: string
  label: string
  icon?: string
  disabled?: boolean
  danger?: boolean
  type?: 'separator'
  submenu?: ContextMenuItem[]
  action?: () => void
}

// ─── Props ────────────────────────────────────────────────────────────────────
interface Props {
  visible: boolean
  position: { x: number; y: number }
  items: ContextMenuItem[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  'item-click': [item: ContextMenuItem]
}>()

// ─── State ────────────────────────────────────────────────────────────────────
const menuRef = ref<HTMLElement | null>(null)
const activeSubmenu = ref<string | null>(null)

// ─── Click outside → close ────────────────────────────────────────────────────
useClickOutside(menuRef, () => {
  if (props.visible) emit('close')
})

// ─── Submenu handling ─────────────────────────────────────────────────────────
function openSubmenu(id: string) {
  activeSubmenu.value = id
}

function closeSubmenu() {
  activeSubmenu.value = null
}

// ─── Item click ───────────────────────────────────────────────────────────────
function handleItemClick(item: ContextMenuItem) {
  if (item.disabled) return
  emit('item-click', item)
  item.action?.()
  emit('close')
}

function handleSubItemClick(item: ContextMenuItem) {
  if (item.disabled) return
  emit('item-click', item)
  item.action?.()
  emit('close')
}

// ─── Focus menu on open ───────────────────────────────────────────────────────
watch(
  () => props.visible,
  async (v) => {
    if (v) {
      activeSubmenu.value = null
      await nextTick()
      menuRef.value?.focus()
    }
  },
)
</script>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 9999;
  min-width: 180px;
  background: var(--color-neutral-800, #1f2937);
  border: 1px solid var(--color-neutral-600, #4b5563);
  border-radius: 6px;
  padding: 4px 0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  outline: none;
  user-select: none;
}

.context-menu--submenu {
  position: absolute;
  left: 100%;
  top: -4px;
}

.context-menu__separator {
  height: 1px;
  background: var(--color-neutral-600, #4b5563);
  margin: 4px 0;
}

.context-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 0.8125rem;
  color: var(--color-neutral-200, #e5e7eb);
  cursor: pointer;
  border-radius: 0;
  transition: background 80ms ease;
  position: relative;
}

.context-menu__item:hover,
.context-menu__item:focus {
  background: var(--color-neutral-700, #374151);
  outline: none;
}

.context-menu__item--disabled {
  color: var(--color-neutral-500, #525252);
  cursor: not-allowed;
  pointer-events: none;
}

.context-menu__item--danger {
  color: var(--color-red-400, #f87171);
}

.context-menu__item--danger:hover {
  background: rgba(239, 68, 68, 0.15);
}

.context-menu__item--has-submenu {
  padding-right: 28px;
}

.context-menu__icon {
  font-size: 0.875rem;
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.context-menu__label {
  flex: 1;
  white-space: nowrap;
}

.context-menu__arrow {
  position: absolute;
  right: 8px;
  font-size: 0.5rem;
  color: var(--color-neutral-400, #9ca3af);
}
</style>
