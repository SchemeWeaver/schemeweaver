"""API request/response DTOs — wire-format models for all server endpoints.

These are thin Pydantic models that define the HTTP contract.  They live here
so that the full schema surface is visible alongside the domain models.
"""
from typing import Any, Optional

from pydantic import BaseModel


# ── Generate / Update ─────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    model: Optional[str] = None


class GenerateResponse(BaseModel):
    svg: str
    dir: dict[str, Any]
    mermaid: str = ""
    issues: list[str] = []
    model: str = ""


class UpdateRequest(BaseModel):
    dir: dict[str, Any]
    feedback: str
    model: Optional[str] = None


# ── Models registry ───────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    provider: str
    accessible: bool


class ModelsResponse(BaseModel):
    default: str
    models: list[ModelInfo]


# ── Library (legacy diagram store) ────────────────────────────────────────────

class DiagramSummary(BaseModel):
    slug: str
    title: str
    diagram_type: str
    nodes: int
    edges: int
    groups: int
    elapsed_s: float
    issues: list[str] = []
    model: str = ""


class DiagramEntry(BaseModel):
    svg: str
    dir: dict[str, Any]
    mermaid: str = ""
    issues: list[str] = []
    model: str = ""


class SaveRequest(BaseModel):
    dir: dict[str, Any]
    svg: str
    mermaid: str = ""
    issues: list[str] = []
    model: str = ""
    slug: Optional[str] = None  # provided → overwrite; omitted → new slug


class SaveResponse(BaseModel):
    slug: str


# ── Repo analysis ─────────────────────────────────────────────────────────────

class AnalyzeRepoRequest(BaseModel):
    source: str           # local path or git URL
    shallow: bool = True  # reserved for future depth control


class AnalyzeRepoResponse(BaseModel):
    repo_name: str
    source: str
    knowledge_base: str   # compiled markdown


# ── Systems ───────────────────────────────────────────────────────────────────

class SystemSummary(BaseModel):
    slug: str
    name: str
    entity_count: int
    view_count: int
    updated_at: str


class GenerateSystemRequest(BaseModel):
    prompt: str
    model: Optional[str] = None


class GenerateSystemResponse(BaseModel):
    slug: str
    system: dict[str, Any]


class UpdateProseRequest(BaseModel):
    prose: str


class UpdateOntologyRequest(BaseModel):
    ontology: dict[str, Any]


class AddViewRequest(BaseModel):
    name: str
    description: Optional[str] = None
    scope: Optional[dict[str, Any]] = None


class ViewResponse(BaseModel):
    view_id: str
    svg: str
    dir: dict[str, Any]


class SyncViewRequest(BaseModel):
    view_id: str
    model: Optional[str] = None


class SyncModelRequest(BaseModel):
    model: Optional[str] = None


class LogActionRequest(BaseModel):
    action: str                          # ActionType value
    target_type: str
    target_id: Optional[str] = None
    view_context: Optional[str] = None
    payload: dict[str, Any] = {}


class FromRepoRequest(BaseModel):
    source: str                          # local path or git URL
    knowledge_base: Optional[str] = None # pre-compiled KB markdown
    model: Optional[str] = None
