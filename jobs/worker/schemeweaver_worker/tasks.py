"""ARQ task definitions for async diagram generation."""
from schemeweaver_core.models.dir import ComplexityLevel
from schemeweaver_core.pipeline import Pipeline
from schemeweaver_core.renderer import Renderer
from schemeweaver_svgkit.postprocess import PostProcessor

from .config import settings


async def generate_diagram(
    ctx: dict,
    prompt: str,
    context: str | None = None,
    complexity: str | None = None,
) -> dict:
    """ARQ task: generate a diagram from a prompt."""
    pipeline: Pipeline = ctx["pipeline"]
    renderer: Renderer = ctx["renderer"]
    postprocessor: PostProcessor = ctx["postprocessor"]

    dir_result = pipeline.generate(prompt, context)

    active_complexity = ComplexityLevel(complexity) if complexity else None
    svg = renderer.render(dir_result, active_complexity=active_complexity)
    svg = postprocessor.process(svg)
    issues = postprocessor.validate(svg)

    return {
        "svg": svg,
        "dir": dir_result.model_dump(),
        "issues": issues,
    }


async def refine_diagram(
    ctx: dict,
    dir_data: dict,
    feedback: str,
    complexity: str | None = None,
) -> dict:
    """ARQ task: refine an existing diagram."""
    from schemeweaver_core.models.dir import DIR

    pipeline: Pipeline = ctx["pipeline"]
    renderer: Renderer = ctx["renderer"]
    postprocessor: PostProcessor = ctx["postprocessor"]

    current_dir = DIR.model_validate(dir_data)
    updated_dir = pipeline.refine(current_dir, feedback)

    active_complexity = ComplexityLevel(complexity) if complexity else None
    svg = renderer.render(updated_dir, active_complexity=active_complexity)
    svg = postprocessor.process(svg)

    return {
        "svg": svg,
        "dir": updated_dir.model_dump(),
        "issues": postprocessor.validate(svg),
    }
