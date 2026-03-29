<script setup lang="ts">
import { useDiagram } from '~/composables/useDiagram'

const { dir, loading, generate, refine } = useDiagram()

const prompt = ref('')
const isUpdate = computed(() => !!dir.value)
const placeholder = computed(() =>
  isUpdate.value
    ? 'Describe changes (e.g. "add a Redis cache between the API and DB")…'
    : 'Describe your architecture (e.g. "AWS three-tier app with API Gateway, Lambda, RDS")…',
)

async function submit(): Promise<void> {
  if (!prompt.value.trim() || loading.value) return
  if (isUpdate.value) {
    await refine(prompt.value.trim())
  } else {
    await generate(prompt.value.trim())
  }
  prompt.value = ''
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
    submit()
  }
}
</script>

<template>
  <div class="prompt-bar">
    <textarea
      v-model="prompt"
      :placeholder="placeholder"
      :disabled="loading"
      rows="2"
      class="prompt-bar__input"
      @keydown="onKeydown"
    />
    <button
      :disabled="!prompt.trim() || loading"
      class="prompt-bar__btn"
      @click="submit"
    >
      <span v-if="loading" class="prompt-bar__spinner" />
      <span v-else>{{ isUpdate ? 'Update' : 'Generate' }}</span>
    </button>
  </div>
</template>

<style scoped>
.prompt-bar {
  display: flex;
  gap: 8px;
  padding: 10px 16px;
  background: #fff;
  border-top: 1px solid #e5e7eb;
  align-items: flex-end;
}

.prompt-bar__input {
  flex: 1;
  resize: none;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 10px;
  font: 14px/1.4 sans-serif;
  color: #111;
  outline: none;
  transition: border-color 0.15s;
}

.prompt-bar__input:focus {
  border-color: #6c8ebf;
}

.prompt-bar__input:disabled {
  background: #f9fafb;
  color: #9ca3af;
}

.prompt-bar__btn {
  flex-shrink: 0;
  height: 38px;
  padding: 0 18px;
  background: #6c8ebf;
  color: #fff;
  border: none;
  border-radius: 6px;
  font: 600 14px sans-serif;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s;
}

.prompt-bar__btn:hover:not(:disabled) {
  background: #5a7aad;
}

.prompt-bar__btn:disabled {
  background: #9cb0d0;
  cursor: not-allowed;
}

.prompt-bar__spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.5);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
