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
 *  group-alignment     align group members into a row or column (available for custom configs)
 *  group-grid-packing  assign each member a slot in the minimal zero-waste grid:
 *                      n=3→column, n=4→2×2, n=6→2×3, n=9→3×3 etc.
 *  topological-order prefer edges to flow top-to-bottom or left-to-right
 *  edge-crossing     approximate crossing penalty (O(E²), fast in practice)
 *  edge-straightness push connected nodes to share a coordinate on the
 *                    axis perpendicular to their dominant direction, producing
 *                    straight vertical or horizontal edges
 *  grid-alignment        attract each node toward the nearest grid snap point
 *  group-grid-alignment  snap each group's bounding box origin to the grid
 *                        by moving all members as a unit
 *  boundary              soft wall: keep nodes inside canvas padding
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
  /**
   * Per-node size overrides.  Used when nodes in the simulation have
   * non-uniform bounding boxes — e.g. group proxy nodes whose bbox is larger
   * than a single node.  Falls back to nodeW / nodeH when absent.
   */
  readonly nodeSizes?: Readonly<Record<string, { w: number; h: number }>>
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

/** Centre of a node, honouring per-node size overrides in LayoutState. */
function nCenter(s: LayoutState, id: string): Point {
  const p = s.positions[id]
  const sz = s.nodeSizes?.[id]
  return { x: p.x + (sz?.w ?? s.nodeW) / 2, y: p.y + (sz?.h ?? s.nodeH) / 2 }
}

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
 * Bounding-box-aware collision avoidance.  The minimum centre-to-centre
 * distance before repulsion fires is computed from the actual node dimensions
 * in the direction of separation, rather than a single fixed radius:
 *
 *   minDist(ux,uy) = |ux|·nodeW + |uy|·nodeH + gap
 *
 * This means:
 *  • Horizontal neighbours fire at nodeW+gap  (≈ column stride — no false triggers)
 *  • Vertical   neighbours fire at nodeH+gap  (≈ row stride — no false triggers)
 *  • Overlapping nodes (any direction) are pushed apart strongly
 *
 * Gap defaults to 20 px, which exactly matches the padding built into the
 * grid strides (colStride = nodeW+20 rounded up, rowStride = nodeH+20 rounded
 * up), so correctly-placed grid nodes sit right at the threshold and the force
 * is zero — it only activates when nodes genuinely intrude on each other.
 */
function makeNodeRepulsion(weight: number, gap: number): LayoutObjective {
  return {
    name: 'node-repulsion', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (let i = 0; i < s.nodes.length; i++) {
        const a = s.nodes[i].id; if (!s.positions[a]) continue
        const ca = nCenter(s, a)
        const sA = s.nodeSizes?.[a] ?? { w: s.nodeW, h: s.nodeH }
        for (let j = i + 1; j < s.nodes.length; j++) {
          const b = s.nodes[j].id; if (!s.positions[b]) continue
          const cb = nCenter(s, b)
          const sB = s.nodeSizes?.[b] ?? { w: s.nodeW, h: s.nodeH }
          const dx = cb.x - ca.x, dy = cb.y - ca.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.1
          const ux = dx / dist, uy = dy / dist
          // Bounding-box-aware: each node contributes its own half-extent in the
          // separation direction.  gap=20 leaves one minor grid unit of breathing room.
          const minDist = Math.abs(ux) * (sA.w / 2 + sB.w / 2)
                        + Math.abs(uy) * (sA.h / 2 + sB.h / 2) + gap
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
 *
 * Intra-group edges are skipped — group-grid-packing already controls the
 * spacing between members of the same group, and applying an ideal length
 * (typically larger than the grid stride) would pull nodes away from their
 * assigned slots and cause overlap.
 */
function makeEdgeAttraction(weight: number, idealLength: number): LayoutObjective {
  return {
    name: 'edge-attraction', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const e of s.edges) {
        if (!s.positions[e.from_node] || !s.positions[e.to_node]) continue
        const ca = nCenter(s, e.from_node)
        const cb = nCenter(s, e.to_node)
        const dx = cb.x - ca.x, dy = cb.y - ca.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.1
        // Scale ideal length up when either endpoint is larger than a default node,
        // so groups are naturally pushed further from their neighbours.
        const sA = s.nodeSizes?.[e.from_node] ?? { w: s.nodeW, h: s.nodeH }
        const sB = s.nodeSizes?.[e.to_node]   ?? { w: s.nodeW, h: s.nodeH }
        const base = Math.max(s.nodeW, s.nodeH)
        const extraA = (Math.max(sA.w, sA.h) - base) / 2
        const extraB = (Math.max(sB.w, sB.h) - base) / 2
        const effective = idealLength + Math.max(0, extraA) + Math.max(0, extraB)
        const stretch = (dist - effective) / dist
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
 * Choose (cols, rows) for packing n nodes into a minimal grid.
 *
 * Priority 1 — fewest wasted slots (cols*rows - n).
 * Priority 2 — bounding-box aspect ratio closest to a single node's own
 *              aspect ratio (nodeW/nodeH), normalised so wide and tall
 *              deviations are penalised equally.
 *
 * Examples for 160×60 nodes on a 200/80 stride:
 *   n=2 → (1,2)  — column of 2
 *   n=3 → (1,3)  — column of 3   (not 2×2 which wastes a slot)
 *   n=4 → (2,2)  — 2×2 grid      (aspect 360/140≈2.6, very close to 2.67)
 *   n=5 → (1,5)  — column of 5   (no zero-waste alternative is squarer)
 *   n=6 → (2,3)  — 2 cols, 3 rows
 *   n=9 → (3,3)  — 3×3 grid
 */
function bestPackingDims(
  n: number,
  colStride: number, rowStride: number,
  nodeW: number, nodeH: number,
): [number, number] {
  if (n <= 1) return [1, 1]
  const nodeAspect = nodeW / nodeH
  let bestCols = 1
  let bestScore = Infinity
  for (let c = 1; c <= n; c++) {
    const r = Math.ceil(n / c)
    const waste = c * r - n
    const bboxW = c * colStride - (colStride - nodeW)
    const bboxH = r * rowStride - (rowStride - nodeH)
    const aspect = bboxW / bboxH
    // Normalised aspect-ratio deviation: symmetric on log scale so
    // (too wide) and (too tall) are penalised the same
    const aspectDiff = Math.abs(Math.log(aspect / nodeAspect))
    // Waste is heavily penalised so we only choose a wasteful layout when
    // every zero-waste option has a significantly worse aspect ratio
    const score = waste * 100 + aspectDiff
    if (score < bestScore) { bestScore = score; bestCols = c }
  }
  return [bestCols, Math.ceil(n / bestCols)]
}

/**
 * group-grid-packing
 * Assigns each group member a slot in the minimal zero-waste grid chosen by
 * bestPackingDims(), then pushes it there.  Strides are multiples of gridSize
 * so every slot coincides with the global grid — members land on clean,
 * aligned positions without overlap.
 *
 * Slot assignment is stable across iterations: nodes are sorted by quantised
 * row-band then x, so a node must drift more than 1.5 row-strides before its
 * band changes.  This prevents slot-swapping oscillation once nodes are close
 * to their targets.
 *
 * The returned correction vector equals the full remaining displacement;
 * the optimizer's 60 px/iteration cap keeps convergence smooth.  At weight
 * 2.2 this force comfortably overrides node-repulsion for within-group pairs,
 * which would otherwise push tightly-packed nodes apart.
 */
function makeGroupGridPacking(weight: number, gridSize: number): LayoutObjective {
  return {
    name: 'group-grid-packing', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      // Strides snap to gridSize multiples → nodes land on the global grid
      const colStride = Math.ceil((s.nodeW + gridSize) / gridSize) * gridSize  // 200 for nodeW=160, grid=40
      const rowStride = Math.ceil((s.nodeH + gridSize) / gridSize) * gridSize  // 80  for nodeH=60,  grid=40

      for (const g of s.groups) {
        const members = g.contains.filter(id => s.positions[id])
        if (members.length < 2) continue

        const [cols, rows] = bestPackingDims(members.length, colStride, rowStride, s.nodeW, s.nodeH)

        // Stable slot assignment: sort by quantised row-band then x.
        // Band size = 1.5 strides so a node must move > half a stride out of
        // its row before its band number changes.
        const rowBand = rowStride * 1.5
        const sorted = [...members].sort((a, b) => {
          const pa = s.positions[a], pb = s.positions[b]
          const ra = Math.floor(pa.y / rowBand), rb = Math.floor(pb.y / rowBand)
          if (ra !== rb) return ra - rb
          return pa.x - pb.x
        })

        // Anchor the grid on the centroid of current member positions
        let sumX = 0, sumY = 0
        for (const id of sorted) { sumX += s.positions[id].x; sumY += s.positions[id].y }
        const totalW = cols * colStride - (colStride - s.nodeW)
        const totalH = rows * rowStride - (rowStride - s.nodeH)
        const anchorX = sumX / sorted.length - totalW / 2
        const anchorY = sumY / sorted.length - totalH / 2

        for (let i = 0; i < sorted.length; i++) {
          const col = i % cols
          const row = Math.floor(i / cols)
          const targetX = anchorX + col * colStride
          const targetY = anchorY + row * rowStride
          const p = s.positions[sorted[i]]
          push(f, sorted[i], targetX - p.x, targetY - p.y)
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
        if (!s.positions[e.from_node] || !s.positions[e.to_node]) continue
        const ca = nCenter(s, e.from_node)
        const cb = nCenter(s, e.to_node)
        const hA = (s.nodeSizes?.[e.from_node]?.h ?? s.nodeH)
        const hB = (s.nodeSizes?.[e.to_node]?.h   ?? s.nodeH)
        const wA = (s.nodeSizes?.[e.from_node]?.w  ?? s.nodeW)
        const wB = (s.nodeSizes?.[e.to_node]?.w    ?? s.nodeW)
        if (direction === 'vertical') {
          const overlap = ca.y - cb.y + (hA + hB) / 2 + 30
          if (overlap > 0) {
            push(f, e.from_node, 0, -overlap * 0.12)
            push(f, e.to_node,   0,  overlap * 0.12)
          }
        } else {
          const overlap = ca.x - cb.x + (wA + wB) / 2 + 30
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
        const ca1 = nCenter(s, ea.from_node)
        const ca2 = nCenter(s, ea.to_node)
        for (let j = i + 1; j < edges.length; j++) {
          const eb = edges[j]
          // Skip edges sharing an endpoint
          if (ea.from_node === eb.from_node || ea.from_node === eb.to_node ||
              ea.to_node   === eb.from_node || ea.to_node   === eb.to_node) continue
          const cb1 = nCenter(s, eb.from_node)
          const cb2 = nCenter(s, eb.to_node)
          if (!segmentsIntersect(ca1.x, ca1.y, ca2.x, ca2.y, cb1.x, cb1.y, cb2.x, cb2.y)) continue
          // Perpendicular to edge A; push A one way, B the other
          const adx = ca2.x - ca1.x; const ady = ca2.y - ca1.y
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
 * edge-straightness
 * For each edge, push the two endpoints toward sharing a coordinate on the
 * axis perpendicular to the edge's dominant direction:
 *  • mostly vertical   → align centres on the same x (eliminate lateral drift)
 *  • mostly horizontal → align centres on the same y (eliminate vertical drift)
 *
 * The correction is proportional to the offset so large deviations get a
 * stronger nudge while small ones converge gently.  The force is halved for
 * each node so the pair moves symmetrically toward each other.
 */
function makeEdgeStraightness(weight: number): LayoutObjective {
  return {
    name: 'edge-straightness', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const e of s.edges) {
        if (!s.positions[e.from_node] || !s.positions[e.to_node]) continue
        const ca = nCenter(s, e.from_node)
        const cb = nCenter(s, e.to_node)
        const dx = cb.x - ca.x; const dy = cb.y - ca.y
        if (Math.abs(dy) >= Math.abs(dx)) {
          // Mostly vertical: push both nodes toward the same x
          push(f, e.from_node,  dx / 2, 0)
          push(f, e.to_node,   -dx / 2, 0)
        } else {
          // Mostly horizontal: push both nodes toward the same y
          push(f, e.from_node, 0,  dy / 2)
          push(f, e.to_node,   0, -dy / 2)
        }
      }
      return f
    },
  }
}

/**
 * grid-alignment
 * Attract each node's top-left corner toward its nearest grid snap point.
 * Produces cleaner, more aligned final layouts by removing sub-grid scatter.
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
 * group-grid-alignment
 * Snap entire groups to the grid by computing each group's bounding box
 * top-left corner and nudging all members by the same offset so the corner
 * lands on the nearest grid point.  Moving members uniformly preserves the
 * internal arrangement of the group while giving it a clean grid origin.
 */
function makeGroupGridAlignment(weight: number, gridSize: number): LayoutObjective {
  return {
    name: 'group-grid-alignment', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      const groupPad = 20   // matches the visual padding drawn around groups
      for (const g of s.groups) {
        const members = g.contains.filter(id => s.positions[id])
        if (!members.length) continue
        // Bounding box top-left of the group (inner edge minus visual padding)
        let minX = Infinity, minY = Infinity
        for (const id of members) {
          const p = s.positions[id]
          if (p.x - groupPad < minX) minX = p.x - groupPad
          if (p.y - groupPad < minY) minY = p.y - groupPad
        }
        const snapX = Math.round(minX / gridSize) * gridSize
        const snapY = Math.round(minY / gridSize) * gridSize
        const dx = (snapX - minX) * 0.4
        const dy = (snapY - minY) * 0.4
        if (Math.abs(dx) < 0.05 && Math.abs(dy) < 0.05) continue
        // Apply the same uniform delta to every member so the group moves as a unit
        for (const id of members) push(f, id, dx, dy)
      }
      return f
    },
  }
}

/**
 * boundary
 * Soft wall: nodes that stray within `padding` pixels of the canvas edge are
 * pushed back inward.  High weight keeps nodes well inside the viewport.
 * Honours per-node size overrides so group proxy nodes (which are larger than
 * a default node) get a correct right/bottom boundary check.
 */
function makeBoundary(weight: number, padding: number): LayoutObjective {
  return {
    name: 'boundary', weight,
    forces(s) {
      const f: Record<string, Point> = {}
      for (const n of s.nodes) {
        const p = s.positions[n.id]; if (!p) continue
        const sz = s.nodeSizes?.[n.id] ?? { w: s.nodeW, h: s.nodeH }
        let fx = 0; let fy = 0
        const overL = padding - p.x
        const overT = padding - p.y
        const overR = p.x + sz.w - (s.canvasW - padding)
        const overB = p.y + sz.h - (s.canvasH - padding)
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
  (w, p) => makeNodeRepulsion(w,     (p?.gap         as number) ?? 20))
registerObjective('edge-attraction',
  (w, p) => makeEdgeAttraction(w,    (p?.idealLength as number) ?? 220))
registerObjective('group-cohesion',
  (w)    => makeGroupCohesion(w))
registerObjective('group-separation',
  (w, p) => makeGroupSeparation(w,   (p?.minDist     as number) ?? 360))
registerObjective('group-alignment',
  (w)    => makeGroupAlignment(w))
registerObjective('group-grid-packing',
  (w, p) => makeGroupGridPacking(w,   (p?.gridSize    as number) ?? 40))
registerObjective('topological-order',
  (w, p) => makeTopologicalOrder(w,  (p?.direction   as 'vertical' | 'horizontal') ?? 'vertical'))
registerObjective('edge-crossing',
  (w)    => makeEdgeCrossing(w))
registerObjective('edge-straightness',
  (w)    => makeEdgeStraightness(w))
registerObjective('grid-alignment',
  (w, p) => makeGridAlignment(w,      (p?.gridSize   as number) ?? 40))
registerObjective('group-grid-alignment',
  (w, p) => makeGroupGridAlignment(w, (p?.gridSize   as number) ?? 40))
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
 *
 * Group layout is now handled hierarchically — each group is treated as a
 * single rigid proxy node in the simulation (see autoLayout).  Intra-group
 * arrangement is computed deterministically via bestPackingDims before the
 * simulation starts, so no group-* force objectives are needed here.
 *
 * The group-* objectives (group-cohesion, group-separation, group-grid-packing,
 * group-grid-alignment) remain registered for use in custom objective configs.
 */
export const DEFAULT_OBJECTIVES: ObjectiveDef[] = [
  // Bounding-box-aware repulsion: gap=20 matches the grid stride padding so
  // correctly-placed grid nodes sit exactly at the threshold (force = 0).
  { type: 'node-repulsion',    weight: 3.0 },
  { type: 'edge-attraction',   weight: 0.4,  params: { idealLength: 260 } },
  { type: 'topological-order', weight: 0.7 },
  { type: 'edge-crossing',     weight: 0.2 },
  { type: 'edge-straightness', weight: 0.4 },
  { type: 'grid-alignment',    weight: 0.3 },
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

// ── Intra-group layout ────────────────────────────────────────────────────────

/** Grid pitch used for group member slot strides (matches canvas GRID constant). */
const LAYOUT_GRID = 20

/** Visual padding drawn around a group bbox — members start this far inside. */
const GROUP_PAD = 20

/** Prefix applied to group IDs when creating proxy nodes for the virtual graph. */
const GROUP_PROXY_PREFIX = '__group__'

interface IntraGroupLayout {
  /** Total width of member area (excludes GROUP_PAD border). */
  totalW: number
  /** Total height of member area (excludes GROUP_PAD border). */
  totalH: number
  /** Member ID → offset from member-area origin (top-left inside the padding). */
  memberOffsets: Map<string, Point>
  /** Sorted member list used for stable slot assignment. */
  sortedMembers: string[]
}

/**
 * Compute a deterministic slot arrangement for every group.
 *
 * Strides are multiples of LAYOUT_GRID so every member slot is on the global
 * grid when the group proxy's top-left is also on the grid.
 *
 * Sort order:
 *  - When stored positions are available, sort by row-band then x so the
 *    existing visual order is preserved after re-layout.
 *  - Otherwise, sort by declaration order.
 */
function computeIntraGroupLayouts(
  dir: DIR,
  stored: Record<string, Point> | undefined,
  nodeW: number,
  nodeH: number,
): Map<string, IntraGroupLayout> {
  const gridSize = LAYOUT_GRID
  const colStride = Math.ceil((nodeW + gridSize) / gridSize) * gridSize  // 180 for nodeW=160
  const rowStride = Math.ceil((nodeH + gridSize) / gridSize) * gridSize  // 80  for nodeH=60
  const result = new Map<string, IntraGroupLayout>()

  for (const g of dir.groups) {
    const members = g.contains
    if (!members.length) continue

    if (members.length === 1) {
      result.set(g.id, {
        totalW: nodeW, totalH: nodeH,
        memberOffsets: new Map([[members[0], { x: 0, y: 0 }]]),
        sortedMembers: [members[0]],
      })
      continue
    }

    const [cols] = bestPackingDims(members.length, colStride, rowStride, nodeW, nodeH)
    const rows = Math.ceil(members.length / cols)

    const rowBand = rowStride * 1.5
    const sorted = [...members].sort((a, b) => {
      if (stored?.[a] && stored?.[b]) {
        const ra = Math.floor(stored[a].y / rowBand), rb = Math.floor(stored[b].y / rowBand)
        if (ra !== rb) return ra - rb
        return stored[a].x - stored[b].x
      }
      return members.indexOf(a) - members.indexOf(b)
    })

    const totalW = cols * colStride - (colStride - nodeW)
    const totalH = rows * rowStride - (rowStride - nodeH)

    const offsets = new Map<string, Point>()
    for (let i = 0; i < sorted.length; i++) {
      offsets.set(sorted[i], {
        x: (i % cols) * colStride,
        y: Math.floor(i / cols) * rowStride,
      })
    }

    result.set(g.id, { totalW, totalH, memberOffsets: offsets, sortedMembers: sorted })
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
 * ## Hierarchical strategy
 *
 * Groups are treated as **rigid proxy nodes** in the global simulation.
 * Intra-group arrangement is computed deterministically via bestPackingDims
 * before the simulation starts (see computeIntraGroupLayouts).  The simulation
 * only moves group proxies and ungrouped nodes — it never touches individual
 * group members.  After the simulation, member positions are reconstructed
 * from the proxy position plus their precomputed slot offsets.
 *
 * This approach eliminates all inter-force fighting that plagued the flat
 * simulation (repulsion vs grid-packing vs cohesion) and guarantees that the
 * final intra-group arrangement is always the clean minimal grid, regardless
 * of simulation convergence.
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
  const hGap  = 100
  const vGap  = 120
  const pad   = 80

  const hasStored = !!stored && Object.keys(stored).length > 0

  // ── Step 1: Compute intra-group slot arrangement ──────────────────────────
  const intraLayouts = computeIntraGroupLayouts(dir, stored, nodeW, nodeH)

  // ── Step 2: Build nodeToGroup map (first group wins) ─────────────────────
  const nodeToGroup = new Map<string, string>()
  for (const g of dir.groups) {
    for (const id of g.contains) {
      if (!nodeToGroup.has(id)) nodeToGroup.set(id, g.id)
    }
  }

  const nodeIdSet = new Set(dir.nodes.map(n => n.id))
  const ungroupedIds = dir.nodes
    .filter(n => !nodeToGroup.has(n.id))
    .map(n => n.id)

  // ── Step 3: Build virtual graph ───────────────────────────────────────────
  // One proxy per group + one entry per ungrouped node.
  // Proxy ID = GROUP_PROXY_PREFIX + groupId

  const virtualNodeIds: string[] = [
    ...dir.groups.map(g => GROUP_PROXY_PREFIX + g.id),
    ...ungroupedIds,
  ]

  // Fake DiagramNode objects — objectives only use .id from nodes[]
  const virtualNodes: DiagramNode[] = virtualNodeIds.map(id => ({
    id, label: id, node_type: 'service', children: [],
  } as unknown as DiagramNode))

  // Map real endpoint → virtual endpoint
  function toVirtual(nodeId: string): string {
    const grp = nodeToGroup.get(nodeId)
    return grp ? GROUP_PROXY_PREFIX + grp : nodeId
  }

  // Deduplicated cross-group/node virtual edges
  const edgeKeySet = new Set<string>()
  const virtualEdges: DiagramEdge[] = []
  for (const e of dir.edges) {
    if (!nodeIdSet.has(e.from_node) || !nodeIdSet.has(e.to_node)) continue
    const vFrom = toVirtual(e.from_node)
    const vTo   = toVirtual(e.to_node)
    if (vFrom === vTo) continue           // intra-group edge — skip
    const key = `${vFrom}→${vTo}`
    if (edgeKeySet.has(key)) continue     // deduplicate parallel edges
    edgeKeySet.add(key)
    virtualEdges.push({ ...e, id: `v-${e.id}`, from_node: vFrom, to_node: vTo })
  }

  // ── Step 4: Per-virtual-node size map ─────────────────────────────────────
  // Group proxies are larger than a default node — their bbox is the group's
  // member area plus GROUP_PAD padding on all sides.
  const nodeSizes: Record<string, { w: number; h: number }> = {}
  for (const g of dir.groups) {
    const layout = intraLayouts.get(g.id)
    if (!layout) continue
    nodeSizes[GROUP_PROXY_PREFIX + g.id] = {
      w: layout.totalW + GROUP_PAD * 2,
      h: layout.totalH + GROUP_PAD * 2,
    }
  }

  // ── Step 5: Seed virtual positions ───────────────────────────────────────
  // Reference positions: stored member positions if available, else BFS seed.
  const bfsPos = bfsSeed(dir, nodeW, nodeH, hGap, vGap, pad)
  const refPos: Record<string, Point> = hasStored
    ? { ...bfsPos, ...stored }   // BFS as fallback for nodes missing from stored
    : bfsPos

  const virtualSeed: Record<string, Point> = {}

  for (const g of dir.groups) {
    const vId     = GROUP_PROXY_PREFIX + g.id
    const layout  = intraLayouts.get(g.id)
    const sz      = nodeSizes[vId] ?? { w: nodeW, h: nodeH }
    // Estimate group centre from member reference positions
    let sumCx = 0, sumCy = 0, cnt = 0
    for (const mId of (layout?.sortedMembers ?? g.contains)) {
      const p = refPos[mId]
      if (p) { sumCx += p.x + nodeW / 2; sumCy += p.y + nodeH / 2; cnt++ }
    }
    const cx = cnt ? sumCx / cnt : pad + sz.w / 2
    const cy = cnt ? sumCy / cnt : pad + sz.h / 2
    virtualSeed[vId] = { x: cx - sz.w / 2, y: cy - sz.h / 2 }
  }

  for (const id of ungroupedIds) {
    virtualSeed[id] = refPos[id] ?? {
      x: pad + Math.random() * 200,
      y: pad + Math.random() * 200,
    }
  }

  // ── Step 6: Canvas sizing ─────────────────────────────────────────────────
  const vCount  = Math.max(virtualNodeIds.length, 1)
  const vCols   = Math.max(3, Math.ceil(Math.sqrt(vCount)))
  const vRows   = Math.ceil(vCount / vCols)
  // Use a generous estimate accounting for group proxy sizes
  const avgW    = virtualNodeIds.reduce((s, id) => s + (nodeSizes[id]?.w ?? nodeW), 0) / vCount
  const avgH    = virtualNodeIds.reduce((s, id) => s + (nodeSizes[id]?.h ?? nodeH), 0) / vCount
  const canvasW = Math.max(vCols * (avgW + hGap) + 2 * pad, 900)
  const canvasH = Math.max(vRows * (avgH + vGap) + 2 * pad, 600)

  // ── Step 7: Run force simulation on virtual graph ─────────────────────────
  const {
    iterations           = hasStored ? 80 : 400,
    stepSize             = 1.0,
    cooling              = 0.985,
    convergenceThreshold = 0.4,
  } = opts

  const objectives: LayoutObjective[] = (opts.objectives ?? DEFAULT_OBJECTIVES)
    .map(def => {
      const factory = _registry.get(def.type)
      return factory ? factory(def.weight, def.params) : null
    })
    .filter((o): o is LayoutObjective => o !== null)

  const positions: Record<string, Point> = {}
  for (const id of virtualNodeIds) positions[id] = { ...virtualSeed[id] }

  const state: LayoutState = {
    positions,
    nodes:   virtualNodes,
    edges:   virtualEdges,
    groups:  [],           // groups are now expressed as proxy nodes + nodeSizes
    nodeW, nodeH, canvasW, canvasH,
    nodeSizes,
  }

  let step = stepSize

  for (let iter = 0; iter < iterations; iter++) {
    const total: Record<string, Point> = {}
    for (const obj of objectives) {
      const forces = obj.forces(state)
      for (const id of Object.keys(forces)) {
        const fv = forces[id]
        push(total, id, fv.x * obj.weight, fv.y * obj.weight)
      }
    }

    let maxMag = 0
    for (const id of Object.keys(total)) {
      const fv = total[id]
      const mag = Math.sqrt(fv.x * fv.x + fv.y * fv.y)
      if (mag > maxMag) maxMag = mag
      const cap   = Math.min(mag, 60)
      const scale = (cap / (mag || 1)) * step
      const nx = positions[id].x + fv.x * scale
      const ny = positions[id].y + fv.y * scale
      positions[id] = { x: Math.max(0, nx), y: Math.max(0, ny) }
    }

    step *= cooling
    if (maxMag * step < convergenceThreshold) break
  }

  // ── Step 8: Expand virtual positions → individual node positions ──────────
  const result: Record<string, Point> = {}

  // Group members: proxy top-left + GROUP_PAD + slot offset
  for (const g of dir.groups) {
    const vId    = GROUP_PROXY_PREFIX + g.id
    const vPos   = state.positions[vId]
    const layout = intraLayouts.get(g.id)
    if (!vPos || !layout) continue
    for (const [mId, offset] of layout.memberOffsets) {
      result[mId] = {
        x: vPos.x + GROUP_PAD + offset.x,
        y: vPos.y + GROUP_PAD + offset.y,
      }
    }
  }

  // Ungrouped nodes: use virtual position directly
  for (const id of ungroupedIds) {
    result[id] = state.positions[id] ?? { x: pad, y: pad }
  }

  return result
}
