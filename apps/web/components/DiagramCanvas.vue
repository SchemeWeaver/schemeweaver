<script setup lang="ts">
import { useSystem } from '~/composables/useSystem'
import { useTool } from '~/composables/useTool'
import ContextMenu from '~/components/ContextMenu.vue'
import type { CtxItem } from '~/components/ContextMenu.vue'
import type { DiagramEdge, DiagramGroup, DiagramNode, DIR } from '~/types/dir'
import { shapeKind, labelY, typeTextY, nodeColor } from '~/utils/nodeShapes'
import type { ShapeKind } from '~/utils/nodeShapes'
import { getVendorBadge, getTechIcon } from '~/utils/iconRegistry'
import type { VendorBadge, TechIcon } from '~/utils/iconRegistry'
import { autoLayout } from '~/utils/layout'

// ── Layout constants (must match Python layout.py) ─────────────────────────
const NODE_W = 160
const NODE_H = 60
const PAD    = 80

// ── Composable ─────────────────────────────────────────────────────────────
const { dir, layoutResetToken, updateNodePosition, addNode, addEdge, deleteNode, deleteEdge, updateNode, updateEdge } = useSystem()
const { tool } = useTool()

// ── Node positions (reactive, keyed by node id) ────────────────────────────
const pos = reactive<Record<string, { x: number; y: number }>>({})

// ── Selection ──────────────────────────────────────────────────────────────
const selected = reactive(new Set<string>())

// ── Structural fingerprint ─────────────────────────────────────────────────
// Encodes only node/edge/group identity — NOT positions or metadata.
// Layout re-runs only when this changes, so dragging a node (which updates
// node.x/node.y inside dir) never triggers a re-layout.
const _structuralKey = computed(() => {
  const d = dir.value
  if (!d) return ''
  return [
    d.nodes.map(n => n.id).sort().join(','),
    d.edges.map(e => e.id).sort().join(','),
    d.groups.map(g => g.id).sort().join(','),
  ].join('|')
})

watch(
  _structuralKey,
  (newKey, oldKey) => {
    const d = dir.value
    if (!d || !newKey) {
      selected.clear()
      for (const k of Object.keys(pos)) delete pos[k]
      return
    }

    const nodeIds = new Set(d.nodes.map(n => n.id))

    // Drop positions for nodes that no longer exist
    for (const k of Object.keys(pos)) {
      if (!nodeIds.has(k)) delete pos[k]
    }

    // Decide: fresh diagram (view switch) vs incremental structural change
    // (node/edge added or removed from an existing layout).
    // If fewer than half the new nodes already have positions, treat as fresh.
    const retained = Object.keys(pos).filter(id => nodeIds.has(id)).length
    const isFresh  = retained === 0 || (d.nodes.length > 2 && retained / d.nodes.length < 0.5)

    if (isFresh) {
      // ── Full reset: new diagram or view switch ──────────────────────────
      selected.clear()
      for (const k of Object.keys(pos)) delete pos[k]

      // Nodes may carry persisted x/y from a previous save — use as seed
      const storedPos: Record<string, { x: number; y: number }> = {}
      for (const node of d.nodes) {
        if (node.x != null && node.y != null) storedPos[node.id] = { x: node.x, y: node.y }
      }

      const layout = snapLayout(autoLayout(
        d,
        Object.keys(storedPos).length ? storedPos : undefined,
        { nodeW: NODE_W, nodeH: NODE_H },
      ))
      for (const node of d.nodes) {
        pos[node.id] = layout[node.id] ?? { x: PAD, y: PAD }
      }
      nextTick(fitView)
    } else {
      // ── Incremental: node/edge added or removed ─────────────────────────
      // Keep every position that's already in `pos`; only compute placement
      // for genuinely new nodes.  Don't call fitView — preserve the viewport.

      // Seed the optimizer with current screen positions (authoritative)
      const storedPos: Record<string, { x: number; y: number }> = {}
      for (const [id, p] of Object.entries(pos)) {
        if (nodeIds.has(id)) storedPos[id] = { ...p }
      }
      // Also pick up any new nodes that already carry saved coordinates
      for (const node of d.nodes) {
        if (!storedPos[node.id] && node.x != null && node.y != null) {
          storedPos[node.id] = { x: node.x, y: node.y }
        }
      }

      const layout = snapLayout(autoLayout(d, storedPos, { nodeW: NODE_W, nodeH: NODE_H }))

      // Write back only nodes that don't already have a position
      for (const node of d.nodes) {
        if (!pos[node.id]) {
          pos[node.id] = layout[node.id] ?? { x: PAD, y: PAD }
        }
      }
    }
  },
  { immediate: true },
)

const visibleNodes  = computed(() => dir.value?.nodes  ?? [])
const visibleIds    = computed(() => new Set(visibleNodes.value.map(n => n.id)))
const visibleEdges  = computed(() => (dir.value?.edges ?? []).filter(
  e => visibleIds.value.has(e.from_node) && visibleIds.value.has(e.to_node),
))
const visibleGroups = computed(() => dir.value?.groups ?? [])

// ── Display edges — collapses parallel edges between any (group|node) pair ───
//
// Two collapsing rules, handled in one unified pass:
//
//  Inbound:  one external node/group → 2+ members of the same group
//            collapses to:  external → group
//
//  Outbound: 2+ members of the same group → the same external node/group
//            collapses to:  group → external
//
// Both rules work by mapping each edge endpoint to its "effective container"
// (the group ID if the node belongs to a group, the node ID otherwise) then
// bucketing by (effectiveFrom, effectiveTo).  Any bucket with 2+ raw edges
// becomes a single synthetic DisplayEdge.  Intra-group edges (same container
// on both sides) are always passed through unchanged.

interface DisplayEdge {
  id: string
  /** Representative from-node; used for routing when from_group_id is absent. */
  from_node: string
  /** Set when the source side was collapsed to a group (outbound rule). */
  from_group_id?: string
  /** Set for edges terminating at a plain node. */
  to_node?: string
  /** Set when the target side was collapsed to a group (inbound rule). */
  to_group_id?: string
  style: DiagramEdge['style']
  direction: DiagramEdge['direction']
  label?: string
  description?: string
  /** Number of original edges merged into this one (1 = not collapsed). */
  collapsedCount: number
}

const displayEdges = computed((): DisplayEdge[] => {
  const edges  = visibleEdges.value
  const groups = visibleGroups.value

  // Lookups
  const nodeToGroup = new Map<string, string>()
  const groupIds    = new Set<string>()
  for (const g of groups) {
    groupIds.add(g.id)
    for (const nid of g.contains) nodeToGroup.set(nid, g.id)
  }

  // Effective container: group ID if node is a member, else the node ID itself
  const eff = (nodeId: string) => nodeToGroup.get(nodeId) ?? nodeId

  // Bucket all cross-container edges by (effectiveFrom, effectiveTo).
  // Intra-container edges (effectiveFrom === effectiveTo) skip bucketing —
  // they are always passed through as-is.
  const buckets = new Map<string, DiagramEdge[]>()
  for (const e of edges) {
    const efrom = eff(e.from_node)
    const eto   = eff(e.to_node)
    if (efrom === eto) continue
    const key = `${efrom}\x00${eto}`
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key)!.push(e)
  }

  const collapsed = new Set<string>()
  const synthetic: DisplayEdge[] = []

  for (const [key, bucket] of buckets) {
    if (bucket.length < 2) continue   // single edge → passthrough

    const [efrom, eto] = key.split('\x00')
    for (const e of bucket) collapsed.add(e.id)

    const primary = bucket[0]
    const descs   = bucket.map(e => e.description || e.label).filter(Boolean) as string[]

    synthetic.push({
      id:             `__grp__${efrom}__${eto}`,
      from_node:      primary.from_node,
      from_group_id:  groupIds.has(efrom) ? efrom : undefined,
      to_node:        groupIds.has(eto)   ? undefined : eto,
      to_group_id:    groupIds.has(eto)   ? eto       : undefined,
      style:          primary.style,
      direction:      primary.direction,
      label:          undefined,
      description:    descs.join('; ') || undefined,
      collapsedCount: bucket.length,
    })
  }

  // All edges not collapsed (intra-group + single cross-container edges)
  const passthrough: DisplayEdge[] = edges
    .filter(e => !collapsed.has(e.id))
    .map(e => ({
      id:             e.id,
      from_node:      e.from_node,
      to_node:        e.to_node,
      style:          e.style,
      direction:      e.direction,
      label:          e.label ?? undefined,
      description:    e.description ?? undefined,
      collapsedCount: 1,
    }))

  return [...passthrough, ...synthetic]
})

// ── Canvas bounds ──────────────────────────────────────────────────────────
const canvasW = computed(() => {
  const xs = Object.values(pos).map(p => p.x + NODE_W)
  return xs.length ? Math.max(...xs) + PAD : 800
})
const canvasH = computed(() => {
  const ys = Object.values(pos).map(p => p.y + NODE_H)
  return ys.length ? Math.max(...ys) + PAD : 600
})

// ── Edge routing (smart bezier — adapts to relative node positions) ─────────
function routeEdge(fromId: string, toId: string): string {
  const s = pos[fromId]; const d = pos[toId]
  if (!s || !d) return ''

  const scx = s.x + NODE_W / 2, scy = s.y + NODE_H / 2
  const dcx = d.x + NODE_W / 2, dcy = d.y + NODE_H / 2
  const dx = dcx - scx, dy = dcy - scy

  let x1: number, y1: number, x2: number, y2: number

  if (Math.abs(dx) >= Math.abs(dy)) {
    ;[x1, y1] = dx >= 0 ? [s.x + NODE_W, scy] : [s.x, scy]
    ;[x2, y2] = dx >= 0 ? [d.x, dcy]           : [d.x + NODE_W, dcy]
  } else {
    ;[x1, y1] = dy >= 0 ? [scx, s.y + NODE_H] : [scx, s.y]
    ;[x2, y2] = dy >= 0 ? [dcx, d.y]           : [dcx, d.y + NODE_H]
  }

  const isH  = Math.abs(dx) >= Math.abs(dy)
  const cLen = Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) * 0.45
  const sx   = isH ? Math.sign(x2 - x1) : 0
  const sy   = isH ? 0 : Math.sign(y2 - y1)

  return `M ${x1} ${y1} C ${x1 + sx * cLen} ${y1 + sy * cLen} ${x2 - sx * cLen} ${y2 - sy * cLen} ${x2} ${y2}`
}

// Route from a node to the nearest point on a group bounding box border.
// Mirrors routeEdge's face-selection logic: picks the midpoint of whichever
// face of the box is most directly in front of the source node.
function routeEdgeToBox(
  fromId: string,
  bx: number, by: number, bw: number, bh: number,
): { path: string; ex: number; ey: number } | null {
  const s = pos[fromId]
  if (!s) return null

  const scx = s.x + NODE_W / 2, scy = s.y + NODE_H / 2
  const gcx = bx + bw / 2,      gcy = by + bh / 2
  const dx  = gcx - scx,        dy  = gcy - scy

  // Exit point on source node face
  let x1: number, y1: number
  if (Math.abs(dx) >= Math.abs(dy)) {
    ;[x1, y1] = dx >= 0 ? [s.x + NODE_W, scy] : [s.x, scy]
  } else {
    ;[x1, y1] = dy >= 0 ? [scx, s.y + NODE_H] : [scx, s.y]
  }

  // Entry point on group box border — midpoint of the facing face
  let x2: number, y2: number
  if (Math.abs(dx) >= Math.abs(dy)) {
    ;[x2, y2] = dx >= 0 ? [bx, gcy] : [bx + bw, gcy]
  } else {
    ;[x2, y2] = dy >= 0 ? [gcx, by] : [gcx, by + bh]
  }

  const isH  = Math.abs(dx) >= Math.abs(dy)
  const cLen = Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) * 0.45
  const sx   = isH ? Math.sign(x2 - x1) : 0
  const sy   = isH ? 0 : Math.sign(y2 - y1)

  return {
    path: `M ${x1} ${y1} C ${x1 + sx * cLen} ${y1 + sy * cLen} ${x2 - sx * cLen} ${y2 - sy * cLen} ${x2} ${y2}`,
    ex: x2,
    ey: y2,
  }
}

// Route from a group bounding box border to a target node.
// Symmetric counterpart of routeEdgeToBox.
function routeBoxToNode(
  bx: number, by: number, bw: number, bh: number,
  toId: string,
): { path: string; x1: number; y1: number } | null {
  const d = pos[toId]
  if (!d) return null

  const gcx = bx + bw / 2, gcy = by + bh / 2
  const dcx = d.x + NODE_W / 2, dcy = d.y + NODE_H / 2
  const dx = dcx - gcx, dy = dcy - gcy

  // Exit on group box border — midpoint of facing face
  let x1: number, y1: number
  if (Math.abs(dx) >= Math.abs(dy)) {
    ;[x1, y1] = dx >= 0 ? [bx + bw, gcy] : [bx, gcy]
  } else {
    ;[x1, y1] = dy >= 0 ? [gcx, by + bh] : [gcx, by]
  }

  // Entry on target node face
  let x2: number, y2: number
  if (Math.abs(dx) >= Math.abs(dy)) {
    ;[x2, y2] = dx >= 0 ? [d.x, dcy] : [d.x + NODE_W, dcy]
  } else {
    ;[x2, y2] = dy >= 0 ? [dcx, d.y] : [dcx, d.y + NODE_H]
  }

  const isH  = Math.abs(dx) >= Math.abs(dy)
  const cLen = Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) * 0.45
  const sx   = isH ? Math.sign(x2 - x1) : 0
  const sy   = isH ? 0 : Math.sign(y2 - y1)

  return {
    path: `M ${x1} ${y1} C ${x1 + sx * cLen} ${y1 + sy * cLen} ${x2 - sx * cLen} ${y2 - sy * cLen} ${x2} ${y2}`,
    x1, y1,
  }
}

// Route between two group bounding boxes.
function routeBoxToBox(
  ax: number, ay: number, aw: number, ah: number,
  bx: number, by: number, bw: number, bh: number,
): { path: string; x1: number; y1: number; x2: number; y2: number } | null {
  const acx = ax + aw / 2, acy = ay + ah / 2
  const bcx = bx + bw / 2, bcy = by + bh / 2
  const dx = bcx - acx, dy = bcy - acy

  // Exit on source box A
  let x1: number, y1: number
  if (Math.abs(dx) >= Math.abs(dy)) {
    ;[x1, y1] = dx >= 0 ? [ax + aw, acy] : [ax, acy]
  } else {
    ;[x1, y1] = dy >= 0 ? [acx, ay + ah] : [acx, ay]
  }

  // Entry on target box B
  let x2: number, y2: number
  if (Math.abs(dx) >= Math.abs(dy)) {
    ;[x2, y2] = dx >= 0 ? [bx, bcy] : [bx + bw, bcy]
  } else {
    ;[x2, y2] = dy >= 0 ? [bcx, by] : [bcx, by + bh]
  }

  const isH  = Math.abs(dx) >= Math.abs(dy)
  const cLen = Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) * 0.45
  const sx   = isH ? Math.sign(x2 - x1) : 0
  const sy   = isH ? 0 : Math.sign(y2 - y1)

  return {
    path: `M ${x1} ${y1} C ${x1 + sx * cLen} ${y1 + sy * cLen} ${x2 - sx * cLen} ${y2 - sy * cLen} ${x2} ${y2}`,
    x1, y1, x2, y2,
  }
}

// Computed map so edge paths re-evaluate reactively when positions change.
// Dispatches to one of four routing functions based on edge endpoint types.
const edgePaths = computed(() => {
  const m: Record<string, string> = {}
  for (const de of displayEdges.value) {
    const fgb = de.from_group_id ? groupBoundsMap.value[de.from_group_id] : null
    const tgb = de.to_group_id   ? groupBoundsMap.value[de.to_group_id]   : null

    if (fgb && tgb) {
      // Group → Group
      m[de.id] = routeBoxToBox(fgb.x, fgb.y, fgb.w, fgb.h, tgb.x, tgb.y, tgb.w, tgb.h)?.path ?? ''
    } else if (fgb && de.to_node) {
      // Group → Node
      m[de.id] = routeBoxToNode(fgb.x, fgb.y, fgb.w, fgb.h, de.to_node)?.path ?? ''
    } else if (tgb) {
      // Node → Group
      m[de.id] = routeEdgeToBox(de.from_node, tgb.x, tgb.y, tgb.w, tgb.h)?.path ?? ''
    } else if (de.to_node) {
      // Node → Node
      m[de.id] = routeEdge(de.from_node, de.to_node)
    }
  }
  return m
})

// Badge position for collapsed group edges.
// – to_group_id only:                badge at target group border entry
// – from_group_id only (→ node):     badge at source group border exit
// – from_group_id + to_group_id:     badge at target group border entry
const groupEdgeBadgePos = computed(() => {
  const m: Record<string, { x: number; y: number }> = {}
  for (const de of displayEdges.value) {
    if (de.collapsedCount <= 1) continue
    const fgb = de.from_group_id ? groupBoundsMap.value[de.from_group_id] : null
    const tgb = de.to_group_id   ? groupBoundsMap.value[de.to_group_id]   : null

    if (tgb) {
      // Badge at target group entry
      if (fgb) {
        const r = routeBoxToBox(fgb.x, fgb.y, fgb.w, fgb.h, tgb.x, tgb.y, tgb.w, tgb.h)
        if (r) m[de.id] = { x: r.x2, y: r.y2 }
      } else {
        const r = routeEdgeToBox(de.from_node, tgb.x, tgb.y, tgb.w, tgb.h)
        if (r) m[de.id] = { x: r.ex, y: r.ey }
      }
    } else if (fgb && de.to_node) {
      // Badge at source group exit (outbound collapse)
      const r = routeBoxToNode(fgb.x, fgb.y, fgb.w, fgb.h, de.to_node)
      if (r) m[de.id] = { x: r.x1, y: r.y1 }
    }
  }
  return m
})

// ── Group bounding boxes ───────────────────────────────────────────────────
function gBounds(g: DiagramGroup) {
  const pts = g.contains.map(id => pos[id]).filter(Boolean)
  if (!pts.length) return null
  const p = 20
  const minX = Math.min(...pts.map(q => q.x)) - p
  const minY = Math.min(...pts.map(q => q.y)) - p
  const maxX = Math.max(...pts.map(q => q.x + NODE_W)) + p
  const maxY = Math.max(...pts.map(q => q.y + NODE_H)) + p
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY }
}

const groupBoundsMap = computed(() => {
  const m: Record<string, ReturnType<typeof gBounds>> = {}
  for (const g of visibleGroups.value) m[g.id] = gBounds(g)
  return m
})

// ── Per-node shape metadata (avoids calling helpers multiple times in template)
const nodeShapeData = computed(() => {
  const m: Record<string, {
    kind: ShapeKind
    c: { fill: string; stroke: string }
    lY: number
    tY: number
    badge: VendorBadge | null
    glyph: TechIcon | null
    typeLabel: string
  }> = {}
  for (const n of visibleNodes.value) {
    const vendor = n.vendor ?? null
    const tech   = n.technology ?? null
    let typeLabel = tech || n.node_type
    if (vendor && !tech) typeLabel = `${vendor} · ${n.node_type}`
    m[n.id] = {
      kind:      shapeKind(n.node_type),
      c:         nodeColor(n.node_type, vendor),
      lY:        labelY(n.node_type),
      tY:        typeTextY(n.node_type),
      badge:     getVendorBadge(vendor),
      glyph:     getTechIcon(tech),
      typeLabel,
    }
  }
  return m
})

// ── Lasso ──────────────────────────────────────────────────────────────────
const lasso = ref<{ x1: number; y1: number; x2: number; y2: number } | null>(null)

// ── Connect ────────────────────────────────────────────────────────────────
const connectFrom = ref<string | null>(null)
const connectPreview = ref<{ x: number; y: number } | null>(null)

watch(tool, () => {
  lasso.value = null
  connectFrom.value = null
  connectPreview.value = null
})

// ── Selection helpers ──────────────────────────────────────────────────────
function handleSelect(id: string, additive: boolean) {
  if (additive) {
    if (selected.has(id)) selected.delete(id)
    else selected.add(id)
  } else {
    selected.clear()
    selected.add(id)
  }
}

// ── Pan / zoom ─────────────────────────────────────────────────────────────
const container  = ref<HTMLDivElement>()
const panX       = ref(0)
const panY       = ref(0)
const scale      = ref(1)
const isPanning  = ref(false)
const panStart   = ref({ x: 0, y: 0 })

function zoom(factor: number, ox: number, oy: number) {
  const s = Math.max(0.1, Math.min(5, scale.value * factor))
  const r = s / scale.value
  panX.value = ox - r * (ox - panX.value)
  panY.value = oy - r * (oy - panY.value)
  scale.value = s
}
function zoomBy(f: number) {
  if (!container.value) return
  const { width: w, height: h } = container.value.getBoundingClientRect()
  zoom(f, w / 2, h / 2)
}
function onWheel(e: WheelEvent) {
  e.preventDefault()
  const r = container.value!.getBoundingClientRect()
  zoom(e.deltaY > 0 ? 0.9 : 1.1, e.clientX - r.left, e.clientY - r.top)
}

function fitView() {
  if (!container.value) return
  const { width: cw, height: ch } = container.value.getBoundingClientRect()
  const s = Math.min((cw - 48) / canvasW.value, (ch - 48) / canvasH.value)
  scale.value = s
  panX.value = (cw - canvasW.value * s) / 2
  panY.value = (ch - canvasH.value * s) / 2
}

// ── Drag ───────────────────────────────────────────────────────────────────
const drag = ref<{ id: string; offX: number; offY: number } | null>(null)

// Group drag — moves all member nodes together
interface GroupDragState {
  groupId: string
  memberIds: string[]
  /** Per-node offset from the SVG pointer position at drag start. */
  offsets: Record<string, { dx: number; dy: number }>
}
const groupDrag = ref<GroupDragState | null>(null)

let _pdClient = { x: 0, y: 0 }  // pointerdown client coords, used to detect click vs drag

function toSvg(cx: number, cy: number) {
  const r = container.value!.getBoundingClientRect()
  return { x: (cx - r.left - panX.value) / scale.value, y: (cy - r.top - panY.value) / scale.value }
}

function onNodePointerDown(e: PointerEvent, id: string) {
  e.stopPropagation()
  _pdClient = { x: e.clientX, y: e.clientY }

  if (tool.value === 'connect') {
    if (!connectFrom.value) {
      connectFrom.value = id
    } else if (connectFrom.value !== id) {
      addEdge(connectFrom.value, id)
      connectFrom.value = null
      connectPreview.value = null
    } else {
      connectFrom.value = null
      connectPreview.value = null
    }
    return
  }

  const p = pos[id]; if (!p) return
  const sv = toSvg(e.clientX, e.clientY)
  drag.value = { id, offX: sv.x - p.x, offY: sv.y - p.y }
  ;(e.currentTarget as Element).setPointerCapture(e.pointerId)
}

function onGroupPointerDown(e: PointerEvent, g: DiagramGroup) {
  e.stopPropagation()
  if (tool.value === 'connect') return
  _pdClient = { x: e.clientX, y: e.clientY }

  const sv = toSvg(e.clientX, e.clientY)
  const offsets: Record<string, { dx: number; dy: number }> = {}
  for (const nid of g.contains) {
    const p = pos[nid]
    if (p) offsets[nid] = { dx: sv.x - p.x, dy: sv.y - p.y }
  }
  groupDrag.value = { groupId: g.id, memberIds: g.contains, offsets }
  ;(e.currentTarget as Element).setPointerCapture(e.pointerId)
}

function onCanvasPointerDown(e: PointerEvent) {
  if (e.button !== 0 || drag.value || groupDrag.value) return
  _pdClient = { x: e.clientX, y: e.clientY }

  if (tool.value === 'lasso') {
    const sv = toSvg(e.clientX, e.clientY)
    lasso.value = { x1: sv.x, y1: sv.y, x2: sv.x, y2: sv.y }
  } else if (tool.value === 'connect') {
    connectFrom.value = null
    connectPreview.value = null
  } else {
    isPanning.value = true
    panStart.value = { x: e.clientX - panX.value, y: e.clientY - panY.value }
  }
}

function onPointerMove(e: PointerEvent) {
  if (tool.value === 'connect' && connectFrom.value) {
    connectPreview.value = toSvg(e.clientX, e.clientY)
  }
  if (lasso.value) {
    const sv = toSvg(e.clientX, e.clientY)
    lasso.value = { ...lasso.value, x2: sv.x, y2: sv.y }
    return
  }
  if (drag.value) {
    const sv = toSvg(e.clientX, e.clientY)
    pos[drag.value.id] = {
      x: snap(Math.max(0, sv.x - drag.value.offX)),
      y: snap(Math.max(0, sv.y - drag.value.offY)),
    }
    return
  }
  if (groupDrag.value) {
    const sv = toSvg(e.clientX, e.clientY)
    // Snap the group as a unit: snap the first member's candidate position,
    // then apply the same integer offset to all other members so the group
    // moves in locked grid steps without internal re-arrangement.
    const firstId  = groupDrag.value.memberIds[0]
    const firstOff = groupDrag.value.offsets[firstId]
    if (firstOff) {
      const rawX = sv.x - firstOff.dx
      const rawY = sv.y - firstOff.dy
      const snappedX = snap(Math.max(0, rawX))
      const snappedY = snap(Math.max(0, rawY))
      const dxSnap = snappedX - rawX
      const dySnap = snappedY - rawY
      for (const nid of groupDrag.value.memberIds) {
        const off = groupDrag.value.offsets[nid]
        if (!off) continue
        pos[nid] = {
          x: Math.max(0, sv.x - off.dx + dxSnap),
          y: Math.max(0, sv.y - off.dy + dySnap),
        }
      }
    }
    return
  }
  if (isPanning.value) {
    panX.value = e.clientX - panStart.value.x
    panY.value = e.clientY - panStart.value.y
  }
}

function onPointerUp(e: PointerEvent) {
  const moved = Math.hypot(e.clientX - _pdClient.x, e.clientY - _pdClient.y) > 4

  if (lasso.value) {
    if (moved) {
      const { x1, y1, x2, y2 } = lasso.value
      const minX = Math.min(x1, x2), maxX = Math.max(x1, x2)
      const minY = Math.min(y1, y2), maxY = Math.max(y1, y2)
      if (!e.ctrlKey && !e.metaKey) selected.clear()
      for (const n of visibleNodes.value) {
        const p = pos[n.id]; if (!p) continue
        if (p.x < maxX && p.x + NODE_W > minX && p.y < maxY && p.y + NODE_H > minY)
          selected.add(n.id)
      }
    }
    lasso.value = null
    return
  }

  if (drag.value) {
    if (moved) {
      const p = pos[drag.value.id]
      updateNodePosition(drag.value.id, p.x, p.y)
    } else {
      handleSelect(drag.value.id, e.ctrlKey || e.metaKey)
    }
    drag.value = null
  } else if (groupDrag.value) {
    if (moved) {
      for (const nid of groupDrag.value.memberIds) {
        const p = pos[nid]
        if (p) updateNodePosition(nid, p.x, p.y)
      }
    }
    groupDrag.value = null
  } else if (isPanning.value && !moved) {
    selected.clear()
  }
  isPanning.value = false
}

// ── Drop (from ShapePanel) ─────────────────────────────────────────────────
const isDragOver = ref(false)
let dragDepth = 0  // counter to avoid dragleave flicker on child elements

function onDragEnter(e: DragEvent) {
  if (!e.dataTransfer?.types.includes('application/x-sw-shape')) return
  dragDepth++
  isDragOver.value = true
}

function onDragLeave() {
  dragDepth--
  if (dragDepth <= 0) { dragDepth = 0; isDragOver.value = false }
}

function onDragOver(e: DragEvent) {
  if (!e.dataTransfer?.types.includes('application/x-sw-shape')) return
  e.preventDefault()
  e.dataTransfer.dropEffect = 'copy'
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false; dragDepth = 0
  const raw = e.dataTransfer?.getData('application/x-sw-shape')
  if (!raw) return
  const { nodeType, label, vendor, technology } = JSON.parse(raw) as { nodeType: string; label: string; vendor?: string; technology?: string }
  const sv = toSvg(e.clientX, e.clientY)
  const id = addNode(nodeType, label, vendor, technology)
  if (id) pos[id] = { x: snap(Math.max(0, sv.x - NODE_W / 2)), y: snap(Math.max(0, sv.y - NODE_H / 2)) }
}

// ── Context menu ───────────────────────────────────────────────────────────
const ctxMenu = ref<{ x: number; y: number; type: 'node' | 'edge' | 'canvas'; id?: string } | null>(null)

function openCtxNode(e: MouseEvent, id: string) {
  ctxMenu.value = { x: e.clientX, y: e.clientY, type: 'node', id }
}
function openCtxEdge(e: MouseEvent, id: string) {
  ctxMenu.value = { x: e.clientX, y: e.clientY, type: 'edge', id }
}
function openCtxCanvas(e: MouseEvent) {
  ctxMenu.value = { x: e.clientX, y: e.clientY, type: 'canvas' }
}

function duplicateNode(id: string) {
  const node = dir.value?.nodes.find(n => n.id === id)
  const p = pos[id]
  if (!node || !p) return
  const newId = addNode(node.node_type, node.label)
  if (!newId) return
  updateNode(newId, { description: node.description })
  pos[newId] = { x: snap(p.x + GRID), y: snap(p.y + GRID) }
}

function resetLayout() {
  if (!dir.value) return
  // No stored seed — forces a fresh BFS + full optimization pass
  const computed = snapLayout(autoLayout(dir.value, undefined, { nodeW: NODE_W, nodeH: NODE_H }))
  for (const [id, p] of Object.entries(computed)) {
    pos[id] = p
    updateNodePosition(id, p.x, p.y)
  }
  nextTick(fitView)
}

// ── External layout reset (triggered by SyncBar "Recalibrate") ────────────
// Watches layoutResetToken from useSystem. When incremented, clears all
// stored positions and runs a full fresh layout — same as resetLayout() but
// initiated from outside the canvas.
watch(layoutResetToken, (token) => {
  if (token === 0) return   // initial value, don't fire on mount
  resetLayout()
})

const ctxMenuItems = computed((): CtxItem[] => {
  const ctx = ctxMenu.value
  if (!ctx) return []

  if (ctx.type === 'node' && ctx.id) {
    const node = dir.value?.nodes.find(n => n.id === ctx.id)
    if (!node) return []
    return [
      { label: 'Duplicate', action: () => duplicateNode(ctx.id!) },
      { label: 'Delete node', danger: true, action: () => { deleteNode(ctx.id!); selected.delete(ctx.id!) } },
    ]
  }

  if (ctx.type === 'edge' && ctx.id) {
    const edge = dir.value?.edges.find(e => e.id === ctx.id)
    if (!edge) return []
    return [
      { label: 'Reverse direction', action: () => updateEdge(ctx.id!, { direction: edge.direction === 'backward' ? 'forward' : 'backward' }) },
      { label: 'Delete edge', danger: true, action: () => deleteEdge(ctx.id!) },
      { divider: true },
      { label: 'Style', subtle: true },
      { label: 'Solid',  checked: edge.style === 'solid',  action: () => updateEdge(ctx.id!, { style: 'solid' }) },
      { label: 'Dashed', checked: edge.style === 'dashed', action: () => updateEdge(ctx.id!, { style: 'dashed' }) },
      { label: 'Dotted', checked: edge.style === 'dotted', action: () => updateEdge(ctx.id!, { style: 'dotted' }) },
      { divider: true },
      { label: 'Direction', subtle: true },
      { label: '→ Forward',      checked: edge.direction === 'forward',       action: () => updateEdge(ctx.id!, { direction: 'forward' }) },
      { label: '← Backward',     checked: edge.direction === 'backward',      action: () => updateEdge(ctx.id!, { direction: 'backward' }) },
      { label: '↔ Both ways',    checked: edge.direction === 'bidirectional', action: () => updateEdge(ctx.id!, { direction: 'bidirectional' }) },
    ]
  }

  // canvas
  return [
    { label: 'Fit view',    action: fitView },
    { label: 'Select all',  action: () => { for (const n of visibleNodes.value) selected.add(n.id) } },
    { divider: true },
    { label: 'Reset layout', action: resetLayout },
  ]
})

// ── Keyboard shortcuts ──────────────────────────────────────────────────────
function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (ctxMenu.value) { ctxMenu.value = null; return }
    connectFrom.value = null; connectPreview.value = null
    lasso.value = null; selected.clear()
  }
  if (e.key === 'g' && !e.ctrlKey && !e.metaKey) tool.value = 'grab'
  if (e.key === 'l' && !e.ctrlKey && !e.metaKey) tool.value = 'lasso'
  if (e.key === 'c' && !e.ctrlKey && !e.metaKey) tool.value = 'connect'
}

onMounted(() => {
  container.value?.addEventListener('wheel', onWheel, { passive: false })
  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => {
  container.value?.removeEventListener('wheel', onWheel)
  window.removeEventListener('keydown', onKeyDown)
})

// ── Viewport style ─────────────────────────────────────────────────────────
const vpStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  transformOrigin: '0 0',
}))

// ── Dash array ─────────────────────────────────────────────────────────────
const DASH: Record<string, string> = { solid: 'none', dashed: '8 4', dotted: '2 3' }

// ── Grid ────────────────────────────────────────────────────────────────────
const GRID       = 20   // minor grid pitch (px) — drag snap resolution
const GRID_MAJOR = 80   // major grid pitch (px) — visual reference every 4 cells

/** Snap a coordinate to the nearest minor grid line. */
function snap(v: number): number {
  return Math.round(v / GRID) * GRID
}

/** Snap every position in a layout result map to the minor grid. */
function snapLayout(
  layout: Record<string, { x: number; y: number }>,
): Record<string, { x: number; y: number }> {
  const out: Record<string, { x: number; y: number }> = {}
  for (const [id, p] of Object.entries(layout)) out[id] = { x: snap(p.x), y: snap(p.y) }
  return out
}
</script>

<template>
  <div
    ref="container"
    :class="['diagram-canvas', {
      'diagram-canvas--panning': isPanning && !drag && !groupDrag,
      'diagram-canvas--drop': isDragOver,
      'diagram-canvas--lasso': tool === 'lasso',
      'diagram-canvas--connect': tool === 'connect',
    }]"
    @pointerdown="onCanvasPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointerleave="onPointerUp"
    @dragenter="onDragEnter"
    @dragleave="onDragLeave"
    @dragover="onDragOver"
    @drop="onDrop"
    @contextmenu.prevent="openCtxCanvas"
  >
    <div class="diagram-canvas__viewport" :style="vpStyle">
      <svg
        :width="canvasW"
        :height="canvasH"
        :viewBox="`0 0 ${canvasW} ${canvasH}`"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <!-- Minor grid — one small dot every 20 px -->
          <pattern id="sw-grid-minor" :width="GRID" :height="GRID" patternUnits="userSpaceOnUse">
            <circle cx="0.5" cy="0.5" r="0.6" fill="var(--grid-dot-minor)" />
          </pattern>
          <!-- Major grid — slightly larger dot every 80 px for orientation -->
          <pattern id="sw-grid-major" :width="GRID_MAJOR" :height="GRID_MAJOR" patternUnits="userSpaceOnUse">
            <circle cx="0.5" cy="0.5" r="1.2" fill="var(--grid-dot-major)" />
          </pattern>

          <marker id="sw-arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#888" />
          </marker>
          <marker id="sw-arr-rev" markerWidth="10" markerHeight="7" refX="1" refY="3.5" orient="auto-start-reverse">
            <polygon points="0 0, 10 3.5, 0 7" fill="#888" />
          </marker>
          <marker id="sw-arr-sel" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="var(--accent)" />
          </marker>
          <marker id="sw-arr-rev-sel" markerWidth="10" markerHeight="7" refX="1" refY="3.5" orient="auto-start-reverse">
            <polygon points="0 0, 10 3.5, 0 7" fill="var(--accent)" />
          </marker>
        </defs>

        <!-- ── Grid background (minor + major layers) ──────────────────── -->
        <rect width="100%" height="100%" fill="url(#sw-grid-minor)" pointer-events="none" />
        <rect width="100%" height="100%" fill="url(#sw-grid-major)" pointer-events="none" />

        <!-- ── Groups (behind everything) ────────────────────────────────── -->
        <g id="sw-groups">
          <template v-for="g in visibleGroups" :key="g.id">
            <g
              v-if="groupBoundsMap[g.id]"
              :class="['sw-group', { 'sw-group--dragging': groupDrag?.groupId === g.id }]"
              @pointerdown.stop="onGroupPointerDown($event, g)"
            >
              <rect
                :x="groupBoundsMap[g.id]!.x"
                :y="groupBoundsMap[g.id]!.y"
                :width="groupBoundsMap[g.id]!.w"
                :height="groupBoundsMap[g.id]!.h"
                rx="8"
                fill="rgba(0,0,0,0.02)"
                stroke="#bbb"
                stroke-width="1.5"
                stroke-dasharray="6 3"
                style="cursor: grab"
              />
              <text
                :x="groupBoundsMap[g.id]!.x + 10"
                :y="groupBoundsMap[g.id]!.y + 17"
                class="sw-group-label"
                style="cursor: grab; pointer-events: none"
              >{{ g.label }}</text>
            </g>
          </template>
        </g>

        <!-- ── Edges ─────────────────────────────────────────────────────── -->
        <g id="sw-edges">
          <g
            v-for="de in displayEdges"
            :key="de.id"
            :class="['sw-edge', { 'sw-edge--selected': selected.has(de.id) }]"
            style="cursor: pointer"
            @pointerdown.stop="_pdClient = { x: $event.clientX, y: $event.clientY }"
            @click.stop="handleSelect(de.id, $event.ctrlKey || $event.metaKey)"
            @contextmenu.prevent.stop="openCtxEdge($event, de.id)"
          >
            <!-- Wide invisible hit area -->
            <path :d="edgePaths[de.id]" fill="none" stroke="transparent" stroke-width="12" />
            <!-- Visible stroke — group edges render slightly lighter to distinguish them -->
            <path
              class="sw-edge-line"
              :d="edgePaths[de.id]"
              fill="none"
              :stroke="selected.has(de.id) ? 'var(--accent)' : (de.to_group_id || de.from_group_id ? '#aac4e0' : '#8da8c8')"
              :stroke-width="selected.has(de.id) ? 2.5 : 1.5"
              :stroke-dasharray="de.to_group_id || de.from_group_id ? '6 3' : DASH[de.style]"
              :marker-end="de.direction !== 'backward' ? (selected.has(de.id) ? 'url(#sw-arr-sel)' : 'url(#sw-arr)') : undefined"
              :marker-start="de.direction === 'bidirectional' || de.direction === 'backward' ? (selected.has(de.id) ? 'url(#sw-arr-rev-sel)' : 'url(#sw-arr-rev)') : undefined"
            />
            <!-- Collapsed count badge — at group border entry (inbound) or exit (outbound) -->
            <template v-if="de.collapsedCount > 1 && groupEdgeBadgePos[de.id]">
              <circle
                :cx="groupEdgeBadgePos[de.id].x"
                :cy="groupEdgeBadgePos[de.id].y"
                r="9"
                fill="var(--bg-chrome)"
                stroke="#aac4e0"
                stroke-width="1"
              />
              <text
                :x="groupEdgeBadgePos[de.id].x"
                :y="groupEdgeBadgePos[de.id].y + 4"
                text-anchor="middle"
                style="font: bold 9px system-ui, sans-serif; fill: #7aa3c4; pointer-events: none;"
              >{{ de.collapsedCount }}</text>
            </template>
            <!-- Edge label text is intentionally hidden — diagrams stay clean.
                 de.label / de.description is preserved for future hover/tooltip. -->
          </g>
        </g>

        <!-- ── Nodes ─────────────────────────────────────────────────────── -->
        <g id="sw-nodes">
          <g
            v-for="n in visibleNodes"
            :key="n.id"
            :class="['sw-node', {
              'sw-node--dragging': drag?.id === n.id,
              'sw-node--selected': selected.has(n.id),
              'sw-node--connect-source': connectFrom === n.id,
            }]"
            :transform="pos[n.id] ? `translate(${pos[n.id].x}, ${pos[n.id].y})` : ''"
            @pointerdown.stop="onNodePointerDown($event, n.id)"
            @contextmenu.prevent.stop="openCtxNode($event, n.id)"
          >
            <title>{{ n.label }}{{ n.description ? ` — ${n.description}` : '' }}</title>

            <!-- Shape group — hover/drag filters applied here -->
            <g class="sw-node-shape">
              <!-- Ellipse: user -->
              <ellipse
                v-if="nodeShapeData[n.id]?.kind === 'ellipse'"
                cx="80" cy="30" rx="79" ry="29"
                :fill="nodeShapeData[n.id].c.fill"
                :stroke="nodeShapeData[n.id].c.stroke"
                stroke-width="1.5"
              />

              <!-- Diamond: gateway, aws.api_gateway -->
              <path
                v-else-if="nodeShapeData[n.id]?.kind === 'diamond'"
                d="M 80 2 L 158 30 L 80 58 L 2 30 Z"
                :fill="nodeShapeData[n.id].c.fill"
                :stroke="nodeShapeData[n.id].c.stroke"
                stroke-width="1.5"
              />

              <!-- Cylinder: database, storage, aws.rds, aws.s3, aws.elasticache -->
              <template v-else-if="nodeShapeData[n.id]?.kind === 'cylinder'">
                <!-- Body fill (straight top, curved bottom) -->
                <path
                  d="M 2 12 L 2 54 A 78 11 0 0 0 158 54 L 158 12 Z"
                  :fill="nodeShapeData[n.id].c.fill"
                  stroke="none"
                />
                <!-- Cap fill (top disc) -->
                <ellipse cx="80" cy="12" rx="78" ry="11" :fill="nodeShapeData[n.id].c.fill" stroke="none"/>
                <!-- Cap darkening overlay for 3-D depth -->
                <ellipse cx="80" cy="12" rx="78" ry="11" fill="rgba(0,0,0,0.06)" stroke="none"/>
                <!-- Strokes: sides + bottom arc + top arc -->
                <line x1="2" y1="12" x2="2" y2="54" :stroke="nodeShapeData[n.id].c.stroke" stroke-width="1.5"/>
                <line x1="158" y1="12" x2="158" y2="54" :stroke="nodeShapeData[n.id].c.stroke" stroke-width="1.5"/>
                <path d="M 2 54 A 78 11 0 0 0 158 54" fill="none" :stroke="nodeShapeData[n.id].c.stroke" stroke-width="1.5"/>
                <path d="M 2 12 A 78 11 0 0 1 158 12" fill="none" :stroke="nodeShapeData[n.id].c.stroke" stroke-width="1.5"/>
              </template>

              <!-- Parallelogram: queue -->
              <path
                v-else-if="nodeShapeData[n.id]?.kind === 'parallelogram'"
                d="M 14 2 L 158 2 L 146 58 L 2 58 Z"
                :fill="nodeShapeData[n.id].c.fill"
                :stroke="nodeShapeData[n.id].c.stroke"
                stroke-width="1.5"
                stroke-linejoin="round"
              />

              <!-- Plain rect: generic, aws.ec2 -->
              <rect
                v-else-if="nodeShapeData[n.id]?.kind === 'rect'"
                :width="NODE_W" :height="NODE_H" rx="3"
                :fill="nodeShapeData[n.id].c.fill"
                :stroke="nodeShapeData[n.id].c.stroke"
                stroke-width="1.5"
              />

              <!-- Rounded rect (default): service, aws.lambda, etc. -->
              <rect
                v-else
                :width="NODE_W" :height="NODE_H" rx="8"
                :fill="nodeShapeData[n.id]?.c.fill"
                :stroke="nodeShapeData[n.id]?.c.stroke"
                stroke-width="1.5"
              />
            </g>

            <!-- Labels (always on top of shape) -->
            <text
              :x="NODE_W / 2"
              :y="nodeShapeData[n.id]?.lY ?? 26"
              dominant-baseline="middle"
              text-anchor="middle"
              class="sw-node-label"
            >{{ n.label }}</text>
            <text
              :x="NODE_W / 2"
              :y="nodeShapeData[n.id]?.tY ?? 44"
              text-anchor="middle"
              class="sw-node-type"
            >{{ nodeShapeData[n.id]?.typeLabel ?? n.node_type }}</text>

            <!--
              Technology glyph — simple-icons SVG path scaled to ~18×18,
              centred in the top portion of the node.
              Only rendered when a matching icon exists in the registry.
            -->
            <g
              v-if="nodeShapeData[n.id]?.glyph"
              :transform="`translate(${NODE_W / 2 - 9}, 3) scale(0.75)`"
              opacity="0.22"
              pointer-events="none"
            >
              <path :d="nodeShapeData[n.id].glyph!.path" :fill="nodeShapeData[n.id].glyph!.fill"/>
            </g>

            <!--
              Vendor badge — top-right corner, 18×18 bounding box.
              Renders the vendor's simple-icons path on a coloured circle,
              or falls back to a coloured pill with a short text abbreviation.
            -->
            <g
              v-if="nodeShapeData[n.id]?.badge"
              :transform="`translate(${NODE_W - 20}, 2)`"
              pointer-events="none"
            >
              <!-- Background circle -->
              <circle
                cx="9" cy="9" r="9"
                :fill="nodeShapeData[n.id].badge!.fill"
              />
              <!-- simple-icons path (24×24 → scaled to 18×18 inside circle) -->
              <g
                v-if="nodeShapeData[n.id].badge!.iconPath"
                :transform="`translate(${9 - 9 * 0.75}, ${9 - 9 * 0.75}) scale(0.75)`"
              >
                <path
                  :d="nodeShapeData[n.id].badge!.iconPath"
                  :fill="nodeShapeData[n.id].badge!.textColor"
                />
              </g>
              <!-- Text fallback (AWS, AZ) when no iconPath -->
              <text
                v-else
                x="9" y="9"
                dominant-baseline="middle"
                text-anchor="middle"
                :fill="nodeShapeData[n.id].badge!.textColor"
                style="font: bold 5px system-ui, sans-serif;"
              >{{ nodeShapeData[n.id].badge!.label }}</text>
            </g>

            <!-- Shape-matched selection ring -->
            <template v-if="selected.has(n.id)">
              <!-- ellipse: user -->
              <ellipse
                v-if="nodeShapeData[n.id]?.kind === 'ellipse'"
                cx="80" cy="30" rx="79" ry="29"
                class="sw-sel-ring" pointer-events="none"
              />
              <!-- diamond: gateway -->
              <path
                v-else-if="nodeShapeData[n.id]?.kind === 'diamond'"
                d="M 80 2 L 158 30 L 80 58 L 2 30 Z"
                class="sw-sel-ring" pointer-events="none"
              />
              <!-- cylinder: database / storage -->
              <template v-else-if="nodeShapeData[n.id]?.kind === 'cylinder'">
                <line x1="2" y1="12" x2="2" y2="54" class="sw-sel-ring" pointer-events="none"/>
                <line x1="158" y1="12" x2="158" y2="54" class="sw-sel-ring" pointer-events="none"/>
                <path d="M 2 54 A 78 11 0 0 0 158 54" class="sw-sel-ring" pointer-events="none"/>
                <path d="M 2 12 A 78 11 0 0 1 158 12" class="sw-sel-ring" pointer-events="none"/>
              </template>
              <!-- parallelogram: queue -->
              <path
                v-else-if="nodeShapeData[n.id]?.kind === 'parallelogram'"
                d="M 14 2 L 158 2 L 146 58 L 2 58 Z"
                class="sw-sel-ring" stroke-linejoin="round" pointer-events="none"
              />
              <!-- plain rect: generic / aws.ec2 -->
              <rect
                v-else-if="nodeShapeData[n.id]?.kind === 'rect'"
                :width="NODE_W" :height="NODE_H" rx="3"
                class="sw-sel-ring" pointer-events="none"
              />
              <!-- default: rounded rect (service etc.) -->
              <rect
                v-else
                :width="NODE_W" :height="NODE_H" rx="8"
                class="sw-sel-ring" pointer-events="none"
              />
            </template>
          </g>
        </g>
        <!-- ── Connect preview ───────────────────────────────────────────── -->
        <line
          v-if="connectFrom && connectPreview && pos[connectFrom]"
          :x1="pos[connectFrom].x + NODE_W / 2"
          :y1="pos[connectFrom].y + NODE_H / 2"
          :x2="connectPreview.x"
          :y2="connectPreview.y"
          stroke="var(--accent)"
          stroke-width="1.5"
          stroke-dasharray="5 3"
          pointer-events="none"
        />

        <!-- ── Lasso rect ─────────────────────────────────────────────────── -->
        <rect
          v-if="lasso"
          :x="Math.min(lasso.x1, lasso.x2)"
          :y="Math.min(lasso.y1, lasso.y2)"
          :width="Math.abs(lasso.x2 - lasso.x1)"
          :height="Math.abs(lasso.y2 - lasso.y1)"
          fill="rgba(108, 142, 191, 0.08)"
          stroke="var(--accent)"
          stroke-width="1"
          stroke-dasharray="5 3"
          pointer-events="none"
        />
      </svg>
    </div>

    <!-- ── Context menu ──────────────────────────────────────────────────── -->
    <Transition name="ctx">
      <ContextMenu
        v-if="ctxMenu"
        :x="ctxMenu.x"
        :y="ctxMenu.y"
        :items="ctxMenuItems"
        @close="ctxMenu = null"
      />
    </Transition>

    <!-- ── Controls ──────────────────────────────────────────────────────── -->
    <div class="diagram-canvas__controls">
      <button class="diagram-canvas__ctrl-btn" title="Fit view" @click="fitView">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M1 5V1h4M9 1h4v4M13 9v4H9M5 13H1V9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <button class="diagram-canvas__ctrl-btn" title="Zoom in" @click="zoomBy(1.25)">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 3v8M3 7h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
      <button class="diagram-canvas__ctrl-btn" title="Zoom out" @click="zoomBy(0.8)">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 7h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.diagram-canvas {
  width: 100%;
  height: 100%;
  background: var(--canvas-bg);
  overflow: hidden;
  position: relative;
  cursor: grab;
  user-select: none;
  --grid-dot-minor: #d4d4dc;
  --grid-dot-major: #b4b4c0;
}
@media (prefers-color-scheme: dark) {
  .diagram-canvas {
    --grid-dot-minor: #2e2e3e;
    --grid-dot-major: #48485e;
  }
}
.diagram-canvas--panning { cursor: grabbing; }
.diagram-canvas--drop { outline: 2px dashed var(--accent); outline-offset: -3px; }
.diagram-canvas--lasso { cursor: crosshair; }
.diagram-canvas--connect { cursor: crosshair; }
.diagram-canvas--connect .sw-node { cursor: pointer; }

.diagram-canvas__viewport {
  position: absolute;
  top: 0; left: 0;
  will-change: transform;
}

/* ── Nodes ─────────────────────────────────────────────────────────────── */
.sw-node {
  cursor: grab;
}
.sw-node:hover .sw-node-shape {
  filter: brightness(0.94);
}
.sw-node--dragging {
  cursor: grabbing;
}
.sw-node--dragging .sw-node-shape {
  filter: drop-shadow(0 4px 14px rgba(0, 0, 0, 0.2));
}
.sw-node--connect-source .sw-node-shape {
  filter: drop-shadow(0 0 6px var(--accent));
}
.diagram-canvas--connect .sw-node:hover .sw-node-shape {
  filter: brightness(0.9) drop-shadow(0 0 4px var(--accent));
}
.sw-node-label {
  font: 600 13px system-ui, sans-serif;
  fill: #1e293b;
  pointer-events: none;
}
.sw-node-type {
  font: 10px monospace;
  fill: #8898aa;
  pointer-events: none;
}

/* ── Node selection ring ───────────────────────────────────────────────── */
.sw-sel-ring {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2.5;
  animation:
    sw-sel-pop  0.12s ease-out,
    sw-sel-glow 2s   ease-in-out 0.12s infinite;
}

@keyframes sw-sel-pop {
  from { opacity: 0; stroke-width: 7; }
  to   { opacity: 1; stroke-width: 2.5; }
}

@keyframes sw-sel-glow {
  0%, 100% { filter: drop-shadow(0 0 3px var(--accent)); opacity: 0.85; }
  50%      { filter: drop-shadow(0 0 8px var(--accent)); opacity: 1; }
}

/* ── Edge selection ────────────────────────────────────────────────────── */
.sw-edge-line {
  transition: stroke 0.1s, stroke-width 0.1s;
}

.sw-edge--selected .sw-edge-line {
  animation: sw-sel-glow 2s ease-in-out infinite;
}

/* ── Edges ─────────────────────────────────────────────────────────────── */
.sw-edge-label {
  font: 11px system-ui, sans-serif;
  fill: #4e6080;
  pointer-events: none;
}

/* ── Groups ────────────────────────────────────────────────────────────── */
.sw-group-label {
  font: 600 11px system-ui, sans-serif;
  fill: #7a8ba8;
  pointer-events: none;
}
.sw-group--dragging rect {
  cursor: grabbing !important;
  stroke: var(--accent);
  stroke-width: 2;
}

/* ── Controls ──────────────────────────────────────────────────────────── */
.diagram-canvas__controls {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.diagram-canvas__ctrl-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: #fff;
  border: 1px solid var(--canvas-border);
  border-radius: var(--radius-sm);
  color: #4e6080;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: background 0.1s, color 0.1s;
}
.diagram-canvas__ctrl-btn:hover {
  background: var(--canvas-bg);
  color: #1e293b;
}

/* ── Context menu transition ─────────────────────────────────────────────── */
.ctx-enter-active {
  transition: opacity 0.12s ease-out, transform 0.12s ease-out;
}
.ctx-leave-active {
  transition: opacity 0.08s ease-in, transform 0.08s ease-in;
}
.ctx-enter-from,
.ctx-leave-to {
  opacity: 0;
  transform: scale(0.94) translateY(-4px);
}
</style>
