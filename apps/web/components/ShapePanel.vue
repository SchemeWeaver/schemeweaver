<script setup lang="ts">
import { shapeKind, labelY, typeTextY, nodeColor } from '~/utils/nodeShapes'

const emit = defineEmits<{ close: [] }>()

// ── Shape catalogue ────────────────────────────────────────────────────────
const SHAPES = [
  {
    category: 'General',
    items: [
      { nodeType: 'user',    label: 'User' },
      { nodeType: 'service', label: 'Service' },
      { nodeType: 'gateway', label: 'Gateway' },
      { nodeType: 'generic', label: 'Generic' },
    ],
  },
  {
    category: 'Storage',
    items: [
      { nodeType: 'database', label: 'Database' },
      { nodeType: 'queue',    label: 'Queue' },
      { nodeType: 'storage',  label: 'Storage' },
    ],
  },
  {
    category: 'AWS',
    items: [
      { nodeType: 'aws.lambda',      label: 'Lambda' },
      { nodeType: 'aws.s3',          label: 'S3' },
      { nodeType: 'aws.rds',         label: 'RDS' },
      { nodeType: 'aws.ec2',         label: 'EC2' },
      { nodeType: 'aws.elasticache', label: 'ElastiCache' },
      { nodeType: 'aws.api_gateway', label: 'API Gateway' },
    ],
  },
]

function onDragStart(e: DragEvent, item: { nodeType: string; label: string }) {
  e.dataTransfer!.setData('application/x-sw-shape', JSON.stringify(item))
  e.dataTransfer!.effectAllowed = 'copy'
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

    <div class="shapes__body">
      <div v-for="group in SHAPES" :key="group.category" class="shapes__group">
        <div class="shapes__group-label">{{ group.category }}</div>
        <div class="shapes__grid">
          <div
            v-for="item in group.items"
            :key="item.nodeType"
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
                :fill="nodeColor(item.nodeType).fill"
                :stroke="nodeColor(item.nodeType).stroke"
                stroke-width="1.5"
              />

              <!-- Diamond: gateway -->
              <path
                v-else-if="shapeKind(item.nodeType) === 'diamond'"
                d="M 80 2 L 158 30 L 80 58 L 2 30 Z"
                :fill="nodeColor(item.nodeType).fill"
                :stroke="nodeColor(item.nodeType).stroke"
                stroke-width="1.5"
              />

              <!-- Cylinder: database, storage, aws.rds/s3/elasticache -->
              <template v-else-if="shapeKind(item.nodeType) === 'cylinder'">
                <path d="M 2 12 L 2 54 A 78 11 0 0 0 158 54 L 158 12 Z" :fill="nodeColor(item.nodeType).fill" stroke="none"/>
                <ellipse cx="80" cy="12" rx="78" ry="11" :fill="nodeColor(item.nodeType).fill" stroke="none"/>
                <ellipse cx="80" cy="12" rx="78" ry="11" fill="rgba(0,0,0,0.07)" stroke="none"/>
                <line x1="2" y1="12" x2="2" y2="54" :stroke="nodeColor(item.nodeType).stroke" stroke-width="1.5"/>
                <line x1="158" y1="12" x2="158" y2="54" :stroke="nodeColor(item.nodeType).stroke" stroke-width="1.5"/>
                <path d="M 2 54 A 78 11 0 0 0 158 54" fill="none" :stroke="nodeColor(item.nodeType).stroke" stroke-width="1.5"/>
                <path d="M 2 12 A 78 11 0 0 1 158 12" fill="none" :stroke="nodeColor(item.nodeType).stroke" stroke-width="1.5"/>
              </template>

              <!-- Parallelogram: queue -->
              <path
                v-else-if="shapeKind(item.nodeType) === 'parallelogram'"
                d="M 14 2 L 158 2 L 146 58 L 2 58 Z"
                :fill="nodeColor(item.nodeType).fill"
                :stroke="nodeColor(item.nodeType).stroke"
                stroke-width="1.5"
                stroke-linejoin="round"
              />

              <!-- Plain rect: generic, aws.ec2 -->
              <rect
                v-else-if="shapeKind(item.nodeType) === 'rect'"
                x="1" y="1" width="158" height="58" rx="3"
                :fill="nodeColor(item.nodeType).fill"
                :stroke="nodeColor(item.nodeType).stroke"
                stroke-width="1.5"
              />

              <!-- Rounded rect (default): service, aws.lambda -->
              <rect
                v-else
                x="1" y="1" width="158" height="58" rx="9"
                :fill="nodeColor(item.nodeType).fill"
                :stroke="nodeColor(item.nodeType).stroke"
                stroke-width="1.5"
              />

              <!-- Label -->
              <text
                x="80"
                :y="labelY(item.nodeType)"
                dominant-baseline="middle"
                text-anchor="middle"
                class="preview-label"
              >{{ item.label }}</text>

              <!-- Type -->
              <text
                x="80"
                :y="typeTextY(item.nodeType)"
                text-anchor="middle"
                class="preview-type"
              >{{ item.nodeType }}</text>

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
