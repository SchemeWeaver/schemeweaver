<script setup lang="ts">
import { useSystem } from '~/composables/useSystem'
import { useTool } from '~/composables/useTool'
import ContextMenu from '~/components/ContextMenu.vue'
import type { CtxItem } from '~/components/ContextMenu.vue'
import type { DiagramGroup, DiagramNode, DIR } from '~/types/dir'
import { shapeKind, labelY, typeTextY, nodeColor } from '~/utils/nodeShapes'
import type { ShapeKind } from '~/utils/nodeShapes'

// ── Layout constants (must match Python layout.py) ─────────────────────────
const NODE_W = 160
const NODE_H = 60
const H_GAP  = 80
const V_GAP  = 100
const PAD    = 80

// ── Layout engine (mirrors Python BFS layering in layout.py) ──────────────
function autoLayout(d: DIR): Record<string, { x: number; y: number }> {
  const childIds = new Set<string>()
  const walk = (nodes: DiagramNode[]) => {
    for (const n of nodes) {
      for (const c of n.children ?? []) { childIds.add(c.id); walk([c]) }
    }
  }
  walk(d.nodes)

  const top = d.nodes.filter(n => !childIds.has(n.id))
  if (!top.length) return {}

  const ids  = top.map(n => n.id)
  const set  = new Set(ids)
  const inDeg: Record<string, number> = Object.fromEntries(ids.map(id => [id, 0]))
  const adj:   Record<string, string[]> = Object.fromEntries(ids.map(id => [id, []]))

  for (const e of d.edges) {
    if (set.has(e.from_node) && set.has(e.to_node)) {
      adj[e.from_node].push(e.to_node)
      inDeg[e.to_node]++
    }
  }

  // Kahn's BFS layering
  const q = ids.filter(id => !inDeg[id])
  const layers: string[][] = []
  const seen = new Set<string>()
  while (q.length) {
    const layer: string[] = []
    for (let n = q.length; n > 0; n--) {
      const id = q.shift()!
      if (seen.has(id)) continue
      seen.add(id); layer.push(id)
      for (const nb of adj[id]) if (!--inDeg[nb]) q.push(nb)
    }
    if (layer.length) layers.push(layer)
  }
  const leftover = ids.filter(id => !seen.has(id))
  if (leftover.length) layers.push(leftover)

  // First-pass x (temporary)
  const result: Record<string, { x: number; y: number }> = {}
  let y = PAD; let maxW = 0
  for (const layer of layers) {
    const w = layer.length * NODE_W + (layer.length - 1) * H_GAP
    maxW = Math.max(maxW, w)
    layer.forEach((id, i) => { result[id] = { x: PAD + i * (NODE_W + H_GAP), y } })
    y += NODE_H + V_GAP
  }

  // Center each layer
  const cW = Math.max(maxW + 2 * PAD, 800)
  for (const layer of layers) {
    const w = layer.length * NODE_W + (layer.length - 1) * H_GAP
    const x0 = (cW - w) / 2
    layer.forEach((id, i) => { result[id].x = x0 + i * (NODE_W + H_GAP) })
  }
  return result
}

// ── Composable ─────────────────────────────────────────────────────────────
const { dir, updateNodePosition, addNode, addEdge, deleteNode, deleteEdge, updateNode, updateEdge } = useSystem()
const { tool } = useTool()

// ── Node positions (reactive, keyed by node id) ────────────────────────────
const pos = reactive<Record<string, { x: number; y: number }>>({})

// ── Selection ──────────────────────────────────────────────────────────────
const selected = reactive(new Set<string>())

watch(
  dir,
  (d) => {
    selected.clear()
    for (const k of Object.keys(pos)) delete pos[k]
    if (!d) return
    const computed = autoLayout(d)
    for (const node of d.nodes) {
      // Prefer stored positions from a previous save/load
      pos[node.id] = (node.x != null && node.y != null)
        ? { x: node.x, y: node.y }
        : computed[node.id] ?? { x: PAD, y: PAD }
    }
    nextTick(fitView)
  },
  { immediate: true },
)

const visibleNodes  = computed(() => dir.value?.nodes  ?? [])
const visibleIds    = computed(() => new Set(visibleNodes.value.map(n => n.id)))
const visibleEdges  = computed(() => (dir.value?.edges ?? []).filter(
  e => visibleIds.value.has(e.from_node) && visibleIds.value.has(e.to_node),
))
const visibleGroups = computed(() => dir.value?.groups ?? [])

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

// Computed map so edge paths re-evaluate reactively when positions change
const edgePaths = computed(() => {
  const m: Record<string, string> = {}
  for (const e of visibleEdges.value) m[e.id] = routeEdge(e.from_node, e.to_node)
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

// ── Edge label midpoint ────────────────────────────────────────────────────
const edgeMids = computed(() => {
  const m: Record<string, { x: number; y: number }> = {}
  for (const e of visibleEdges.value) {
    if (!e.label) continue
    const s = pos[e.from_node]; const d = pos[e.to_node]
    if (!s || !d) continue
    m[e.id] = { x: (s.x + d.x + NODE_W) / 2, y: (s.y + d.y + NODE_H) / 2 - 8 }
  }
  return m
})

// ── Per-node shape metadata (avoids calling helpers multiple times in template)
const nodeShapeData = computed(() => {
  const m: Record<string, { kind: ShapeKind; c: { fill: string; stroke: string }; lY: number; tY: number }> = {}
  for (const n of visibleNodes.value) {
    m[n.id] = { kind: shapeKind(n.node_type), c: nodeColor(n.node_type), lY: labelY(n.node_type), tY: typeTextY(n.node_type) }
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

function onCanvasPointerDown(e: PointerEvent) {
  if (e.button !== 0 || drag.value) return
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
    pos[drag.value.id] = { x: Math.max(0, sv.x - drag.value.offX), y: Math.max(0, sv.y - drag.value.offY) }
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
  const { nodeType, label } = JSON.parse(raw) as { nodeType: string; label: string }
  const sv = toSvg(e.clientX, e.clientY)
  const id = addNode(nodeType, label)
  if (id) pos[id] = { x: Math.max(0, sv.x - NODE_W / 2), y: Math.max(0, sv.y - NODE_H / 2) }
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
  pos[newId] = { x: p.x + 24, y: p.y + 24 }
}

function resetLayout() {
  if (!dir.value) return
  const computed = autoLayout(dir.value)
  for (const [id, p] of Object.entries(computed)) {
    pos[id] = p
    updateNodePosition(id, p.x, p.y)
  }
  nextTick(fitView)
}

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
</script>

<template>
  <div
    ref="container"
    :class="['diagram-canvas', {
      'diagram-canvas--panning': isPanning && !drag,
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

        <!-- ── Groups (behind everything) ────────────────────────────────── -->
        <g id="sw-groups">
          <template v-for="g in visibleGroups" :key="g.id">
            <template v-if="groupBoundsMap[g.id]">
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
              />
              <text
                :x="groupBoundsMap[g.id]!.x + 10"
                :y="groupBoundsMap[g.id]!.y + 17"
                class="sw-group-label"
              >{{ g.label }}</text>
            </template>
          </template>
        </g>

        <!-- ── Edges ─────────────────────────────────────────────────────── -->
        <g id="sw-edges">
          <g
            v-for="e in visibleEdges"
            :key="e.id"
            :class="['sw-edge', { 'sw-edge--selected': selected.has(e.id) }]"
            style="cursor: pointer"
            @pointerdown.stop="_pdClient = { x: $event.clientX, y: $event.clientY }"
            @click.stop="handleSelect(e.id, $event.ctrlKey || $event.metaKey)"
            @contextmenu.prevent.stop="openCtxEdge($event, e.id)"
          >
            <!-- Wide invisible hit area -->
            <path :d="edgePaths[e.id]" fill="none" stroke="transparent" stroke-width="12" />
            <!-- Visible stroke -->
            <path
              class="sw-edge-line"
              :d="edgePaths[e.id]"
              fill="none"
              :stroke="selected.has(e.id) ? 'var(--accent)' : '#8da8c8'"
              :stroke-width="selected.has(e.id) ? 2.5 : 1.5"
              :stroke-dasharray="DASH[e.style]"
              :marker-end="e.direction !== 'backward' ? (selected.has(e.id) ? 'url(#sw-arr-sel)' : 'url(#sw-arr)') : undefined"
              :marker-start="e.direction === 'bidirectional' || e.direction === 'backward' ? (selected.has(e.id) ? 'url(#sw-arr-rev-sel)' : 'url(#sw-arr-rev)') : undefined"
            />
            <template v-if="e.label && edgeMids[e.id]">
              <rect
                :x="edgeMids[e.id].x - 22"
                :y="edgeMids[e.id].y - 8"
                width="44" height="14"
                rx="3"
                fill="var(--canvas-bg)"
                stroke="var(--canvas-border)"
                stroke-width="0.5"
              />
              <text
                :x="edgeMids[e.id].x"
                :y="edgeMids[e.id].y + 2"
                class="sw-edge-label"
                text-anchor="middle"
              >{{ e.label }}</text>
            </template>
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
            >{{ n.node_type }}</text>

            <!-- Selection ring -->
            <rect
              v-if="selected.has(n.id)"
              x="-3" y="-3"
              :width="NODE_W + 6"
              :height="NODE_H + 6"
              rx="6"
              fill="none"
              stroke="var(--accent)"
              stroke-width="2"
              class="sw-node-sel"
              pointer-events="none"
            />
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

/* ── Node selection ────────────────────────────────────────────────────── */
.sw-node-sel {
  animation: sw-sel-pop 0.14s ease-out;
}
@keyframes sw-sel-pop {
  from { opacity: 0; stroke-width: 6; }
  to   { opacity: 1; stroke-width: 2; }
}

/* ── Edge selection ────────────────────────────────────────────────────── */
.sw-edge-line {
  transition: stroke 0.1s, stroke-width 0.1s;
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
