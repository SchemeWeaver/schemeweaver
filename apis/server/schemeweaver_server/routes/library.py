"""Library endpoints — browse and load diagrams saved to data/out/."""
import json
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _unique_slug(base: str, out: "Path") -> str:  # type: ignore[name-defined]
    """Return base slug if unused, otherwise base-2, base-3, …"""
    if not (out / base).exists():
        return base
    i = 2
    while (out / f"{base}-{i}").exists():
        i += 1
    return f"{base}-{i}"


class DiagramSummary(BaseModel):
    slug: str
    title: str
    diagram_type: str
    nodes: int
    edges: int
    groups: int
    elapsed_s: float
    issues: list[str] = []
    model: str = ""


class DiagramEntry(BaseModel):
    svg: str
    dir: dict
    mermaid: str = ""
    issues: list[str] = []
    model: str = ""


class SaveRequest(BaseModel):
    dir: dict
    svg: str
    mermaid: str = ""
    issues: list[str] = []
    model: str = ""
    slug: Optional[str] = None  # provided → overwrite, omitted → new


class SaveResponse(BaseModel):
    slug: str


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
                model=data.get("model", ""),
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

    summary_data = {}
    summary_path = slug_dir / "summary.json"
    if summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return DiagramEntry(
        svg=svg_path.read_text(encoding="utf-8"),
        dir=json.loads(dir_path.read_text(encoding="utf-8")),
        mermaid=mmd_path.read_text(encoding="utf-8") if mmd_path.exists() else "",
        model=summary_data.get("model", ""),
    )


@router.post("/library", response_model=SaveResponse)
def save_diagram(req: SaveRequest):
    """Save or overwrite a diagram in data/out/."""
    out = _out_dir()

    # Determine slug
    if req.slug:
        slug_dir = (out / req.slug).resolve()
        if not str(slug_dir).startswith(str(out.resolve())):
            raise HTTPException(status_code=400, detail="Invalid slug")
        slug = req.slug
    else:
        title = req.dir.get("meta", {}).get("title", "diagram")
        slug = _unique_slug(_slugify(title), out)
        slug_dir = out / slug

    slug_dir.mkdir(parents=True, exist_ok=True)

    (slug_dir / "diagram.svg").write_text(req.svg, encoding="utf-8")
    (slug_dir / "diagram.dir.json").write_text(
        json.dumps(req.dir, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if req.mermaid:
        (slug_dir / "diagram.mmd").write_text(req.mermaid, encoding="utf-8")

    meta = req.dir.get("meta", {})
    summary = {
        "slug": slug,
        "title": meta.get("title", slug),
        "diagram_type": meta.get("diagram_type", "generic"),
        "nodes": len(req.dir.get("nodes", [])),
        "edges": len(req.dir.get("edges", [])),
        "groups": len(req.dir.get("groups", [])),
        "elapsed_s": 0.0,
        "issues": req.issues,
        "model": req.model,
    }
    (slug_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return SaveResponse(slug=slug)
