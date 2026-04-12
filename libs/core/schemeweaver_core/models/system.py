"""Pydantic v2 models for the System Ontology layer."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from .dir import DIR, DiagramType


# ── Ontology enums ─────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    SERVICE        = "service"
    DATABASE       = "database"
    QUEUE          = "queue"
    STORAGE        = "storage"
    GATEWAY        = "gateway"
    USER           = "user"
    TEAM           = "team"
    CONCEPT        = "concept"
    DATA_ENTITY    = "data_entity"
    EXTERNAL_SYSTEM = "external_system"
    OTHER          = "other"


class RelationshipType(str, Enum):
    CALLS          = "calls"
    OWNS           = "owns"
    DEPENDS_ON     = "depends_on"
    PUBLISHES      = "publishes"
    SUBSCRIBES_TO  = "subscribes_to"
    STORES_IN      = "stores_in"
    MANAGED_BY     = "managed_by"
    OTHER          = "other"


class EntityStatus(str, Enum):
    ACTIVE     = "active"
    DEPRECATED = "deprecated"
    PLANNED    = "planned"


# DiagramType is imported from .dir — defined once, used here for View.diagram_type.
# Re-exported via models/__init__.py for convenience.

# ── Ontology models ────────────────────────────────────────────────────────────

class EntityOwner(BaseModel):
    team:     Optional[str] = None
    contact:  Optional[str] = None
    docs_url: Optional[str] = None


class EntityTech(BaseModel):
    stack:             Optional[str] = None
    deployment_target: Optional[str] = None
    version:           Optional[str] = None
    sla:               Optional[str] = None


class OntologyEntity(BaseModel):
    id:          str
    name:        str
    type:        EntityType = EntityType.OTHER
    description: Optional[str] = None
    domain:      Optional[str] = None          # bounded context / domain
    status:      EntityStatus = EntityStatus.ACTIVE
    tags:        list[str] = Field(default_factory=list)
    owner:       Optional[EntityOwner] = None
    tech:        Optional[EntityTech] = None
    # simple-icons slug for the technology (e.g. "redis", "postgresql", "docker")
    technology:  Optional[str] = None
    metadata:    dict[str, Any] = Field(default_factory=dict)


class RelationshipMetadata(BaseModel):
    protocol:      Optional[str] = None        # HTTP, gRPC, AMQP, …
    data_contract: Optional[str] = None
    latency_sla:   Optional[str] = None


class OntologyRelationship(BaseModel):
    id:          str
    from_entity: str                           # OntologyEntity.id
    to_entity:   str                           # OntologyEntity.id
    type:        RelationshipType = RelationshipType.OTHER
    description: Optional[str] = None
    status:      EntityStatus = EntityStatus.ACTIVE
    metadata:    Optional[RelationshipMetadata] = None


class Ontology(BaseModel):
    entities:      list[OntologyEntity]      = Field(default_factory=list)
    relationships: list[OntologyRelationship] = Field(default_factory=list)


# ── View ───────────────────────────────────────────────────────────────────────

class ViewScope(BaseModel):
    entity_ids: list[str] = Field(default_factory=list)   # explicit selection
    tags:       list[str] = Field(default_factory=list)   # tag filter
    domain:     Optional[str] = None                      # domain filter
    query:      Optional[str] = None                      # natural-language description


class View(BaseModel):
    id:           str
    name:         str
    description:  Optional[str] = None
    diagram_type: DiagramType = DiagramType.ARCHITECTURE
    scope:        ViewScope = Field(default_factory=ViewScope)
    dir:          DIR
    # Node positions keyed by node ID (mirrors frontend pos state)
    positions:    dict[str, dict[str, float]] = Field(default_factory=dict)
    created_at:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Action log ─────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    ADD_ENTITY            = "AddEntity"
    REMOVE_ENTITY         = "RemoveEntity"
    UPDATE_ENTITY         = "UpdateEntity"
    ADD_RELATIONSHIP      = "AddRelationship"
    REMOVE_RELATIONSHIP   = "RemoveRelationship"
    UPDATE_RELATIONSHIP   = "UpdateRelationship"
    ADD_VIEW              = "AddView"
    UPDATE_VIEW           = "UpdateView"
    REMOVE_VIEW           = "RemoveView"
    EDIT_PROSE            = "EditProse"
    SYNC_PROSE_TO_ONTOLOGY   = "SyncProseToOntology"
    SYNC_ONTOLOGY_TO_PROSE   = "SyncOntologyToProse"
    SYNC_ONTOLOGY_TO_VIEW    = "SyncOntologyToView"
    SYNC_VIEW_TO_ONTOLOGY    = "SyncViewToOntology"
    UNDO_ACTION           = "UndoAction"


class ActionTarget(BaseModel):
    type: str                    # 'entity' | 'relationship' | 'view' | 'prose'
    id:   Optional[str] = None


class ActionLogEntry(BaseModel):
    id:           str
    timestamp:    datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action:       ActionType
    target:       ActionTarget
    view_context: Optional[str] = None   # view.id the action originated from
    payload:      dict[str, Any] = Field(default_factory=dict)   # before/after delta
    undone:       bool = False


# ── System (top-level) ─────────────────────────────────────────────────────────

class System(BaseModel):
    id:         str
    slug:       str
    name:       str
    prose:      str = ""
    ontology:   Ontology = Field(default_factory=Ontology)
    views:      list[View] = Field(default_factory=list)
    log:        list[ActionLogEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
