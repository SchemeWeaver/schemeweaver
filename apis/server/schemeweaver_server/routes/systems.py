"""Systems endpoints — full System CRUD + AI generation."""
import asyncio
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from schemeweaver_core.models import (
    # Domain models
    DiagramType,
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
    # API DTOs
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


@router.post("/systems/migrate-library")
def migrate_library():
    """Wrap all diagrams in data/out/ as Systems in data/systems/.

    Each existing diagram becomes a System with a single 'Overview' view.
    Already-migrated slugs are skipped.
    """
    import uuid
    from datetime import datetime, timezone
    from schemeweaver_core.models.dir import DIR
    from schemeweaver_core.models.system import (
        DiagramType as SystemDiagramType,
        Ontology as SysOntology,
    )

    out_dir = settings.data_out_dir
    if not out_dir.exists():
        return {"migrated": [], "skipped": []}

    migrated: list[str] = []
    skipped:  list[str] = []

    for slug_dir in sorted(out_dir.iterdir(), key=lambda p: p.stat().st_mtime):
        if not slug_dir.is_dir():
            continue
        dir_path     = slug_dir / "diagram.dir.json"
        summary_path = slug_dir / "summary.json"
        if not dir_path.exists():
            continue

        slug = slug_dir.name
        if (_systems_dir() / slug).exists():
            skipped.append(slug)
            continue

        try:
            dir_data = DIR.model_validate_json(dir_path.read_text(encoding="utf-8"))
            summary  = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
            title    = dir_data.meta.title or slug
            now      = datetime.now(timezone.utc)
            view = View(
                id="view-overview",
                name="Overview",
                description="Migrated from library",
                diagram_type=SystemDiagramType.ARCHITECTURE,
                scope=ViewScope(),
                dir=dir_data,
                created_at=now,
                updated_at=now,
            )
            system = System(
                id=str(uuid.uuid4()),
                slug=slug,
                name=title,
                prose=f"Migrated diagram: {title}",
                ontology=SysOntology(),
                views=[view],
                log=[],
                created_at=now,
                updated_at=now,
            )
            _save_system(system, slug)
            migrated.append(slug)
        except Exception as exc:
            log.warning("migrate_library  slug=%s  error=%s", slug, exc)
            skipped.append(slug)

    log.info("migrate_library  migrated=%d skipped=%d", len(migrated), len(skipped))
    return {"migrated": migrated, "skipped": skipped}


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


@router.post("/systems/from-repo", response_model=GenerateSystemResponse)
async def generate_system_from_repo(req: FromRepoRequest):
    """Analyze a repo (or use a pre-compiled KB) and generate a System.

    Two-step flow:
      1. Call POST /repos/analyze → get knowledge_base markdown, review/edit it
      2. Call this endpoint with the (modified) knowledge_base to generate the System

    Single-step flow:
      Pass only `source` — the server will analyze + generate in one call.
    """
    import asyncio
    from schemeweaver_core.repo_analyzer import RepoAnalyzer

    log.info("generate_system_from_repo  source=%r", req.source[:120])

    # Compile or use provided KB
    kb_markdown = req.knowledge_base
    if not kb_markdown:
        try:
            kb = RepoAnalyzer().analyze(req.source)
            kb_markdown = kb.to_markdown()
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            log.exception("generate_system_from_repo  analysis error")
            raise HTTPException(status_code=500, detail="Repo analysis failed — see server logs")

    # Generate System from KB
    loop = asyncio.get_event_loop()
    try:
        pipeline = _build_pipeline(req.model)
        system = await loop.run_in_executor(None, pipeline.generate_from_kb, kb_markdown)
    except HTTPException:
        raise
    except Exception:
        log.exception("generate_system_from_repo  generation error")
        raise HTTPException(status_code=500, detail="System generation failed — see server logs")

    slug = _unique_slug(_slugify(system.name))
    system = system.model_copy(update={"slug": slug})
    _save_system(system, slug)

    # Save knowledge_base.md alongside system.json
    kb_path = _system_path(slug) / "knowledge_base.md"
    kb_path.write_text(kb_markdown, encoding="utf-8")
    log.info("generate_system_from_repo  slug=%s  entities=%d", slug, len(system.ontology.entities))

    return GenerateSystemResponse(slug=slug, system=json.loads(system.model_dump_json()))


@router.post("/systems/{slug}/sync/kb-to-ontology")
async def sync_kb_to_ontology(slug: str, req: SyncModelRequest):
    """Re-derive the ontology from the saved knowledge_base.md (AI).

    Loads knowledge_base.md for the system and re-runs the KB pipeline.
    Returns a proposed ontology without saving — caller decides to apply
    (same pattern as prose-to-ontology).
    """
    import asyncio

    system = _load_system(slug)
    kb_path = _system_path(slug) / "knowledge_base.md"
    if not kb_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No knowledge_base.md found for system '{slug}'. "
                   "Import the system via POST /systems/from-repo to create one.",
        )

    kb_markdown = kb_path.read_text(encoding="utf-8")

    loop = asyncio.get_event_loop()
    try:
        pipeline = _build_pipeline(req.model)
        new_system = await loop.run_in_executor(None, pipeline.generate_from_kb, kb_markdown)
    except HTTPException:
        raise
    except Exception:
        log.exception("sync_kb_to_ontology  slug=%s", slug)
        raise HTTPException(status_code=500, detail="Sync failed — see server logs")

    return {"ontology": json.loads(new_system.ontology.model_dump_json())}


@router.get("/systems/{slug}/knowledge-base")
def get_knowledge_base(slug: str):
    """Return the saved knowledge_base.md for a system, if it exists."""
    _load_system(slug)  # validate slug exists
    kb_path = _system_path(slug) / "knowledge_base.md"
    if not kb_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No knowledge_base.md found for system '{slug}'.",
        )
    return {"knowledge_base": kb_path.read_text(encoding="utf-8")}


@router.put("/systems/{slug}/knowledge-base")
def update_knowledge_base(slug: str, body: dict):
    """Save an updated knowledge_base.md for a system."""
    _load_system(slug)  # validate slug exists
    kb_markdown = body.get("knowledge_base", "")
    kb_path = _system_path(slug) / "knowledge_base.md"
    kb_path.write_text(kb_markdown, encoding="utf-8")
    return {"ok": True}


@router.post("/systems/{slug}/sync/view-to-prose")
async def sync_view_to_prose(slug: str, req: SyncViewRequest):
    """Generate prose from the active view's DIR (AI)."""
    import asyncio

    system = _load_system(slug)
    if not any(v.id == req.view_id for v in system.views):
        raise HTTPException(status_code=404, detail=f"View '{req.view_id}' not found")

    loop = asyncio.get_event_loop()
    try:
        pipeline = _build_pipeline(req.model)
        new_prose = await loop.run_in_executor(None, pipeline.view_to_prose, system, req.view_id)
    except HTTPException:
        raise
    except Exception:
        log.exception("sync_view_to_prose  slug=%s  view=%s", slug, req.view_id)
        raise HTTPException(status_code=500, detail="Sync failed — see server logs")

    return {"prose": new_prose}


@router.post("/systems/{slug}/sync/ontology-to-prose")
async def sync_ontology_to_prose(slug: str, req: SyncModelRequest):
    """Generate new prose from the current ontology (AI)."""
    from datetime import datetime, timezone
    import asyncio

    system = _load_system(slug)
    loop = asyncio.get_event_loop()
    try:
        pipeline = _build_pipeline(req.model)
        new_prose = await loop.run_in_executor(None, pipeline.ontology_to_prose, system)
    except HTTPException:
        raise
    except Exception:
        log.exception("sync_ontology_to_prose  slug=%s", slug)
        raise HTTPException(status_code=500, detail="Sync failed — see server logs")

    # Return the proposed prose without saving (caller decides to apply)
    return {"prose": new_prose}


@router.post("/systems/{slug}/sync/prose-to-ontology")
async def sync_prose_to_ontology(slug: str, req: SyncModelRequest):
    """Derive a new ontology from the current prose (AI)."""
    import asyncio

    system = _load_system(slug)
    loop = asyncio.get_event_loop()
    try:
        pipeline = _build_pipeline(req.model)
        new_ontology = await loop.run_in_executor(None, pipeline.prose_to_ontology, system)
    except HTTPException:
        raise
    except Exception:
        log.exception("sync_prose_to_ontology  slug=%s", slug)
        raise HTTPException(status_code=500, detail="Sync failed — see server logs")

    # Return the proposed ontology without saving (caller decides to apply)
    return {"ontology": json.loads(new_ontology.model_dump_json())}


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


# ── Icon enrichment ────────────────────────────────────────────────────────────

# Ordered list of (keyword, simple-icons slug) pairs.
# Matched case-insensitively against entity name + description.
# More-specific entries must come before broader ones.
_TECH_HINTS: list[tuple[str, str]] = [
    # Databases
    ("postgresql", "postgresql"), ("postgres", "postgresql"),
    ("mysql", "mysql"), ("mariadb", "mariadb"),
    ("mongodb", "mongodb"), ("mongo", "mongodb"),
    ("redis", "redis"),
    ("elasticsearch", "elasticsearch"), ("elastic", "elasticsearch"),
    ("cassandra", "apachecassandra"),
    ("dynamodb", "amazondynamodb"),
    ("sqlite", "sqlite"),
    ("cockroachdb", "cockroachlabs"),
    ("neo4j", "neo4j"),
    ("influxdb", "influxdb"),
    ("clickhouse", "clickhouse"),
    ("supabase", "supabase"),
    ("planetscale", "planetscale"),
    # Queues / streams
    ("kafka", "apachekafka"),
    ("rabbitmq", "rabbitmq"),
    ("nats", "nats"),
    ("sqs", "amazonsqs"),
    ("pubsub", "googlepubsub"),
    ("celery", "celery"),
    # Web / API frameworks
    ("fastapi", "fastapi"), ("fast api", "fastapi"),
    ("django", "django"),
    ("flask", "flask"),
    ("spring boot", "spring"), ("spring", "spring"),
    ("express", "express"),
    ("nestjs", "nestjs"), ("nest.js", "nestjs"),
    ("rails", "rubyonrails"),
    ("laravel", "laravel"),
    ("gin", "go"),
    ("fiber", "go"),
    ("actix", "rust"),
    ("axum", "rust"),
    # Infrastructure / platform
    ("nginx", "nginx"),
    ("apache", "apache"),
    ("caddy", "caddy"),
    ("traefik", "traefikproxy"),
    ("docker", "docker"),
    ("kubernetes", "kubernetes"), ("k8s", "kubernetes"),
    ("helm", "helm"),
    ("terraform", "terraform"),
    ("ansible", "ansible"),
    ("vault", "vault"),
    ("consul", "consul"),
    # Observability
    ("prometheus", "prometheus"),
    ("grafana", "grafana"),
    ("loki", "grafana"),
    ("jaeger", "jaeger"),
    ("datadog", "datadog"),
    ("newrelic", "newrelic"), ("new relic", "newrelic"),
    ("sentry", "sentry"),
    ("opentelemetry", "opentelemetry"),
    # Auth
    ("keycloak", "keycloak"),
    ("auth0", "auth0"),
    ("okta", "okta"),
    ("cognito", "amazoncognito"),
    # Storage / CDN
    ("s3", "amazons3"),
    ("minio", "minio"),
    ("cloudflare", "cloudflare"),
    # Cloud vendors (broad — match last)
    ("lambda", "awslambda"),
    ("fargate", "amazonecs"),
    ("rds", "amazonrds"),
]


def _infer_technology(name: str, description: str | None) -> str | None:
    """Return a simple-icons slug inferred from entity name/description, or None."""
    haystack = (name + " " + (description or "")).lower()
    for keyword, slug in _TECH_HINTS:
        if keyword in haystack:
            return slug
    return None


@router.post("/systems/{slug}/enrich-icons")
def enrich_icons(slug: str):
    """Backfill technology slugs on all ontology entities using name/description heuristics.

    Entities that already have a technology set are left unchanged.
    After enrichment, all views are re-synced from the updated ontology.
    Returns counts of entities enriched and views re-synced.
    """
    from datetime import datetime, timezone

    system = _load_system(slug)
    now = datetime.now(timezone.utc)

    enriched_ids: list[str] = []
    updated_entities = []
    for entity in system.ontology.entities:
        if entity.technology:
            updated_entities.append(entity)
            continue
        slug_guess = _infer_technology(entity.name, entity.description)
        if slug_guess:
            updated_entities.append(entity.model_copy(update={"technology": slug_guess}))
            enriched_ids.append(entity.id)
        else:
            updated_entities.append(entity)

    updated_ontology = system.ontology.model_copy(update={"entities": updated_entities})

    # Re-sync every view from the updated ontology
    updated_views = []
    for view in system.views:
        new_dir = ontology_to_dir(
            updated_ontology,
            title=view.name,
            scope=view.scope,
            diagram_type=DiagramType.ARCHITECTURE,
        )
        updated_views.append(view.model_copy(update={"dir": new_dir, "updated_at": now}))

    system = system.model_copy(update={
        "ontology": updated_ontology,
        "views": updated_views,
        "updated_at": now,
    })
    _save_system(system, slug)

    log.info("enrich_icons  slug=%s  enriched=%d  views=%d", slug, len(enriched_ids), len(updated_views))
    return {
        "enriched": len(enriched_ids),
        "enriched_ids": enriched_ids,
        "views_resynced": len(updated_views),
    }


