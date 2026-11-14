import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from agents.code_agent import CodeAgent
from agents.document_agent import DocumentAgent
from agents.gitea_agent import GiteaAgent
from api.deps import get_graph_repo, get_groq_service, get_settings
from api.security import require_llm_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


class GiteaIngestRequest(BaseModel):
    owner: str
    repo: str


def _require_gitea_enabled(settings) -> None:
    if not getattr(settings, "ENABLE_GITEA_INTEGRATION", False):
        logger.warning("Rejected call to retired Gitea ingest endpoint")
        raise HTTPException(
            status_code=410,
            detail="Gitea repository ingestion has been retired on this deployment.",
        )


@router.post("/document", dependencies=[Depends(require_llm_rate_limit)])
async def ingest_document(
    file: UploadFile = File(...),
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
):
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")

    agent = DocumentAgent(graph_repo, groq_service)
    return agent.run({"filename": file.filename, "content": content})


@router.post("/gitea")
def ingest_gitea(
    body: GiteaIngestRequest,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
):
    _require_gitea_enabled(settings)
    agent = GiteaAgent(
        graph_repo,
        groq_service,
        settings.GITEA_BASE_URL,
        settings.GITEA_TOKEN,
    )
    return agent.run(body.model_dump())


@router.post("/code", dependencies=[Depends(require_llm_rate_limit)])
def ingest_code(
    body: GiteaIngestRequest,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
):
    _require_gitea_enabled(settings)
    agent = CodeAgent(graph_repo, groq_service)
    agent.gitea_base_url = settings.GITEA_BASE_URL
    agent.gitea_token = settings.GITEA_TOKEN
    return agent.run(body.model_dump())
