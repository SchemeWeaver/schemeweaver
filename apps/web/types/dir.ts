/**
 * TypeScript types for the DIR (Diagram Intermediate Representation).
 * Field names match Python model_dump() output: from_node / to_node (not from/to).
 */

export type DiagramType = 'architecture' | 'sequence' | 'er' | 'flowchart' | 'generic'
export type EdgeStyle = 'solid' | 'dashed' | 'dotted'
export type EdgeDirection = 'forward' | 'backward' | 'bidirectional'

/** Vendor-agnostic semantic category — drives shape selection. */
export type NodeType =
  | 'generic'
  | 'user'
  | 'service'
  | 'api'
  | 'gateway'
  | 'database'
  | 'document-store'
  | 'cache'
  | 'queue'
  | 'stream'
  | 'file-store'
  | 'search'
  | 'cdn'
  | 'auth'
  | 'monitor'

/** Cloud / platform vendor — drives icon branding and stroke color. */
export type Vendor = 'aws' | 'azure' | 'gcp' | 'cloudflare' | 'vercel' | 'hashicorp'

export interface DiagramMeta {
  title: string
  description?: string
  diagram_type: DiagramType
  tags: string[]
}

export interface DiagramNode {
  id: string
  label: string
  node_type: NodeType
  /** Optional vendor for brand-specific rendering. */
  vendor?: Vendor | null
  /** Optional specific technology or service (e.g. 'rds', 'fastapi', 'redis'). */
  technology?: string | null
  description?: string
  metadata?: Record<string, unknown>
  children?: DiagramNode[]
  x?: number
  y?: number
}

export interface DiagramEdge {
  id: string
  from_node: string   // NOTE: Python model_dump() uses from_node, not from
  to_node: string     // NOTE: Python model_dump() uses to_node, not to
  label?: string
  style: EdgeStyle
  direction: EdgeDirection
}

export interface DiagramGroup {
  id: string
  label: string
  contains: string[]
  metadata?: Record<string, unknown>
}

export interface DIR {
  version: string
  meta: DiagramMeta
  nodes: DiagramNode[]
  edges: DiagramEdge[]
  groups: DiagramGroup[]
}

/** API response from POST /v1/generate or POST /v1/update */
export interface GenerateResponse {
  svg: string
  dir: DIR
  mermaid: string
  issues: string[]
  model: string
}

export interface ModelInfo {
  id: string
  provider: string
  accessible: boolean
}

export interface ModelsResponse {
  default: string
  models: ModelInfo[]
}
