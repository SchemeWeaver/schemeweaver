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
  border-radius: 6px;
  border: 1.5px solid var(--node-stroke, #aaaaaa);
  background: var(--node-fill, #f5f5f5);
  box-sizing: border-box;
  transition: filter 0.15s;
  cursor: pointer;
}

.sw-base-node:hover {
  filter: brightness(0.93);
}

.sw-base-node__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0 20px;
  gap: 2px;
  overflow: hidden;
}

.sw-base-node__label {
  font: 600 13px/1.2 sans-serif;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.sw-base-node__type {
  font: 10px/1 monospace;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.sw-base-node__badge {
  position: absolute;
  top: 2px;
  right: 4px;
  font: 9px monospace;
  color: #aaa;
  line-height: 1;
}

/* Override Vue Flow handle styles */
:deep(.vue-flow__handle) {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--node-stroke, #aaaaaa);
  border: none;
}
</style>
