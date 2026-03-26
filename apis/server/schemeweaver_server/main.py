"""Scheme Weaver FastAPI server."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import generate, health

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

app.include_router(health.router)
app.include_router(generate.router, prefix="/v1")
