<script setup lang="ts">
export interface CtxItem {
  label?: string
  action?: () => void
  divider?: boolean
  danger?: boolean
  checked?: boolean
  disabled?: boolean
  subtle?: boolean   // muted label (used for section headings)
}

const props = defineProps<{ x: number; y: number; items: CtxItem[] }>()
const emit = defineEmits<{ close: [] }>()

const menuEl = ref<HTMLElement>()
const finalX = ref(props.x)
const finalY = ref(props.y)

onMounted(() => {
  const el = menuEl.value
  if (el) {
    const { width, height } = el.getBoundingClientRect()
    finalX.value = Math.min(props.x, window.innerWidth  - width  - 10)
    finalY.value = Math.min(props.y, window.innerHeight - height - 10)
  }
  // Defer so the triggering click doesn't immediately dismiss the menu
  setTimeout(() => {
    document.addEventListener('pointerdown', onOutside, { capture: true })
    document.addEventListener('contextmenu', onOutside, { capture: true })
    document.addEventListener('keydown', onKey)
  }, 0)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onOutside, { capture: true })
  document.removeEventListener('contextmenu', onOutside, { capture: true })
  document.removeEventListener('keydown', onKey)
})

function onOutside(e: Event) {
  if (e.type === 'contextmenu') e.preventDefault()
  if (!menuEl.value?.contains(e.target as Node)) emit('close')
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

function pick(item: CtxItem) {
  if (item.disabled || item.divider || item.subtle) return
  item.action?.()
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      ref="menuEl"
      class="ctx-menu"
      :style="{ left: `${finalX}px`, top: `${finalY}px` }"
      @contextmenu.prevent
    >
      <template v-for="(item, i) in items" :key="i">
        <div v-if="item.divider" class="ctx-menu__sep" />
        <div v-else-if="item.subtle" class="ctx-menu__section">{{ item.label }}</div>
        <button
          v-else
          :class="[
            'ctx-menu__item',
            {
              'ctx-menu__item--danger':   item.danger,
              'ctx-menu__item--disabled': item.disabled,
              'ctx-menu__item--checked':  item.checked,
            },
          ]"
          :disabled="item.disabled"
          @click="pick(item)"
        >
          <span class="ctx-menu__check" aria-hidden="true">
            <svg v-if="item.checked" width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M1.5 5l2.5 2.5L8.5 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span class="ctx-menu__label">{{ item.label }}</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>

<style scoped>
.ctx-menu {
  position: fixed;
  z-index: 9000;
  min-width: 184px;
  padding: 4px;
  background: var(--bg-chrome);
  border: 1px solid var(--border-chrome);
  border-radius: 8px;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.12),
    0 10px 28px -4px rgba(0, 0, 0, 0.18);
  user-select: none;
  outline: none;
}

/* ── Items ─────────────────────────────────────────────────────────────── */
.ctx-menu__item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 0 10px 0 0;
  height: 30px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text-primary);
  font: 13px system-ui, sans-serif;
  text-align: left;
  cursor: pointer;
  transition: background 0.08s;
}
.ctx-menu__item:hover:not(:disabled) {
  background: var(--bg-chrome-hover);
}
.ctx-menu__item:active:not(:disabled) {
  background: var(--bg-chrome-raised);
}

.ctx-menu__item--danger       { color: #e05c5c; }
.ctx-menu__item--danger:hover { background: rgba(224, 92, 92, 0.1); }

.ctx-menu__item--disabled {
  opacity: 0.4;
  cursor: default;
}

/* ── Check column ──────────────────────────────────────────────────────── */
.ctx-menu__check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  flex-shrink: 0;
  color: var(--accent);
}

.ctx-menu__label {
  flex: 1;
}

/* ── Divider ───────────────────────────────────────────────────────────── */
.ctx-menu__sep {
  height: 1px;
  background: var(--border-chrome);
  margin: 3px 6px;
}

/* ── Section label ─────────────────────────────────────────────────────── */
.ctx-menu__section {
  padding: 4px 10px 2px 28px;
  font: 600 10px system-ui, sans-serif;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
</style>
