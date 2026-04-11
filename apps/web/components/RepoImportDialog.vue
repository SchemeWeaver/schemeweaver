<script setup lang="ts">
/**
 * Two-step dialog for importing a repository as a System.
 *
 * Step 1 — Analyze: user provides a local path or git URL, server compiles a KB.
 * Step 2 — Review: user edits the KB markdown, then generates the System.
 */

const emit = defineEmits<{ close: [] }>()
const props = defineProps<{ onLoad: (slug: string) => Promise<void> }>()

const config  = useRuntimeConfig()
const apiBase = config.public.apiBase as string

// ── State ────────────────────────────────────────────────────────────────────

type Step = 'input' | 'review' | 'generating'

const step      = ref<Step>('input')
const source    = ref('')
const repoName  = ref('')
const kbText    = ref('')
const analyzing = ref(false)
const error     = ref<string | null>(null)

// ── Step 1: Analyze ──────────────────────────────────────────────────────────

async function analyze(): Promise<void> {
  if (!source.value.trim()) return
  analyzing.value = true
  error.value     = null

  try {
    const res = await $fetch<{ repo_name: string; source: string; knowledge_base: string }>(
      `${apiBase}/v1/repos/analyze`,
      { method: 'POST', body: { source: source.value.trim() } },
    )
    repoName.value = res.repo_name
    kbText.value   = res.knowledge_base
    step.value     = 'review'
  } catch (e: unknown) {
    error.value = extractMessage(e)
  } finally {
    analyzing.value = false
  }
}

// ── Step 2: Generate ─────────────────────────────────────────────────────────

async function generate(): Promise<void> {
  if (!kbText.value.trim()) return
  step.value  = 'generating'
  error.value = null

  try {
    const res = await $fetch<{ slug: string }>(
      `${apiBase}/v1/systems/from-repo`,
      {
        method: 'POST',
        body: {
          source: source.value.trim(),
          knowledge_base: kbText.value,
        },
      },
    )
    await props.onLoad(res.slug)
    emit('close')
  } catch (e: unknown) {
    error.value = extractMessage(e)
    step.value  = 'review'
  }
}

function back(): void {
  step.value  = 'input'
  error.value = null
}

function extractMessage(e: unknown): string {
  if (e && typeof e === 'object') {
    const fe = e as Record<string, unknown>
    if (fe.data && typeof fe.data === 'object') {
      const d = fe.data as Record<string, unknown>
      if (typeof d.detail === 'string') return d.detail
    }
    if (typeof fe.message === 'string') return fe.message
  }
  return String(e)
}

// ── Keyboard ─────────────────────────────────────────────────────────────────

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && step.value !== 'generating') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div class="rid-overlay" @click.self="step !== 'generating' && emit('close')">
      <div class="rid-dialog" role="dialog" aria-modal="true">

        <!-- Header -->
        <div class="rid-header">
          <span class="rid-title">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style="margin-right:6px;vertical-align:-2px">
              <path d="M2 2h4v4H2zM10 2h4v4h-4zM2 10h4v4H2zM10 10h4v4h-4z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
              <path d="M6 4h4M4 6v4M12 6v4M6 12h4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            </svg>
            Import from Repository
          </span>
          <div class="rid-steps">
            <span :class="['rid-step', { active: step === 'input', done: step !== 'input' }]">1 Analyze</span>
            <span class="rid-step-sep">›</span>
            <span :class="['rid-step', { active: step === 'review' || step === 'generating' }]">2 Review</span>
            <span class="rid-step-sep">›</span>
            <span :class="['rid-step', { active: step === 'generating' }]">3 Generate</span>
          </div>
          <button v-if="step !== 'generating'" class="rid-close" @click="emit('close')">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <!-- Step 1: Source input -->
        <template v-if="step === 'input'">
          <div class="rid-body">
            <label class="rid-field">
              <span class="rid-label">Local path or Git URL</span>
              <input
                v-model="source"
                class="rid-input"
                placeholder="e.g. /home/user/my-project  or  https://github.com/org/repo"
                autofocus
                spellcheck="false"
                @keydown.enter="analyze"
              />
            </label>
            <p class="rid-hint">
              The server will read manifests, README, directory structure, and
              docker-compose files to compile a Knowledge Base.
              Git URLs require <code>git</code> on the server PATH.
            </p>
            <div v-if="error" class="rid-error">{{ error }}</div>
          </div>
          <div class="rid-footer">
            <button class="rid-cancel" @click="emit('close')">Cancel</button>
            <button
              class="rid-action"
              :disabled="!source.trim() || analyzing"
              @click="analyze"
            >
              <span v-if="analyzing" class="rid-spinner" />
              <template v-else>Analyze</template>
            </button>
          </div>
        </template>

        <!-- Step 2: Review KB -->
        <template v-else-if="step === 'review' || step === 'generating'">
          <div class="rid-body rid-body--review">
            <div class="rid-kb-header">
              <span class="rid-kb-title">
                Knowledge Base
                <span v-if="repoName" class="rid-kb-repo">— {{ repoName }}</span>
              </span>
              <span class="rid-kb-hint">Edit before generating</span>
            </div>
            <textarea
              v-model="kbText"
              class="rid-kb-textarea"
              :disabled="step === 'generating'"
              spellcheck="false"
            />
            <div v-if="error" class="rid-error">{{ error }}</div>
          </div>
          <div class="rid-footer">
            <button class="rid-cancel" :disabled="step === 'generating'" @click="back">Back</button>
            <button
              class="rid-action"
              :disabled="!kbText.trim() || step === 'generating'"
              @click="generate"
            >
              <span v-if="step === 'generating'" class="rid-spinner" />
              <template v-else>Generate System</template>
            </button>
          </div>
        </template>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.rid-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
}

.rid-dialog {
  background: var(--bg-chrome);
  border: 1px solid var(--border-chrome);
  border-radius: 10px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.35);
  width: min(640px, 94vw);
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Header ─────────────────────────────────────────────────────── */
.rid-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px 11px;
  border-bottom: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.rid-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.rid-steps {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: center;
}

.rid-step {
  font-size: 11px;
  color: var(--text-subtle);
  padding: 2px 7px;
  border-radius: 10px;
  transition: background 0.1s, color 0.1s;
}

.rid-step.active {
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 600;
}

.rid-step.done {
  color: var(--success);
}

.rid-step-sep {
  font-size: 10px;
  color: var(--text-subtle);
  opacity: 0.5;
}

.rid-close {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  display: flex;
  transition: color 0.1s;
  flex-shrink: 0;
}
.rid-close:hover { color: var(--text-primary); }

/* ── Body ───────────────────────────────────────────────────────── */
.rid-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rid-body--review {
  padding: 12px 16px;
  min-height: 0;
}

.rid-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.rid-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.rid-input {
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  padding: 7px 10px;
  outline: none;
  font-family: ui-monospace, monospace;
  transition: border-color 0.12s;
}

.rid-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-muted);
}

.rid-hint {
  font-size: 12px;
  color: var(--text-subtle);
  margin: 0;
  line-height: 1.5;
}

.rid-hint code {
  font-size: 11px;
  font-family: ui-monospace, monospace;
  background: var(--bg-chrome-raised);
  border: 1px solid var(--border-chrome);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
}

/* KB review */
.rid-kb-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-shrink: 0;
}

.rid-kb-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.rid-kb-repo {
  font-weight: 400;
  color: var(--text-subtle);
}

.rid-kb-hint {
  font-size: 11px;
  color: var(--text-subtle);
  margin-left: auto;
  font-style: italic;
}

.rid-kb-textarea {
  flex: 1;
  min-height: 360px;
  resize: vertical;
  background: var(--bg-canvas);
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 12px;
  font-family: ui-monospace, monospace;
  line-height: 1.6;
  padding: 10px 12px;
  outline: none;
  transition: border-color 0.12s;
}

.rid-kb-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-muted);
}

.rid-kb-textarea:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Error */
.rid-error {
  font-size: 12px;
  color: var(--danger);
  padding: 7px 10px;
  background: rgba(220,53,69,0.08);
  border: 1px solid rgba(220,53,69,0.2);
  border-radius: var(--radius-sm);
}

/* ── Footer ─────────────────────────────────────────────────────── */
.rid-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 11px 16px;
  border-top: 1px solid var(--border-chrome);
  flex-shrink: 0;
}

.rid-cancel {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid var(--border-chrome);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}
.rid-cancel:hover:not(:disabled) { background: var(--bg-chrome-raised); color: var(--text-primary); }
.rid-cancel:disabled { opacity: 0.4; cursor: not-allowed; }

.rid-action {
  padding: 6px 20px;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s;
  display: inline-flex;
  align-items: center;
  min-width: 120px;
  justify-content: center;
}
.rid-action:hover:not(:disabled) { background: var(--accent-hover); }
.rid-action:disabled { opacity: 0.45; cursor: not-allowed; }

.rid-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
