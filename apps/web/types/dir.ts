/**
 * TypeScript types for the DIR (Diagram Intermediate Representation).
 * Field names match Python model_dump() output: from_node / to_node (not from/to).
 */

export type ComplexityLevel = 'low' | 'medium' | 'high'
export type DiagramType = 'architecture' | 'sequence' | 'flowchart' | 'er' | 'generic'
export type EdgeStyle = 'solid' | 'dashed' | 'dotted'
export type EdgeDirection = 'forward' | 'backward' | 'bidirectional'

export type NodeType =
  | 'user'
  | 'gateway'
  | 'service'
  | 'database'
  | 'queue'
  | 'storage'
  | 'generic'
  | 'aws.api_gateway'
  | 'aws.rds'
  | 'aws.s3'
  | 'aws.lambda'
  | 'aws.ec2'
  | 'aws.elasticache'

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
  description?: string
  complexity: ComplexityLevel
  group?: string
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
  complexity: ComplexityLevel
}

export interface DiagramGroup {
  id: string
  label: string
  contains: string[]
  complexity: ComplexityLevel
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
