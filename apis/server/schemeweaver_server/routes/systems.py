"""Systems endpoints — full System CRUD + AI generation."""
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schemeweaver_core.models.dir import DiagramType
from schemeweaver_core.models.system import (
    ActionLogEntry,
    ActionTarget,
    ActionType,
    Ontology,
    OntologyEntity,
    OntologyRelationship,
    RelationshipType,
    System,
    View,
    ViewScope,
)
from schemeweaver_core.ontology_to_dir import ontology_to_dir
from schemeweaver_core.system_pipeline import SystemPipeline
from schemeweaver_core.providers import make_provider
from schemeweaver_core.renderer import Renderer

from ..config import settings

log = logging.getLogger("schemeweaver.systems")
router = APIRouter()
renderer = Renderer()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _systems_dir() -> Path:
    d = settings.data_systems_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _system_path(slug: str) -> Path:
    """Resolve and guard against path traversal."""
    base = _systems_dir().resolve()
    target = (base / slug).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid slug")
    return target


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "system"


def _unique_slug(base: str) -> str:
    systems = _systems_dir()
    if not (systems / base).exists():
        return base
    i = 2
    while (systems / f"{base}-{i}").exists():
        i += 1
    return f"{base}-{i}"


def _load_system(slug: str) -> System:
    path = _system_path(slug) / "system.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"System '{slug}' not found")
    return System.model_validate_json(path.read_text(encoding="utf-8"))


def _save_system(system: System, slug: str) -> None:
    system_dir = _system_path(slug)
    system_dir.mkdir(parents=True, exist_ok=True)
    (system_dir / "system.json").write_text(
        system.model_dump_json(indent=2), encoding="utf-8"
    )
    # Write a lightweight summary for fast listing
    summary = {
        "slug": slug,
        "name": system.name,
        "entity_count": len(system.ontology.entities),
        "view_count": len(system.views),
        "updated_at": system.updated_at.isoformat(),
    }
    (system_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _build_pipeline(model_id: str | None = None) -> SystemPipeline:
    """Build a SystemPipeline using the first accessible provider."""
    if model_id:
        # Try to use the specified model
        from ..routes.generate import _provider_for
        try:
            provider_name = _provider_for(model_id)
        except Exception:
            provider_name = "anthropic"
            model_id = None

    if not model_id:
        # Default to claude-sonnet if available, else first accessible
        if settings.anthropic_api_key:
            provider_name = "anthropic"
            model_id = "claude-sonnet-4-6"
        elif settings.openai_api_key:
            provider_name = "openai"
            model_id = "gpt-4o"
        else:
            raise HTTPException(status_code=503, detail="No accessible AI provider configured")

    if provider_name == "anthropic":
        api_key, base_url = settings.anthropic_api_key, None
    elif provider_name == "openai":
        api_key, base_url = settings.openai_api_key, None
    else:
        api_key, base_url = "ollama", f"{settings.ollama_base_url}/v1"

    provider = make_provider(provider=provider_name, model=model_id, api_key=api_key, base_url=base_url)
    return SystemPipeline(provider)


# ── Pydantic request/response models ──────────────────────────────────────────

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
    system: dict


class UpdateProseRequest(BaseModel):
    prose: str


class UpdateOntologyRequest(BaseModel):
    ontology: dict


class AddViewRequest(BaseModel):
    name: str
    description: Optional[str] = None
    scope: Optional[dict] = None


class ViewResponse(BaseModel):
    view_id: str
    svg: str
    dir: dict


class SyncViewRequest(BaseModel):
    view_id: str
    model: Optional[str] = None


class LogActionRequest(BaseModel):
    action: str          # ActionType value
    target_type: str
    target_id: Optional[str] = None
    view_context: Optional[str] = None
    payload: dict = {}


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/systems", response_model=list[SystemSummary])
def list_systems():
    """List all saved systems, newest first."""
    systems = _systems_dir()
    results: list[SystemSummary] = []
    for slug_dir in sorted(systems.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not slug_dir.is_dir():
            continue
        summary_path = slug_dir / "summary.json"
        if not summary_path.exists():
            continue
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            results.append(SystemSummary(**data))
        except Exception:
            continue
    return results


@router.post("/systems/generate", response_model=GenerateSystemResponse)
async def generate_system(req: GenerateSystemRequest):
    """Generate a new System from a natural-language prompt."""
    log.info("generate_system  prompt=%r", req.prompt[:80])
    loop = asyncio.get_event_loop()
    try:
        pipeline = _build_pipeline(req.model)
        system = await loop.run_in_executor(None, pipeline.generate, req.prompt)
    except HTTPException:
        raise
    except Exception:
        log.exception("generate_system  unexpected error")
        raise HTTPException(status_code=500, detail="System generation failed — see server logs")

    slug = _unique_slug(_slugify(system.name))
    system = system.model_copy(update={"slug": slug})
    _save_system(system, slug)
    log.info("generate_system  slug=%s  entities=%d", slug, len(system.ontology.entities))
    return GenerateSystemResponse(slug=slug, system=json.loads(system.model_dump_json()))


@router.get("/systems/{slug}", response_model=dict)
def get_system(slug: str):
    """Load a full System by slug."""
    system = _load_system(slug)
    return json.loads(system.model_dump_json())


@router.delete("/systems/{slug}", status_code=204)
def delete_system(slug: str):
    """Delete a system and all its files."""
    import shutil
    path = _system_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"System '{slug}' not found")
    shutil.rmtree(path)


@router.patch("/systems/{slug}/prose")
def update_prose(slug: str, req: UpdateProseRequest):
    """Update the prose description of a system."""
    from datetime import datetime, timezone
    system = _load_system(slug)
    system = system.model_copy(update={
        "prose": req.prose,
        "updated_at": datetime.now(timezone.utc),
    })
    _save_system(system, slug)
    return {"ok": True}


@router.patch("/systems/{slug}/ontology")
def update_ontology(slug: str, req: UpdateOntologyRequest):
    """Replace the ontology of a system."""
    from datetime import datetime, timezone
    system = _load_system(slug)
    ontology = Ontology.model_validate(req.ontology)
    system = system.model_copy(update={
        "ontology": ontology,
        "updated_at": datetime.now(timezone.utc),
    })
    _save_system(system, slug)
    return {"ok": True}


@router.post("/systems/{slug}/views", response_model=ViewResponse)
def add_view(slug: str, req: AddViewRequest):
    """Create a new scoped view derived from the system ontology."""
    from datetime import datetime, timezone
    import uuid
    system = _load_system(slug)

    scope = ViewScope.model_validate(req.scope) if req.scope else ViewScope()
    now = datetime.now(timezone.utc)
    view_id = f"view-{uuid.uuid4().hex[:8]}"

    dir_data = ontology_to_dir(
        system.ontology,
        title=req.name,
        scope=scope,
        diagram_type=DiagramType.ARCHITECTURE,
    )
    view = View(
        id=view_id,
        name=req.name,
        description=req.description,
        scope=scope,
        dir=dir_data,
        created_at=now,
        updated_at=now,
    )

    updated_views = list(system.views) + [view]
    system = system.model_copy(update={"views": updated_views, "updated_at": now})
    _save_system(system, slug)

    svg = renderer.render(dir_data)
    return ViewResponse(view_id=view_id, svg=svg, dir=json.loads(dir_data.model_dump_json()))


@router.get("/systems/{slug}/views/{view_id}/svg")
def get_view_svg(slug: str, view_id: str):
    """Render and return SVG for a specific view."""
    system = _load_system(slug)
    view = next((v for v in system.views if v.id == view_id), None)
    if not view:
        raise HTTPException(status_code=404, detail=f"View '{view_id}' not found")
    svg = renderer.render(view.dir)
    return {"svg": svg}


@router.patch("/systems/{slug}/views/{view_id}")
def update_view_dir(slug: str, view_id: str, body: dict):
    """Update the DIR of a view (e.g. after user edits on canvas)."""
    from schemeweaver_core.models.dir import DIR
    from datetime import datetime, timezone

    system = _load_system(slug)
    views = list(system.views)
    idx = next((i for i, v in enumerate(views) if v.id == view_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"View '{view_id}' not found")

    updated_dir = DIR.model_validate(body.get("dir", {}))
    positions = body.get("positions", {})
    now = datetime.now(timezone.utc)
    views[idx] = views[idx].model_copy(update={
        "dir": updated_dir,
        "positions": positions,
        "updated_at": now,
    })
    system = system.model_copy(update={"views": views, "updated_at": now})
    _save_system(system, slug)
    return {"ok": True}


@router.post("/systems/{slug}/log")
def append_log(slug: str, req: LogActionRequest):
    """Append an action to the system log."""
    import uuid
    from datetime import datetime, timezone

    system = _load_system(slug)
    try:
        action = ActionType(req.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown action type: {req.action}")

    entry = ActionLogEntry(
        id=str(uuid.uuid4()),
        action=action,
        target=ActionTarget(type=req.target_type, id=req.target_id),
        view_context=req.view_context,
        payload=req.payload,
    )
    updated_log = list(system.log) + [entry]
    system = system.model_copy(update={
        "log": updated_log,
        "updated_at": datetime.now(timezone.utc),
    })
    _save_system(system, slug)
    return {"entry_id": entry.id}


@router.post("/systems/{slug}/sync/ontology-to-view")
async def sync_ontology_to_view(slug: str, req: SyncViewRequest):
    """Re-derive a view's DIR from the current ontology."""
    from datetime import datetime, timezone

    system = _load_system(slug)
    views = list(system.views)
    idx = next((i for i, v in enumerate(views) if v.id == req.view_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"View '{req.view_id}' not found")

    view = views[idx]
    now = datetime.now(timezone.utc)
    new_dir = ontology_to_dir(
        system.ontology,
        title=view.name,
        scope=view.scope,
        diagram_type=DiagramType.ARCHITECTURE,
    )
    views[idx] = view.model_copy(update={"dir": new_dir, "updated_at": now})
    system = system.model_copy(update={"views": views, "updated_at": now})
    _save_system(system, slug)

    svg = renderer.render(new_dir)
    return {"svg": svg, "dir": json.loads(new_dir.model_dump_json())}
