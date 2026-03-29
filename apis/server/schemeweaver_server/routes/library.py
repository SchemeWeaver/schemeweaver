"""Library endpoints — browse and load diagrams saved to data/out/."""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter()


class DiagramSummary(BaseModel):
    slug: str
    title: str
    diagram_type: str
    nodes: int
    edges: int
    groups: int
    elapsed_s: float
    issues: list[str] = []


class DiagramEntry(BaseModel):
    svg: str
    dir: dict
    mermaid: str = ""
    issues: list[str] = []


def _out_dir():
    return settings.data_out_dir


@router.get("/library", response_model=list[DiagramSummary])
def list_diagrams():
    """List all diagrams saved in data/out/, newest first."""
    out = _out_dir()
    if not out.exists():
        return []

    results: list[DiagramSummary] = []
    for slug_dir in sorted(out.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not slug_dir.is_dir():
            continue
        summary_path = slug_dir / "summary.json"
        if not summary_path.exists():
            continue
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            results.append(DiagramSummary(
                slug=slug_dir.name,
                title=data.get("title", slug_dir.name),
                diagram_type=data.get("diagram_type", "generic"),
                nodes=data.get("nodes", 0),
                edges=data.get("edges", 0),
                groups=data.get("groups", 0),
                elapsed_s=data.get("elapsed_s", 0.0),
                issues=data.get("issues", []),
            ))
        except Exception:
            continue
    return results


@router.get("/library/{slug}", response_model=DiagramEntry)
def get_diagram(slug: str):
    """Load a saved diagram by slug."""
    # Basic path traversal guard
    slug_dir = (_out_dir() / slug).resolve()
    if not str(slug_dir).startswith(str(_out_dir().resolve())):
        raise HTTPException(status_code=400, detail="Invalid slug")
    if not slug_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Diagram '{slug}' not found")

    svg_path = slug_dir / "diagram.svg"
    dir_path = slug_dir / "diagram.dir.json"
    mmd_path = slug_dir / "diagram.mmd"

    if not svg_path.exists() or not dir_path.exists():
        raise HTTPException(status_code=404, detail=f"Diagram '{slug}' is incomplete")

    return DiagramEntry(
        svg=svg_path.read_text(encoding="utf-8"),
        dir=json.loads(dir_path.read_text(encoding="utf-8")),
        mermaid=mmd_path.read_text(encoding="utf-8") if mmd_path.exists() else "",
    )
