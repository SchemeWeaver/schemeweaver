<script setup lang="ts">
import ProseEditor from './ProseEditor.vue'
import OntologyPanel from './OntologyPanel.vue'
import ViewBar from './ViewBar.vue'
import DiagramCanvas from './DiagramCanvas.vue'
import EmptyState from './EmptyState.vue'
import ShapePanel from './ShapePanel.vue'
import { useWorkspace } from '~/composables/useWorkspace'
import { useSystem } from '~/composables/useSystem'

const props = defineProps<{ shapesOpen: boolean }>()
const emit = defineEmits<{
  'update:shapesOpen': [value: boolean]
  'use': [prompt: string]
}>()

const { mode, leftTab, setLeftTab } = useWorkspace()
const { dir } = useSystem()

const showLeft   = computed(() => mode.value === 'split' || mode.value === 'text')
const showCanvas = computed(() => mode.value === 'canvas' || mode.value === 'split')

function useExample(prompt: string): void { emit('use', prompt) }
</script>

<template>
  <div :class="['workspace', `workspace--${mode}`]">
    <!-- Left panel -->
    <Transition name="ws-left">
      <aside v-if="showLeft" class="workspace__left">
        <!-- Tabs -->
        <div class="workspace__tabs">
          <button
            v-for="tab in (['prose', 'ontology', 'log'] as const)"
            :key="tab"
            :class="['workspace__tab', { active: leftTab === tab }]"
            @click="setLeftTab(tab)"
          >
            {{ tab.charAt(0).toUpperCase() + tab.slice(1) }}
          </button>
        </div>

        <!-- Tab content -->
        <div class="workspace__tab-content">
          <ProseEditor v-if="leftTab === 'prose'" />

          <OntologyPanel v-else-if="leftTab === 'ontology'" />

          <div v-else-if="leftTab === 'log'" class="workspace__coming-soon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" opacity="0.3">
              <rect x="4" y="4" width="20" height="20" rx="3" stroke="currentColor" stroke-width="1.5"/>
              <path d="M9 10h10M9 14h7M9 18h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <p>Action log coming soon.</p>
          </div>
        </div>
      </aside>
    </Transition>

    <!-- Canvas area -->
    <div v-if="showCanvas" class="workspace__canvas-area">
      <ViewBar />
      <div class="workspace__canvas">
        <EmptyState v-if="!dir" @use="useExample" />
        <DiagramCanvas v-else />
      </div>
    </div>

    <!-- Right: shapes panel -->
    <Transition name="ws-right">
      <ShapePanel
        v-if="shapesOpen"
        @close="emit('update:shapesOpen', false)"
      />
    </Transition>
  </div>
</template>

<style scoped>
.workspace {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Left panel ─────────────────────────────────────────────────────────── */
.workspace__left {
  display: flex;
  flex-direction: column;
  width: 320px;
  flex-shrink: 0;
  background: var(--bg-chrome);
  border-right: 1px solid var(--border-chrome);
  overflow: hidden;
}

.workspace--text .workspace__left {
  flex: 1;
  width: unset;
}

.workspace__tabs {
  display: flex;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.workspace__tab {
  flex: 1;
  padding: 0 12px;
  height: 36px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-subtle);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
}

.workspace__tab:hover {
  color: var(--text-primary);
}

.workspace__tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.workspace__tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.workspace__coming-soon {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-subtle);
  font-size: 13px;
  padding: 24px;
  text-align: center;
}

.workspace__coming-soon p { margin: 0; }

/* ── Canvas area ─────────────────────────────────────────────────────────── */
.workspace__canvas-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.workspace__canvas {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* ── Transitions ────────────────────────────────────────────────────────── */
.ws-left-enter-active,
.ws-left-leave-active {
  transition: width 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
}

.ws-left-enter-from,
.ws-left-leave-to {
  width: 0 !important;
  opacity: 0;
}

.ws-right-enter-active,
.ws-right-leave-active {
  transition: width 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
}

.ws-right-enter-from,
.ws-right-leave-to {
  width: 0 !important;
  opacity: 0;
}
</style>
