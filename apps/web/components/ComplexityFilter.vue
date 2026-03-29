<script setup lang="ts">
import { useDiagram } from '~/composables/useDiagram'
import type { ComplexityLevel } from '~/types/dir'

const { complexity, dir } = useDiagram()

const levels: { value: ComplexityLevel; label: string; title: string }[] = [
  { value: 'low',    label: 'Core',     title: 'Core services only' },
  { value: 'medium', label: 'Standard', title: 'Core + supporting infra' },
  { value: 'high',   label: 'Full',     title: 'All detail' },
]
</script>

<template>
  <div v-if="dir" class="complexity-filter">
    <span class="complexity-filter__label">Detail</span>
    <div class="complexity-filter__group">
      <button
        v-for="level in levels"
        :key="level.value"
        :class="['complexity-filter__btn', { active: complexity === level.value }]"
        :title="level.title"
        @click="complexity = level.value"
      >
        {{ level.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.complexity-filter {
  display: flex;
  align-items: center;
  gap: 8px;
}

.complexity-filter__label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.complexity-filter__group {
  display: flex;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 1px;
}

.complexity-filter__btn {
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 500;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  white-space: nowrap;
}

.complexity-filter__btn:hover:not(.active) {
  background: var(--bg-chrome-hover);
  color: var(--text-primary);
}

.complexity-filter__btn.active {
  background: var(--accent);
  color: #fff;
}
</style>
