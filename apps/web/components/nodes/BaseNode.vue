<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import type { NodeType, ComplexityLevel } from '~/types/dir'

interface Props {
  data: {
    label: string
    nodeType: NodeType
    description?: string
    complexity: ComplexityLevel
    visible: boolean
  }
}

const props = defineProps<Props>()

// CSS class for node type (dots become escaped in CSS but stored as data attr)
const typeClass = computed(() =>
  `sw-node-${props.data.nodeType.replace('.', '\\.')}`,
)

const complexityBadge: Record<ComplexityLevel, string> = {
  low: '',
  medium: 'M',
  high: 'H',
}
</script>

<template>
  <div
    :class="['sw-base-node', typeClass]"
    :title="data.description"
    :data-complexity="data.complexity"
    :data-node-type="data.nodeType"
  >
    <Handle type="target" :position="Position.Left" />

    <div class="sw-base-node__inner">
      <span class="sw-base-node__label">{{ data.label }}</span>
      <span class="sw-base-node__type">{{ data.nodeType }}</span>
    </div>

    <span v-if="complexityBadge[data.complexity]" class="sw-base-node__badge">
      {{ complexityBadge[data.complexity] }}
    </span>

    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<style scoped>
.sw-base-node {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--node-stroke, #aaaaaa);
  background: var(--node-fill, #f5f5f5);
  box-sizing: border-box;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07), 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.15s, filter 0.15s;
  cursor: pointer;
}

.sw-base-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08);
  filter: brightness(0.97);
}

.sw-base-node__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0 20px;
  gap: 3px;
  overflow: hidden;
}

.sw-base-node__label {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.2;
  font-family: system-ui, -apple-system, sans-serif;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.sw-base-node__type {
  font-size: 10px;
  font-family: ui-monospace, monospace;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.sw-base-node__badge {
  position: absolute;
  top: 3px;
  right: 5px;
  font-size: 9px;
  font-family: ui-monospace, monospace;
  color: #cbd5e1;
  line-height: 1;
}

/* Vue Flow handle dots */
:deep(.vue-flow__handle) {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--node-stroke, #aaaaaa);
  border: 2px solid white;
  box-shadow: 0 0 0 1px var(--node-stroke, #aaaaaa);
}
</style>
