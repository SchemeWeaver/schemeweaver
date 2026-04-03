<script setup lang="ts">
import type { ModelInfo, ModelsResponse } from '~/types/dir'
import { useSystem } from '~/composables/useSystem'

defineProps<{ hideLabel?: boolean }>()

const { selectedModel } = useSystem()
const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

const models = ref<ModelInfo[]>([])
const defaultModel = ref('')

// Group models by provider for <optgroup> rendering
const grouped = computed<Record<string, ModelInfo[]>>(() => {
  const out: Record<string, ModelInfo[]> = {}
  for (const m of models.value) {
    ;(out[m.provider] ??= []).push(m)
  }
  return out
})

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  ollama: 'Ollama (local)',
}

onMounted(async () => {
  try {
    const res = await $fetch<ModelsResponse>(`${apiBase}/v1/models`)
    models.value = res.models
    defaultModel.value = res.default

    // Pick the configured default if accessible, otherwise the first accessible model
    const defaultEntry = res.models.find(m => m.id === res.default)
    if (defaultEntry?.accessible) {
      selectedModel.value = res.default
    } else {
      const first = res.models.find(m => m.accessible)
      selectedModel.value = first?.id ?? res.default
    }
  } catch {
    // server not ready yet
  }
})
</script>

<template>
  <div v-if="models.length" class="model-selector">
    <span v-if="!hideLabel" class="model-selector__label">Model</span>
    <select
      v-model="selectedModel"
      class="model-selector__select"
      title="Select model for generation"
    >
      <template v-for="(group, provider) in grouped" :key="provider">
        <optgroup :label="PROVIDER_LABELS[provider] ?? provider">
          <option
            v-for="m in group"
            :key="m.id"
            :value="m.id"
            :disabled="!m.accessible"
            :class="{ 'model-selector__option--inaccessible': !m.accessible }"
          >
            {{ m.id }}{{ !m.accessible ? ' (no key)' : '' }}
          </option>
        </optgroup>
      </template>
    </select>
  </div>
</template>

<style scoped>
.model-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.model-selector__label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.model-selector__select {
  appearance: none;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  padding: 3px 22px 3px 8px;
  cursor: pointer;
  outline: none;
  max-width: 180px;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23666' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 7px center;
  transition: border-color 0.12s;
}

.model-selector__select:hover,
.model-selector__select:focus {
  border-color: var(--accent);
}
</style>
