<script setup lang="ts">
import { useSystem } from '~/composables/useSystem'

const emit = defineEmits<{ close: [] }>()
const props = defineProps<{ onLoad: (slug: string) => Promise<void> }>()

const { systems, loadingList, listError, currentSystem, fetchList, migrateLibrary } = useSystem()

const showRepoImport = ref(false)

const loadingSlug   = ref<string | null>(null)
const migrating     = ref(false)
const migrateResult = ref<string | null>(null)

async function migrate(): Promise<void> {
  migrating.value = true
  migrateResult.value = null
  try {
    const res = await migrateLibrary()
    migrateResult.value = res.migrated.length
      ? `Migrated ${res.migrated.length} diagram(s).`
      : 'Nothing new to migrate.'
  } catch {
    migrateResult.value = 'Migration failed.'
  } finally {
    migrating.value = false
  }
}

async function select(slug: string): Promise<void> {
  loadingSlug.value = slug
  try {
    await props.onLoad(slug)
    emit('close')
  } finally {
    loadingSlug.value = null
  }
}

onMounted(() => {
  if (import.meta.client) {
    fetchList()
  }
})
</script>

<template>
  <aside class="library">
    <div class="library__header">
      <span class="library__title">Library</span>
      <div class="library__header-actions">
        <button
          class="library__action-btn"
          title="Import from repository"
          @click="showRepoImport = true"
        >
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
            <path d="M2 2h4v4H2zM10 2h4v4h-4zM2 10h4v4H2zM10 10h4v4h-4z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
            <path d="M6 4h4M4 6v4M12 6v4M6 12h4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          </svg>
        </button>
        <button
          class="library__action-btn"
          title="Refresh"
          :disabled="loadingList"
          @click="fetchList"
        >
          <svg :class="['library__refresh-icon', { spinning: loadingList }]" width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2c1.2 0 2.3.47 3.1 1.24L11 5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            <path d="M9 5h2.2V2.8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button class="library__action-btn" title="Close" @click="emit('close')">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>

    <RepoImportDialog
      v-if="showRepoImport"
      :on-load="props.onLoad"
      @close="showRepoImport = false; fetchList()"
    />

    <div class="library__body">
      <!-- Loading skeleton -->
      <div v-if="loadingList" class="library__skeletons">
        <div v-for="i in 4" :key="i" class="library__skeleton" />
      </div>

      <!-- Error -->
      <div v-else-if="listError" class="library__empty library__empty--error">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
          <path d="M12 7v5M12 16v1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <span>{{ listError }}</span>
      </div>

      <!-- Empty -->
      <div v-else-if="systems.length === 0" class="library__empty">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" opacity="0.3">
          <polygon points="16,3 29,10 29,22 16,29 3,22 3,10" stroke="currentColor" stroke-width="1.5" fill="none"/>
        </svg>
        <p>No saved systems yet.</p>
        <p>Generate one with the prompt bar below.</p>
        <button class="library__migrate-btn" :disabled="migrating" @click="migrate">
          <span v-if="migrating" class="library__item-spinner" />
          <template v-else>Import from old library</template>
        </button>
        <span v-if="migrateResult" class="library__migrate-result">{{ migrateResult }}</span>
      </div>

      <!-- List -->
      <ul v-else class="library__list">
        <li
          v-for="entry in systems"
          :key="entry.slug"
          :class="['library__item', { active: currentSystem?.slug === entry.slug }]"
          @click="select(entry.slug)"
        >
          <span class="library__type-icon" style="color: #5b8cd7">⬡</span>

          <div class="library__item-info">
            <span class="library__item-name">{{ entry.name }}</span>
            <span class="library__item-meta">
              {{ entry.entity_count }} entities · {{ entry.view_count }} view{{ entry.view_count !== 1 ? 's' : '' }}
            </span>
          </div>

          <span v-if="loadingSlug === entry.slug" class="library__item-spinner" />
          <svg v-else class="library__item-arrow" width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </li>
      </ul>
    </div>
  </aside>
</template>

<style scoped>
.library {
  width: 256px;
  height: 100%;
  background: var(--bg-chrome);
  border-right: 1px solid var(--border-chrome);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

/* ── Header ────────────────────────────────────────────────────────── */
.library__header {
  display: flex;
  align-items: center;
  padding: 0 12px;
  height: 40px;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.library__title {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.library__header-actions {
  display: flex;
  gap: 2px;
}

.library__action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-subtle);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.library__action-btn:hover:not(:disabled) {
  background: var(--bg-chrome-hover);
  color: var(--text-primary);
}

.library__action-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.library__refresh-icon { transition: transform 0.5s; }
.library__refresh-icon.spinning { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Body ──────────────────────────────────────────────────────────── */
.library__body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* Skeleton */
.library__skeletons {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.library__skeleton {
  height: 48px;
  background: var(--bg-chrome-raised);
  border-radius: var(--radius-md);
  animation: shimmer 1.4s ease infinite;
}

@keyframes shimmer {
  0%, 100% { opacity: 0.6; }
  50%       { opacity: 1; }
}

/* Empty / Error */
.library__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 20px;
  color: var(--text-subtle);
  text-align: center;
  font-size: 13px;
}

.library__empty p { margin: 0; }

.library__empty code {
  font-size: 11px;
  font-family: ui-monospace, monospace;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
}

.library__empty--error { color: var(--danger); }

.library__migrate-btn {
  margin-top: 4px;
  padding: 5px 14px;
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.library__migrate-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.library__migrate-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.library__migrate-result {
  font-size: 11px;
  color: var(--success);
  margin-top: 4px;
}

/* List */
.library__list {
  list-style: none;
  margin: 0;
  padding: 6px 0;
}

.library__item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  cursor: pointer;
  transition: background 0.1s;
  border-radius: 0;
}

.library__item:hover { background: var(--bg-chrome-raised); }
.library__item:hover .library__item-arrow { opacity: 1; }

.library__item.active {
  background: var(--accent-muted);
  border-left: 2px solid var(--accent);
  padding-left: 10px;
}

.library__type-icon {
  font-size: 15px;
  flex-shrink: 0;
  width: 22px;
  text-align: center;
  line-height: 1;
}

.library__item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.library__item-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.library__item-meta {
  font-size: 11px;
  color: var(--text-subtle);
}

.library__item-warn {
  color: var(--warn);
  margin-left: 4px;
}

.library__item-arrow {
  color: var(--text-subtle);
  opacity: 0;
  flex-shrink: 0;
  transition: opacity 0.1s;
}

.library__item-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 1.5px solid var(--border-chrome);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}
</style>
