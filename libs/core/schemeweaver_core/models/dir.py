"""Pydantic v2 models for the Diagram Intermediate Representation (DIR)."""
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class DiagramType(str, Enum):
    ARCHITECTURE = "architecture"
    FLOWCHART = "flowchart"
    ERD = "erd"
    SEQUENCE = "sequence"
    GENERIC = "generic"


class NodeType(str, Enum):
    GENERIC        = "generic"
    USER           = "user"
    SERVICE        = "service"
    API            = "api"
    GATEWAY        = "gateway"
    DATABASE       = "database"
    DOCUMENT_STORE = "document-store"
    CACHE          = "cache"
    QUEUE          = "queue"
    STREAM         = "stream"
    FILE_STORE     = "file-store"
    SEARCH         = "search"
    CDN            = "cdn"
    AUTH           = "auth"
    MONITOR        = "monitor"


class Vendor(str, Enum):
    AWS        = "aws"
    AZURE      = "azure"
    GCP        = "gcp"
    CLOUDFLARE = "cloudflare"
    VERCEL     = "vercel"
    HASHICORP  = "hashicorp"


class EdgeStyle(str, Enum):
    SOLID  = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class EdgeDirection(str, Enum):
    FORWARD       = "forward"
    BACKWARD      = "backward"
    BIDIRECTIONAL = "bidirectional"


class DiagramMeta(BaseModel):
    title: str
    description: Optional[str] = None
    diagram_type: DiagramType = DiagramType.GENERIC
    tags: list[str] = Field(default_factory=list)
    author: str = "schemeweaver"
    version: str = "1.0"


class DiagramNode(BaseModel):
    id: str
    label: str
    node_type: NodeType = NodeType.GENERIC
    vendor: Optional[Vendor] = None
    technology: Optional[str] = None
    description: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    children: list["DiagramNode"] = Field(default_factory=list)
    # Canvas position (set by frontend after user arranges nodes; None = auto-layout)
    x: Optional[float] = None
    y: Optional[float] = None


class DiagramEdge(BaseModel):
    id: str
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    label: Optional[str] = None
    style: EdgeStyle = EdgeStyle.SOLID
    direction: EdgeDirection = EdgeDirection.FORWARD

    model_config = {"populate_by_name": True}


class DiagramGroup(BaseModel):
    id: str
    label: str
    contains: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DIR(BaseModel):
    """Diagram Intermediate Representation."""

    version: str = "1.0"
    meta: DiagramMeta
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    groups: list[DiagramGroup] = Field(default_factory=list)
