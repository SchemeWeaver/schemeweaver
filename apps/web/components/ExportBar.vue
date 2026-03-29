<script setup lang="ts">
import { useDiagram } from '~/composables/useDiagram'
import { useExport } from '~/composables/useExport'

const { dir, svg, mermaid } = useDiagram()
const { exportSvg, exportMermaid, exportDir, copyMermaid } = useExport()

const copied = ref(false)

async function handleCopyMermaid(): Promise<void> {
  await copyMermaid(mermaid.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1800)
}
</script>

<template>
  <div v-if="dir" class="export-bar">
    <button class="export-bar__btn" title="Download SVG" @click="exportSvg(svg, dir?.meta.title)">
      SVG
    </button>
    <button class="export-bar__btn" title="Download Mermaid" @click="exportMermaid(mermaid, dir?.meta.title)">
      Mermaid
    </button>
    <button class="export-bar__btn" title="Copy Mermaid to clipboard" @click="handleCopyMermaid">
      {{ copied ? 'Copied!' : 'Copy MMD' }}
    </button>
    <button class="export-bar__btn" title="Download DIR JSON" @click="exportDir(dir!)">
      JSON
    </button>
  </div>
</template>

<style scoped>
.export-bar {
  display: flex;
  gap: 4px;
}

.export-bar__btn {
  padding: 4px 10px;
  font: 12px sans-serif;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  transition: background 0.1s;
  white-space: nowrap;
}

.export-bar__btn:hover {
  background: #f3f4f6;
}
</style>
