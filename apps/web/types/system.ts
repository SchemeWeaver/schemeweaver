/**
 * TypeScript types for the System Ontology layer.
 * Mirrors libs/core/schemeweaver_core/models/system.py.
 */
import type { DIR } from './dir'

// ── Ontology enums ─────────────────────────────────────────────────────────

export type EntityType =
  | 'service' | 'database' | 'queue' | 'storage' | 'gateway' | 'user'
  | 'team' | 'concept' | 'data_entity' | 'external_system' | 'other'

export type RelationshipType =
  | 'calls' | 'owns' | 'depends_on' | 'publishes'
  | 'subscribes_to' | 'stores_in' | 'managed_by' | 'other'

export type EntityStatus = 'active' | 'deprecated' | 'planned'

export type SystemDiagramType = 'architecture' | 'sequence' | 'er' | 'flowchart' | 'generic'

// ── Ontology models ────────────────────────────────────────────────────────

export interface EntityOwner {
  team?:     string
  contact?:  string
  docs_url?: string
}

export interface EntityTech {
  stack?:             string
  deployment_target?: string
  version?:           string
  sla?:               string
}

export interface OntologyEntity {
  id:          string
  name:        string
  type:        EntityType
  description?: string
  domain?:     string
  status:      EntityStatus
  tags:        string[]
  owner?:      EntityOwner
  tech?:       EntityTech
  metadata:    Record<string, string>
}

export interface RelationshipMetadata {
  protocol?:      string
  data_contract?: string
  latency_sla?:   string
}

export interface OntologyRelationship {
  id:          string
  from_entity: string
  to_entity:   string
  type:        RelationshipType
  description?: string
  status:      EntityStatus
  metadata?:   RelationshipMetadata
}

export interface Ontology {
  entities:      OntologyEntity[]
  relationships: OntologyRelationship[]
}

// ── View ───────────────────────────────────────────────────────────────────

export interface ViewScope {
  entity_ids: string[]
  tags:       string[]
  domain?:    string
  query?:     string
}

export interface View {
  id:           string
  name:         string
  description?: string
  diagram_type: SystemDiagramType
  scope:        ViewScope
  dir:          DIR
  positions:    Record<string, { x: number; y: number }>
  created_at:   string
  updated_at:   string
}

// ── Action log ─────────────────────────────────────────────────────────────

export type ActionType =
  | 'AddEntity'          | 'RemoveEntity'         | 'UpdateEntity'
  | 'AddRelationship'    | 'RemoveRelationship'    | 'UpdateRelationship'
  | 'AddView'            | 'UpdateView'            | 'RemoveView'
  | 'EditProse'
  | 'SyncProseToOntology' | 'SyncOntologyToProse'
  | 'SyncOntologyToView'  | 'SyncViewToOntology'
  | 'UndoAction'

export interface ActionTarget {
  type: 'entity' | 'relationship' | 'view' | 'prose'
  id?:  string
}

export interface ActionLogEntry {
  id:           string
  timestamp:    string
  action:       ActionType
  target:       ActionTarget
  view_context?: string
  payload:      Record<string, unknown>
  undone:       boolean
}

// ── System ─────────────────────────────────────────────────────────────────

export interface System {
  id:         string
  slug:       string
  name:       string
  prose:      string
  ontology:   Ontology
  views:      View[]
  log:        ActionLogEntry[]
  created_at: string
  updated_at: string
}

// ── API request/response shapes ────────────────────────────────────────────

export interface SystemSummary {
  slug:        string
  name:        string
  view_count:  number
  entity_count: number
  updated_at:  string
}
