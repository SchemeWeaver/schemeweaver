/**
 * Browse and load diagrams saved in data/out/ via the library API.
 */
import type { GenerateResponse } from '~/types/dir'

export interface DiagramSummary {
  slug: string
  title: string
  diagram_type: string
  nodes: number
  edges: number
  groups: number
  elapsed_s: number
  issues: string[]
  model: string
}

// Module-level state so all consumers share the same list
const entries = ref<DiagramSummary[]>([])
const loadingList = ref(false)
const listError = ref<string | null>(null)

export function useLibrary() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string

  async function fetchList(): Promise<void> {
    loadingList.value = true
    listError.value = null
    try {
      entries.value = await $fetch<DiagramSummary[]>(`${apiBase}/v1/library`)
    } catch (e: unknown) {
      listError.value = e instanceof Error ? e.message : String(e)
    } finally {
      loadingList.value = false
    }
  }

  async function loadDiagram(slug: string): Promise<GenerateResponse> {
    return $fetch<GenerateResponse>(`${apiBase}/v1/library/${encodeURIComponent(slug)}`)
  }

  return { entries, loadingList, listError, fetchList, loadDiagram }
}
