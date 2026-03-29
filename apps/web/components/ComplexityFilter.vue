<script setup lang="ts">
import { useDiagram } from '~/composables/useDiagram'
import type { ComplexityLevel } from '~/types/dir'

const { complexity, dir } = useDiagram()

const levels: { value: ComplexityLevel; label: string; title: string }[] = [
  { value: 'low', label: 'Core', title: 'Core services only (low complexity)' },
  { value: 'medium', label: 'Standard', title: 'Core + supporting infra (medium)' },
  { value: 'high', label: 'Full', title: 'All detail (high complexity)' },
]
</script>

<template>
  <div v-if="dir" class="complexity-filter">
    <span class="complexity-filter__label">Detail:</span>
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
</template>

<style scoped>
.complexity-filter {
  display: flex;
  align-items: center;
  gap: 4px;
}

.complexity-filter__label {
  font: 12px sans-serif;
  color: #6b7280;
  margin-right: 4px;
}

.complexity-filter__btn {
  padding: 4px 10px;
  font: 12px sans-serif;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s;
}

.complexity-filter__btn:hover {
  background: #f3f4f6;
}

.complexity-filter__btn.active {
  background: #6c8ebf;
  border-color: #6c8ebf;
  color: #fff;
}
</style>
