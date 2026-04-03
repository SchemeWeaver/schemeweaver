<script setup lang="ts">
import { useSystem } from '~/composables/useSystem'

const { currentSystem, saving, saveProse } = useSystem()

const localProse = ref('')
const dirty = ref(false)

// Sync local value when system changes externally
watch(
  () => currentSystem.value?.prose,
  (prose) => {
    localProse.value = prose ?? ''
    dirty.value = false
  },
  { immediate: true },
)

function onInput(): void {
  dirty.value = localProse.value !== (currentSystem.value?.prose ?? '')
}

async function save(): Promise<void> {
  if (!dirty.value) return
  await saveProse(localProse.value)
  dirty.value = false
}

// Auto-save on blur
function onBlur(): void { save() }
</script>

<template>
  <div class="prose-editor">
    <div class="prose-editor__header">
      <span class="prose-editor__label">Prose Description</span>
      <button
        v-if="dirty"
        class="prose-editor__save-btn"
        :disabled="saving"
        @click="save"
      >
        <span v-if="saving" class="prose-editor__spinner" />
        <template v-else>Save</template>
      </button>
    </div>

    <div v-if="!currentSystem" class="prose-editor__empty">
      Generate a system to edit its prose description.
    </div>

    <textarea
      v-else
      v-model="localProse"
      class="prose-editor__textarea"
      placeholder="Describe the system in plain English…"
      @input="onInput"
      @blur="onBlur"
    />
  </div>
</template>

<style scoped>
.prose-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.prose-editor__header {
  display: flex;
  align-items: center;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
  gap: 8px;
}

.prose-editor__label {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

.prose-editor__save-btn {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.12s;
  display: inline-flex;
  align-items: center;
}

.prose-editor__save-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.prose-editor__save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.prose-editor__spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.prose-editor__empty {
  padding: 24px 16px;
  font-size: 13px;
  color: var(--text-subtle);
  text-align: center;
}

.prose-editor__textarea {
  flex: 1;
  width: 100%;
  resize: none;
  border: none;
  background: var(--bg-canvas);
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.65;
  padding: 14px 16px;
  outline: none;
  font-family: system-ui, -apple-system, sans-serif;
  box-sizing: border-box;
}

.prose-editor__textarea::placeholder {
  color: var(--text-subtle);
}
</style>
