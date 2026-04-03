<script setup lang="ts">
/**
 * SyncBar — explicit AI-mediated sync between prose ↔ ontology.
 * Proposes a change, shows a diff/preview, lets the user apply or dismiss.
 */
import type { Ontology } from '~/types/system'
import { useSystem } from '~/composables/useSystem'
import { useWorkspace } from '~/composables/useWorkspace'

type SyncOp = 'prose-to-ontology' | 'ontology-to-prose' | 'view-to-prose'

const { currentSystem, activeViewId, saving, saveProse, saveOntology } = useSystem()
const { leftTab, setLeftTab } = useWorkspace()

const syncing  = ref(false)
const syncError = ref<string | null>(null)

// Preview state
const previewProse    = ref<string | null>(null)
const previewOntology = ref<Ontology | null>(null)
const pendingOp       = ref<SyncOp | null>(null)

const config  = useRuntimeConfig()
const apiBase = config.public.apiBase as string

async function runSync(op: SyncOp): Promise<void> {
  if (!currentSystem.value || syncing.value) return
  syncing.value  = true
  syncError.value = null
  previewProse.value    = null
  previewOntology.value = null
  pendingOp.value       = null
  try {
    const slug = encodeURIComponent(currentSystem.value.slug)
    if (op === 'view-to-prose') {
      const res = await $fetch<{ prose: string }>(
        `${apiBase}/v1/systems/${slug}/sync/view-to-prose`,
        { method: 'POST', body: { view_id: activeViewId.value } },
      )
      previewProse.value = res.prose
    } else if (op === 'ontology-to-prose') {
      const res = await $fetch<{ prose: string }>(
        `${apiBase}/v1/systems/${slug}/sync/ontology-to-prose`,
        { method: 'POST', body: {} },
      )
      previewProse.value = res.prose
    } else {
      const res = await $fetch<{ ontology: Ontology }>(
        `${apiBase}/v1/systems/${slug}/sync/prose-to-ontology`,
        { method: 'POST', body: {} },
      )
      previewOntology.value = res.ontology
    }
    pendingOp.value = op
  } catch (e: unknown) {
    syncError.value = e instanceof Error ? e.message : String(e)
  } finally {
    syncing.value = false
  }
}

async function applyPreview(): Promise<void> {
  if (!pendingOp.value) return
  if (pendingOp.value === 'ontology-to-prose' && previewProse.value !== null) {
    await saveProse(previewProse.value)
    setLeftTab('prose')
  } else if (pendingOp.value === 'prose-to-ontology' && previewOntology.value !== null) {
    await saveOntology(previewOntology.value)
    setLeftTab('ontology')
  }
  dismiss()
}

function dismiss(): void {
  previewProse.value    = null
  previewOntology.value = null
  pendingOp.value       = null
  syncError.value       = null
}

// Summary line for ontology preview
const ontologyPreviewSummary = computed(() => {
  if (!previewOntology.value) return ''
  const e = previewOntology.value.entities.length
  const r = previewOntology.value.relationships.length
  return `${e} entit${e !== 1 ? 'ies' : 'y'}, ${r} relationship${r !== 1 ? 's' : ''}`
})
</script>

<template>
  <div v-if="currentSystem" class="sync-bar">
    <span class="sync-bar__label">Sync</span>

    <button
      class="sync-bar__btn"
      :disabled="syncing || saving || !activeViewId"
      title="Derive prose from the current diagram (AI)"
      @click="runSync('view-to-prose')"
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      View → Prose
    </button>

    <button
      class="sync-bar__btn"
      :disabled="syncing || saving"
      title="Derive prose from ontology (AI)"
      @click="runSync('ontology-to-prose')"
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Ontology → Prose
    </button>

    <button
      class="sync-bar__btn"
      :disabled="syncing || saving"
      title="Derive ontology from prose (AI)"
      @click="runSync('prose-to-ontology')"
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M10 6H2M5 3L2 6l3 3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Prose → Ontology
    </button>

    <span v-if="syncing" class="sync-bar__spinner-wrap">
      <span class="sync-bar__spinner" />
      <span class="sync-bar__syncing-text">Syncing…</span>
    </span>

    <span v-if="syncError" class="sync-bar__error" :title="syncError">
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <circle cx="6" cy="6" r="5" stroke="currentColor" stroke-width="1.2"/>
        <path d="M6 4v2.5M6 8v.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
      </svg>
      Sync failed
      <button class="sync-bar__dismiss-x" @click="syncError = null">×</button>
    </span>
  </div>

  <!-- Preview overlay -->
  <Transition name="preview">
    <div v-if="pendingOp" class="sync-preview">
      <div class="sync-preview__inner">
        <div class="sync-preview__header">
          <span class="sync-preview__title">
            {{ pendingOp === 'prose-to-ontology' ? 'New Ontology Preview' : 'New Prose Preview' }}
          </span>
          <button class="sync-preview__close" @click="dismiss">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <!-- Prose preview -->
        <div v-if="previewProse !== null" class="sync-preview__prose">
          {{ previewProse }}
        </div>

        <!-- Ontology preview -->
        <div v-else-if="previewOntology !== null" class="sync-preview__ontology">
          <div class="sync-preview__summary">{{ ontologyPreviewSummary }}</div>
          <div class="sync-preview__entities">
            <div
              v-for="e in previewOntology.entities.slice(0, 8)"
              :key="e.id"
              class="sync-preview__entity"
            >
              <span class="sync-preview__entity-type">{{ e.type.replace('_',' ') }}</span>
              <span class="sync-preview__entity-name">{{ e.name }}</span>
              <span v-if="e.domain" class="sync-preview__entity-domain">{{ e.domain }}</span>
            </div>
            <div v-if="previewOntology.entities.length > 8" class="sync-preview__more">
              +{{ previewOntology.entities.length - 8 }} more
            </div>
          </div>
        </div>

        <div class="sync-preview__footer">
          <button class="sync-preview__dismiss" @click="dismiss">Dismiss</button>
          <button class="sync-preview__apply" :disabled="saving" @click="applyPreview">
            <span v-if="saving" class="sync-preview__spinner" />
            <template v-else>Apply</template>
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* ── Sync bar ──────────────────────────────────────────────────────── */
.sync-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  background: var(--bg-chrome);
  border-top: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.sync-bar__label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-subtle);
  margin-right: 2px;
}

.sync-bar__btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  white-space: nowrap;
}

.sync-bar__btn:hover:not(:disabled) {
  background: var(--bg-chrome-raised);
  border-color: var(--accent);
  color: var(--accent);
}

.sync-bar__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sync-bar__spinner-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-subtle);
}

.sync-bar__spinner {
  display: inline-block;
  width: 11px;
  height: 11px;
  border: 1.5px solid var(--border-chrome);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.sync-bar__syncing-text { font-size: 11px; color: var(--text-subtle); }

.sync-bar__error {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--danger);
  margin-left: 4px;
}

.sync-bar__dismiss-x {
  background: none;
  border: none;
  color: var(--danger);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0 2px;
}

/* ── Preview overlay ───────────────────────────────────────────────── */
.sync-preview {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.sync-preview__inner {
  background: var(--bg-chrome);
  border: 1px solid var(--border-chrome);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  width: min(520px, 90vw);
  display: flex;
  flex-direction: column;
  max-height: 70vh;
  overflow: hidden;
}

.sync-preview__header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.sync-preview__title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.sync-preview__close {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: color 0.1s;
}

.sync-preview__close:hover { color: var(--text-primary); }

/* Prose preview */
.sync-preview__prose {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-primary);
  white-space: pre-wrap;
}

/* Ontology preview */
.sync-preview__ontology {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.sync-preview__summary {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-subtle);
  margin-bottom: 10px;
}

.sync-preview__entities {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sync-preview__entity {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  background: var(--bg-chrome-raised);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.sync-preview__entity-type {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-width: 50px;
}

.sync-preview__entity-name {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
}

.sync-preview__entity-domain {
  font-size: 10px;
  color: var(--text-subtle);
  background: var(--bg-canvas);
  border: 1px solid var(--border-chrome);
  padding: 1px 6px;
  border-radius: 8px;
}

.sync-preview__more {
  font-size: 11px;
  color: var(--text-subtle);
  padding: 4px 8px;
  text-align: center;
}

/* Footer */
.sync-preview__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.sync-preview__dismiss {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.sync-preview__dismiss:hover {
  background: var(--bg-chrome-raised);
  color: var(--text-primary);
}

.sync-preview__apply {
  padding: 6px 20px;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s;
  display: inline-flex;
  align-items: center;
  min-width: 64px;
  justify-content: center;
}

.sync-preview__apply:hover:not(:disabled) { background: var(--accent-hover); }
.sync-preview__apply:disabled { opacity: 0.5; cursor: not-allowed; }

.sync-preview__spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* Transition */
.preview-enter-active,
.preview-leave-active {
  transition: opacity 0.18s ease;
}

.preview-enter-from,
.preview-leave-to {
  opacity: 0;
}
</style>
