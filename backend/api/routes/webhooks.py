import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from agents.gitea_agent import GiteaAgent
from api.deps import get_graph_repo, get_groq_service, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/gitea")
async def gitea_webhook(
    request: Request,
    graph_repo=Depends(get_graph_repo),
    groq_service=Depends(get_groq_service),
    settings=Depends(get_settings),
    x_gitea_signature: str | None = Header(None),
):
    """
    Gitea webhook receiver — disabled (410 Gone) by default after Gitea was
    decommissioned on the shared VM.

    Even if explicitly re-enabled via `ENABLE_GITEA_INTEGRATION=true`, fails
    closed (503) unless `GITEA_WEBHOOK_SECRET` is configured and HMAC-SHA256
    signature verification succeeds. Unsigned webhook ingest is never allowed.
    """
    if not getattr(settings, "ENABLE_GITEA_INTEGRATION", False):
        logger.warning("Rejected call to retired /api/webhook/gitea endpoint")
        raise HTTPException(
            status_code=410,
            detail="Gitea webhook integration has been retired on this deployment.",
        )

    secret = (getattr(settings, "GITEA_WEBHOOK_SECRET", None) or "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="GITEA_WEBHOOK_SECRET must be configured when Gitea integration is enabled.",
        )

    if not x_gitea_signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    body = await request.body()
    supplied_sig = x_gitea_signature.strip()
    if supplied_sig.lower().startswith("sha256="):
        supplied_sig = supplied_sig[7:].strip()

    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, supplied_sig):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    event_type = request.headers.get("X-Gitea-Event", "")
    agent = GiteaAgent(
        graph_repo,
        groq_service,
        settings.GITEA_BASE_URL,
        settings.GITEA_TOKEN,
    )
    return agent.process_webhook(event_type, payload)
