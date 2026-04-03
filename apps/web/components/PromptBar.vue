<script setup lang="ts">
import ModelSelector from './ModelSelector.vue'
import { useSystem } from '~/composables/useSystem'

const { dir, loading, generate, refine } = useSystem()

const prompt = ref('')
const isUpdate = computed(() => !!dir.value)

const placeholder = computed(() =>
  isUpdate.value
    ? 'Describe changes…'
    : 'Describe your architecture… e.g. "three-tier app with API Gateway, Lambda, and RDS"',
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
    <div class="prompt-bar__box">
      <textarea
        v-model="prompt"
        :placeholder="placeholder"
        :disabled="loading"
        rows="2"
        class="prompt-bar__input"
        @keydown="onKeydown"
      />

      <div class="prompt-bar__toolbar">
        <!-- Mode badge -->
        <span :class="['prompt-bar__mode', isUpdate ? 'prompt-bar__mode--update' : 'prompt-bar__mode--new']">
          {{ isUpdate ? 'Update' : 'New' }}
        </span>

        <span class="prompt-bar__spacer" />

        <!-- Shortcut hint -->
        <span class="prompt-bar__shortcut">⌘↵</span>

        <!-- Model selector -->
        <ModelSelector hide-label />

        <!-- Submit -->
        <button
          :class="['prompt-bar__submit', isUpdate ? 'prompt-bar__submit--update' : 'prompt-bar__submit--generate']"
          :disabled="!prompt.trim() || loading"
          :title="isUpdate ? 'Update diagram (⌘↵)' : 'Generate (⌘↵)'"
          @click="submit"
        >
          <span v-if="loading" class="prompt-bar__spinner" />
          <template v-else>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span v-if="!isUpdate" class="prompt-bar__submit-label">Generate</span>
          </template>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.prompt-bar {
  padding: 8px 14px 10px;
  background: var(--bg-chrome);
  border-top: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

/* ── Main box ────────────────────────────────────────────────────────────── */
.prompt-bar__box {
  display: flex;
  flex-direction: column;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-md);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.prompt-bar__box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-muted);
}

/* ── Textarea ────────────────────────────────────────────────────────────── */
.prompt-bar__input {
  resize: none;
  border: none;
  background: transparent;
  padding: 10px 12px 4px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  outline: none;
  min-height: 48px;
  max-height: 120px;
  overflow-y: auto;
  font-family: system-ui, -apple-system, sans-serif;
}

.prompt-bar__input::placeholder { color: var(--text-subtle); }
.prompt-bar__input:disabled     { color: var(--text-subtle); }

/* ── Bottom toolbar ──────────────────────────────────────────────────────── */
.prompt-bar__toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 6px 8px;
}

.prompt-bar__spacer { flex: 1; }

/* Mode badge */
.prompt-bar__mode {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  padding: 2px 7px;
  border-radius: 10px;
  flex-shrink: 0;
}

.prompt-bar__mode--new {
  background: var(--accent-muted);
  color: var(--accent);
  border: 1px solid rgba(91, 140, 215, 0.25);
}

.prompt-bar__mode--update {
  background: rgba(240, 163, 58, 0.1);
  color: var(--warn);
  border: 1px solid rgba(240, 163, 58, 0.25);
}

/* Shortcut hint */
.prompt-bar__shortcut {
  font-size: 11px;
  color: var(--text-subtle);
  letter-spacing: 0.02em;
  user-select: none;
}

/* ── Submit button ───────────────────────────────────────────────────────── */
.prompt-bar__submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s;
  flex-shrink: 0;
}

.prompt-bar__submit:hover:not(:disabled) { background: var(--accent-hover); }
.prompt-bar__submit:disabled { opacity: 0.4; cursor: not-allowed; }

/* Generate: icon + label */
.prompt-bar__submit--generate {
  padding: 5px 12px;
  height: 28px;
}

/* Update: icon only, square */
.prompt-bar__submit--update {
  width: 28px;
  height: 28px;
  padding: 0;
}

.prompt-bar__spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
