"""Generate endpoint — sync and async modes."""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schemeweaver_core.models.dir import ComplexityLevel
from schemeweaver_core.pipeline import Pipeline
from schemeweaver_core.renderer import Renderer
from schemeweaver_svgkit.postprocess import PostProcessor

from ..config import settings

router = APIRouter()
pipeline = Pipeline(api_key=settings.anthropic_api_key, model=settings.model)
renderer = Renderer()
postprocessor = PostProcessor()


class GenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    complexity: Optional[ComplexityLevel] = None  # None = interactive SVG with all levels


class GenerateResponse(BaseModel):
    svg: str
    dir: dict
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
            issues=issues,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
