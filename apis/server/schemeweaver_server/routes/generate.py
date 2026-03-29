"""Generate endpoint — sync and async modes."""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schemeweaver_core.exporters import MermaidExporter
from schemeweaver_core.models.dir import ComplexityLevel
from schemeweaver_core.pipeline import Pipeline
from schemeweaver_core.providers import make_provider
from schemeweaver_core.renderer import Renderer
from schemeweaver_svgkit.postprocess import PostProcessor

from ..config import settings

router = APIRouter()
_provider = make_provider(
    provider=settings.llm_provider,
    model=settings.llm_model,
    api_key=settings.anthropic_api_key or settings.openai_api_key,
    base_url=settings.llm_base_url,
)
pipeline = Pipeline(provider=_provider)
renderer = Renderer()
postprocessor = PostProcessor()
mermaid_exporter = MermaidExporter()


class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    complexity: Optional[ComplexityLevel] = None  # None = interactive SVG with all levels


class GenerateResponse(BaseModel):
    svg: str
    dir: dict
    mermaid: str = ""
    issues: list[str] = []


class UpdateRequest(BaseModel):
    dir: dict
    feedback: str
    complexity: Optional[ComplexityLevel] = None


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    try:
        loop = asyncio.get_event_loop()
        dir_result = await loop.run_in_executor(None, pipeline.generate, req.prompt, req.context)
        svg = renderer.render(dir_result, active_complexity=req.complexity)
        svg = postprocessor.process(svg)
        issues = postprocessor.validate(svg)
        return GenerateResponse(
            svg=svg,
            dir=dir_result.model_dump(),
            mermaid=mermaid_exporter.serialize(dir_result),
            issues=issues,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update", response_model=GenerateResponse)
async def update(req: UpdateRequest):
    try:
        from schemeweaver_core.models.dir import DIR

        current_dir = DIR.model_validate(req.dir)
        loop = asyncio.get_event_loop()
        updated_dir = await loop.run_in_executor(
            None, pipeline.refine, current_dir, req.feedback
        )
        svg = renderer.render(updated_dir, active_complexity=req.complexity)
        svg = postprocessor.process(svg)
        issues = postprocessor.validate(svg)
        return GenerateResponse(
            svg=svg,
            dir=updated_dir.model_dump(),
            mermaid=mermaid_exporter.serialize(updated_dir),
            issues=issues,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
