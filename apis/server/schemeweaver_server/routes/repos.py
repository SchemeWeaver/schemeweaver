"""Repos endpoints — analyze a local path or git URL to produce a Knowledge Base."""
import logging

from fastapi import APIRouter, HTTPException

from schemeweaver_core.models import AnalyzeRepoRequest, AnalyzeRepoResponse
from schemeweaver_core.repo_analyzer import RepoAnalyzer

log = logging.getLogger("schemeweaver.repos")
router = APIRouter()

_analyzer = RepoAnalyzer()



@router.post("/repos/analyze", response_model=AnalyzeRepoResponse)
def analyze_repo(req: AnalyzeRepoRequest):
    """Walk a local repo or clone a git URL and return a Knowledge Base markdown string.

    This is step 1 of the two-step import workflow. The caller reviews/edits the
    returned markdown, then calls POST /systems/from-repo with the (possibly modified)
    knowledge_base field to generate the System.
    """
    log.info("analyze_repo  source=%r", req.source[:120])
    try:
        kb = _analyzer.analyze(req.source)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        log.exception("analyze_repo  unexpected error")
        raise HTTPException(status_code=500, detail="Repo analysis failed — see server logs")

    return AnalyzeRepoResponse(
        repo_name=kb.repo_name,
        source=kb.source,
        knowledge_base=kb.to_markdown(),
    )
