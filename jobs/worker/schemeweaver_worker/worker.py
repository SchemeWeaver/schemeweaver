"""ARQ worker entry point."""
from arq.connections import RedisSettings
from schemeweaver_core.pipeline import Pipeline
from schemeweaver_core.renderer import Renderer
from schemeweaver_svgkit.postprocess import PostProcessor

from .config import settings
from .tasks import generate_diagram, refine_diagram


async def startup(ctx: dict) -> None:
    ctx["pipeline"] = Pipeline(api_key=settings.anthropic_api_key, model=settings.model)
    ctx["renderer"] = Renderer()
    ctx["postprocessor"] = PostProcessor()


async def shutdown(ctx: dict) -> None:
    pass


class WorkerSettings:
    functions = [generate_diagram, refine_diagram]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 120
