<script setup lang="ts">
import { useDiagram } from '~/composables/useDiagram'

const { complexity, dir } = useDiagram()
</script>

<template>
  <select v-if="dir" v-model="complexity" class="complexity-select" title="Detail level">
    <option value="low">Core</option>
    <option value="medium">Standard</option>
    <option value="high">Full detail</option>
  </select>
</template>

<style scoped>
.complexity-select {
  padding: 4px 24px 4px 9px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  background: var(--bg-chrome-raised);
  color: var(--text-muted);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath d='M2 3.5L5 6.5L8 3.5' stroke='%237a8ba8' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round' fill='none'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 7px center;
  transition: background-color 0.1s, color 0.1s, border-color 0.1s;
  white-space: nowrap;
}
.complexity-select:hover {
  background-color: var(--bg-chrome-hover);
  color: var(--text-primary);
  border-color: #3d5070;
}
.complexity-select:focus {
  outline: none;
  border-color: var(--accent);
}
.complexity-select option {
  background: var(--bg-chrome-raised);
  color: var(--text-primary);
}
</style>
