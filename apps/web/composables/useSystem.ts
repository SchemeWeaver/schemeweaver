/**
 * Central state hub for the System Ontology layer.
 * Replaces useDiagram + useLibrary.
 *
 * Owns: current System, active view, SVG/Mermaid for the active view,
 * systems list, and all mutations that flow through the action log.
 */
import type { DIR, DiagramNode, DiagramEdge, GenerateResponse } from '~/types/dir'
import type { System, SystemSummary, View } from '~/types/system'

// ── Module-level shared state ──────────────────────────────────────────────
const currentSystem   = ref<System | null>(null)
const activeViewId    = ref<string | null>(null)
const svg             = ref<string>('')
const mermaid         = ref<string>('')
const issues          = ref<string[]>([])
const loading         = ref(false)
const error           = ref<string | null>(null)
const saving          = ref(false)
const selectedModel   = ref<string>('')
const systems         = ref<SystemSummary[]>([])
const loadingList     = ref(false)
const listError       = ref<string | null>(null)

// ── Derived ────────────────────────────────────────────────────────────────
const activeView = computed<View | null>(() => {
  if (!currentSystem.value || !activeViewId.value) return null
  return currentSystem.value.views.find(v => v.id === activeViewId.value) ?? null
})

const dir = computed<DIR | null>(() => activeView.value?.dir ?? null)

// ── Helpers ────────────────────────────────────────────────────────────────
function _mutateActiveDir(fn: (d: DIR) => void): void {
  if (!currentSystem.value || !activeViewId.value) return
  const views = currentSystem.value.views
  const idx = views.findIndex(v => v.id === activeViewId.value)
  if (idx === -1) return
  // Clone view with mutated dir so Vue reactivity picks up the change
  const view = views[idx]
  const clonedDir: DIR = JSON.parse(JSON.stringify(view.dir))
  fn(clonedDir)
  const updatedViews = [...views]
  updatedViews[idx] = { ...view, dir: clonedDir }
  currentSystem.value = { ...currentSystem.value, views: updatedViews }
}

export function useSystem() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string

  // ── System generation ────────────────────────────────────────────────────

  async function generate(prompt: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const body: Record<string, unknown> = { prompt }
      if (selectedModel.value) body.model = selectedModel.value

      const res = await $fetch<{ slug: string; system: System }>(
        `${apiBase}/v1/systems/generate`,
        { method: 'POST', body },
      )
      currentSystem.value = res.system
      const firstView = res.system.views[0]
      if (firstView) {
        activeViewId.value = firstView.id
        await _renderActiveView()
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  /** Refine the active view's DIR via AI (like the old "update" endpoint). */
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
      // Patch the active view's DIR with the AI-refined version
      _mutateActiveDir(d => {
        d.meta = res.dir.meta
        d.nodes = res.dir.nodes
        d.edges = res.dir.edges
        d.groups = res.dir.groups
      })
      svg.value    = res.svg
      mermaid.value = res.mermaid
      issues.value  = res.issues
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  /** Persist the current state of the active view to the server. */
  async function save(): Promise<void> {
    if (!currentSystem.value || !activeViewId.value || !dir.value) return
    saving.value = true
    error.value = null
    try {
      await $fetch(
        `${apiBase}/v1/systems/${encodeURIComponent(currentSystem.value.slug)}/views/${encodeURIComponent(activeViewId.value)}`,
        {
          method: 'PATCH',
          body: { dir: dir.value, positions: {} },
        },
      )
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      saving.value = false
    }
  }

  // ── Systems list ─────────────────────────────────────────────────────────

  async function fetchList(): Promise<void> {
    loadingList.value = true
    listError.value = null
    try {
      systems.value = await $fetch<SystemSummary[]>(`${apiBase}/v1/systems`)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      if (!msg.includes('ECONNRESET')) listError.value = msg
    } finally {
      loadingList.value = false
    }
  }

  async function migrateLibrary(): Promise<{ migrated: string[]; skipped: string[] }> {
    const res = await $fetch<{ migrated: string[]; skipped: string[] }>(
      `${apiBase}/v1/systems/migrate-library`,
      { method: 'POST' },
    )
    await fetchList()
    return res
  }

  async function loadSystem(slug: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const system = await $fetch<System>(
        `${apiBase}/v1/systems/${encodeURIComponent(slug)}`,
      )
      currentSystem.value = system
      const firstView = system.views[0]
      if (firstView) {
        activeViewId.value = firstView.id
        await _renderActiveView()
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  // ── View management ──────────────────────────────────────────────────────

  function setActiveView(viewId: string): void {
    if (!currentSystem.value) return
    const view = currentSystem.value.views.find(v => v.id === viewId)
    if (!view) return
    activeViewId.value = viewId
    _renderActiveView()
  }

  async function syncViewFromOntology(): Promise<void> {
    if (!currentSystem.value || !activeViewId.value) return
    loading.value = true
    error.value = null
    try {
      const res = await $fetch<{ svg: string; dir: DIR }>(
        `${apiBase}/v1/systems/${encodeURIComponent(currentSystem.value.slug)}/sync/ontology-to-view`,
        { method: 'POST', body: { view_id: activeViewId.value } },
      )
      _mutateActiveDir(d => {
        d.meta   = res.dir.meta
        d.nodes  = res.dir.nodes
        d.edges  = res.dir.edges
        d.groups = res.dir.groups
      })
      svg.value = res.svg
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  // ── Canvas mutations (mirror useDiagram API) ─────────────────────────────

  function addNode(nodeType: string, label: string): string | null {
    if (!dir.value) return null
    const id = `${nodeType.replace(/\./g, '-')}-${Date.now()}`
    _mutateActiveDir(d => {
      d.nodes.push({ id, label, node_type: nodeType as DiagramNode['node_type'], children: [] })
    })
    return id
  }

  function deleteNode(id: string): void {
    _mutateActiveDir(d => {
      d.nodes = d.nodes.filter(n => n.id !== id)
      d.edges = d.edges.filter(e => e.from_node !== id && e.to_node !== id)
      for (const g of d.groups) g.contains = g.contains.filter(c => c !== id)
    })
  }

  function deleteEdge(id: string): void {
    _mutateActiveDir(d => { d.edges = d.edges.filter(e => e.id !== id) })
  }

  function updateNode(id: string, patch: Partial<DiagramNode>): void {
    _mutateActiveDir(d => {
      const node = d.nodes.find(n => n.id === id)
      if (node) Object.assign(node, patch)
    })
  }

  function updateEdge(id: string, patch: Partial<DiagramEdge>): void {
    _mutateActiveDir(d => {
      const edge = d.edges.find(e => e.id === id)
      if (edge) Object.assign(edge, patch)
    })
  }

  function addEdge(fromId: string, toId: string): string | null {
    if (!dir.value) return null
    const id = `edge-${fromId}-${toId}-${Date.now()}`
    _mutateActiveDir(d => {
      d.edges.push({ id, from_node: fromId, to_node: toId, style: 'solid', direction: 'forward' })
    })
    return id
  }

  function updateNodePosition(id: string, x: number, y: number): void {
    _mutateActiveDir(d => {
      const node = d.nodes.find(n => n.id === id)
      if (node) { node.x = x; node.y = y }
    })
  }

  // ── Ontology ─────────────────────────────────────────────────────────────

  async function saveOntology(ontology: import('~/types/system').Ontology): Promise<void> {
    if (!currentSystem.value) return
    saving.value = true
    error.value = null
    try {
      await $fetch(
        `${apiBase}/v1/systems/${encodeURIComponent(currentSystem.value.slug)}/ontology`,
        { method: 'PATCH', body: { ontology } },
      )
      currentSystem.value = { ...currentSystem.value, ontology }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      saving.value = false
    }
  }

  // ── Prose ────────────────────────────────────────────────────────────────

  async function saveProse(prose: string): Promise<void> {
    if (!currentSystem.value) return
    saving.value = true
    error.value = null
    try {
      await $fetch(
        `${apiBase}/v1/systems/${encodeURIComponent(currentSystem.value.slug)}/prose`,
        { method: 'PATCH', body: { prose } },
      )
      currentSystem.value = { ...currentSystem.value, prose }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      saving.value = false
    }
  }

  // ── Misc ─────────────────────────────────────────────────────────────────

  function reset(): void {
    currentSystem.value = null
    activeViewId.value  = null
    svg.value           = ''
    mermaid.value       = ''
    issues.value        = []
    error.value         = null
  }

  /** Re-render the active view's SVG from the server. */
  async function _renderActiveView(): Promise<void> {
    if (!currentSystem.value || !activeViewId.value) return
    try {
      const res = await $fetch<{ svg: string }>(
        `${apiBase}/v1/systems/${encodeURIComponent(currentSystem.value.slug)}/views/${encodeURIComponent(activeViewId.value)}/svg`,
      )
      svg.value = res.svg
    } catch {
      // Non-fatal — canvas will show stale SVG
    }
  }

  return {
    // State
    currentSystem:  readonly(currentSystem) as Ref<System | null>,
    activeView:     activeView as ComputedRef<View | null>,
    dir:            dir as ComputedRef<DIR | null>,
    svg:            readonly(svg),
    mermaid:        readonly(mermaid),
    issues:         readonly(issues),
    loading:        readonly(loading),
    error:          readonly(error),
    saving:         readonly(saving),
    selectedModel,
    systems:        readonly(systems),
    loadingList:    readonly(loadingList),
    listError:      readonly(listError),
    activeViewId:   readonly(activeViewId),
    // Actions
    generate,
    refine,
    save,
    saveOntology,
    saveProse,
    reset,
    fetchList,
    loadSystem,
    migrateLibrary,
    setActiveView,
    syncViewFromOntology,
    addNode,
    addEdge,
    deleteNode,
    deleteEdge,
    updateNode,
    updateEdge,
    updateNodePosition,
  }
}
