<script setup lang="ts">
import ComplexityFilter from './ComplexityFilter.vue'
import ExportBar from './ExportBar.vue'
import { useDiagram } from '~/composables/useDiagram'

const { dir, loading, reset } = useDiagram()
</script>

<template>
  <div class="app-shell">
    <!-- Header -->
    <header class="app-shell__header">
      <div class="app-shell__brand">
        <span class="app-shell__logo">⬡</span>
        <span class="app-shell__title">Scheme Weaver</span>
      </div>

      <div class="app-shell__controls">
        <ComplexityFilter />
        <ExportBar />
        <button
          v-if="dir"
          class="app-shell__new-btn"
          title="Start a new diagram"
          @click="reset"
        >
          New
        </button>
      </div>
    </header>

    <!-- Loading bar -->
    <div v-if="loading" class="app-shell__progress" />

    <!-- Content slot -->
    <main class="app-shell__main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #1e2433;
}

.app-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 48px;
  background: #1e2433;
  border-bottom: 1px solid #2d3748;
  flex-shrink: 0;
  gap: 12px;
}

.app-shell__brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-shell__logo {
  font-size: 22px;
  color: #6c8ebf;
  line-height: 1;
}

.app-shell__title {
  font: 600 15px sans-serif;
  color: #e2e8f0;
  letter-spacing: 0.01em;
}

.app-shell__controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.app-shell__new-btn {
  padding: 4px 10px;
  font: 12px sans-serif;
  border: 1px solid #4a5568;
  border-radius: 4px;
  background: transparent;
  color: #a0aec0;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.app-shell__new-btn:hover {
  background: #2d3748;
  color: #e2e8f0;
}

.app-shell__progress {
  height: 2px;
  background: linear-gradient(90deg, #6c8ebf 0%, #9b59b6 50%, #6c8ebf 100%);
  background-size: 200% 100%;
  animation: progress-sweep 1.2s linear infinite;
  flex-shrink: 0;
}

@keyframes progress-sweep {
  from { background-position: 100% 0; }
  to   { background-position: -100% 0; }
}

.app-shell__main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
