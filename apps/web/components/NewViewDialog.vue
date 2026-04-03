<script setup lang="ts">
/**
 * Dialog for creating a new scoped view from the system ontology.
 * Scope options: all entities, by domain, by tags, or manual entity selection.
 */
import type { OntologyEntity } from '~/types/system'
import { useSystem } from '~/composables/useSystem'

const emit = defineEmits<{ close: []; created: [viewId: string] }>()

const { currentSystem, loading } = useSystem()

const config  = useRuntimeConfig()
const apiBase = config.public.apiBase as string

// ── Form state ───────────────────────────────────────────────────────────────
const name        = ref('')
const description = ref('')
const scopeMode   = ref<'all' | 'domain' | 'tags' | 'entities'>('all')
const selectedDomain   = ref('')
const tagsInput        = ref('')
const selectedEntities = reactive(new Set<string>())
const creating = ref(false)
const createError = ref<string | null>(null)

// ── Derived ──────────────────────────────────────────────────────────────────
const entities = computed<OntologyEntity[]>(() => currentSystem.value?.ontology.entities ?? [])

const domains = computed(() => {
  const d = new Set<string>()
  for (const e of entities.value) if (e.domain) d.add(e.domain)
  return [...d].sort()
})

const allTags = computed(() => {
  const t = new Set<string>()
  for (const e of entities.value) e.tags.forEach(tag => t.add(tag))
  return [...t].sort()
})

function toggleEntity(id: string): void {
  selectedEntities.has(id) ? selectedEntities.delete(id) : selectedEntities.add(id)
}

// ── Create ───────────────────────────────────────────────────────────────────
async function create(): Promise<void> {
  if (!currentSystem.value || !name.value.trim()) return
  creating.value   = true
  createError.value = null

  const scope: Record<string, unknown> = {}
  if (scopeMode.value === 'domain' && selectedDomain.value) {
    scope.domain = selectedDomain.value
  } else if (scopeMode.value === 'tags') {
    scope.tags = tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  } else if (scopeMode.value === 'entities') {
    scope.entity_ids = [...selectedEntities]
  }

  try {
    const res = await $fetch<{ view_id: string }>(
      `${apiBase}/v1/systems/${encodeURIComponent(currentSystem.value.slug)}/views`,
      {
        method: 'POST',
        body: {
          name: name.value.trim(),
          description: description.value.trim() || undefined,
          scope: Object.keys(scope).length ? scope : undefined,
        },
      },
    )
    emit('created', res.view_id)
    emit('close')
  } catch (e: unknown) {
    createError.value = e instanceof Error ? e.message : String(e)
  } finally {
    creating.value = false
  }
}

// Close on Escape
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div class="nvd-overlay" @click.self="emit('close')">
      <div class="nvd-dialog" role="dialog" aria-modal="true">
        <div class="nvd-header">
          <span class="nvd-title">New View</span>
          <button class="nvd-close" @click="emit('close')">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <div class="nvd-body">
          <!-- Name -->
          <label class="nvd-field">
            <span class="nvd-label">View Name</span>
            <input
              v-model="name"
              class="nvd-input"
              placeholder="e.g. Auth Flow"
              autofocus
            />
          </label>

          <!-- Description -->
          <label class="nvd-field">
            <span class="nvd-label">Description <span class="nvd-optional">(optional)</span></span>
            <input v-model="description" class="nvd-input" placeholder="What does this view show?" />
          </label>

          <!-- Scope mode -->
          <div class="nvd-field">
            <span class="nvd-label">Scope</span>
            <div class="nvd-scope-modes">
              <label v-for="m in (['all', 'domain', 'tags', 'entities'] as const)" :key="m" class="nvd-scope-mode">
                <input v-model="scopeMode" type="radio" :value="m" />
                <span>{{ { all: 'All entities', domain: 'By domain', tags: 'By tags', entities: 'Pick entities' }[m] }}</span>
              </label>
            </div>
          </div>

          <!-- Domain picker -->
          <div v-if="scopeMode === 'domain'" class="nvd-field">
            <span class="nvd-label">Domain</span>
            <select v-model="selectedDomain" class="nvd-select">
              <option value="">— select domain —</option>
              <option v-for="d in domains" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>

          <!-- Tags input -->
          <div v-else-if="scopeMode === 'tags'" class="nvd-field">
            <span class="nvd-label">Tags <span class="nvd-optional">(comma-separated)</span></span>
            <input v-model="tagsInput" class="nvd-input" placeholder="auth, api, core" />
            <div v-if="allTags.length" class="nvd-tag-hints">
              <button
                v-for="t in allTags"
                :key="t"
                class="nvd-tag-hint"
                type="button"
                @click="tagsInput = tagsInput ? tagsInput + ', ' + t : t"
              >{{ t }}</button>
            </div>
          </div>

          <!-- Entity picker -->
          <div v-else-if="scopeMode === 'entities'" class="nvd-field">
            <span class="nvd-label">Entities <span class="nvd-optional">({{ selectedEntities.size }} selected)</span></span>
            <div class="nvd-entity-list">
              <label
                v-for="e in entities"
                :key="e.id"
                class="nvd-entity-row"
                :class="{ selected: selectedEntities.has(e.id) }"
              >
                <input
                  type="checkbox"
                  :checked="selectedEntities.has(e.id)"
                  @change="toggleEntity(e.id)"
                />
                <span class="nvd-entity-name">{{ e.name }}</span>
                <span class="nvd-entity-type">{{ e.type.replace('_', ' ') }}</span>
                <span v-if="e.domain" class="nvd-entity-domain">{{ e.domain }}</span>
              </label>
            </div>
          </div>

          <div v-if="createError" class="nvd-error">{{ createError }}</div>
        </div>

        <div class="nvd-footer">
          <button class="nvd-cancel" @click="emit('close')">Cancel</button>
          <button
            class="nvd-create"
            :disabled="!name.trim() || creating || (scopeMode === 'entities' && selectedEntities.size === 0)"
            @click="create"
          >
            <span v-if="creating" class="nvd-spinner" />
            <template v-else>Create View</template>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.nvd-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
}

.nvd-dialog {
  background: var(--bg-chrome);
  border: 1px solid var(--border-chrome);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  width: min(460px, 92vw);
  display: flex;
  flex-direction: column;
  max-height: 80vh;
  overflow: hidden;
}

.nvd-header {
  display: flex;
  align-items: center;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.nvd-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.nvd-close {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: color 0.1s;
  display: flex;
}
.nvd-close:hover { color: var(--text-primary); }

.nvd-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.nvd-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.nvd-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.nvd-optional {
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  color: var(--text-subtle);
  font-size: 10px;
}

.nvd-input,
.nvd-select {
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  padding: 6px 9px;
  outline: none;
  transition: border-color 0.12s;
  font-family: inherit;
}

.nvd-input:focus,
.nvd-select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-muted);
}

/* Scope modes */
.nvd-scope-modes {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.nvd-scope-mode {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 10px;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  transition: background 0.1s, border-color 0.1s, color 0.1s;
}

.nvd-scope-mode:has(input:checked) {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.nvd-scope-mode input { display: none; }

/* Tag hints */
.nvd-tag-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.nvd-tag-hint {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: 10px;
  color: var(--text-muted);
  cursor: pointer;
  transition: border-color 0.1s, color 0.1s;
}

.nvd-tag-hint:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* Entity picker */
.nvd-entity-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  padding: 4px;
}

.nvd-entity-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: calc(var(--radius-sm) - 2px);
  cursor: pointer;
  font-size: 12px;
  transition: background 0.1s;
}

.nvd-entity-row:hover { background: var(--bg-chrome-raised); }
.nvd-entity-row.selected { background: var(--accent-muted); }

.nvd-entity-name {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
}

.nvd-entity-type {
  font-size: 10px;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.nvd-entity-domain {
  font-size: 10px;
  color: var(--text-subtle);
  background: var(--bg-canvas);
  border: 1px solid var(--border-chrome);
  padding: 1px 5px;
  border-radius: 8px;
}

.nvd-error {
  font-size: 12px;
  color: var(--danger);
  padding: 6px 10px;
  background: rgba(220,53,69,0.08);
  border: 1px solid rgba(220,53,69,0.2);
  border-radius: var(--radius-sm);
}

/* Footer */
.nvd-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.nvd-cancel {
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
.nvd-cancel:hover { background: var(--bg-chrome-raised); color: var(--text-primary); }

.nvd-create {
  padding: 6px 18px;
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
  min-width: 100px;
  justify-content: center;
}
.nvd-create:hover:not(:disabled) { background: var(--accent-hover); }
.nvd-create:disabled { opacity: 0.45; cursor: not-allowed; }

.nvd-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
