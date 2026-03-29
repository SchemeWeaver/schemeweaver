<script setup lang="ts">
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import BaseNode from './nodes/BaseNode.vue'
import { useFlowGraph } from '~/composables/useFlowGraph'
import { useDiagram } from '~/composables/useDiagram'

const { dir, complexity } = useDiagram()
const { flowNodes, flowEdges } = useFlowGraph(dir, complexity)
const { fitView } = useVueFlow()

// fitView only when a brand-new DIR arrives (not on complexity toggle)
const prevDirVersion = ref<string | null>(null)
watch(dir, (newDir) => {
  if (!newDir) return
  const key = newDir.meta.title + ':' + newDir.nodes.length
  if (key !== prevDirVersion.value) {
    prevDirVersion.value = key
    nextTick(() => fitView({ padding: 0.12, duration: 400 }))
  }
})
</script>

<template>
  <div class="diagram-canvas">
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      :node-types="{ 'sw-node': BaseNode }"
      fit-view-on-init
      class="diagram-canvas__flow"
    >
      <Background variant="dots" :gap="20" :size="1" color="#d1d5db" />
      <Controls position="bottom-right" />
      <MiniMap
        position="bottom-left"
        :node-color="(n) => n.data?.nodeType === 'database' ? '#d4edda' : '#f0f4ff'"
      />
    </VueFlow>
  </div>
</template>

<style scoped>
.diagram-canvas {
  width: 100%;
  height: 100%;
  background: #f8f9fa;
}

.diagram-canvas__flow {
  width: 100%;
  height: 100%;
}
</style>
