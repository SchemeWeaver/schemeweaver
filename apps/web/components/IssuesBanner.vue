<script setup lang="ts">
import { useDiagram } from '~/composables/useDiagram'

const { issues, error } = useDiagram()

const visible = computed(() => issues.value.length > 0 || !!error.value)
</script>

<template>
  <Transition name="banner">
    <div v-if="visible" class="issues-banner">
      <div v-if="error" class="issues-banner__error">
        <strong>Error:</strong> {{ error }}
      </div>
      <div v-if="issues.length" class="issues-banner__issues">
        <strong>{{ issues.length }} validation issue{{ issues.length > 1 ? 's' : '' }}:</strong>
        <ul>
          <li v-for="issue in issues" :key="issue">{{ issue }}</li>
        </ul>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.issues-banner {
  background: #fff7ed;
  border-bottom: 1px solid #fed7aa;
  padding: 8px 16px;
  font: 13px/1.4 sans-serif;
}

.issues-banner__error {
  color: #b91c1c;
}

.issues-banner__issues {
  color: #92400e;
}

.issues-banner__issues ul {
  margin: 4px 0 0;
  padding-left: 18px;
}

/* Slide-down transition */
.banner-enter-active,
.banner-leave-active {
  transition: max-height 0.2s ease, opacity 0.2s ease;
  max-height: 200px;
  overflow: hidden;
}

.banner-enter-from,
.banner-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
