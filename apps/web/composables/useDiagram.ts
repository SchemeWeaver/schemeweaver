/**
 * Central state hub for the diagram editor.
 * Owns the current DIR, SVG, Mermaid, issues, and loading state.
 */
import type { DIR, GenerateResponse, NodeType, DiagramNode, DiagramEdge } from '~/types/dir'

const dir = ref<DIR | null>(null)
const svg = ref<string>('')
const mermaid = ref<string>('')
const issues = ref<string[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedModel = ref<string>('')
const activeModel = ref<string>('')  // model that produced the current diagram
const currentSlug = ref<string | null>(null)  // null = unsaved draft
const saving = ref(false)

export function useDiagram() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string

  async function generate(prompt: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const body: Record<string, unknown> = { prompt }
      if (selectedModel.value) body.model = selectedModel.value
      const res = await $fetch<GenerateResponse>(`${apiBase}/v1/generate`, {
        method: 'POST',
        body,
      })
      dir.value = res.dir
      svg.value = res.svg
      mermaid.value = res.mermaid
      issues.value = res.issues
      activeModel.value = res.model ?? ''
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
      const body: Record<string, unknown> = { dir: dir.value, feedback }
      if (selectedModel.value) body.model = selectedModel.value
      const res = await $fetch<GenerateResponse>(`${apiBase}/v1/update`, {
        method: 'POST',
        body,
      })
      dir.value = res.dir
      svg.value = res.svg
      mermaid.value = res.mermaid
      issues.value = res.issues
      activeModel.value = res.model ?? ''
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function save(): Promise<void> {
    if (!dir.value || !svg.value) return
    saving.value = true
    error.value = null
    try {
      const res = await $fetch<{ slug: string }>(`${apiBase}/v1/library`, {
        method: 'POST',
        body: {
          slug: currentSlug.value ?? undefined,
          dir: dir.value,
          svg: svg.value,
          mermaid: mermaid.value,
          issues: issues.value,
          model: activeModel.value,
        },
      })
      currentSlug.value = res.slug
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      saving.value = false
    }
  }

  function addNode(nodeType: string, label: string, vendor?: string | null, technology?: string | null): string | null {
    if (!dir.value) return null
    const id = `${nodeType.replace(/[^a-z0-9]/g, '-')}-${Date.now()}`
    dir.value.nodes.push({
      id,
      label,
      node_type: nodeType as NodeType,
      vendor: (vendor ?? null) as DiagramNode['vendor'],
      technology: technology ?? null,
      children: [],
    })
    return id
  }

  function deleteNode(id: string): void {
    if (!dir.value) return
    dir.value.nodes = dir.value.nodes.filter(n => n.id !== id)
    dir.value.edges = dir.value.edges.filter(e => e.from_node !== id && e.to_node !== id)
    for (const g of dir.value.groups) g.contains = g.contains.filter(c => c !== id)
  }

  function deleteEdge(id: string): void {
    if (!dir.value) return
    dir.value.edges = dir.value.edges.filter(e => e.id !== id)
  }

  function updateNode(id: string, patch: Partial<DiagramNode>): void {
    if (!dir.value) return
    const node = dir.value.nodes.find(n => n.id === id)
    if (node) Object.assign(node, patch)
  }

  function updateEdge(id: string, patch: Partial<DiagramEdge>): void {
    if (!dir.value) return
    const edge = dir.value.edges.find(e => e.id === id)
    if (edge) Object.assign(edge, patch)
  }

  function addEdge(fromId: string, toId: string): string | null {
    if (!dir.value) return null
    const id = `edge-${fromId}-${toId}-${Date.now()}`
    dir.value.edges.push({ id, from_node: fromId, to_node: toId, style: 'solid', direction: 'forward' })
    return id
  }

  function updateNodePosition(id: string, x: number, y: number): void {
    if (!dir.value) return
    const node = dir.value.nodes.find(n => n.id === id)
    if (node) { node.x = x; node.y = y }
  }

  function reset(): void {
    dir.value = null
    svg.value = ''
    mermaid.value = ''
    issues.value = []
    error.value = null
    activeModel.value = ''
    currentSlug.value = null
  }

  function loadSaved(res: GenerateResponse, slug: string): void {
    dir.value = res.dir
    svg.value = res.svg
    mermaid.value = res.mermaid
    issues.value = res.issues
    error.value = null
    activeModel.value = res.model ?? ''
    currentSlug.value = slug
  }

  return {
    dir: readonly(dir) as Ref<DIR | null>,
    svg: readonly(svg),
    mermaid: readonly(mermaid),
    issues: readonly(issues),
    loading: readonly(loading),
    error: readonly(error),
    selectedModel,
    activeModel: readonly(activeModel),
    currentSlug: readonly(currentSlug),
    saving: readonly(saving),
    generate,
    refine,
    save,
    reset,
    loadSaved,
    addNode,
    addEdge,
    deleteNode,
    deleteEdge,
    updateNode,
    updateEdge,
    updateNodePosition,
  }
}
