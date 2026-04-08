<script setup lang="ts">
import { ref } from 'vue'
import { shapeKind, labelY, typeTextY, nodeColor } from '~/utils/nodeShapes'
import { VENDOR_BADGES, getTechIcon } from '~/utils/iconRegistry'

const emit = defineEmits<{ close: [] }>()

// ── Types ──────────────────────────────────────────────────────────────────

interface ShapeItem {
  nodeType: string
  label: string
  vendor?: string
  technology?: string
}

// ── Shape catalogue ────────────────────────────────────────────────────────

const GENERIC_CATALOGUE: { category: string; items: ShapeItem[] }[] = [
  {
    category: 'Compute',
    items: [
      { nodeType: 'user',    label: 'User' },
      { nodeType: 'service', label: 'Service' },
      { nodeType: 'api',     label: 'API' },
      { nodeType: 'gateway', label: 'Gateway' },
      { nodeType: 'generic', label: 'Generic' },
    ],
  },
  {
    category: 'Storage',
    items: [
      { nodeType: 'database',       label: 'Database' },
      { nodeType: 'document-store', label: 'Doc Store' },
      { nodeType: 'file-store',     label: 'File Store' },
      { nodeType: 'cache',          label: 'Cache' },
      { nodeType: 'search',         label: 'Search' },
    ],
  },
  {
    category: 'Messaging',
    items: [
      { nodeType: 'queue',  label: 'Queue' },
      { nodeType: 'stream', label: 'Stream' },
    ],
  },
  {
    category: 'Infrastructure',
    items: [
      { nodeType: 'cdn',     label: 'CDN' },
      { nodeType: 'auth',    label: 'Auth' },
      { nodeType: 'monitor', label: 'Monitor' },
    ],
  },
]

const VENDOR_CATALOGUE: Record<string, { category: string; items: ShapeItem[] }[]> = {
  aws: [
    {
      category: 'Compute',
      items: [
        { nodeType: 'service', label: 'Lambda',      vendor: 'aws', technology: 'lambda' },
        { nodeType: 'service', label: 'EC2',         vendor: 'aws', technology: 'ec2' },
        { nodeType: 'gateway', label: 'API Gateway', vendor: 'aws', technology: 'api-gateway' },
      ],
    },
    {
      category: 'Storage & Data',
      items: [
        { nodeType: 'database',   label: 'RDS',         vendor: 'aws', technology: 'rds' },
        { nodeType: 'file-store', label: 'S3',           vendor: 'aws', technology: 's3' },
        { nodeType: 'cache',      label: 'ElastiCache',  vendor: 'aws', technology: 'elasticache' },
        { nodeType: 'queue',      label: 'SQS',          vendor: 'aws', technology: 'sqs' },
        { nodeType: 'stream',     label: 'Kinesis',      vendor: 'aws', technology: 'kinesis' },
      ],
    },
    {
      category: 'Networking',
      items: [
        { nodeType: 'cdn',  label: 'CloudFront', vendor: 'aws', technology: 'cloudfront' },
        { nodeType: 'auth', label: 'Cognito',    vendor: 'aws', technology: 'cognito' },
      ],
    },
  ],
  azure: [
    {
      category: 'Compute',
      items: [
        { nodeType: 'service', label: 'Functions',   vendor: 'azure', technology: 'functions' },
        { nodeType: 'service', label: 'App Service', vendor: 'azure', technology: 'app-service' },
        { nodeType: 'gateway', label: 'API Mgmt',    vendor: 'azure', technology: 'api-management' },
      ],
    },
    {
      category: 'Storage & Data',
      items: [
        { nodeType: 'database',       label: 'SQL DB',     vendor: 'azure', technology: 'sql-database' },
        { nodeType: 'document-store', label: 'Cosmos DB',  vendor: 'azure', technology: 'cosmos-db' },
        { nodeType: 'file-store',     label: 'Blob',        vendor: 'azure', technology: 'blob-storage' },
        { nodeType: 'cache',          label: 'Redis Cache', vendor: 'azure', technology: 'cache-for-redis' },
        { nodeType: 'stream',         label: 'Event Hub',   vendor: 'azure', technology: 'event-hub' },
      ],
    },
  ],
  gcp: [
    {
      category: 'Compute',
      items: [
        { nodeType: 'service', label: 'Cloud Run',   vendor: 'gcp', technology: 'cloud-run' },
        { nodeType: 'service', label: 'Functions',   vendor: 'gcp', technology: 'cloud-functions' },
        { nodeType: 'gateway', label: 'Apigee',      vendor: 'gcp', technology: 'apigee' },
      ],
    },
    {
      category: 'Storage & Data',
      items: [
        { nodeType: 'database',   label: 'Cloud SQL',  vendor: 'gcp', technology: 'cloud-sql' },
        { nodeType: 'file-store', label: 'GCS',         vendor: 'gcp', technology: 'cloud-storage' },
        { nodeType: 'cache',      label: 'Memorystore', vendor: 'gcp', technology: 'memorystore' },
        { nodeType: 'stream',     label: 'Pub/Sub',     vendor: 'gcp', technology: 'pubsub' },
      ],
    },
  ],
}

// ── Active filter ──────────────────────────────────────────────────────────

type Filter = 'generic' | 'aws' | 'azure' | 'gcp'
const activeFilter = ref<Filter>('generic')

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'generic',    label: 'Generic' },
  { id: 'aws',        label: 'AWS' },
  { id: 'azure',      label: 'Azure' },
  { id: 'gcp',        label: 'GCP' },
]

const catalogue = computed(() =>
  activeFilter.value === 'generic'
    ? GENERIC_CATALOGUE
    : (VENDOR_CATALOGUE[activeFilter.value] ?? [])
)

// ── Drag & drop ────────────────────────────────────────────────────────────

function onDragStart(e: DragEvent, item: ShapeItem) {
  e.dataTransfer!.setData('application/x-sw-shape', JSON.stringify(item))
  e.dataTransfer!.effectAllowed = 'copy'
}

// ── Helpers ────────────────────────────────────────────────────────────────

function activeBadge(item: ShapeItem) {
  return item.vendor ? VENDOR_BADGES[item.vendor] : null
}

function activeTechIcon(item: ShapeItem) {
  return item.technology ? getTechIcon(item.technology) : null
}

function typeLabel(item: ShapeItem): string {
  if (item.technology) return item.technology
  if (item.vendor) return `${item.vendor} · ${item.nodeType}`
  return item.nodeType
}
</script>

<template>
  <aside class="shapes">
    <div class="shapes__header">
      <span class="shapes__title">Shapes</span>
      <button class="shapes__close" title="Close" @click="emit('close')">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- Vendor filter tabs -->
    <div class="shapes__filters">
      <button
        v-for="f in FILTERS"
        :key="f.id"
        :class="['filter-btn', { 'filter-btn--active': activeFilter === f.id }]"
        @click="activeFilter = f.id"
      >{{ f.label }}</button>
    </div>

    <div class="shapes__body">
      <div v-for="group in catalogue" :key="group.category" class="shapes__group">
        <div class="shapes__group-label">{{ group.category }}</div>
        <div class="shapes__grid">
          <div
            v-for="item in group.items"
            :key="`${item.nodeType}-${item.technology ?? ''}`"
            class="shapes__item"
            draggable="true"
            :title="`Drag to add ${item.label} node`"
            @dragstart="onDragStart($event, item)"
          >
            <!--
              Preview SVG uses viewBox="0 0 160 60" so all shape paths
              defined at canvas scale render correctly at any display size.
            -->
            <svg viewBox="0 0 160 60" class="shapes__preview" xmlns="http://www.w3.org/2000/svg">

              <!-- Ellipse: user -->
              <ellipse
                v-if="shapeKind(item.nodeType) === 'ellipse'"
                cx="80" cy="30" rx="79" ry="29"
                :fill="nodeColor(item.nodeType, item.vendor).fill"
                :stroke="nodeColor(item.nodeType, item.vendor).stroke"
                stroke-width="1.5"
              />

              <!-- Diamond: gateway -->
              <path
                v-else-if="shapeKind(item.nodeType) === 'diamond'"
                d="M 80 2 L 158 30 L 80 58 L 2 30 Z"
                :fill="nodeColor(item.nodeType, item.vendor).fill"
                :stroke="nodeColor(item.nodeType, item.vendor).stroke"
                stroke-width="1.5"
              />

              <!-- Cylinder: database, file-store, cache, search, document-store -->
              <template v-else-if="shapeKind(item.nodeType) === 'cylinder'">
                <path d="M 2 12 L 2 54 A 78 11 0 0 0 158 54 L 158 12 Z" :fill="nodeColor(item.nodeType, item.vendor).fill" stroke="none"/>
                <ellipse cx="80" cy="12" rx="78" ry="11" :fill="nodeColor(item.nodeType, item.vendor).fill" stroke="none"/>
                <ellipse cx="80" cy="12" rx="78" ry="11" fill="rgba(0,0,0,0.07)" stroke="none"/>
                <line x1="2" y1="12" x2="2" y2="54" :stroke="nodeColor(item.nodeType, item.vendor).stroke" stroke-width="1.5"/>
                <line x1="158" y1="12" x2="158" y2="54" :stroke="nodeColor(item.nodeType, item.vendor).stroke" stroke-width="1.5"/>
                <path d="M 2 54 A 78 11 0 0 0 158 54" fill="none" :stroke="nodeColor(item.nodeType, item.vendor).stroke" stroke-width="1.5"/>
                <path d="M 2 12 A 78 11 0 0 1 158 12" fill="none" :stroke="nodeColor(item.nodeType, item.vendor).stroke" stroke-width="1.5"/>
              </template>

              <!-- Parallelogram: queue, stream -->
              <path
                v-else-if="shapeKind(item.nodeType) === 'parallelogram'"
                d="M 14 2 L 158 2 L 146 58 L 2 58 Z"
                :fill="nodeColor(item.nodeType, item.vendor).fill"
                :stroke="nodeColor(item.nodeType, item.vendor).stroke"
                stroke-width="1.5"
                stroke-linejoin="round"
              />

              <!-- Plain rect: generic -->
              <rect
                v-else-if="shapeKind(item.nodeType) === 'rect'"
                x="1" y="1" width="158" height="58" rx="3"
                :fill="nodeColor(item.nodeType, item.vendor).fill"
                :stroke="nodeColor(item.nodeType, item.vendor).stroke"
                stroke-width="1.5"
              />

              <!-- Rounded rect (default): service, api, cdn, auth, monitor -->
              <rect
                v-else
                x="1" y="1" width="158" height="58" rx="9"
                :fill="nodeColor(item.nodeType, item.vendor).fill"
                :stroke="nodeColor(item.nodeType, item.vendor).stroke"
                stroke-width="1.5"
              />

              <!-- Technology glyph (centered, muted) -->
              <g
                v-if="activeTechIcon(item)"
                :transform="`translate(${160 / 2 - 9}, 3) scale(0.75)`"
                opacity="0.2"
                pointer-events="none"
              >
                <path :d="activeTechIcon(item)!.path" :fill="activeTechIcon(item)!.fill"/>
              </g>

              <!-- Label -->
              <text
                x="80"
                :y="labelY(item.nodeType)"
                dominant-baseline="middle"
                text-anchor="middle"
                class="preview-label"
              >{{ item.label }}</text>

              <!-- Type hint -->
              <text
                x="80"
                :y="typeTextY(item.nodeType)"
                text-anchor="middle"
                class="preview-type"
              >{{ typeLabel(item) }}</text>

              <!-- Vendor badge (top-right) -->
              <g
                v-if="activeBadge(item)"
                transform="translate(140, 2)"
                pointer-events="none"
              >
                <circle cx="9" cy="9" r="9" :fill="activeBadge(item)!.fill"/>
                <g
                  v-if="activeBadge(item)!.iconPath"
                  :transform="`translate(${9 - 9 * 0.75}, ${9 - 9 * 0.75}) scale(0.75)`"
                >
                  <path :d="activeBadge(item)!.iconPath" :fill="activeBadge(item)!.textColor"/>
                </g>
                <text
                  v-else
                  x="9" y="9"
                  dominant-baseline="middle"
                  text-anchor="middle"
                  :fill="activeBadge(item)!.textColor"
                  style="font: bold 5px system-ui, sans-serif;"
                >{{ activeBadge(item)!.label }}</text>
              </g>

            </svg>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.shapes {
  width: 220px;
  height: 100%;
  background: var(--bg-chrome);
  border-left: 1px solid var(--border-chrome);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

/* ── Header ────────────────────────────────────────────────────────────── */
.shapes__header {
  display: flex;
  align-items: center;
  padding: 0 12px;
  height: 40px;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.shapes__title {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.shapes__close {
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
.shapes__close:hover {
  background: var(--bg-chrome-hover);
  color: var(--text-primary);
}

/* ── Vendor filter tabs ────────────────────────────────────────────────── */
.shapes__filters {
  display: flex;
  gap: 4px;
  padding: 8px 10px 4px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.filter-btn {
  flex: 1;
  min-width: 0;
  padding: 3px 6px;
  font-size: 10px;
  font-weight: 600;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  background: none;
  color: var(--text-subtle);
  cursor: pointer;
  transition: background 0.1s, color 0.1s, border-color 0.1s;
  white-space: nowrap;
}
.filter-btn:hover {
  background: var(--bg-chrome-hover);
  color: var(--text-primary);
}
.filter-btn--active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

/* ── Body ──────────────────────────────────────────────────────────────── */
.shapes__body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.shapes__group-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
  padding-left: 2px;
}

.shapes__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

/* ── Shape item ────────────────────────────────────────────────────────── */
.shapes__item {
  border-radius: var(--radius-sm);
  cursor: grab;
  transition: transform 0.1s, box-shadow 0.1s;
  user-select: none;
  -webkit-user-drag: element;
}
.shapes__item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.22);
}
.shapes__item:active { cursor: grabbing; transform: scale(0.97); }

.shapes__preview {
  width: 100%;
  height: auto;
  display: block;
  border-radius: var(--radius-sm);
}

.preview-label {
  font: 600 13px system-ui, sans-serif;
  fill: #1e293b;
  pointer-events: none;
}
.preview-type {
  font: 10px monospace;
  fill: #8898aa;
  pointer-events: none;
}
</style>
