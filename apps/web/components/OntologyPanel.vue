<script setup lang="ts">
import type {
  Ontology, OntologyEntity, OntologyRelationship,
  EntityType, RelationshipType, EntityStatus,
} from '~/types/system'
import { useSystem } from '~/composables/useSystem'

const { currentSystem, saving, saveOntology } = useSystem()

// ── Local draft ─────────────────────────────────────────────────────────────
const draft = ref<Ontology>({ entities: [], relationships: [] })

watch(
  () => currentSystem.value?.ontology,
  (ont) => {
    if (ont) draft.value = JSON.parse(JSON.stringify(ont))
  },
  { immediate: true, deep: false },
)

// ── Debounced save ───────────────────────────────────────────────────────────
let _saveTimer: ReturnType<typeof setTimeout> | null = null
function scheduleSave(): void {
  if (_saveTimer) clearTimeout(_saveTimer)
  _saveTimer = setTimeout(() => saveOntology(draft.value), 700)
}

// ── Expanded rows ────────────────────────────────────────────────────────────
const expandedEntities = reactive(new Set<string>())
const expandedRels     = reactive(new Set<string>())

function toggleEntity(id: string): void {
  expandedEntities.has(id) ? expandedEntities.delete(id) : expandedEntities.add(id)
}
function toggleRel(id: string): void {
  expandedRels.has(id) ? expandedRels.delete(id) : expandedRels.add(id)
}

// ── Entity operations ────────────────────────────────────────────────────────
function addEntity(): void {
  const id = `entity-${Date.now()}`
  draft.value.entities.push({
    id, name: 'New Entity', type: 'other', status: 'active', tags: [], metadata: {},
  })
  expandedEntities.add(id)
  scheduleSave()
}

function removeEntity(id: string): void {
  draft.value.entities = draft.value.entities.filter(e => e.id !== id)
  draft.value.relationships = draft.value.relationships.filter(
    r => r.from_entity !== id && r.to_entity !== id,
  )
  expandedEntities.delete(id)
  scheduleSave()
}

function patchEntity(id: string, key: keyof OntologyEntity, value: unknown): void {
  const e = draft.value.entities.find(e => e.id === id)
  if (e) (e as Record<string, unknown>)[key] = value
  scheduleSave()
}

// ── Relationship operations ──────────────────────────────────────────────────
function addRelationship(): void {
  if (draft.value.entities.length < 2) return
  const id = `rel-${Date.now()}`
  draft.value.relationships.push({
    id,
    from_entity: draft.value.entities[0].id,
    to_entity:   draft.value.entities[1]?.id ?? draft.value.entities[0].id,
    type:        'other',
    status:      'active',
    description: '',
  })
  expandedRels.add(id)
  scheduleSave()
}

function removeRelationship(id: string): void {
  draft.value.relationships = draft.value.relationships.filter(r => r.id !== id)
  expandedRels.delete(id)
  scheduleSave()
}

function patchRel(id: string, key: keyof OntologyRelationship, value: unknown): void {
  const r = draft.value.relationships.find(r => r.id === id)
  if (r) (r as Record<string, unknown>)[key] = value
  scheduleSave()
}

// ── Display helpers ──────────────────────────────────────────────────────────
const ENTITY_TYPES: EntityType[] = [
  'service','database','queue','storage','gateway','user',
  'team','concept','data_entity','external_system','other',
]

const REL_TYPES: RelationshipType[] = [
  'calls','owns','depends_on','publishes','subscribes_to','stores_in','managed_by','other',
]

const STATUSES: EntityStatus[] = ['active','deprecated','planned']

const TYPE_COLOR: Record<EntityType, string> = {
  service:         '#5b8cd7',
  database:        '#52b788',
  queue:           '#e8a020',
  storage:         '#48cae4',
  gateway:         '#9b59b6',
  user:            '#7a8ba8',
  team:            '#f4a261',
  concept:         '#e9c46a',
  data_entity:     '#a8dadc',
  external_system: '#e63946',
  other:           '#94a3b8',
}

const TYPE_ABBR: Record<EntityType, string> = {
  service:         'SVC',
  database:        'DB',
  queue:           'Q',
  storage:         'STR',
  gateway:         'GW',
  user:            'USR',
  team:            'TEAM',
  concept:         'CON',
  data_entity:     'DAT',
  external_system: 'EXT',
  other:           '—',
}

const STATUS_COLOR: Record<EntityStatus, string> = {
  active:     'var(--success)',
  deprecated: 'var(--warn)',
  planned:    'var(--text-subtle)',
}

function entityName(id: string): string {
  return draft.value.entities.find(e => e.id === id)?.name ?? id
}
</script>

<template>
  <div class="onto-panel">
    <!-- ── Entities ────────────────────────────────────────────────── -->
    <div class="onto-panel__section-header">
      <span class="onto-panel__section-title">
        Entities
        <span class="onto-panel__count">{{ draft.entities.length }}</span>
      </span>
      <button
        class="onto-panel__add-btn"
        :disabled="!currentSystem"
        title="Add entity"
        @click="addEntity"
      >
        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
          <path d="M5.5 1v9M1 5.5h9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        Add
      </button>
    </div>

    <div v-if="!currentSystem" class="onto-panel__empty">
      Generate a system to view its ontology.
    </div>

    <ul v-else class="onto-panel__list">
      <li
        v-for="entity in draft.entities"
        :key="entity.id"
        class="onto-panel__item"
      >
        <!-- Collapsed row -->
        <div
          class="onto-panel__row"
          @click.stop="toggleEntity(entity.id)"
        >
          <span
            class="onto-panel__type-badge"
            :style="{ background: TYPE_COLOR[entity.type] + '22', color: TYPE_COLOR[entity.type] }"
          >{{ TYPE_ABBR[entity.type] }}</span>

          <input
            class="onto-panel__name-input"
            :value="entity.name"
            @click.stop
            @change="patchEntity(entity.id, 'name', ($event.target as HTMLInputElement).value)"
          />

          <span
            v-if="entity.domain"
            class="onto-panel__domain"
          >{{ entity.domain }}</span>

          <span
            class="onto-panel__status-dot"
            :title="entity.status"
            :style="{ background: STATUS_COLOR[entity.status] }"
          />

          <button
            class="onto-panel__chevron"
            :class="{ rotated: expandedEntities.has(entity.id) }"
            @click.stop="toggleEntity(entity.id)"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 4l3 3 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>

        <!-- Expanded fields -->
        <div v-if="expandedEntities.has(entity.id)" class="onto-panel__expand">
          <label class="onto-panel__field">
            <span class="onto-panel__field-label">ID</span>
            <span class="onto-panel__field-id">{{ entity.id }}</span>
          </label>

          <label class="onto-panel__field">
            <span class="onto-panel__field-label">Type</span>
            <select
              class="onto-panel__select"
              :value="entity.type"
              @change="patchEntity(entity.id, 'type', ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="t in ENTITY_TYPES" :key="t" :value="t">{{ t.replace('_', ' ') }}</option>
            </select>
          </label>

          <label class="onto-panel__field">
            <span class="onto-panel__field-label">Domain</span>
            <input
              class="onto-panel__input"
              :value="entity.domain ?? ''"
              placeholder="e.g. payments"
              @change="patchEntity(entity.id, 'domain', ($event.target as HTMLInputElement).value || undefined)"
            />
          </label>

          <label class="onto-panel__field">
            <span class="onto-panel__field-label">Status</span>
            <select
              class="onto-panel__select"
              :value="entity.status"
              @change="patchEntity(entity.id, 'status', ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
            </select>
          </label>

          <label class="onto-panel__field onto-panel__field--full">
            <span class="onto-panel__field-label">Description</span>
            <textarea
              class="onto-panel__textarea"
              :value="entity.description ?? ''"
              rows="2"
              placeholder="What does this entity do?"
              @change="patchEntity(entity.id, 'description', ($event.target as HTMLTextAreaElement).value || undefined)"
            />
          </label>

          <label class="onto-panel__field onto-panel__field--full">
            <span class="onto-panel__field-label">Tags</span>
            <input
              class="onto-panel__input"
              :value="entity.tags.join(', ')"
              placeholder="tag1, tag2"
              @change="patchEntity(entity.id, 'tags', ($event.target as HTMLInputElement).value.split(',').map(t => t.trim()).filter(Boolean))"
            />
          </label>

          <div class="onto-panel__actions">
            <button
              class="onto-panel__delete-btn"
              @click="removeEntity(entity.id)"
            >
              <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                <path d="M1.5 1.5l8 8M9.5 1.5l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              Remove entity
            </button>
          </div>
        </div>
      </li>
    </ul>

    <!-- ── Relationships ──────────────────────────────────────────── -->
    <div class="onto-panel__section-header onto-panel__section-header--rel">
      <span class="onto-panel__section-title">
        Relationships
        <span class="onto-panel__count">{{ draft.relationships.length }}</span>
      </span>
      <button
        class="onto-panel__add-btn"
        :disabled="!currentSystem || draft.entities.length < 2"
        :title="draft.entities.length < 2 ? 'Need at least 2 entities' : 'Add relationship'"
        @click="addRelationship"
      >
        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
          <path d="M5.5 1v9M1 5.5h9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        Add
      </button>
    </div>

    <ul v-if="currentSystem" class="onto-panel__list onto-panel__list--rel">
      <li
        v-for="rel in draft.relationships"
        :key="rel.id"
        class="onto-panel__item"
      >
        <!-- Collapsed row -->
        <div class="onto-panel__row" @click.stop="toggleRel(rel.id)">
          <span class="onto-panel__rel-from">{{ entityName(rel.from_entity) }}</span>
          <span class="onto-panel__rel-type">{{ rel.type.replace('_', ' ') }}</span>
          <span class="onto-panel__rel-to">{{ entityName(rel.to_entity) }}</span>

          <button
            class="onto-panel__chevron"
            :class="{ rotated: expandedRels.has(rel.id) }"
            @click.stop="toggleRel(rel.id)"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 4l3 3 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>

        <!-- Expanded fields -->
        <div v-if="expandedRels.has(rel.id)" class="onto-panel__expand">
          <label class="onto-panel__field">
            <span class="onto-panel__field-label">From</span>
            <select
              class="onto-panel__select"
              :value="rel.from_entity"
              @change="patchRel(rel.id, 'from_entity', ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="e in draft.entities" :key="e.id" :value="e.id">{{ e.name }}</option>
            </select>
          </label>

          <label class="onto-panel__field">
            <span class="onto-panel__field-label">Type</span>
            <select
              class="onto-panel__select"
              :value="rel.type"
              @change="patchRel(rel.id, 'type', ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="t in REL_TYPES" :key="t" :value="t">{{ t.replace('_', ' ') }}</option>
            </select>
          </label>

          <label class="onto-panel__field">
            <span class="onto-panel__field-label">To</span>
            <select
              class="onto-panel__select"
              :value="rel.to_entity"
              @change="patchRel(rel.id, 'to_entity', ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="e in draft.entities" :key="e.id" :value="e.id">{{ e.name }}</option>
            </select>
          </label>

          <label class="onto-panel__field onto-panel__field--full">
            <span class="onto-panel__field-label">Description</span>
            <input
              class="onto-panel__input"
              :value="rel.description ?? ''"
              placeholder="What does this relationship represent?"
              @change="patchRel(rel.id, 'description', ($event.target as HTMLInputElement).value || undefined)"
            />
          </label>

          <div class="onto-panel__actions">
            <button class="onto-panel__delete-btn" @click="removeRelationship(rel.id)">
              <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                <path d="M1.5 1.5l8 8M9.5 1.5l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              Remove relationship
            </button>
          </div>
        </div>
      </li>
    </ul>

    <!-- Saving indicator -->
    <div v-if="saving" class="onto-panel__saving">
      <span class="onto-panel__saving-spinner" />
      Saving…
    </div>
  </div>
</template>

<style scoped>
.onto-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

/* ── Section header ──────────────────────────────────────────────── */
.onto-panel__section-header {
  display: flex;
  align-items: center;
  padding: 8px 14px 6px;
  position: sticky;
  top: 0;
  background: var(--bg-chrome);
  z-index: 1;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.onto-panel__section-header--rel {
  border-top: 1px solid var(--border-chrome);
  margin-top: 2px;
}

.onto-panel__section-title {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  display: flex;
  align-items: center;
  gap: 6px;
}

.onto-panel__count {
  font-size: 10px;
  font-weight: 500;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: 8px;
  padding: 1px 6px;
  color: var(--text-muted);
}

.onto-panel__add-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 500;
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.1s, color 0.1s, border-color 0.1s;
  white-space: nowrap;
}

.onto-panel__add-btn:hover:not(:disabled) {
  background: var(--bg-chrome-raised);
  border-color: var(--accent);
  color: var(--accent);
}

.onto-panel__add-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── List ────────────────────────────────────────────────────────── */
.onto-panel__list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
}

.onto-panel__item {
  border-bottom: 1px solid var(--border-chrome);
}

.onto-panel__item:last-child {
  border-bottom: none;
}

/* ── Collapsed row ───────────────────────────────────────────────── */
.onto-panel__row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 12px 7px 10px;
  cursor: pointer;
  transition: background 0.1s;
}

.onto-panel__row:hover {
  background: var(--bg-chrome-raised);
}

.onto-panel__type-badge {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 5px;
  border-radius: 4px;
  flex-shrink: 0;
  min-width: 30px;
  text-align: center;
}

.onto-panel__name-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  padding: 1px 3px;
  border-radius: 3px;
  outline: none;
  cursor: text;
  min-width: 0;
}

.onto-panel__name-input:hover {
  background: var(--bg-chrome-hover);
}

.onto-panel__name-input:focus {
  background: var(--bg-chrome-hover);
  box-shadow: 0 0 0 1px var(--accent);
}

.onto-panel__domain {
  font-size: 10px;
  color: var(--text-subtle);
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  padding: 1px 6px;
  border-radius: 8px;
  white-space: nowrap;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.onto-panel__status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.onto-panel__chevron {
  background: none;
  border: none;
  padding: 0;
  color: var(--text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  transition: transform 0.15s;
}

.onto-panel__chevron.rotated {
  transform: rotate(180deg);
}

/* ── Expanded fields ─────────────────────────────────────────────── */
.onto-panel__expand {
  padding: 8px 12px 10px;
  background: var(--bg-canvas);
  border-top: 1px solid var(--border-chrome);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.onto-panel__field {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.onto-panel__field--full {
  grid-column: 1 / -1;
}

.onto-panel__field-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.onto-panel__field-id {
  font-size: 11px;
  font-family: ui-monospace, monospace;
  color: var(--text-muted);
  padding: 3px 0;
}

.onto-panel__input,
.onto-panel__select,
.onto-panel__textarea {
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 12px;
  padding: 4px 7px;
  outline: none;
  transition: border-color 0.12s;
  font-family: inherit;
}

.onto-panel__textarea {
  resize: none;
  line-height: 1.5;
}

.onto-panel__input:focus,
.onto-panel__select:focus,
.onto-panel__textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-muted);
}

.onto-panel__actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  padding-top: 2px;
}

.onto-panel__delete-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 500;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-subtle);
  cursor: pointer;
  transition: color 0.1s, border-color 0.1s, background 0.1s;
}

.onto-panel__delete-btn:hover {
  color: var(--danger);
  border-color: var(--danger);
  background: rgba(220, 53, 69, 0.06);
}

/* ── Relationship row ────────────────────────────────────────────── */
.onto-panel__rel-from,
.onto-panel__rel-to {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.onto-panel__rel-type {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-subtle);
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  padding: 1px 6px;
  border-radius: 8px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── Empty ───────────────────────────────────────────────────────── */
.onto-panel__empty {
  padding: 24px 16px;
  font-size: 13px;
  color: var(--text-subtle);
  text-align: center;
}

/* ── Saving indicator ────────────────────────────────────────────── */
.onto-panel__saving {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--bg-chrome);
  border-top: 1px solid var(--border-chrome);
  font-size: 11px;
  color: var(--text-subtle);
}

.onto-panel__saving-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1.5px solid var(--border-chrome);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
