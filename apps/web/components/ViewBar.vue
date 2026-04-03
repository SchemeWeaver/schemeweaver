<script setup lang="ts">
import NewViewDialog from './NewViewDialog.vue'
import { useSystem } from '~/composables/useSystem'

const { currentSystem, activeViewId, loading, setActiveView, syncViewFromOntology, loadSystem } = useSystem()

const views = computed(() => currentSystem.value?.views ?? [])
const showNewViewDialog = ref(false)

function onViewChange(e: Event): void {
  const id = (e.target as HTMLSelectElement).value
  setActiveView(id)
}

async function onViewCreated(viewId: string): Promise<void> {
  // Reload the system so the new view appears, then switch to it
  if (currentSystem.value) {
    await loadSystem(currentSystem.value.slug)
    setActiveView(viewId)
  }
}
</script>

<template>
  <div v-if="currentSystem" class="view-bar">
    <div class="view-bar__left">
      <span class="view-bar__icon">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
          <rect x="1" y="1" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.2"/>
          <rect x="7" y="1" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.2"/>
          <rect x="1" y="7" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.2"/>
          <rect x="7" y="7" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.2"/>
        </svg>
      </span>
      <select
        class="view-bar__select"
        :value="activeViewId ?? ''"
        @change="onViewChange"
      >
        <option v-for="v in views" :key="v.id" :value="v.id">
          {{ v.name }}
        </option>
      </select>
    </div>

    <div class="view-bar__right">
      <button
        class="view-bar__sync-btn"
        :disabled="loading"
        title="Re-derive this view from the system ontology"
        @click="syncViewFromOntology"
      >
        <svg :class="['view-bar__sync-icon', { spinning: loading }]" width="13" height="13" viewBox="0 0 13 13" fill="none">
          <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2c1.2 0 2.3.47 3.1 1.24L11 5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          <path d="M9 5h2.2V2.8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Derive from ontology
      </button>

      <button
        class="view-bar__new-btn"
        :disabled="loading"
        title="Create a new scoped view"
        @click="showNewViewDialog = true"
      >
        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
          <path d="M5.5 1v9M1 5.5h9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        New view
      </button>
    </div>
  </div>

  <NewViewDialog
    v-if="showNewViewDialog"
    @close="showNewViewDialog = false"
    @created="onViewCreated"
  />
</template>

<style scoped>
.view-bar {
  display: flex;
  align-items: center;
  height: 36px;
  padding: 0 12px;
  background: var(--bg-chrome);
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
  gap: 8px;
}

.view-bar__left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.view-bar__icon {
  color: var(--text-subtle);
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.view-bar__select {
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  padding: 3px 8px 3px 6px;
  cursor: pointer;
  outline: none;
  max-width: 200px;
  transition: border-color 0.12s;
}

.view-bar__select:hover,
.view-bar__select:focus {
  border-color: var(--accent);
}

.view-bar__right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.view-bar__sync-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  white-space: nowrap;
}

.view-bar__sync-btn:hover:not(:disabled) {
  background: var(--bg-chrome-raised);
  border-color: var(--accent);
  color: var(--accent);
}

.view-bar__sync-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.view-bar__new-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 9px;
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  white-space: nowrap;
}

.view-bar__new-btn:hover:not(:disabled) {
  background: var(--bg-chrome-raised);
  border-color: var(--accent);
  color: var(--accent);
}

.view-bar__new-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.view-bar__sync-icon {
  transition: transform 0.5s;
}

.view-bar__sync-icon.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
