"""Generate endpoint — sync and async modes."""
import asyncio
import json
import logging
import urllib.request
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

log = logging.getLogger("schemeweaver.generate")

from schemeweaver_core.exporters import MermaidExporter
from schemeweaver_core.models.dir import ComplexityLevel
from schemeweaver_core.pipeline import Pipeline
from schemeweaver_core.providers import make_provider
from schemeweaver_core.renderer import Renderer
from schemeweaver_svgkit.postprocess import PostProcessor

from ..config import settings

router = APIRouter()
renderer = Renderer()
postprocessor = PostProcessor()
mermaid_exporter = MermaidExporter()

# Load the model registry once at startup
_REGISTRY: list[dict] = json.loads(settings.models_registry.read_text(encoding="utf-8"))

# Static model → provider mapping (excludes dynamic Ollama entries)
_STATIC_MODEL_PROVIDER: dict[str, str] = {
    entry["id"]: entry["provider"]
    for entry in _REGISTRY
    if "id" in entry
}

_HAS_OLLAMA_ENTRY = any(entry.get("dynamic") for entry in _REGISTRY)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fetch_ollama_models() -> tuple[bool, list[str]]:
    """Query the local Ollama daemon. Returns (reachable, model_ids)."""
    try:
        url = f"{settings.ollama_base_url}/api/tags"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read())
        return True, [m["name"] for m in data.get("models", [])]
    except Exception:
        return False, []


def _provider_for(model_id: str) -> str:
    """Return the provider name for a model ID.

    Static models are looked up from the registry.
    Anything not in the static registry is assumed to be an Ollama model.
    """
    if model_id in _STATIC_MODEL_PROVIDER:
        return _STATIC_MODEL_PROVIDER[model_id]
    if _HAS_OLLAMA_ENTRY:
        return "ollama"
    raise ValueError(f"Unknown model '{model_id}' — not in registry and no Ollama entry")


def _build_pipeline(model_id: str) -> Pipeline:
    provider_name = _provider_for(model_id)
    if provider_name == "anthropic":
        api_key, base_url = settings.anthropic_api_key, None
    elif provider_name == "openai":
        api_key, base_url = settings.openai_api_key, None
    else:  # ollama
        api_key, base_url = "ollama", f"{settings.ollama_base_url}/v1"
    return Pipeline(make_provider(provider=provider_name, model=model_id, api_key=api_key, base_url=base_url))


def _build_model_list() -> list["ModelInfo"]:
    """Build the full model list from registry + live Ollama discovery."""
    anthropic_ok = bool(settings.anthropic_api_key)
    openai_ok = bool(settings.openai_api_key)
    ollama_ok, ollama_ids = _fetch_ollama_models() if _HAS_OLLAMA_ENTRY else (False, [])

    results: list[ModelInfo] = []
    for entry in _REGISTRY:
        if entry.get("dynamic"):
            # Expand into concrete Ollama models
            for mid in ollama_ids:
                results.append(ModelInfo(id=mid, provider="ollama", accessible=ollama_ok))
        else:
            prov = entry["provider"]
            acc = (
                anthropic_ok if prov == "anthropic" else
                openai_ok   if prov == "openai"    else
                False
            )
            results.append(ModelInfo(id=entry["id"], provider=prov, accessible=acc))
    return results


def _default_model(models: list["ModelInfo"]) -> str:
    """Return the ID of the first accessible model in registry order."""
    first = next((m.id for m in models if m.accessible), None)
    if first is None:
        raise ValueError("No accessible model found. Add an API key or start Ollama.")
    return first


# ── Pydantic models ────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    complexity: Optional[ComplexityLevel] = None
    model: Optional[str] = None


class GenerateResponse(BaseModel):
    svg: str
    dir: dict
    mermaid: str = ""
    issues: list[str] = []
    model: str = ""


class UpdateRequest(BaseModel):
    dir: dict
    feedback: str
    complexity: Optional[ComplexityLevel] = None
    model: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    provider: str
    accessible: bool


class ModelsResponse(BaseModel):
    default: str
    models: list[ModelInfo]


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """Return all registry models with live accessibility status."""
    models = await asyncio.get_event_loop().run_in_executor(None, _build_model_list)
    return ModelsResponse(default=_default_model(models), models=models)


def _resolve_model_id(requested: str | None, models: list[ModelInfo]) -> str:
    model_id = requested or _default_model(models)
    entry = next((m for m in models if m.id == model_id), None)
    if entry and not entry.accessible:
        raise HTTPException(status_code=400, detail=f"Model '{model_id}' is not accessible — missing API key or provider unavailable")
    return model_id


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    loop = asyncio.get_event_loop()
    models = await loop.run_in_executor(None, _build_model_list)
    model_id = _resolve_model_id(req.model, models)
    log.info("generate  model=%s  prompt=%r", model_id, req.prompt[:80])
    try:
        pipeline = _build_pipeline(model_id)
        dir_result = await loop.run_in_executor(None, pipeline.generate, req.prompt, req.context)
        svg = renderer.render(dir_result, active_complexity=req.complexity)
        svg = postprocessor.process(svg)
        issues = postprocessor.validate(svg)
        if issues:
            log.warning("generate  model=%s  validation issues: %s", model_id, issues)
        log.info("generate  model=%s  OK  nodes=%d edges=%d", model_id, len(dir_result.nodes), len(dir_result.edges))
        return GenerateResponse(
            svg=svg,
            dir=dir_result.model_dump(),
            mermaid=mermaid_exporter.serialize(dir_result),
            issues=issues,
            model=model_id,
        )
    except ValidationError as exc:
        log.error("generate  model=%s  DIR validation failed:\n%s", model_id, exc)
        raise HTTPException(status_code=422, detail=f"Model returned an invalid diagram structure: {exc.error_count()} field error(s). Check server logs.")
    except Exception:
        log.exception("generate  model=%s  unexpected error", model_id)
        raise HTTPException(status_code=500, detail="Diagram generation failed — see server logs for details")


@router.post("/update", response_model=GenerateResponse)
async def update(req: UpdateRequest):
    from schemeweaver_core.models.dir import DIR

    loop = asyncio.get_event_loop()
    models = await loop.run_in_executor(None, _build_model_list)
    model_id = _resolve_model_id(req.model, models)
    log.info("update  model=%s  feedback=%r", model_id, req.feedback[:80])
    try:
        pipeline = _build_pipeline(model_id)
        current_dir = DIR.model_validate(req.dir)
        updated_dir = await loop.run_in_executor(None, pipeline.refine, current_dir, req.feedback)
        svg = renderer.render(updated_dir, active_complexity=req.complexity)
        svg = postprocessor.process(svg)
        issues = postprocessor.validate(svg)
        if issues:
            log.warning("update  model=%s  validation issues: %s", model_id, issues)
        log.info("update  model=%s  OK  nodes=%d edges=%d", model_id, len(updated_dir.nodes), len(updated_dir.edges))
        return GenerateResponse(
            svg=svg,
            dir=updated_dir.model_dump(),
            mermaid=mermaid_exporter.serialize(updated_dir),
            issues=issues,
            model=model_id,
        )
    except ValidationError as exc:
        log.error("update  model=%s  DIR validation failed:\n%s", model_id, exc)
        raise HTTPException(status_code=422, detail=f"Model returned an invalid diagram structure: {exc.error_count()} field error(s). Check server logs.")
    except Exception:
        log.exception("update  model=%s  unexpected error", model_id)
        raise HTTPException(status_code=500, detail="Diagram update failed — see server logs for details")
