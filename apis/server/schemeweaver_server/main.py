"""Scheme Weaver FastAPI server."""
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routes import generate, health, library, systems

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
# Quieten noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

log = logging.getLogger("schemeweaver")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Scheme Weaver API",
    description="AI-powered SVG diagram generation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    log.info("[%s] %s %s  %.0fms", response.status_code, request.method, request.url.path, ms)
    return response


app.include_router(health.router)
app.include_router(generate.router, prefix="/v1")
app.include_router(library.router, prefix="/v1")
app.include_router(systems.router, prefix="/v1")
