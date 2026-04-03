<script setup lang="ts">
import { useSystem } from '~/composables/useSystem'
import { useExport } from '~/composables/useExport'

const { dir, svg, mermaid } = useSystem()
const { exportSvg, exportMermaid, exportDir, copyMermaid } = useExport()

const root   = ref<HTMLElement>()
const open   = ref(false)
const copied = ref(false)

function close() { open.value = false }
function toggle() { open.value = !open.value }

function onDocPointerDown(e: PointerEvent) {
  if (!root.value?.contains(e.target as Node)) close()
}
onMounted(() => document.addEventListener('pointerdown', onDocPointerDown, { capture: true }))
onUnmounted(() => document.removeEventListener('pointerdown', onDocPointerDown, { capture: true }))

function doExportSvg() { exportSvg(svg.value, dir.value?.meta.title); close() }
function doExportMermaid() { exportMermaid(mermaid.value, dir.value?.meta.title); close() }
function doExportDir() { exportDir(dir.value!); close() }

async function doCopyMermaid() {
  await copyMermaid(mermaid.value)
  copied.value = true
  close()
  setTimeout(() => { copied.value = false }, 1800)
}
</script>

<template>
  <div v-if="dir" ref="root" class="export-dd">
    <button
      :class="['export-dd__trigger', { 'export-dd__trigger--open': open }]"
      @click="toggle"
    >
      Export
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" class="export-dd__chevron">
        <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div v-if="open" class="export-dd__panel">
      <button class="export-dd__item" @click="doExportSvg">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><rect x="1" y="1" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.2"/><path d="M4 6.5h5M6.5 4v5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
        Download SVG
      </button>
      <button class="export-dd__item" @click="doExportMermaid">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2 2h9M2 5h6M2 8h7M2 11h4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
        Download Mermaid
      </button>
      <button :class="['export-dd__item', { 'export-dd__item--copied': copied }]" @click="doCopyMermaid">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><rect x="4" y="1" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.2"/><path d="M1 4.5V11a1 1 0 001 1h6.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
        {{ copied ? 'Copied!' : 'Copy Mermaid' }}
      </button>
      <div class="export-dd__divider" />
      <button class="export-dd__item" @click="doExportDir">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2 2.5A1.5 1.5 0 013.5 1h3L8 2.5H11A1.5 1.5 0 0112.5 4v6A1.5 1.5 0 0111 11.5H2A1.5 1.5 0 01.5 10V4A1.5 1.5 0 012 2.5z" stroke="currentColor" stroke-width="1.2"/></svg>
        Download DIR JSON
      </button>
    </div>
  </div>
</template>

<style scoped>
.export-dd {
  position: relative;
}

.export-dd__trigger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  background: var(--bg-chrome-raised);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.1s, color 0.1s, border-color 0.1s;
  white-space: nowrap;
}
.export-dd__trigger:hover,
.export-dd__trigger--open {
  background: var(--bg-chrome-hover);
  color: var(--text-primary);
  border-color: #3d5070;
}

.export-dd__chevron {
  transition: transform 0.15s;
}
.export-dd__trigger--open .export-dd__chevron {
  transform: rotate(180deg);
}

.export-dd__panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 160px;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
  padding: 4px;
  z-index: 200;
}

.export-dd__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 500;
  text-align: left;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  white-space: nowrap;
}
.export-dd__item:hover {
  background: var(--bg-chrome-hover);
  color: var(--text-primary);
}
.export-dd__item--copied {
  color: var(--success);
}

.export-dd__divider {
  height: 1px;
  background: var(--border-chrome);
  margin: 4px 0;
}
</style>
