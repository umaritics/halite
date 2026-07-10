import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from agents.gitea_agent import GiteaAgent
from api.deps import get_graph_repo, get_groq_service, get_settings

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/gitea")
async def gitea_webhook(
    request: Request,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
    x_gitea_signature: str | None = Header(None),
):
    body = await request.body()
    if settings.GITEA_WEBHOOK_SECRET and x_gitea_signature:
        expected = hmac.new(
            settings.GITEA_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, x_gitea_signature):
            raise HTTPException(401, "Invalid webhook signature")

    payload = await request.json()
    event_type = request.headers.get("X-Gitea-Event", "")
    agent = GiteaAgent(
        graph_repo,
        groq_service,
        settings.GITEA_BASE_URL,
        settings.GITEA_TOKEN,
    )
    return agent.process_webhook(event_type, payload)
