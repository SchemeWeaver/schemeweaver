/**
 * Shared node shape and colour data used by DiagramCanvas and ShapePanel.
 * All shapes are defined within a 160 × 60 coordinate space.
 */

import { VENDOR_STROKE_COLORS } from './iconRegistry'

export type ShapeKind = 'rounded-rect' | 'rect' | 'ellipse' | 'diamond' | 'cylinder' | 'parallelogram'

export function shapeKind(nodeType: string): ShapeKind {
  switch (nodeType) {
    case 'user':                                                                    return 'ellipse'
    case 'gateway':                                                                 return 'diamond'
    case 'database': case 'document-store': case 'cache':
    case 'file-store': case 'search':                                               return 'cylinder'
    case 'queue': case 'stream':                                                    return 'parallelogram'
    case 'generic':                                                                 return 'rect'
    default:                                                                        return 'rounded-rect'
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
  user:             { fill: '#e8f4f8', stroke: '#5bc0de' },
  service:          { fill: '#f0f4ff', stroke: '#6c8ebf' },
  api:              { fill: '#eef2ff', stroke: '#6c8ebf' },
  gateway:          { fill: '#fff3cd', stroke: '#f0ad4e' },
  database:         { fill: '#d4edda', stroke: '#5cb85c' },
  'document-store': { fill: '#d4edda', stroke: '#5cb85c' },
  cache:            { fill: '#fde8e8', stroke: '#d9534f' },
  queue:            { fill: '#fef3e2', stroke: '#e8963a' },
  stream:           { fill: '#fef3e2', stroke: '#e8963a' },
  'file-store':     { fill: '#e2d9f3', stroke: '#9b59b6' },
  search:           { fill: '#e2d9f3', stroke: '#9b59b6' },
  cdn:              { fill: '#e8f8f5', stroke: '#1abc9c' },
  auth:             { fill: '#fce8ff', stroke: '#c039e0' },
  monitor:          { fill: '#f0f0f0', stroke: '#7f8c8d' },
  generic:          { fill: '#f5f5f5', stroke: '#aaaaaa' },
}

/**
 * Returns fill + stroke colors for a node.
 * When `vendor` is provided, the stroke shifts to the vendor's brand color.
 */
export function nodeColor(nodeType: string, vendor?: string | null): { fill: string; stroke: string } {
  const base = NODE_COLORS[nodeType] ?? NODE_COLORS.generic
  if (vendor) {
    const vendorStroke = VENDOR_STROKE_COLORS[vendor]
    if (vendorStroke) return { fill: base.fill, stroke: vendorStroke }
  }
  return base
}
