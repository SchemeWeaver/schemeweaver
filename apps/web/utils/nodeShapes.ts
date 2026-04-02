/**
 * Shared node shape and colour data used by DiagramCanvas and ShapePanel.
 * All shapes are defined within a 160 × 60 coordinate space.
 */

export type ShapeKind = 'rounded-rect' | 'rect' | 'ellipse' | 'diamond' | 'cylinder' | 'parallelogram'

export function shapeKind(nodeType: string): ShapeKind {
  switch (nodeType) {
    case 'user':                                                   return 'ellipse'
    case 'gateway': case 'aws.api_gateway':                        return 'diamond'
    case 'database': case 'aws.rds': case 'aws.elasticache':
    case 'storage':  case 'aws.s3':                                return 'cylinder'
    case 'queue':                                                  return 'parallelogram'
    case 'generic': case 'aws.ec2':                                return 'rect'
    default:                                                       return 'rounded-rect'
  }
}

// ── Text Y positions within a 160 × 60 node box ────────────────────────────

/** Y for the primary label (uses dominant-baseline="middle") */
export function labelY(nodeType: string): number {
  switch (shapeKind(nodeType)) {
    case 'cylinder': return 33   // centre of body (cap at y=12, bottom arc at y=54)
    default:         return 26   // NODE_H/2 - 4
  }
}

/** Y for the secondary type text (baseline anchor, no dominant-baseline) */
export function typeTextY(nodeType: string): number {
  switch (shapeKind(nodeType)) {
    case 'cylinder': return 48
    case 'diamond':  return 37
    default:         return 44   // NODE_H/2 + 14
  }
}

// ── Node colours ────────────────────────────────────────────────────────────

export const NODE_COLORS: Record<string, { fill: string; stroke: string }> = {
  user:              { fill: '#e8f4f8', stroke: '#5bc0de' },
  gateway:           { fill: '#fff3cd', stroke: '#f0ad4e' },
  'aws.api_gateway': { fill: '#fff3cd', stroke: '#f0ad4e' },
  service:           { fill: '#f0f4ff', stroke: '#6c8ebf' },
  generic:           { fill: '#f5f5f5', stroke: '#aaaaaa' },
  database:          { fill: '#d4edda', stroke: '#5cb85c' },
  'aws.rds':         { fill: '#d4edda', stroke: '#5cb85c' },
  queue:             { fill: '#fde8e8', stroke: '#d9534f' },
  storage:           { fill: '#e2d9f3', stroke: '#9b59b6' },
  'aws.s3':          { fill: '#e2d9f3', stroke: '#9b59b6' },
  'aws.lambda':      { fill: '#f0f4ff', stroke: '#6c8ebf' },
  'aws.ec2':         { fill: '#f5f5f5', stroke: '#aaaaaa' },
  'aws.elasticache': { fill: '#fde8e8', stroke: '#d9534f' },
}

export const nodeColor = (t: string) => NODE_COLORS[t] ?? NODE_COLORS.generic
