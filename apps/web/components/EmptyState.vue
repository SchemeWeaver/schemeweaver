<script setup lang="ts">
const examples = [
  'AWS three-tier web app with API Gateway, Lambda, RDS, and S3',
  'Kubernetes cluster with ingress controller, services, and PostgreSQL',
  'Event-driven microservices with Kafka, producers, consumers, and DLQ',
  'CI/CD pipeline with GitHub, Docker, and a Kubernetes deployment',
]

const emit = defineEmits<{ use: [prompt: string] }>()
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__icon">⬡</div>
    <h2 class="empty-state__heading">Describe your architecture</h2>
    <p class="empty-state__sub">
      Type a prompt below and press <kbd>Generate</kbd> — or try an example:
    </p>
    <ul class="empty-state__examples">
      <li v-for="ex in examples" :key="ex">
        <button class="empty-state__example-btn" @click="emit('use', ex)">
          {{ ex }}
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: #6b7280;
  text-align: center;
  padding: 32px;
}

.empty-state__icon {
  font-size: 56px;
  opacity: 0.2;
  line-height: 1;
}

.empty-state__heading {
  font: 600 20px sans-serif;
  color: #374151;
  margin: 0;
}

.empty-state__sub {
  font: 14px/1.5 sans-serif;
  margin: 0;
}

kbd {
  display: inline-block;
  padding: 1px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font: 12px monospace;
  background: #f3f4f6;
  color: #374151;
}

.empty-state__examples {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 560px;
  width: 100%;
}

.empty-state__example-btn {
  width: 100%;
  padding: 8px 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font: 13px/1.4 sans-serif;
  color: #4b5563;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s, border-color 0.1s;
}

.empty-state__example-btn:hover {
  background: #f0f4ff;
  border-color: #6c8ebf;
  color: #374151;
}
</style>
