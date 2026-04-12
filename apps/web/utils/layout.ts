/**
 * Multi-objective force-directed layout engine.
 *
 * Architecture
 * ─────────────
 * • LayoutObjective  – computes force vectors (dx/dy per node) for one step
 * • registerObjective – plug in custom objectives by name
 * • autoLayout        – the public entry point; seeds from BFS then refines
 *
 * Built-in objectives
 * ────────────────────
 *  node-repulsion    push nodes apart to prevent overlap
 *  edge-attraction   pull connected nodes toward an ideal separation
 *  group-cohesion    pull group members toward their centroid
 *  group-separation  push distinct-group centroids apart
 *                    (skips pairs that share a member — entity in 2 groups)
 *  group-alignment   align group members into a row or column
 *  topological-order prefer edges to flow top-to-bottom or left-to-right
 *  edge-crossing     approximate crossing penalty (O(E²), fast in practice)
 *  grid-alignment    attract each node toward the nearest grid snap point
 *  boundary          soft wall: keep nodes inside canvas padding
 *
 * Adding a custom objective
 * ──────────────────────────
 *  registerObjective('my-objective', (weight, params) => ({
 *    name: 'my-objective',
 *    weight,
 *    forces(state) {
 *      // return Record<nodeId, {x, y}> — force vectors
 *      return {}
 *    },
 *  }))
 *
 * Then include `{ type: 'my-objective', weight: 0.5 }` in LayoutOptions.objectives.
 */

import type { DIR, DiagramEdge, DiagramGroup, DiagramNode } from '~/types/dir'

// ── Core types ───────────────────────────────────────────────────────────────

export interface Point { x: number; y: number }

/**
 * All context an objective needs to compute forces for one iteration.
 * Treat `positions` as read-only; the optimizer mutates it between steps.
 */
export interface LayoutState {
  readonly positions: Readonly<Record<string, Point>>
  readonly nodes: DiagramNode[]
  readonly edges: DiagramEdge[]
  readonly groups: DiagramGroup[]
  readonly nodeW: number
  readonly nodeH: number
  readonly canvasW: number
  readonly canvasH: number
}

/**
 * A layout objective.
 * Returns a partial map of nodeId → force vector.
 * Missing entries are treated as {x:0, y:0}.
 * The returned vectors are scaled by `weight` before being applied.
 */
export interface LayoutObjective {
  readonly name: string
  readonly weight: number
  forces(state: LayoutState): Record<string, Point>
}

// ── Objective registry ───────────────────────────────────────────────────────

type ObjectiveFactory = (weight: number, params?: Record<string, unknown>) => LayoutObjective

const _registry = new Map<string, ObjectiveFactory>()

/**
 * Register a factory under `name` so it can be referenced by type string
 * in LayoutOptions.objectives.
 */
export function registerObjective(name: string, factory: ObjectiveFactory): void {
  _registry.set(name, factory)
}

// ── Geometry helpers (module-private) ────────────────────────────────────────

/** Centre x of a node given its top-left x */
function ncx(px: number, w: number): number { return px + w / 2 }
/** Centre y of a node given its top-left y */
function ncy(py: number, h: number): number { return py + h / 2 }

/** Accumulate a force vector into a mutable forces map. */
function push(f: Record<string, Point>, id: string, dx: number, dy: number): void {
  const prev = f[id]
  f[id] = prev ? { x: prev.x + dx, y: prev.y + dy } : { x: dx, y: dy }
}

/**
 * Segment–segment intersection test (excludes endpoint touches).
 * Returns true if the open segments (a1→a2) and (b1→b2) properly cross.
 */
function segmentsIntersect(
  ax1: number, ay1: number, ax2: number, ay2: number,
  bx1: number, by1: number, bx2: number, by2: number,
): boolean {
  const dax = ax2 - ax1, day = ay2 - ay1
  const dbx = bx2 - bx1, dby = by2 - by1
  const cross = dax * dby - day * dbx
  if (Math.abs(cross) < 1e-8) return false
  const t = ((bx1 - ax1) * dby - (by1 - ay1) * dbx) / cross
  const u = ((bx1 - ax1) * day  - (by1 - ay1) * dax) / cross
  return t > 0.04 && t < 0.96 && u > 0.04 && u < 0.96
}

/** Centroid of a list of ids (centre points). */
function centroid(
  ids: string[],
  positions: Readonly<Record<string, Point>>,
  w: number, h: number,
): { x: number; y: number } {
  let sx = 0, sy = 0, n = 0
  for (const id of ids) {
    const p = positions[id]
    if (!p) continue
    sx += ncx(p.x, w); sy += ncy(p.y, h); n++
  }
  return n ? { x: sx / n, y: sy / n } : { x: 0, y: 0 }
}

// ── Built-in objective implementations ──────────────────────────────────────

/**
 * node-repulsion
 * Every pair of nodes closer than `minDist` pushes each other away.
 * This is the primary collision-avoidance force.
 */
function makeNodeRepulsion(weight: number, minDist: number): LayoutObjective {
  return {
    name: 'node-repulsion', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      const ids = s.nodes.map(n => n.id)
      for (let i = 0; i < ids.length; i++) {
        const a = ids[i]; const pa = s.positions[a]; if (!pa) continue
        for (let j = i + 1; j < ids.length; j++) {
          const b = ids[j]; const pb = s.positions[b]; if (!pb) continue
          const dx = ncx(pb.x, s.nodeW) - ncx(pa.x, s.nodeW)
          const dy = ncy(pb.y, s.nodeH) - ncy(pa.y, s.nodeH)
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.1
          if (dist >= minDist) continue
          const mag = (minDist - dist) / dist
          push(f, a, -dx * mag, -dy * mag)
          push(f, b,  dx * mag,  dy * mag)
        }
      }
      return f
    },
  }
}

/**
 * edge-attraction
 * Spring force: connected nodes pulled toward `idealLength` separation.
 * Too-short edges push; too-long edges pull.
 */
function makeEdgeAttraction(weight: number, idealLength: number): LayoutObjective {
  return {
    name: 'edge-attraction', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const e of s.edges) {
        const pa = s.positions[e.from_node]; const pb = s.positions[e.to_node]
        if (!pa || !pb) continue
        const dx = ncx(pb.x, s.nodeW) - ncx(pa.x, s.nodeW)
        const dy = ncy(pb.y, s.nodeH) - ncy(pa.y, s.nodeH)
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.1
        const stretch = (dist - idealLength) / dist
        push(f, e.from_node,  dx * stretch,  dy * stretch)
        push(f, e.to_node,   -dx * stretch, -dy * stretch)
      }
      return f
    },
  }
}

/**
 * group-cohesion
 * Pull each group member toward the group's centroid.
 * Keeps group members physically close.
 */
function makeGroupCohesion(weight: number): LayoutObjective {
  return {
    name: 'group-cohesion', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const g of s.groups) {
        const members = g.contains.filter(id => s.positions[id])
        if (members.length < 2) continue
        const { x: gcx, y: gcy } = centroid(members, s.positions, s.nodeW, s.nodeH)
        for (const id of members) {
          const p = s.positions[id]
          push(f, id, gcx - ncx(p.x, s.nodeW), gcy - ncy(p.y, s.nodeH))
        }
      }
      return f
    },
  }
}

/**
 * group-separation
 * Push distinct groups' centroids apart so groups don't visually overlap.
 * Groups that share at least one member (entity in 2 groups) are exempt —
 * their shared member acts as a natural anchor.
 */
function makeGroupSeparation(weight: number, minDist: number): LayoutObjective {
  return {
    name: 'group-separation', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (let i = 0; i < s.groups.length; i++) {
        for (let j = i + 1; j < s.groups.length; j++) {
          const ga = s.groups[i]; const gb = s.groups[j]
          // Shared member → skip (they need to overlap or touch)
          const setA = new Set(ga.contains)
          if (gb.contains.some(id => setA.has(id))) continue
          const mbA = ga.contains.filter(id => s.positions[id])
          const mbB = gb.contains.filter(id => s.positions[id])
          if (!mbA.length || !mbB.length) continue
          const ca = centroid(mbA, s.positions, s.nodeW, s.nodeH)
          const cb = centroid(mbB, s.positions, s.nodeW, s.nodeH)
          const dx = cb.x - ca.x; const dy = cb.y - ca.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.1
          if (dist >= minDist) continue
          const mag = (minDist - dist) / dist
          // Distribute force across all members of each group
          for (const id of mbA) push(f, id, -dx * mag / mbA.length, -dy * mag / mbA.length)
          for (const id of mbB) push(f, id,  dx * mag / mbB.length,  dy * mag / mbB.length)
        }
      }
      return f
    },
  }
}

/**
 * group-alignment
 * Within each group, detect the dominant axis (horizontal if bounding box is
 * wider than tall; vertical if taller) then nudge members to share that axis.
 *
 *  • Horizontal group → align node centres on the same y
 *  • Vertical   group → align node centres on the same x
 *
 * A dead-band ratio of 1.2 prevents oscillation for near-square groups
 * (they're left as horizontal by default).
 */
function makeGroupAlignment(weight: number): LayoutObjective {
  return {
    name: 'group-alignment', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const g of s.groups) {
        const members = g.contains.filter(id => s.positions[id])
        if (members.length < 2) continue
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
        for (const id of members) {
          const p = s.positions[id]
          minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x + s.nodeW)
          minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y + s.nodeH)
        }
        const spanX = maxX - minX
        const spanY = maxY - minY
        const meanCY = members.reduce((sum, id) => sum + ncy(s.positions[id].y, s.nodeH), 0) / members.length
        const meanCX = members.reduce((sum, id) => sum + ncx(s.positions[id].x, s.nodeW), 0) / members.length

        if (spanY > spanX * 1.2) {
          // Vertical group: align on shared x
          for (const id of members)
            push(f, id, meanCX - ncx(s.positions[id].x, s.nodeW), 0)
        } else {
          // Horizontal group: align on shared y (default for square groups)
          for (const id of members)
            push(f, id, 0, meanCY - ncy(s.positions[id].y, s.nodeH))
        }
      }
      return f
    },
  }
}

/**
 * topological-order
 * Penalizes edges that go "against the grain":
 *  • vertical   → from_node should be above to_node
 *  • horizontal → from_node should be left of to_node
 *
 * This produces a clear directional flow in the final diagram.
 */
function makeTopologicalOrder(weight: number, direction: 'vertical' | 'horizontal'): LayoutObjective {
  return {
    name: 'topological-order', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const e of s.edges) {
        const pa = s.positions[e.from_node]; const pb = s.positions[e.to_node]
        if (!pa || !pb) continue
        if (direction === 'vertical') {
          // pa.y should be < pb.y  (from flows down into to)
          const overlap = ncy(pa.y, s.nodeH) - ncy(pb.y, s.nodeH) + s.nodeH + 30
          if (overlap > 0) {
            push(f, e.from_node, 0, -overlap * 0.12)
            push(f, e.to_node,   0,  overlap * 0.12)
          }
        } else {
          // pa.x should be < pb.x
          const overlap = ncx(pa.x, s.nodeW) - ncx(pb.x, s.nodeW) + s.nodeW + 30
          if (overlap > 0) {
            push(f, e.from_node, -overlap * 0.12, 0)
            push(f, e.to_node,    overlap * 0.12, 0)
          }
        }
      }
      return f
    },
  }
}

/**
 * edge-crossing
 * For every pair of edges whose straight-line approximations cross, apply a
 * perpendicular nudge to push them apart.  O(E²) per iteration — still fast
 * for typical diagrams (< 100 edges).
 */
function makeEdgeCrossing(weight: number): LayoutObjective {
  return {
    name: 'edge-crossing', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      const edges = s.edges.filter(e => s.positions[e.from_node] && s.positions[e.to_node])
      for (let i = 0; i < edges.length; i++) {
        const ea = edges[i]
        const ax1 = ncx(s.positions[ea.from_node].x, s.nodeW)
        const ay1 = ncy(s.positions[ea.from_node].y, s.nodeH)
        const ax2 = ncx(s.positions[ea.to_node].x,   s.nodeW)
        const ay2 = ncy(s.positions[ea.to_node].y,   s.nodeH)
        for (let j = i + 1; j < edges.length; j++) {
          const eb = edges[j]
          // Skip edges sharing an endpoint
          if (ea.from_node === eb.from_node || ea.from_node === eb.to_node ||
              ea.to_node   === eb.from_node || ea.to_node   === eb.to_node) continue
          const bx1 = ncx(s.positions[eb.from_node].x, s.nodeW)
          const by1 = ncy(s.positions[eb.from_node].y, s.nodeH)
          const bx2 = ncx(s.positions[eb.to_node].x,   s.nodeW)
          const by2 = ncy(s.positions[eb.to_node].y,   s.nodeH)
          if (!segmentsIntersect(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2)) continue
          // Perpendicular to edge A; push A one way, B the other
          const adx = ax2 - ax1; const ady = ay2 - ay1
          const alen = Math.sqrt(adx * adx + ady * ady) || 1
          const nx = -ady / alen * 28; const ny = adx / alen * 28
          push(f, ea.from_node,  nx,  ny)
          push(f, ea.to_node,    nx,  ny)
          push(f, eb.from_node, -nx, -ny)
          push(f, eb.to_node,   -nx, -ny)
        }
      }
      return f
    },
  }
}

/**
 * grid-alignment
 * Attract each node toward its nearest grid snap point.
 * Produces cleaner, more aligned final layouts.
 */
function makeGridAlignment(weight: number, gridSize: number): LayoutObjective {
  return {
    name: 'grid-alignment', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const n of s.nodes) {
        const p = s.positions[n.id]; if (!p) continue
        const snapX = Math.round(p.x / gridSize) * gridSize
        const snapY = Math.round(p.y / gridSize) * gridSize
        push(f, n.id, (snapX - p.x) * 0.4, (snapY - p.y) * 0.4)
      }
      return f
    },
  }
}

/**
 * boundary
 * Soft wall: nodes that stray within `padding` pixels of the canvas edge are
 * pushed back inward.  High weight keeps nodes well inside the viewport.
 */
function makeBoundary(weight: number, padding: number): LayoutObjective {
  return {
    name: 'boundary', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const n of s.nodes) {
        const p = s.positions[n.id]; if (!p) continue
        let fx = 0; let fy = 0
        const overL = padding - p.x
        const overT = padding - p.y
        const overR = p.x + s.nodeW - (s.canvasW - padding)
        const overB = p.y + s.nodeH - (s.canvasH - padding)
        if (overL > 0) fx += overL * 2
        if (overT > 0) fy += overT * 2
        if (overR > 0) fx -= overR * 2
        if (overB > 0) fy -= overB * 2
        if (fx || fy) push(f, n.id, fx, fy)
      }
      return f
    },
  }
}

// ── Register all built-ins ───────────────────────────────────────────────────

registerObjective('node-repulsion',
  (w, p) => makeNodeRepulsion(w,     (p?.minDist     as number) ?? 220))
registerObjective('edge-attraction',
  (w, p) => makeEdgeAttraction(w,    (p?.idealLength as number) ?? 220))
registerObjective('group-cohesion',
  (w)    => makeGroupCohesion(w))
registerObjective('group-separation',
  (w, p) => makeGroupSeparation(w,   (p?.minDist     as number) ?? 360))
registerObjective('group-alignment',
  (w)    => makeGroupAlignment(w))
registerObjective('topological-order',
  (w, p) => makeTopologicalOrder(w,  (p?.direction   as 'vertical' | 'horizontal') ?? 'vertical'))
registerObjective('edge-crossing',
  (w)    => makeEdgeCrossing(w))
registerObjective('grid-alignment',
  (w, p) => makeGridAlignment(w,     (p?.gridSize    as number) ?? 40))
registerObjective('boundary',
  (w, p) => makeBoundary(w,          (p?.padding     as number) ?? 80))

// ── Default objective configuration ─────────────────────────────────────────

export interface ObjectiveDef {
  /** Must match a registered objective name. */
  type: string
  /** Scalar multiplier applied to all force vectors from this objective. */
  weight: number
  /** Optional objective-specific tuning parameters. */
  params?: Record<string, unknown>
}

/**
 * The default objective set used when no override is provided.
 * Weights are normalised so the boundary constraint always wins.
 */
export const DEFAULT_OBJECTIVES: ObjectiveDef[] = [
  { type: 'node-repulsion',    weight: 1.2 },
  { type: 'edge-attraction',   weight: 0.35 },
  { type: 'group-cohesion',    weight: 0.9 },
  { type: 'group-separation',  weight: 0.7 },
  { type: 'group-alignment',   weight: 0.45 },
  { type: 'topological-order', weight: 0.6 },
  { type: 'edge-crossing',     weight: 0.25 },
  { type: 'boundary',          weight: 2.5 },
]

// ── BFS seed ─────────────────────────────────────────────────────────────────

/**
 * Kahn's BFS topological layering — a deterministic, good-looking initial
 * placement used as the optimizer's starting point when no positions are stored.
 */
function bfsSeed(
  dir: DIR,
  nodeW: number,
  nodeH: number,
  hGap: number,
  vGap: number,
  pad: number,
): Record<string, Point> {
  const ids = dir.nodes.map(n => n.id)
  if (!ids.length) return {}
  const set = new Set(ids)
  const inDeg: Record<string, number> = Object.fromEntries(ids.map(id => [id, 0]))
  const adj: Record<string, string[]> = Object.fromEntries(ids.map(id => [id, []]))

  for (const e of dir.edges) {
    if (set.has(e.from_node) && set.has(e.to_node)) {
      adj[e.from_node].push(e.to_node)
      inDeg[e.to_node]++
    }
  }

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

  // Temporary placement
  const result: Record<string, Point> = {}
  let y = pad; let maxW = 0
  for (const layer of layers) {
    const w = layer.length * nodeW + (layer.length - 1) * hGap
    maxW = Math.max(maxW, w)
    layer.forEach((id, i) => { result[id] = { x: pad + i * (nodeW + hGap), y } })
    y += nodeH + vGap
  }

  // Centre each layer horizontally
  const totalW = Math.max(maxW + 2 * pad, 900)
  for (const layer of layers) {
    const w = layer.length * nodeW + (layer.length - 1) * hGap
    const x0 = (totalW - w) / 2
    layer.forEach((id, i) => { result[id].x = x0 + i * (nodeW + hGap) })
  }
  return result
}

// ── Public API ────────────────────────────────────────────────────────────────

export interface LayoutOptions {
  /**
   * Override the default objective list.
   * Each entry references a registered objective by `type`.
   * Unknown types are silently skipped.
   */
  objectives?: ObjectiveDef[]
  /** Maximum number of optimizer iterations. Default: 350 (80 when using stored positions). */
  iterations?: number
  /** Initial step-size multiplier. Default: 1.0 */
  stepSize?: number
  /** Multiplicative cool-down applied to step after each iteration. Default: 0.985 */
  cooling?: number
  /**
   * Stop early when the largest per-node force magnitude (after step scaling)
   * falls below this value. Default: 0.4
   */
  convergenceThreshold?: number
  nodeW?: number
  nodeH?: number
}

/**
 * Compute an optimised layout for `dir`.
 *
 * @param dir     Diagram to lay out.
 * @param stored  Existing positions (from user drag / DB save).  If provided,
 *                they seed the optimizer — fewer iterations run to avoid
 *                discarding the user's intentional arrangement.
 * @param opts    Tuning knobs; all fields are optional.
 * @returns       Map of nodeId → top-left {x, y}.
 */
export function autoLayout(
  dir: DIR,
  stored?: Record<string, Point>,
  opts: LayoutOptions = {},
): Record<string, Point> {
  const nodeW = opts.nodeW ?? 160
  const nodeH = opts.nodeH ?? 60
  const hGap  = 80
  const vGap  = 100
  const pad   = 80

  // Estimate a canvas big enough to contain all nodes comfortably
  const n      = Math.max(dir.nodes.length, 1)
  const cols   = Math.max(3, Math.ceil(Math.sqrt(n)))
  const rows   = Math.ceil(n / cols)
  const canvasW = Math.max(cols * (nodeW + hGap) + 2 * pad, 900)
  const canvasH = Math.max(rows * (nodeH + vGap) + 2 * pad, 600)

  // Choose seed
  const hasStored = !!stored && Object.keys(stored).length > 0
  const seed: Record<string, Point> = hasStored
    ? { ...stored }
    : bfsSeed(dir, nodeW, nodeH, hGap, vGap, pad)

  // Fill in nodes absent from the seed (new nodes added after initial layout)
  for (const node of dir.nodes) {
    if (!seed[node.id]) {
      seed[node.id] = {
        x: pad + Math.random() * Math.max(canvasW - 2 * pad - nodeW, 1),
        y: pad + Math.random() * Math.max(canvasH - 2 * pad - nodeH, 1),
      }
    }
  }

  const {
    iterations          = hasStored ? 80  : 350,
    stepSize            = 1.0,
    cooling             = 0.985,
    convergenceThreshold = 0.4,
  } = opts

  // Instantiate objectives (unknown types skipped gracefully)
  const objectives: LayoutObjective[] = (opts.objectives ?? DEFAULT_OBJECTIVES)
    .map(def => {
      const factory = _registry.get(def.type)
      return factory ? factory(def.weight, def.params) : null
    })
    .filter((o): o is LayoutObjective => o !== null)

  // Mutable working copy of positions
  const positions: Record<string, Point> = {}
  for (const id of Object.keys(seed)) positions[id] = { ...seed[id] }

  const state: LayoutState = {
    positions,
    nodes:   dir.nodes,
    edges:   dir.edges,
    groups:  dir.groups,
    nodeW, nodeH, canvasW, canvasH,
  }

  let step = stepSize

  for (let iter = 0; iter < iterations; iter++) {
    // Accumulate weighted forces from every objective
    const total: Record<string, Point> = {}
    for (const obj of objectives) {
      const forces = obj.forces(state)
      for (const id of Object.keys(forces)) {
        const fv = forces[id]
        push(total, id, fv.x * obj.weight, fv.y * obj.weight)
      }
    }

    // Apply forces — cap per-iteration displacement to avoid explosions
    let maxMag = 0
    for (const id of Object.keys(total)) {
      const fv = total[id]
      const mag = Math.sqrt(fv.x * fv.x + fv.y * fv.y)
      if (mag > maxMag) maxMag = mag
      const cap   = Math.min(mag, 60)
      const scale = (cap / (mag || 1)) * step
      const nx = state.positions[id].x + fv.x * scale
      const ny = state.positions[id].y + fv.y * scale
      state.positions[id] = { x: Math.max(0, nx), y: Math.max(0, ny) }
    }

    step *= cooling
    if (maxMag * step < convergenceThreshold) break
  }

  return state.positions
}
