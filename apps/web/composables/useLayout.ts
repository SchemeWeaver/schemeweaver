/**
 * Dagre-based hierarchical layout for Vue Flow nodes.
 * Returns x/y positions keyed by node id.
 */
import dagre from '@dagrejs/dagre'

// Match Python layout constants (NODE_W=160, NODE_H=60 in layout.py)
const NODE_W = 160
const NODE_H = 60
const RANK_SEP = 80
const NODE_SEP = 40

export interface LayoutPosition {
  x: number
  y: number
  width: number
  height: number
}

export function useLayout() {
  function computeLayout(
    nodes: { id: string }[],
    edges: { from_node: string; to_node: string }[],
  ): Map<string, LayoutPosition> {
    const g = new dagre.graphlib.Graph()
    g.setDefaultEdgeLabel(() => ({}))
    g.setGraph({ rankdir: 'LR', ranksep: RANK_SEP, nodesep: NODE_SEP })

    for (const node of nodes) {
      g.setNode(node.id, { width: NODE_W, height: NODE_H })
    }
    for (const edge of edges) {
      if (edge.from_node && edge.to_node) {
        g.setEdge(edge.from_node, edge.to_node)
      }
    }

    dagre.layout(g)

    const positions = new Map<string, LayoutPosition>()
    for (const node of nodes) {
      const n = g.node(node.id)
      if (n) {
        positions.set(node.id, {
          x: n.x - NODE_W / 2,
          y: n.y - NODE_H / 2,
          width: NODE_W,
          height: NODE_H,
        })
      }
    }
    return positions
  }

  return { computeLayout }
}
