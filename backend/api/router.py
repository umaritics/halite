"""
Centralized route registration and explicit public/authenticated allowlist.

Shared by `main.py` and `tests/conftest.py` so production and test apps always
enforce the exact same authentication boundary:

  - Public (no API key):
      GET /health
      GET /api/health
      GET /api/ops/version
  - Webhook boundary (dedicated HMAC / retirement policy, never unsigned):
      POST /api/webhook/gitea  (410 Gone unless ENABLE_GITEA_INTEGRATION=true)
  - Authenticated (`/api/*` parent router with `Depends(require_halite_api_key)`):
      All other `/api/*` routes (maintenance, diagnostics, graph, chat,
      decisions, ingest, alerts, domains, ops/logs).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI

from api.routes import alerts, chat, decisions, graph, ingest, webhooks
from api.routes.diagnostics import router as diagnostics_router
from api.routes.maintenance import domains_router, router as maintenance_router
from api.routes.ops import public_router as ops_public_router, router as ops_router
from api.security import require_halite_api_key


def register_api_routers(app: FastAPI) -> None:
    """Mount public metadata, webhook boundary, and authenticated `/api/*` routers."""
    # 1. Explicit public build-metadata route (/api/ops/version)
    app.include_router(ops_public_router, prefix="/api")

    # 2. Webhook boundary (self-authenticating via HMAC or 410 Gone)
    app.include_router(webhooks.router, prefix="/api")

    # 3. Authenticated application surface — every route mounted here inherits
    #    `require_halite_api_key` automatically.
    protected_api = APIRouter(
        prefix="/api",
        dependencies=[Depends(require_halite_api_key)],
    )
    protected_api.include_router(chat.router)
    protected_api.include_router(decisions.router)
    protected_api.include_router(graph.router)
    protected_api.include_router(ingest.router)
    protected_api.include_router(alerts.router)
    protected_api.include_router(maintenance_router)
    protected_api.include_router(diagnostics_router)
    protected_api.include_router(domains_router)
    protected_api.include_router(ops_router)

    app.include_router(protected_api)
