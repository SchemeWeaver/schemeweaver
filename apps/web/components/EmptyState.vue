<script setup lang="ts">
const examples = [
  { icon: '☁', text: 'AWS three-tier web app with API Gateway, Lambda, RDS, and S3' },
  { icon: '⎈', text: 'Kubernetes cluster with ingress controller, services, and PostgreSQL' },
  { icon: '⇄', text: 'Event-driven microservices with Kafka, producers, consumers, and DLQ' },
  { icon: '⟳', text: 'CI/CD pipeline with GitHub Actions, Docker, and Kubernetes' },
]

const emit = defineEmits<{ use: [prompt: string] }>()
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__center">
      <div class="empty-state__logo">
        <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
          <polygon points="26,4 48,17 48,35 26,48 4,35 4,17" stroke="#5b8cd7" stroke-width="1.5" fill="none" opacity="0.4"/>
          <polygon points="26,12 40,20 40,32 26,40 12,32 12,20" stroke="#5b8cd7" stroke-width="1.5" fill="none" opacity="0.6"/>
          <polygon points="26,20 34,25 34,31 26,36 18,31 18,25" fill="#5b8cd7" opacity="0.7"/>
        </svg>
      </div>

      <h2 class="empty-state__heading">Start with a prompt</h2>
      <p class="empty-state__sub">
        Describe any system — Scheme Weaver will generate an interactive architecture diagram.
        <br>Press <kbd>⌘ Enter</kbd> or click <kbd>Generate</kbd> to begin.
      </p>

      <div class="empty-state__examples">
        <p class="empty-state__examples-label">Try an example</p>
        <div class="empty-state__example-grid">
          <button
            v-for="ex in examples"
            :key="ex.text"
            class="empty-state__example-btn"
            @click="emit('use', ex.text)"
          >
            <span class="empty-state__example-icon">{{ ex.icon }}</span>
            <span class="empty-state__example-text">{{ ex.text }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: var(--canvas-bg);
  padding: 32px;
}

.empty-state__center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  max-width: 560px;
  width: 100%;
  text-align: center;
}

.empty-state__logo {
  margin-bottom: 4px;
}

.empty-state__heading {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #1e293b;
  letter-spacing: -0.01em;
}

.empty-state__sub {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: #64748b;
}

kbd {
  display: inline-block;
  padding: 1px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 12px;
  font-family: system-ui, sans-serif;
  background: #f8fafc;
  color: #334155;
}

.empty-state__examples {
  width: 100%;
  margin-top: 8px;
}

.empty-state__examples-label {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #94a3b8;
}

.empty-state__example-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.empty-state__example-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.12s, box-shadow 0.12s, background 0.12s;
}

.empty-state__example-btn:hover {
  border-color: var(--accent);
  background: #f0f5ff;
  box-shadow: 0 0 0 3px var(--accent-muted);
}

.empty-state__example-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
  color: #64748b;
}

.empty-state__example-text {
  font-size: 13px;
  line-height: 1.4;
  color: #334155;
}
</style>
