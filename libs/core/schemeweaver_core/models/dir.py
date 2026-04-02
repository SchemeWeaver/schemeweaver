"""Pydantic v2 models for the Diagram Intermediate Representation (DIR)."""
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DiagramType(str, Enum):
    ARCHITECTURE = "architecture"
    FLOWCHART = "flowchart"
    ERD = "erd"
    SEQUENCE = "sequence"
    GENERIC = "generic"


class NodeType(str, Enum):
    GENERIC = "generic"
    SERVICE = "service"
    DATABASE = "database"
    QUEUE = "queue"
    STORAGE = "storage"
    GATEWAY = "gateway"
    USER = "user"
    AWS_LAMBDA = "aws.lambda"
    AWS_S3 = "aws.s3"
    AWS_RDS = "aws.rds"
    AWS_EC2 = "aws.ec2"
    AWS_ELASTICACHE = "aws.elasticache"
    AWS_API_GATEWAY = "aws.api_gateway"


class EdgeStyle(str, Enum):
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class EdgeDirection(str, Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    BIDIRECTIONAL = "bidirectional"


class DiagramMeta(BaseModel):
    title: str
    description: Optional[str] = None
    diagram_type: DiagramType = DiagramType.GENERIC
    author: str = "schemeweaver"
    version: str = "1.0"


class DiagramNode(BaseModel):
    id: str
    label: str
    node_type: NodeType = NodeType.GENERIC
    complexity: ComplexityLevel = ComplexityLevel.LOW
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
    complexity: ComplexityLevel = ComplexityLevel.LOW
    style: EdgeStyle = EdgeStyle.SOLID
    direction: EdgeDirection = EdgeDirection.FORWARD

    model_config = {"populate_by_name": True}


class DiagramGroup(BaseModel):
    id: str
    label: str
    complexity: ComplexityLevel = ComplexityLevel.MEDIUM
    contains: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DIR(BaseModel):
    """Diagram Intermediate Representation."""

    version: str = "1.0"
    meta: DiagramMeta
    complexity_levels: list[ComplexityLevel] = Field(
        default=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH]
    )
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    groups: list[DiagramGroup] = Field(default_factory=list)
