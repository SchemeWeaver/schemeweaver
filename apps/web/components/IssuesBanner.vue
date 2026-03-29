<script setup lang="ts">
import { useDiagram } from '~/composables/useDiagram'

const { issues, error } = useDiagram()

const visible = computed(() => issues.value.length > 0 || !!error.value)
</script>

<template>
  <Transition name="banner">
    <div v-if="visible" :class="['issues-banner', error ? 'issues-banner--error' : 'issues-banner--warn']">
      <div class="issues-banner__icon">
        <svg v-if="error" width="15" height="15" viewBox="0 0 15 15" fill="none">
          <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" stroke-width="1.3"/>
          <path d="M7.5 4.5v3.5M7.5 10.5v.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        <svg v-else width="15" height="15" viewBox="0 0 15 15" fill="none">
          <path d="M7.5 1.5L13.5 12.5H1.5L7.5 1.5Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
          <path d="M7.5 6v3M7.5 11v.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
      </div>

      <div class="issues-banner__content">
        <span v-if="error" class="issues-banner__message">{{ error }}</span>
        <template v-else>
          <span class="issues-banner__message">
            {{ issues.length }} validation issue{{ issues.length > 1 ? 's' : '' }}
          </span>
          <span class="issues-banner__detail">{{ issues.join(' · ') }}</span>
        </template>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.issues-banner {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 16px;
  font-size: 12px;
  line-height: 1.4;
  flex-shrink: 0;
  border-bottom: 1px solid;
}

.issues-banner--error {
  background: rgba(224, 82, 82, 0.08);
  border-color: rgba(224, 82, 82, 0.25);
  color: #ef4444;
}

.issues-banner--warn {
  background: rgba(240, 163, 58, 0.08);
  border-color: rgba(240, 163, 58, 0.25);
  color: #d97706;
}

.issues-banner__icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.issues-banner__content {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: baseline;
}

.issues-banner__message { font-weight: 600; }

.issues-banner__detail {
  color: inherit;
  opacity: 0.75;
}

.banner-enter-active,
.banner-leave-active {
  transition: max-height 0.18s ease, opacity 0.18s ease;
  max-height: 80px;
  overflow: hidden;
}

.banner-enter-from,
.banner-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
