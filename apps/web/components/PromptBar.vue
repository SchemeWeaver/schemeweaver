<script setup lang="ts">
import ModelSelector from './ModelSelector.vue'
import { useSystem } from '~/composables/useSystem'

const { dir, loading, generate, refine } = useSystem()

const prompt = ref('')
const isUpdate = computed(() => !!dir.value)

const placeholder = computed(() =>
  isUpdate.value
    ? 'Describe changes… e.g. "add a Redis cache between the API and the database"'
    : 'Describe your architecture… e.g. "AWS three-tier app with API Gateway, Lambda, and RDS"',
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
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
}
</script>

<template>
  <div class="prompt-bar">
    <div class="prompt-bar__inner">
      <div :class="['prompt-bar__mode', isUpdate ? 'prompt-bar__mode--update' : 'prompt-bar__mode--new']">
        {{ isUpdate ? 'Update' : 'New' }}
      </div>

      <ModelSelector class="prompt-bar__model" hide-label />

      <textarea
        v-model="prompt"
        :placeholder="placeholder"
        :disabled="loading"
        rows="1"
        class="prompt-bar__input"
        @keydown="onKeydown"
      />

      <button
        :disabled="!prompt.trim() || loading"
        class="prompt-bar__btn"
        @click="submit"
      >
        <span v-if="loading" class="prompt-bar__spinner" />
        <template v-else>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {{ isUpdate ? 'Update' : 'Generate' }}
        </template>
      </button>
    </div>

    <div class="prompt-bar__hint">
      <kbd>⌘ Enter</kbd> to submit
    </div>
  </div>
</template>

<style scoped>
.prompt-bar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 16px 10px;
  background: var(--bg-chrome);
  border-top: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.prompt-bar__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-md);
  padding: 6px 8px 6px 10px;
  transition: border-color 0.15s;
}

.prompt-bar__inner:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-muted);
}

.prompt-bar__mode {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  padding: 2px 7px;
  border-radius: 10px;
  flex-shrink: 0;
  white-space: nowrap;
}

.prompt-bar__mode--new {
  background: var(--accent-muted);
  color: var(--accent);
  border: 1px solid rgba(91, 140, 215, 0.3);
}

.prompt-bar__mode--update {
  background: rgba(240, 163, 58, 0.12);
  color: var(--warn);
  border: 1px solid rgba(240, 163, 58, 0.3);
}

.prompt-bar__input {
  flex: 1;
  resize: none;
  border: none;
  background: transparent;
  padding: 4px 0;
  font-size: 14px;
  line-height: 1.4;
  color: var(--text-primary);
  outline: none;
  min-height: 24px;
  max-height: 80px;
  overflow-y: auto;
  font-family: system-ui, -apple-system, sans-serif;
}

.prompt-bar__input::placeholder {
  color: var(--text-subtle);
}

.prompt-bar__input:disabled {
  color: var(--text-subtle);
}

.prompt-bar__btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.prompt-bar__btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.prompt-bar__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.prompt-bar__spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.prompt-bar__model {
  flex-shrink: 0;
}

.prompt-bar__hint {
  display: flex;
  justify-content: flex-end;
  padding-right: 2px;
}

.prompt-bar__hint kbd {
  font-size: 10px;
  color: var(--text-subtle);
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: 3px;
  padding: 1px 5px;
  font-family: system-ui, sans-serif;
}
</style>
