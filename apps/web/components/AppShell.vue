<script setup lang="ts">
import ComplexityFilter from './ComplexityFilter.vue'
import ExportBar from './ExportBar.vue'
import { useDiagram } from '~/composables/useDiagram'

const props = defineProps<{ libraryOpen: boolean }>()
const emit = defineEmits<{ 'update:libraryOpen': [value: boolean] }>()

const { dir, loading, reset } = useDiagram()

function toggleLibrary(): void {
  emit('update:libraryOpen', !props.libraryOpen)
}
</script>

<template>
  <div class="app-shell">
    <header class="app-shell__header">
      <!-- Left: brand + library toggle -->
      <div class="app-shell__left">
        <button
          :class="['app-shell__icon-btn', { active: libraryOpen }]"
          title="Toggle saved diagrams (library)"
          @click="toggleLibrary"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="3" width="12" height="1.5" rx="0.75" fill="currentColor"/>
            <rect x="2" y="7.25" width="12" height="1.5" rx="0.75" fill="currentColor"/>
            <rect x="2" y="11.5" width="8" height="1.5" rx="0.75" fill="currentColor"/>
          </svg>
        </button>

        <div class="app-shell__brand">
          <svg class="app-shell__logo" width="22" height="22" viewBox="0 0 22 22" fill="none">
            <polygon points="11,2 20,7 20,15 11,20 2,15 2,7" stroke="currentColor" stroke-width="1.5" fill="none"/>
            <polygon points="11,6 16,9 16,13 11,16 6,13 6,9" fill="currentColor" opacity="0.3"/>
          </svg>
          <span class="app-shell__title">Scheme Weaver</span>
        </div>
      </div>

      <!-- Center: diagram title when active -->
      <div v-if="dir" class="app-shell__diagram-title">
        {{ dir.meta.title }}
        <span class="app-shell__diagram-type">{{ dir.meta.diagram_type }}</span>
      </div>

      <!-- Right: controls -->
      <div class="app-shell__right">
        <ComplexityFilter />

        <div class="app-shell__divider" />

        <ExportBar />

        <div v-if="dir" class="app-shell__divider" />

        <button
          v-if="dir"
          class="app-shell__icon-btn app-shell__new-btn"
          title="New diagram"
          @click="reset"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          New
        </button>
      </div>
    </header>

    <div v-if="loading" class="app-shell__progress" />

    <main class="app-shell__main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-chrome);
  font-family: system-ui, -apple-system, sans-serif;
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.app-shell__header {
  display: flex;
  align-items: center;
  height: 48px;
  padding: 0 12px;
  background: var(--bg-chrome);
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
  gap: 8px;
}

.app-shell__left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.app-shell__brand {
  display: flex;
  align-items: center;
  gap: 7px;
  padding-left: 2px;
}

.app-shell__logo {
  color: var(--accent);
  flex-shrink: 0;
}

.app-shell__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.01em;
  white-space: nowrap;
}

/* Center title */
.app-shell__diagram-title {
  flex: 1;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.app-shell__diagram-type {
  font-size: 10px;
  font-weight: 400;
  color: var(--text-subtle);
  background: var(--bg-chrome-hover);
  padding: 2px 6px;
  border-radius: 10px;
  border: 1px solid var(--border-chrome);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.app-shell__right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  margin-left: auto;
}

/* Shared icon/action button style — used in header only */
.app-shell__icon-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  white-space: nowrap;
}

.app-shell__icon-btn:hover {
  background: var(--bg-chrome-raised);
  border-color: var(--border-chrome);
  color: var(--text-primary);
}

.app-shell__icon-btn.active {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.app-shell__new-btn {
  color: var(--text-muted);
}

.app-shell__divider {
  width: 1px;
  height: 20px;
  background: var(--border-chrome);
  flex-shrink: 0;
}

/* ── Progress bar ────────────────────────────────────────────────────────── */
.app-shell__progress {
  height: 2px;
  background: linear-gradient(90deg, var(--accent) 0%, #9b59b6 50%, var(--accent) 100%);
  background-size: 200% 100%;
  animation: progress-sweep 1.2s linear infinite;
  flex-shrink: 0;
}

@keyframes progress-sweep {
  from { background-position: 100% 0; }
  to   { background-position: -100% 0; }
}

/* ── Main content area ───────────────────────────────────────────────────── */
.app-shell__main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
