"""
Centralized route registration and explicit public/authenticated allowlist.

Shared by `main.py` and `tests/conftest.py` so production and test apps always
enforce the exact same authentication & RBAC boundary:

  - Public (no token, rate-limited):
      GET  /health
      GET  /api/health
      GET  /api/ops/version
  - Public authentication handshake (rate-limited + lockout-protected):
      POST /api/auth/login
      POST /api/auth/refresh
      POST /api/auth/logout
      GET  /api/auth/invites/verify
      POST /api/auth/invites/accept
  - Webhook boundary (dedicated HMAC / retirement policy, never unsigned):
      POST /api/webhook/gitea  (410 Gone unless ENABLE_GITEA_INTEGRATION=true)
  - Authenticated (`/api/*` parent router with `Depends(require_halite_api_key)`):
      All other `/api/*` routes (`auth/me`, `auth/password`, `admin/*`, `maintenance/*`,
      `diagnostics/*`, `graph/*`, `chat`, `decisions/*`, `ingest/*`, `alerts/*`, `domains`, `ops/logs`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI

from api.routes import alerts, chat, decisions, graph, ingest, webhooks
# --- Vertical registration points (backend preparation) ---
from api.routes import evaluation, integrity, retrieval, sessions
from api.routes.auth import admin_router, protected_auth_router, public_auth_router
from api.routes.diagnostics import router as diagnostics_router
from api.routes.maintenance import domains_router, router as maintenance_router
from api.routes.ops import public_router as ops_public_router, router as ops_router
from api.security import require_halite_api_key


def register_api_routers(app: FastAPI) -> None:
    """Mount public metadata, auth handshake, webhook boundary, and authenticated `/api/*` routers."""
    # 1. Explicit public build-metadata route (/api/ops/version)
    app.include_router(ops_public_router, prefix="/api")

    # 2. Public authentication handshake routes (/api/auth/login, /refresh, /logout, /invites/*)
    app.include_router(public_auth_router, prefix="/api")

    # 3. Webhook boundary (self-authenticating via HMAC or 410 Gone)
    app.include_router(webhooks.router, prefix="/api")

    # 4. Authenticated application surface — every route mounted here inherits
    #    `require_halite_api_key` (User JWT, server HALITE_API_KEY, or OPS_TOKEN).
    protected_api = APIRouter(
        prefix="/api",
        dependencies=[Depends(require_halite_api_key)],
    )
    protected_api.include_router(protected_auth_router)
    protected_api.include_router(admin_router)
    protected_api.include_router(chat.router)
    protected_api.include_router(decisions.router)
    protected_api.include_router(graph.router)
    protected_api.include_router(ingest.router)
    protected_api.include_router(alerts.router)
    protected_api.include_router(maintenance_router)
    protected_api.include_router(diagnostics_router)
    protected_api.include_router(domains_router)
    protected_api.include_router(ops_router)

    # --- Vertical registration points (backend preparation) ---
    for vertical in (retrieval, evaluation, integrity, sessions):
        protected_api.include_router(vertical.router)

    app.include_router(protected_api)
