"""SchemeWeaver models — all schemas in one place.

Domain models:
  dir.py    — DIR (Diagram Intermediate Representation) and its constituent types
  system.py — System Ontology layer (entities, relationships, views, action log)

API transport models:
  api.py    — HTTP request/response DTOs for every server endpoint
"""

from .dir import (
    DIR,
    DiagramType,
    DiagramEdge,
    DiagramGroup,
    DiagramMeta,
    DiagramNode,
    EdgeDirection,
    EdgeStyle,
    NodeType,
    Vendor,
)

from .system import (
    # Re-exported for convenience — DiagramType is the canonical definition in dir.py
    DiagramType,
    # Enums
    ActionType,
    EntityStatus,
    EntityType,
    RelationshipType,
    # Sub-models
    EntityOwner,
    EntityTech,
    RelationshipMetadata,
    # Core domain models
    ActionLogEntry,
    ActionTarget,
    Ontology,
    OntologyEntity,
    OntologyRelationship,
    System,
    View,
    ViewScope,
)

from .api import (
    # Generate / update
    GenerateRequest,
    GenerateResponse,
    UpdateRequest,
    # Model registry
    ModelInfo,
    ModelsResponse,
    # Library (legacy diagram store)
    DiagramEntry,
    DiagramSummary,
    SaveRequest,
    SaveResponse,
    # Repo analysis
    AnalyzeRepoRequest,
    AnalyzeRepoResponse,
    # Systems
    AddViewRequest,
    FromRepoRequest,
    GenerateSystemRequest,
    GenerateSystemResponse,
    LogActionRequest,
    SyncModelRequest,
    SyncViewRequest,
    SystemSummary,
    UpdateOntologyRequest,
    UpdateProseRequest,
    ViewResponse,
)

__all__ = [
    # ── dir.py ──────────────────────────────────────────────────────────────
    "DIR",
    "DiagramType",
    "DiagramEdge",
    "DiagramGroup",
    "DiagramMeta",
    "DiagramNode",
    "EdgeDirection",
    "EdgeStyle",
    "NodeType",
    "Vendor",
    # ── system.py ───────────────────────────────────────────────────────────
    "ActionType",
    "EntityStatus",
    "EntityType",
    "RelationshipType",
    "EntityOwner",
    "EntityTech",
    "RelationshipMetadata",
    "ActionLogEntry",
    "ActionTarget",
    "Ontology",
    "OntologyEntity",
    "OntologyRelationship",
    "System",
    "View",
    "ViewScope",
    # ── api.py ──────────────────────────────────────────────────────────────
    "GenerateRequest",
    "GenerateResponse",
    "UpdateRequest",
    "ModelInfo",
    "ModelsResponse",
    "DiagramEntry",
    "DiagramSummary",
    "SaveRequest",
    "SaveResponse",
    "AnalyzeRepoRequest",
    "AnalyzeRepoResponse",
    "AddViewRequest",
    "FromRepoRequest",
    "GenerateSystemRequest",
    "GenerateSystemResponse",
    "LogActionRequest",
    "SyncModelRequest",
    "SyncViewRequest",
    "SystemSummary",
    "UpdateOntologyRequest",
    "UpdateProseRequest",
    "ViewResponse",
]
