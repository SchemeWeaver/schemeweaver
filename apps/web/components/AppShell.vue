<script setup lang="ts">
import ComplexityFilter from './ComplexityFilter.vue'
import ExportBar from './ExportBar.vue'
import { useDiagram } from '~/composables/useDiagram'

const props = defineProps<{ libraryOpen: boolean; shapesOpen: boolean }>()
const emit = defineEmits<{ 'update:libraryOpen': [value: boolean]; 'update:shapesOpen': [value: boolean] }>()

const { dir, loading, saving, currentSlug, save, reset } = useDiagram()

const saveLabel = ref('Save')

async function handleSave(): Promise<void> {
  await save()
  saveLabel.value = 'Saved ✓'
  setTimeout(() => { saveLabel.value = 'Save' }, 2000)
}

function toggleLibrary(): void { emit('update:libraryOpen', !props.libraryOpen) }
function toggleShapes(): void { emit('update:shapesOpen', !props.shapesOpen) }
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
        <button
          :class="['app-shell__icon-btn', { active: shapesOpen }]"
          title="Toggle shape palette"
          @click="toggleShapes"
        >
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <rect x="1" y="1" width="5.5" height="5.5" rx="1.2" stroke="currentColor" stroke-width="1.3"/>
            <rect x="8.5" y="1" width="5.5" height="5.5" rx="1.2" stroke="currentColor" stroke-width="1.3"/>
            <rect x="1" y="8.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" stroke-width="1.3"/>
            <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" stroke-width="1.3"/>
          </svg>
        </button>

        <div class="app-shell__divider" />
        <ComplexityFilter />

        <div class="app-shell__divider" />

        <ExportBar />

        <template v-if="dir">
          <div class="app-shell__divider" />

          <button
            :class="['app-shell__save-btn', { 'app-shell__save-btn--saved': saveLabel !== 'Save' }]"
            :disabled="saving"
            :title="currentSlug ? `Overwrite '${currentSlug}'` : 'Save as new diagram'"
            @click="handleSave"
          >
            <span v-if="saving" class="app-shell__spinner" />
            <template v-else>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 2h6.5L10 3.5V10H2V2z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
                <rect x="3.5" y="6.5" width="5" height="3.5" rx="0.4" stroke="currentColor" stroke-width="1.2"/>
                <rect x="3.5" y="2" width="3.5" height="2" rx="0.4" stroke="currentColor" stroke-width="1.2"/>
              </svg>
              {{ saveLabel }}
            </template>
          </button>

          <div class="app-shell__divider" />

          <button
            class="app-shell__icon-btn app-shell__new-btn"
            title="New diagram"
            @click="reset"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            New
          </button>
        </template>
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

.app-shell__save-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  white-space: nowrap;
}

.app-shell__save-btn:hover:not(:disabled) {
  background: var(--bg-chrome-hover);
  border-color: var(--accent);
  color: var(--text-primary);
}

.app-shell__save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.app-shell__save-btn--saved {
  color: var(--success);
  border-color: var(--success);
  background: rgba(82, 183, 136, 0.08);
}

.app-shell__spinner {
  display: inline-block;
  width: 11px;
  height: 11px;
  border: 1.5px solid var(--border-chrome);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
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
