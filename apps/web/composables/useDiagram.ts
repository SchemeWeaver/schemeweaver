/**
 * Central state hub for the diagram editor.
 * Owns the current DIR, SVG, Mermaid, issues, and loading state.
 */
import type { DIR, GenerateResponse, ComplexityLevel } from '~/types/dir'

const dir = ref<DIR | null>(null)
const svg = ref<string>('')
const mermaid = ref<string>('')
const issues = ref<string[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const complexity = ref<ComplexityLevel>('medium')

export function useDiagram() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string

  async function generate(prompt: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<GenerateResponse>(`${apiBase}/v1/generate`, {
        method: 'POST',
        body: { prompt },
      })
      dir.value = res.dir
      svg.value = res.svg
      mermaid.value = res.mermaid
      issues.value = res.issues
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function refine(feedback: string): Promise<void> {
    if (!dir.value) return
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<GenerateResponse>(`${apiBase}/v1/update`, {
        method: 'POST',
        body: { dir: dir.value, feedback },
      })
      dir.value = res.dir
      svg.value = res.svg
      mermaid.value = res.mermaid
      issues.value = res.issues
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    dir.value = null
    svg.value = ''
    mermaid.value = ''
    issues.value = []
    error.value = null
  }

  return {
    dir: readonly(dir),
    svg: readonly(svg),
    mermaid: readonly(mermaid),
    issues: readonly(issues),
    loading: readonly(loading),
    error: readonly(error),
    complexity,
    generate,
    refine,
    reset,
  }
}
