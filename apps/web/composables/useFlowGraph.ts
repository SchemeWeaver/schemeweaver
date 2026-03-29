/**
 * Converts DIR + complexity filter → Vue Flow nodes and edges.
 *
 * Layout is computed once when the DIR changes.
 * Complexity filtering only toggles hidden/visible via a class — no re-layout.
 */
import { MarkerType } from '@vue-flow/core'
import type { Node as FlowNode, Edge as FlowEdge } from '@vue-flow/core'
import type { DIR, ComplexityLevel } from '~/types/dir'
import { useLayout } from './useLayout'

const COMPLEXITY_ORDER: Record<ComplexityLevel, number> = {
  low: 0,
  medium: 1,
  high: 2,
}

export function useFlowGraph(
  dir: Readonly<Ref<DIR | null>>,
  complexity: Ref<ComplexityLevel>,
) {
  const { computeLayout } = useLayout()

  // Recompute layout only when dir changes
  const layout = computed(() => {
    if (!dir.value) return new Map()
    return computeLayout(dir.value.nodes, dir.value.edges)
  })

  const flowNodes = computed<FlowNode[]>(() => {
    if (!dir.value) return []
    const maxOrder = COMPLEXITY_ORDER[complexity.value]

    return dir.value.nodes.map((node) => {
      const pos = layout.value.get(node.id) ?? { x: 0, y: 0, width: 160, height: 60 }
      const visible = COMPLEXITY_ORDER[node.complexity] <= maxOrder

      return {
        id: node.id,
        type: 'sw-node',
        position: { x: pos.x, y: pos.y },
        data: {
          label: node.label,
          nodeType: node.node_type,
          description: node.description,
          complexity: node.complexity,
          visible,
        },
        class: visible ? '' : 'sw-hidden',
        style: { width: `${pos.width}px`, height: `${pos.height}px` },
      } satisfies FlowNode
    })
  })

  const flowEdges = computed<FlowEdge[]>(() => {
    if (!dir.value) return []
    const maxOrder = COMPLEXITY_ORDER[complexity.value]

    return dir.value.edges
      .filter((e) => COMPLEXITY_ORDER[e.complexity] <= maxOrder)
      .map((edge) => ({
        id: edge.id,
        source: edge.from_node,
        target: edge.to_node,
        label: edge.label,
        animated: edge.style !== 'solid',
        type: 'smoothstep',
        markerEnd: { type: MarkerType.ArrowClosed, color: '#666' },
        class: `sw-edge-${edge.style}`,
        data: { style: edge.style, direction: edge.direction },
      } satisfies FlowEdge))
  })

  return { flowNodes, flowEdges }
}
