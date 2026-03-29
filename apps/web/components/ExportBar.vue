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
    <span class="export-bar__label">Export</span>
    <button class="export-bar__btn" title="Download SVG" @click="exportSvg(svg, dir?.meta.title)">
      SVG
    </button>
    <button class="export-bar__btn" title="Download Mermaid (.mmd)" @click="exportMermaid(mermaid, dir?.meta.title)">
      Mermaid
    </button>
    <button
      :class="['export-bar__btn', { 'export-bar__btn--copied': copied }]"
      title="Copy Mermaid to clipboard"
      @click="handleCopyMermaid"
    >
      {{ copied ? '✓ Copied' : 'Copy MMD' }}
    </button>
    <button class="export-bar__btn" title="Download DIR JSON" @click="exportDir(dir!)">
      JSON
    </button>
  </div>
</template>

<style scoped>
.export-bar {
  display: flex;
  align-items: center;
  gap: 3px;
}

.export-bar__label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 4px;
  white-space: nowrap;
}

.export-bar__btn {
  padding: 4px 9px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  background: var(--bg-chrome-raised);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.1s, color 0.1s, border-color 0.1s;
  white-space: nowrap;
}

.export-bar__btn:hover {
  background: var(--bg-chrome-hover);
  color: var(--text-primary);
  border-color: #3d5070;
}

.export-bar__btn--copied {
  color: var(--success);
  border-color: var(--success);
  background: rgba(82, 183, 136, 0.1);
}
</style>
